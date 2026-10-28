// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 japes98
//! `fwtest decode FILE`: what fwtest does with single instructions, for the
//! toolchain audit (C-HARNESS-ISA, harness/isa/isa_check.py). Each line of
//! FILE is one instruction's bytes in hex, as they lie in memory (2, 4 or 6
//! bytes). Each output line is the same hex, the length fwtest decodes it
//! to (`-` when it cannot) and one word: `runs` (decoded and executed),
//! `no-decode` (an instruction the emulated CPU cannot decode), `unsupported`
//! (decoded, but an instruction it does not run) or `panic`. Nothing else of
//! the emulator is printed.
//!
//! The instruction runs once on core 0 at 0x02001000 over a flat memory,
//! each register rN set to 0x01800000 + 0x100 * N and the stacks to
//! 0x01808000, so loads and stores land in memory, and as after an `fcmp`
//! (the flag branches' condition); a jump is just taken.

use fm1_core::{Bus, CoreError, Cpu};
use std::collections::HashMap;

const PC: u32 = 0x0200_1000;

struct Flat(HashMap<u32, u8>);

impl Flat {
    fn byte(&self, a: u32) -> u8 {
        *self.0.get(&a).unwrap_or(&0)
    }
}

impl Bus for Flat {
    fn read8(&mut self, a: u32) -> u8 {
        self.byte(a)
    }
    fn read16(&mut self, a: u32) -> u16 {
        u16::from_le_bytes([self.byte(a), self.byte(a.wrapping_add(1))])
    }
    fn read32(&mut self, a: u32) -> u32 {
        u32::from_le_bytes([self.byte(a), self.byte(a.wrapping_add(1)), self.byte(a.wrapping_add(2)), self.byte(a.wrapping_add(3))])
    }
    fn write8(&mut self, a: u32, v: u8) {
        self.0.insert(a, v);
    }
    fn write16(&mut self, a: u32, v: u16) {
        for (i, b) in v.to_le_bytes().into_iter().enumerate() {
            self.0.insert(a.wrapping_add(i as u32), b);
        }
    }
    fn write32(&mut self, a: u32, v: u32) {
        for (i, b) in v.to_le_bytes().into_iter().enumerate() {
            self.0.insert(a.wrapping_add(i as u32), b);
        }
    }
}

/// One instruction: (the length fwtest decodes, or None; the outcome word).
pub fn probe(bytes: &[u8]) -> (Option<usize>, &'static str) {
    let mut win = 0u64;
    for (i, b) in bytes.iter().take(6).enumerate() {
        win |= (*b as u64) << (8 * i);
    }
    let len = fm1_core::decode_info(win, PC).map(|(l, _)| l);
    let outcome = std::panic::catch_unwind(|| {
        let mut mem = Flat(HashMap::new());
        for (i, b) in bytes.iter().enumerate() {
            mem.0.insert(PC + i as u32, *b);
        }
        let mut cpu = Cpu::new(PC);
        cpu.jit_on = false;
        for r in 0..16 {
            cpu.regs[r] = 0x0180_0000 + 0x100 * r as u32;
        }
        (cpu.sp, cpu.ssp, cpu.usp) = (0x0180_8000, 0x0180_8000, 0x0180_8000);
        // as after `fcmp r1, r2`, so the flag branches have their condition's source
        cpu.fcmp_ab = Some((1.0f32.to_bits(), 2.0f32.to_bits()));
        match cpu.step(&mut mem) {
            Ok(()) => "runs",
            Err(CoreError::Decode(_)) => "no-decode",
            Err(_) => "unsupported",
        }
    })
    .unwrap_or("panic");
    (len, outcome)
}

/// The report for a file's text (see the module's comment).
pub fn report(text: &str) -> Result<String, String> {
    let hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(|_| {}));
    let mut out = String::new();
    let mut result = Ok(());
    for (n, line) in text.lines().enumerate() {
        let h = line.trim();
        if h.is_empty() {
            continue;
        }
        let ok = h.len() % 2 == 0 && matches!(h.len() / 2, 2 | 4 | 6) && h.bytes().all(|c| c.is_ascii_hexdigit());
        if !ok {
            result = Err(format!("line {}: not 2, 4 or 6 bytes of hex", n + 1));
            break;
        }
        let bytes: Vec<u8> = (0..h.len()).step_by(2).map(|i| u8::from_str_radix(&h[i..i + 2], 16).unwrap()).collect();
        let (len, outcome) = probe(&bytes);
        let len = len.map_or("-".to_string(), |l| l.to_string());
        out.push_str(&format!("{h}\t{len}\t{outcome}\n"));
    }
    std::panic::set_hook(hook);
    result.map(|()| out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decode_report() {
        // `10 18` r0 += r1, `3f e5 30 57` r5 = r3 + r7 (f), `58 ec 2a 03` r1_r0 = d[r2+r3<<3],
        // and two bytes whatever they are, then a line that is not 2, 4 or 6 bytes
        let r = report("1018\n3fe53057\n58ec2a03\nffff\n").unwrap();
        let lines: Vec<&str> = r.lines().collect();
        assert_eq!(lines[0], "1018\t2\truns");
        assert_eq!(lines[1], "3fe53057\t4\truns");
        assert_eq!(lines[2], "58ec2a03\t4\truns");
        assert!(lines[3].starts_with("ffff\t"));
        assert!(report("12345\n").is_err());
    }
}
