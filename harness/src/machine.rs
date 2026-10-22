// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 japes98
//! The emulated board around a raw image: boot, run, and the state fwtest
//! samples between runs.
//!
//! Boot follows the upstream CLI's raw-image path (`fm1-emu --bin`, read for
//! this, not vendored): the image is the XIP window's contents at
//! `XIP_BASE`, cpu0 starts at its first byte in user mode with r0 pointing at
//! a zeroed block near the top of RAM (whose first word points just past
//! it), 1 MiB of zeroed RAM. Unlike that path, the image is also written
//! into the flash chip at `XIP_FLASH_OFFSET`, where an installed app sits, so
//! SPI reads of the chip see it and the window and the chip agree.
//!
//! Running follows upstream's shared runner (`fm1_soc::machine`): cpu0 in
//! blocks with interrupts taken between them, cpu1 alongside once released
//! (`machine::run_dual`). `run_blocks` below is upstream's loop of the same
//! name with one addition: after each SoC service it notes the end of an
//! audio half-buffer, with cpu0's instruction count at that point.
//!
//! Determinism: no JIT (`jit_on` stays false on both cores), `skip_idle` on
//! (time jumps over `idle` and TIMER4 polling, so instruction counts measure
//! work, not waiting), and `main` clears every `FM1_*` environment variable
//! before anything is built, since several switch execution paths or traces.

use fm1_core::{Cpu, CoreError};
use fm1_soc::{machine, Soc, FLASH_SIZE, OVL_BASE, RAM_BASE, SRAM2_BASE, XIP_BASE, XIP_FLASH_OFFSET};

/// RAM given to the image, as upstream's raw-image default.
pub const RAM_SIZE: usize = 1 << 20;
/// The image fills the XIP window from its start; the window shows the flash
/// chip from XIP_FLASH_OFFSET, so an image can be at most this long.
pub const MAX_IMAGE: usize = FLASH_SIZE - XIP_FLASH_OFFSET;
/// cpu0 instructions per run call: the granularity of halt and fault checks,
/// captures, the watchdog and cpu1's per-block counts.
pub const SLICE: u32 = 1024;
/// Emulated cycles per millisecond (`fm1_soc::CPU_HZ`, one instruction per
/// cycle when nothing is skipped).
pub const CYCLES_PER_MS: u64 = fm1_soc::CPU_HZ / 1000;
/// Overlay RAM and the SRAM banks: sizes as `Soc::new` makes them.
const OVL_SIZE: u32 = 512 * 1024;
const SRAM2_SIZE: u32 = 256 * 1024;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Stop {
    /// The CPU could not go on: an instruction it can't decode or execute,
    /// or the pc outside every memory that can hold code.
    Fault { core: u32, pc: u32, what: String },
    /// cpu0 jumped to itself with interrupts disabled: a deliberate stop.
    Halt { pc: u32 },
}

/// One finished audio half-buffer: when, and the instructions each core had
/// retired by then (cpu0 exactly; cpu1 at the end of that run call).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Block {
    pub cycle: u64,
    pub core0: u64,
    pub core1: u64,
}

pub struct Board {
    pub soc: Soc,
    pub cpu0: Cpu,
    pub cpu1: Option<Cpu>,
    pending_tick: bool,
    image_len: u32,
    pub blocks: Vec<Block>,
    halves_seen: u64,
}

impl Board {
    pub fn boot(image: &[u8], flash: Option<&[u8]>) -> Result<Board, String> {
        if image.is_empty() {
            return Err("the image is empty".into());
        }
        if image.len() > MAX_IMAGE {
            return Err(format!("the image is {} bytes; at most {} fit", image.len(), MAX_IMAGE));
        }
        if let Some(f) = flash {
            if f.len() > FLASH_SIZE {
                return Err(format!("the flash file is {} bytes; the chip holds {}", f.len(), FLASH_SIZE));
            }
        }
        let mut soc = Soc::new(RAM_SIZE, image.to_vec());
        soc.periph.skip_idle = true;
        soc.xip_flash = true;
        if let Some(f) = flash {
            soc.flash.load(f);
        }
        soc.flash.mem[XIP_FLASH_OFFSET..XIP_FLASH_OFFSET + image.len()].copy_from_slice(image);
        let mut cpu0 = Cpu::new(XIP_BASE);
        cpu0.user = true;
        cpu0.jit_on = false;
        let params = RAM_BASE + 0x7fc00;
        fm1_core::Bus::write32(&mut soc, params, params + 0x40);
        cpu0.regs[0] = params;
        Ok(Board { soc, cpu0, cpu1: None, pending_tick: false, image_len: image.len() as u32, blocks: Vec::new(), halves_seen: 0 })
    }

    pub fn cycles(&self) -> u64 {
        self.soc.periph.cycles
    }

    pub fn instructions(&self) -> (u64, u64) {
        (self.cpu0.insn_count, self.cpu1.as_ref().map_or(0, |c| c.insn_count))
    }

