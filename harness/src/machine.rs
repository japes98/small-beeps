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
//! `run_dual` and `run_cpu1` are upstream's too, copied for one more: while
//! the flash chip is busy with an erase or program (`SpiFlash::working`,
//! timed by `FLASH_PROGRAM_MS` and `FLASH_ERASE_MS`), each core runs a block
//! at a time and the run ends as a fault when a core is about to run a block
//! in the code window, or read the window (`Soc::window_read_busy`): on the
//! chip the window can't be served then (docs/HARDWARE-SPEC.md HW-79).
//!
//! Determinism: no JIT (`jit_on` stays false on both cores), `skip_idle` on
//! (time jumps over `idle` and TIMER4 polling, so instruction counts measure
//! work, not waiting), and `main` clears every `FM1_*` environment variable
//! before anything is built, since several switch execution paths or traces.

use fm1_core::{Cpu, CoreError};
use fm1_soc::machine::{self, Core1Bus};
use fm1_soc::{FlashTiming, Soc, FLASH_SIZE, OVL_BASE, RAM_BASE, SRAM2_BASE, VEC_BASE, XIP_BASE, XIP_FLASH_OFFSET};

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
/// How long a page program and an erase (of any size) keep the flash chip
/// busy: the P25Q80H datasheet's maximum times (HW-77).
pub const FLASH_PROGRAM_MS: u64 = 3;
pub const FLASH_ERASE_MS: u64 = 12;
/// A fault's text for code-window use while the flash is busy.
const WINDOW_BUSY_RUN: &str = "ran code in the code window while the flash chip was busy (an erase or program in progress)";
/// Errors from the core-1 loop that are ours, not upstream's debug text.
const CORE1: &str = "core 1: ";
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
        soc.flash.timing = FlashTiming { program: FLASH_PROGRAM_MS * CYCLES_PER_MS, erase: FLASH_ERASE_MS * CYCLES_PER_MS };
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
        let r = run_dual(cpu1, soc, n, RAM_SIZE, |soc, k| {
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
                Some(c) if e.starts_with(CORE1) => Stop::Fault { core: 1, pc: c.pc, what: e[CORE1.len()..].into() },
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
                    let handler = fm1_core::Bus::read32(soc, VEC_BASE + 4 * irq as u32);
                    cpu.interrupt(handler, prio);
                }
            }
        }
        // the flash busy: a block at a time, none in the code window
        let busy = flash_busy(soc);
        if busy && in_window(cpu.pc) {
            return Err(WINDOW_BUSY_RUN.into());
        }
        let r = cpu.run_fast(soc, if busy { 1 } else { n - done });
        if let Some(a) = soc.window_read_busy.take() {
            return Err(window_busy_read(a));
        }
        match r {
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

fn flash_busy(soc: &Soc) -> bool {
    soc.flash.working(soc.periph.cycles)
}

/// The code window: the image and the flash chip behind it.
fn in_window(pc: u32) -> bool {
    pc.wrapping_sub(XIP_BASE) < MAX_IMAGE as u32
}

fn window_busy_read(addr: u32) -> String {
    format!("read the code window at {addr:#010x} while the flash chip was busy (an erase or program in progress)")
}

/// Upstream's `fm1_soc::machine::run_dual` (MIT), without the JIT switch,
/// running core 1 through `run_cpu1` below.
fn run_dual(
    cpu1: &mut Option<Cpu>,
    soc: &mut Soc,
    n: u32,
    ram_size: usize,
    mut run0: impl FnMut(&mut Soc, u32) -> Result<(), String>,
) -> Result<(), String> {
    let mut done = 0;
    while cpu1.is_none() {
        *cpu1 = machine::released_cpu1(soc, ram_size).map(|mut c| {
            c.jit_on = false;
            c
        });
        if cpu1.is_some() || done >= n {
            break;
        }
        let k = (n - done).min(4096);
        soc.periph.room_cap = k as u64;
        run0(soc, k)?;
        done += k;
    }
    let Some(c1) = cpu1.as_mut() else { return Ok(()) };
    soc.periph.room_cap = machine::SLICE as u64;
    while done < n {
        let k = (n - done).min(machine::SLICE);
        let c0 = soc.periph.cycles;
        if soc.core_paused(0) {
            soc.advance(k as u64);
        } else {
            run0(soc, k)?;
        }
        done += k;
        let dt = soc.periph.cycles - c0;
        run_cpu1(c1, soc, dt)?;
    }
    Ok(())
}

/// Upstream's `fm1_soc::machine::run_cpu1` (MIT), with the same check as
/// `run_blocks` while the flash is busy (on cpu0's clock, which core 1
/// trails by at most one run call).
fn run_cpu1(c1: &mut Cpu, soc: &mut Soc, cycles: u64) -> Result<(), String> {
    if soc.core_paused(1) {
        return Ok(());
    }
    let probe = (c1.pc, c1.regs, c1.sp);
    let mut left = cycles.min(1 << 20);
    let mut probing = 512u64;
    while left > 0 {
        if soc.periph.any_pending() {
            if let Some((irq, prio)) = soc.pending_irq_for(1) {
                if c1.irq_ready(prio) {
                    let handler = fm1_core::Bus::read32(soc, VEC_BASE + 4 * irq as u32);
                    c1.interrupt(handler, prio);
                }
            }
        }
        let busy = flash_busy(soc);
        if busy && in_window(c1.pc) {
            return Err(format!("{CORE1}{WINDOW_BUSY_RUN}"));
        }
        let chunk = if probing > 0 || busy { 1 } else { left.min(256) };
        let mut bus = Core1Bus { soc: &mut *soc, budget: chunk.max(64) + 1 };
        let r = c1.run_fast(&mut bus, chunk as u32);
        if let Some(a) = soc.window_read_busy.take() {
            return Err(format!("{CORE1}{}", window_busy_read(a)));
        }
        let k = match r {
            Ok((0, _)) => {
                let mut bus = Core1Bus { soc: &mut *soc, budget: 65 };
                if let Err(e) = c1.step(&mut bus) {
                    return Err(format!("cpu1: {e:?} at pc {:#010x}", c1.pc));
                }
                1
            }
            Ok((k, _)) => k as u64,
            Err(e) => return Err(format!("cpu1: {e:?} at pc {:#010x}", c1.pc)),
        };
        left = left.saturating_sub(k);
        probing = probing.saturating_sub(k);
        if c1.pc == probe.0 && c1.sp == probe.2 && c1.regs == probe.1 {
            break;
        }
    }
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