    /// Run about `n` cpu0 instructions (fewer when time reaches `until`
    /// first is not checked here: callers bound `n`).
    pub fn run(&mut self, n: u32) -> Result<(), Stop> {
        let before = (self.cpu0.pc, self.cpu0.regs, self.cpu0.sp);
        let first_new = self.blocks.len();
        let Board { soc, cpu0, cpu1, pending_tick, blocks, halves_seen, .. } = self;
        let r = machine::run_dual(cpu1, soc, n, RAM_SIZE, false, |soc, k| {
            run_blocks(cpu0, soc, k, pending_tick, blocks, halves_seen)
        });
        let c1 = self.cpu1.as_ref().map_or(0, |c| c.insn_count);
        for b in &mut self.blocks[first_new..] {
            b.core1 = c1;
        }
        if let Err(e) = r {
            // cpu1's errors come back from upstream's runner as debug text: keep only the
            // kind (the clean side reads these messages)
            return Err(match self.cpu1.as_ref() {
                Some(c) if e.starts_with("cpu1:") => Stop::Fault {
                    core: 1,
                    pc: c.pc,
                    what: if e.contains("Decode") { "an instruction the emulated CPU cannot decode" } else { "an instruction the emulator does not implement" }.into(),
                },
                _ => Stop::Fault { core: 0, pc: self.cpu0.pc, what: e },
            });
        }
        for (core, pc) in [(0u32, Some(self.cpu0.pc)), (1, self.cpu1.as_ref().map(|c| c.pc))] {
            if let Some(pc) = pc {
                if !self.code_at(pc) {
                    return Err(Stop::Fault { core, pc, what: "the pc left every memory that can hold code".into() });
                }
            }
        }
        // the same state after a whole run with interrupts off: one more instruction
        // tells a jump to itself (a halt) from a loop that happens to line up
        // (exactly one: the block runner may retire a glued pair at once, and a
        // two-instruction loop then looks like a jump to itself)
        if !self.cpu0.ie && (self.cpu0.pc, self.cpu0.regs, self.cpu0.sp) == before {
            let (pc, count) = (self.cpu0.pc, self.cpu0.insn_count);
            let Board { soc, cpu0, pending_tick, blocks, halves_seen, .. } = self;
            if let Err(e) = run_blocks(cpu0, soc, 1, pending_tick, blocks, halves_seen) {
                return Err(Stop::Fault { core: 0, pc: self.cpu0.pc, what: e });
            }
            if self.cpu0.insn_count == count + 1 && (self.cpu0.pc, self.cpu0.regs, self.cpu0.sp) == before {
                return Err(Stop::Halt { pc });
            }
        }
        Ok(())
    }

    fn code_at(&self, pc: u32) -> bool {
        let within = |base: u32, len: u32| pc.wrapping_sub(base) < len;
        within(XIP_BASE, self.image_len)
            || within(RAM_BASE, RAM_SIZE as u32)
            || within(OVL_BASE, OVL_SIZE)
            || within(SRAM2_BASE, SRAM2_SIZE)
    }

    /// Bytes of main RAM, the overlay RAM or the SRAM banks (reads there have
    /// no side effects). None if any byte is elsewhere.
    pub fn read_ram(&mut self, addr: u32, len: u32) -> Option<Vec<u8>> {
        let ok = |base: u32, size: u32| addr >= base && (addr as u64 + len as u64) <= base as u64 + size as u64;
        if !(ok(RAM_BASE, RAM_SIZE as u32) || ok(OVL_BASE, OVL_SIZE) || ok(SRAM2_BASE, SRAM2_SIZE)) {
            return None;
        }
        Some((0..len).map(|i| fm1_core::Bus::read8(&mut self.soc, addr + i)).collect())
    }

    pub fn word(&mut self, addr: u32) -> Option<u32> {
        self.read_ram(addr, 4).map(|b| u32::from_le_bytes([b[0], b[1], b[2], b[3]]))
    }
}

/// Upstream's `fm1_soc::machine::run_blocks` (MIT), unchanged but for the
/// audio half-buffer note after each `advance` and a typed error.
fn run_blocks(
    cpu: &mut Cpu,
    soc: &mut Soc,
    n: u32,
    pending_tick: &mut bool,
    blocks: &mut Vec<Block>,
    halves_seen: &mut u64,
) -> Result<(), String> {
    let mut done = 0u32;
    let mut ticked = std::mem::take(pending_tick);
    while done < n {
        if ticked || soc.periph.tick() {
            soc.advance(0);
            if soc.periph.audio_halves != *halves_seen {
                *halves_seen = soc.periph.audio_halves;
                blocks.push(Block { cycle: soc.periph.cycles, core0: cpu.insn_count, core1: 0 });
            }
        }
        ticked = false;
        soc.periph.in_isr = !cpu.irq_levels.is_empty();
        if soc.periph.any_pending() {
            if let Some((irq, prio)) = soc.pending_irq() {
                if cpu.irq_ready(prio) {
                    let handler = fm1_core::Bus::read32(soc, fm1_soc::VEC_BASE + 4 * irq as u32);
                    cpu.interrupt(handler, prio);
                }
            }
        }
        match cpu.run_fast(soc, n - done) {
            Ok((0, _)) => {
                cpu.step(soc).map_err(describe)?;
                done += 1;
            }
            Ok((k, due)) => {
                done += k;
                ticked = due;
            }
            Err(e) => return Err(describe(e)),
        }
        if soc.cpu1_release {
            break;
        }
    }
    *pending_tick = ticked;
    Ok(())
}

/// A core error in the words HARNESS.md uses (no class names: the clean side
/// sees these messages).
fn describe(e: CoreError) -> String {
    match e {
        CoreError::Decode(_) => "an instruction the emulated CPU cannot decode".into(),
        CoreError::Unsupported { raw, .. } => format!("an instruction the emulator does not implement (bytes {:012x})", raw),
        CoreError::MissingSlot { .. } => "an instruction the emulator does not implement".into(),
    }
}
