// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 japes98
//! The harness's own tests (R-HARN-*), on the test images in tests/images/
//! (built from their sources by tests/images/build.sh with the pinned
//! toolchain; C-HARNESS-IMAGES checks the committed binaries match).

use fwtest::run::{run, Options, Outcome, When};
use fwtest::{formats, script};
use std::path::{Path, PathBuf};
use std::process::Command;

const OUT0: u32 = 0x01c0_0100;
const OUTBUF: u32 = 0x01c0_0200;

fn image(name: &str) -> Vec<u8> {
    std::fs::read(Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/images").join(format!("{name}.bin"))).unwrap()
}

fn opts(ms: u64) -> Options {
    Options { ms_us: ms * 1000, ..Default::default() }
}

fn output<'a>(r: &'a fwtest::run::Report, name: &str) -> &'a [u8] {
    &r.outputs.iter().find(|o| o.name == name).unwrap_or_else(|| panic!("no output {name}")).data
}

fn words(b: &[u8]) -> Vec<u32> {
    b.chunks(4).map(|c| u32::from_le_bytes(c.try_into().unwrap())).collect()
}

fn scratch(name: &str) -> PathBuf {
    let d = Path::new(env!("CARGO_TARGET_TMPDIR")).join(name);
    let _ = std::fs::remove_dir_all(&d);
    d
}

/// R-HARN-1: a raw image boots at the window's start and runs for the time asked.
#[test]
fn boots_and_runs_for_the_time_asked() {
    let mut o = opts(20);
    o.ram = vec![(OUT0, 8, When::At(10_000)), (OUT0, 8, When::End)];
    let r = run(&image("heartbeat"), &o).unwrap();
    assert_eq!(r.outcome, Outcome::Completed);
    assert_eq!(r.end_us, 20_000);
    let mid = words(output(&r, "ram-01c00100-8-10ms.bin"));
    let end = words(output(&r, "ram-01c00100-8-end.bin"));
    assert_eq!((mid[0], end[0]), (0x600d_f00d, 0x600d_f00d));
    assert!(end[1] > mid[1] && mid[1] > 0, "the counter runs on: {mid:?} {end:?}");
    // one instruction per cycle while nothing is skipped: 240 000 a millisecond
    assert_eq!(r.instructions.0, 20 * 240_000 + 3);
}

/// R-HARN-1: bad images are refused.
#[test]
fn refuses_empty_and_oversized_images() {
    assert!(run(&[], &opts(1)).is_err());
    assert!(run(&vec![0u8; fwtest::machine::MAX_IMAGE + 1], &opts(1)).is_err());
}

/// R-HARN-4: halt, fault (two kinds) and hang are told apart.
#[test]
fn halts_faults_and_hangs() {
    let r = run(&image("halt"), &opts(20)).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    assert!(r.end_us < 1000);

    let r = run(&image("wild"), &opts(20)).unwrap();
    match r.outcome {
        Outcome::Fault { core: 0, pc, ref what } => {
            assert_eq!(pc & 0xfff0_0000, 0x1000_0000);
            assert!(what.contains("left every memory"), "{what}");
        }
        ref o => panic!("{o:?}"),
    }

    // a halfword the decoder has no entry for, at the first byte
    let r = run(&[0x04, 0x00, 0, 0, 0, 0, 0, 0], &opts(1)).unwrap();
    match r.outcome {
        Outcome::Fault { core: 0, pc: 0x0200_0000, ref what } => assert!(what.contains("cannot decode"), "{what}"),
        ref o => panic!("{o:?}"),
    }

    let mut o = opts(50);
    o.watchdog = Some((OUT0 + 4, 5));
    let r = run(&image("hang"), &o).unwrap();
    assert_eq!(r.outcome, Outcome::Hang { addr: OUT0 + 4, ms: 5 });
    assert!(r.end_us > 5_000 && r.end_us < 7_000, "{}", r.end_us);

    // a counter that keeps changing never trips the watchdog
    let mut o = opts(20);
    o.watchdog = Some((OUT0 + 4, 1));
    assert_eq!(run(&image("heartbeat"), &o).unwrap().outcome, Outcome::Completed);
}

/// R-HARN-2: keys, encoders, the pot and MIDI from a script.
#[test]
fn inputs_from_a_script() {
    let mut o = opts(40);
    o.script = script::parse("2 key 12 down\n4 key 12 up\n6 key 5 tap 3\n10 enc 0 +2\n").unwrap();
    o.ram = vec![(OUT0, 44, When::At(3_000)), (OUT0, 44, When::At(7_000)), (OUT0 + 0x40, 4, When::End)];
    let r = run(&image("keys"), &o).unwrap();
    let at3 = words(output(&r, "ram-01c00100-2c-3ms.bin"));
    let at7 = words(output(&r, "ram-01c00100-2c-7ms.bin"));
    assert_eq!(at3.iter().filter(|&&w| w != 0).count(), 1);
    assert_ne!(at3[10], 0, "key 12 down at 3 ms: {at3:?}");
    assert_eq!(at7.iter().filter(|&&w| w != 0).count(), 1);
    assert_ne!(at7[0], 0, "key 5 down at 7 ms: {at7:?}");
    assert_eq!(words(output(&r, "ram-01c00140-4-end.bin")), vec![8], "two detents, four contact changes each");

    let mut o = opts(10);
    o.script = script::parse("5 pot 300\n").unwrap();
    o.ram = vec![(OUT0, 4, When::At(2_000)), (OUT0, 4, When::End)];
    let r = run(&image("pot"), &o).unwrap();
    assert_eq!(words(output(&r, "ram-01c00100-4-2ms.bin")), vec![900], "the pot's reading before any input");
    assert_eq!(words(output(&r, "ram-01c00100-4-end.bin")), vec![300]);

    let mut o = opts(10);
    o.script = script::parse("1 midi 90 3c 64\n3 midi 80 3c 00\n").unwrap();
    o.ram = vec![(OUTBUF, 8, When::At(1_500)), (OUTBUF, 8, When::At(2_500)), (OUTBUF, 8, When::End)];
    let r = run(&image("midi"), &o).unwrap();
    // one byte time (320 us) after another
    assert_eq!(output(&r, "ram-01c00200-8-1.500ms.bin"), &[0x90, 0, 0, 0, 0, 0, 0, 0]);
    assert_eq!(output(&r, "ram-01c00200-8-2.500ms.bin"), &[0x90, 0x3c, 0x64, 0, 0, 0, 0, 0]);
    assert_eq!(output(&r, "ram-01c00200-8-end.bin"), &[0x90, 0x3c, 0x64, 0x80, 0x3c, 0, 0, 0]);
}

/// R-HARN-3: the LCD as PNG.
#[test]
fn lcd_capture() {
    let mut o = opts(30);
    o.lcd = vec![When::End];
    o.halt_ok = true;
    let r = run(&image("lcd"), &o).unwrap();
    let (w, h, rgb) = formats::png_read(output(&r, "lcd-end.png")).unwrap();
    assert_eq!((w, h), (240, 240));
    let px = |x: usize, y: usize| &rgb[(y * 240 + x) * 3..(y * 240 + x) * 3 + 3];
    assert_eq!(px(10, 50), [255, 0, 0]);
    assert_eq!(px(200, 50), [0, 255, 0]);
    assert_eq!(px(10, 200), [0, 0, 255]);
    assert_eq!(px(200, 150), [255, 255, 255]);
    assert_eq!(px(100, 100), [0, 0, 0], "the diagonal");
}

/// HARNESS.md ("The LCD"): SPI1's CON reads back as last written (bit 15
/// set: transfers finish at once), and a finished transfer, DMA or single
/// byte, raises source 16 only while bit 13 is set (SR-3).
#[test]
fn spi1_interrupt_follows_con_bit_13() {
    let mut o = opts(2);
    o.ram = vec![(OUT0, 32, When::End)];
    o.halt_ok = true;
    let r = run(&image("spi1irq"), &o).unwrap();
    let w = words(output(&r, "ram-01c00100-20-end.bin"));
    assert_eq!(&w[0..2], &[1, 0xa000], "bit 13 set: the DMA raised it");
    assert_eq!(&w[2..4], &[1, 0x8000], "CON written 0: bit 13 clear, no interrupt");
    assert_eq!(&w[4..6], &[1, 0x8000], "a byte with bit 13 clear: none");
    assert_eq!(&w[6..8], &[2, 0xa000], "a byte with bit 13 set: one");
}

/// R-HARN-11: the block moves with a register base, every mode (SR-7): the
/// lowest register at the lowest address, `[-rN]` ending just below the
/// base, the base kept unless `++` / `--` moves it past the block, and every
/// address from the original base when the base is also loaded.
#[test]
fn block_moves_every_mode() {
    const SRC: u32 = 0x01c0_1000;
    const DST: u32 = 0x01c0_1200;
    let s = |i: u32| 0xa500_0000 + i;
    let mut o = opts(2);
    o.ram = vec![(OUT0, 84, When::End), (DST, 256, When::End)];
    o.halt_ok = true;
    let r = run(&image("blockmv"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-54-end.bin"));
    assert_eq!(&w[0..4], &[s(4), s(5), s(6), SRC + 0x10], "A {{r3, r1, r0}} = [r6+]");
    assert_eq!(&w[4..7], &[s(8), s(9), SRC + 0x28], "B {{r2, r1}} = [r7++]");
    assert_eq!(&w[7..10], &[s(2), s(3), SRC + 0x10], "C {{r3, r0}} = [-r4]");
    assert_eq!(&w[10..12], &[s(2), s(3)], "D {{r3, r0}} = [-r0]");
    assert_eq!(&w[12..16], &[s(13), s(14), s(15), SRC + 0x34], "E {{r12, r11, r10}} = [--r9]");
    assert_eq!(&w[16..21], &[DST + 0x10, DST + 0x24, DST + 0x40, DST + 0x5c, DST + 0x70], "F to J: the bases");
    let d = words(output(&r, "ram-01c01200-100-end.bin"));
    let mut want = vec![0u32; 64];
    want[2..4].copy_from_slice(&[0xb2, 0xb5]); // F [-r8] = {r5, r2}
    want[9..12].copy_from_slice(&[0xc0, 0xce, 0xcf]); // G [--r13] = {r15, r14, r0}
    want[16..18].copy_from_slice(&[0xd3, 0xd6]); // H [r10+] = {r6, r3}
    want[20..23].copy_from_slice(&[0xe1, 0xe2, 0xe4]); // I [r11++] = {r4, r2, r1}
    want[26..28].copy_from_slice(&[0xf1, DST + 0x70]); // J [-r5] = {r5, r1}
    for i in 0..15 {
        want[32 + i] = s(16 + i as u32); // K {r14-r0} = [-r15], then [r15+] = {r14-r0}
    }
    assert_eq!(d, want);
}

/// R-HARN-11: SR-7's reproduction as the request gives it: r0 and r3 take
/// the two words below r4, and r4 keeps its value.
#[test]
fn block_move_below_the_base_sr7() {
    let mut o = opts(1);
    o.ram = vec![(0x01c0_0020, 12, When::End)];
    let r = run(&image("sr7"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    assert_eq!(words(output(&r, "ram-01c00020-c-end.bin")), [0x29f3_a1c5, 0x7e41_d60b, 0x01c0_0010]);
}

/// R-HARN-11: the forms below a base as the compiler emits them, built with
/// the firmware's CPU flags (build.sh fails if they are gone).
#[test]
fn block_moves_from_the_compiler() {
    const DST: u32 = 0x01c0_1200;
    let s = |i: u32| 0xa500_0000 + i;
    let mut o = opts(2);
    o.ram = vec![(OUT0, 16, When::End), (DST + 24, 24, When::End)];
    o.halt_ok = true;
    let r = run(&image("blockc"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-10-end.bin"));
    let o0 = s(7).wrapping_mul(3) ^ s(6).wrapping_mul(5);
    assert_eq!(w, [s(7) + 0x100, o0, s(6) + 0x100, DST + 24]);
    assert_eq!(words(output(&r, "ram-01c01218-18-end.bin")), [0x71, 0x51, 0x31, 0x71, 0x51, 0x31]);
}

/// R-HARN-12: a dual-issue pair's head among the 4-byte ALU forms, one of
/// each family: the pair's second half sees the destination as it was, and
/// after the pair it holds what the plain form computes.
#[test]
fn alu_pair_heads_hold_their_result() {
    const OLD: u32 = 0x0bad_f00d;
    let mut o = opts(2);
    o.ram = vec![(OUT0, 300, When::End)];
    o.halt_ok = true;
    let r = run(&image("pairhead"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-12c-end.bin"));
    for k in 0..25 {
        let (plain, during, after) = (w[3 * k], w[3 * k + 1], w[3 * k + 2]);
        assert_ne!(plain, OLD, "case {k}: the plain form changes the destination");
        assert_eq!(during, OLD, "case {k}: the pair's second half sees the value before the head");
        assert_eq!(after, plain, "case {k}: after the pair, the head's result");
    }
}

/// R-HARN-12: the rotate right by a register, across registers and amounts
/// (0 to 31 as the compiler's code shows; 32 and over taken mod 32), its
/// pair head, and the rotate by a constant beside it.
#[test]
fn rotate_by_a_register() {
    const X: u32 = 0x1234_5678;
    let mut o = opts(2);
    o.ram = vec![(OUT0, 44, When::End)];
    o.halt_ok = true;
    let r = run(&image("rotr"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let d = 0xdead_beefu32;
    assert_eq!(
        words(output(&r, "ram-01c00100-2c-end.bin")),
        [
            X.rotate_right(8),
            0xc000_0000,
            X.rotate_right(31),
            0x13u32.rotate_right(19),
            d,
            d,
            d.rotate_right(1),
            d.rotate_right(1),
            X.rotate_right(7),
            0x0bad_f00d,
            X.rotate_right(4),
        ]
    );
}

/// R-HARN-12: the rotates as the compiler emits them, built with the
/// firmware's CPU flags (build.sh fails if the rotate by a register is
/// gone): `(x << s) | (x >> (32 - s))`, its masked form, `(x >> 7) | (x << 25)`.
#[test]
fn rotates_from_the_compiler() {
    const X: u32 = 0x1234_5678;
    let mut o = opts(2);
    o.ram = vec![(OUT0, 276, When::End)];
    o.halt_ok = true;
    let r = run(&image("rotc"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-114-end.bin"));
    assert_eq!(w[0], X);
    for s in 1..32u32 {
        assert_eq!(w[4 + s as usize], X.rotate_left(s), "rotl(x, {s})");
    }
    for s in 0..32u32 {
        assert_eq!(w[36 + s as usize], X.rotate_left(s), "rotl_m(x, {s})");
    }
    assert_eq!(w[68], X.rotate_right(7), "rotr7(x)");
}

/// R-HARN-12: the 4-byte push and pop of a register list, lists above r0,
/// alone, not contiguous, from r0, and empty: the lowest register at the
/// lowest address, sp moved by 4 a register.
#[test]
fn push_pop_any_register_list() {
    const SP: u32 = 0x01c7_d000;
    let mut o = opts(2);
    o.ram = vec![(OUT0, 168, When::End)];
    o.halt_ok = true;
    let r = run(&image("pushpop"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-a8-end.bin"));
    assert_eq!(&w[0..2], &[SP, SP - 20], "A [--sp] = {{r5-r1}}");
    assert_eq!(&w[2..7], &[0xa1, 0xa2, 0xa3, 0xa4, 0xa5], "A: r1 at sp");
    assert_eq!(&w[7..13], &[0xa1, 0xa2, 0xa3, 0xa4, 0xa5, SP], "A {{r11-r7}} = [sp++]");
    assert_eq!(&w[13..15], &[0xf15, SP], "B {{r15}}, then {{r9}}");
    assert_eq!(w[15], SP - 24, "C [--sp] = {{r14, r10, r8, r6, r4, r2}}");
    assert_eq!(&w[16..23], &[0xb2, 0xb4, 0xb6, 0xb8, 0xba, 0xbe, SP], "C {{r15, r13, r11, r9, r7, r5}} = [sp++]");
    assert_eq!(&w[23..31], &[0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7], "D {{r7-r0}}, then {{r15-r8}}");
    assert_eq!(&w[31..40], &[0xd8, 0xd9, 0xda, 0xdb, 0xdc, 0xdd, 0xde, 0xdf, SP], "D {{r15-r8}}, then {{r7-r0}}");
    assert_eq!(&w[40..42], &[SP, SP], "E the empty list");
}

/// R-HARN-1: code the image writes into RAM runs as memory holds it, also
/// after a halfword, byte or word store changes it between runs.
#[test]
fn ram_code_runs_as_written() {
    let mut o = opts(2);
    o.ram = vec![(OUT0, 16, When::End)];
    o.halt_ok = true;
    let r = run(&image("ramcode"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    assert_eq!(words(output(&r, "ram-01c00100-10-end.bin")), [0x1234_5678, 0x1234_beef, 0x7734_beef, 0x5566_beef]);
}

/// R-HARN-3: LED duty per sample.
#[test]
fn led_capture() {
    let mut o = opts(20);
    o.leds_every_us = Some(5_000);
    let r = run(&image("leds"), &o).unwrap();
    let csv = String::from_utf8(output(&r, "leds.csv").to_vec()).unwrap();
    let rows: Vec<Vec<&str>> = csv.lines().map(|l| l.split(',').collect()).collect();
    assert_eq!(rows[0].len(), 42);
    assert_eq!((rows[0][6], rows[0][35]), ("led5", "led34"));
    let at = |t: &str, col: usize| rows.iter().find(|r| r[0] == t).unwrap()[col];
    assert_eq!((at("5", 6), at("5", 35)), ("1000", "0"));
    assert_eq!((at("15", 6), at("15", 35)), ("0", "1000"));
}

/// R-HARN-3: flash in and out, and the image in the chip.
#[test]
fn flash_capture() {
    let mut chip = vec![0xffu8; 0x100000];
    chip[0x5000..0x5010].copy_from_slice(b"flash file bytes");
    let mut o = opts(5);
    o.flash_in = Some(chip);
    o.flash_out = true;
    o.halt_ok = true;
    o.ram = vec![(OUTBUF, 16, When::End)];
    let img = image("flashrw");
    let r = run(&img, &o).unwrap();
    assert_eq!(output(&r, "ram-01c00200-10-end.bin"), b"flash file bytes", "read through the window");
    let f = output(&r, "flash.bin");
    assert_eq!(f.len(), 0x100000);
    assert_eq!(&f[0x80000..0x80010], b"flash written!!!");
    assert!(f[0x80010..0x81000].iter().all(|&b| b == 0xff), "rest of the sector erased");
    assert_eq!(&f[0x4000..0x4000 + img.len()], &img[..], "the image sits in the chip");
}

/// R-HARN-3: audio as WAV, instructions per audio block, the console.
#[test]
fn audio_ipb_and_console() {
    let mut o = opts(20);
    o.wav = true;
    o.ipb = true;
    let r = run(&image("audio"), &o).unwrap();
    let (rate, ch, s) = formats::wav_read(output(&r, "audio.wav")).unwrap();
    assert_eq!((rate, ch), (44100, 2));
    assert_eq!(&s[..6], &[0, 0, 97, -97, 194, -194]);
    let ipb = String::from_utf8(output(&r, "ipb.csv").to_vec()).unwrap();
    let lines: Vec<&str> = ipb.lines().collect();
    assert_eq!(lines[0], "block,end_ms,core0,core1");
    assert_eq!(lines.len() - 1, s.len() / 64, "one row per half-buffer");
    // idle between blocks costs nothing: the same small count every block
    let counts: Vec<&str> = lines[2..].iter().map(|l| l.split(',').nth(2).unwrap()).collect();
    assert!(counts.iter().all(|c| *c == counts[0]) && counts[0].parse::<u32>().unwrap() < 2000, "{counts:?}");

    let mut o = opts(5);
    o.console = true;
    o.halt_ok = true;
    assert_eq!(output(&run(&image("console"), &o).unwrap(), "console.txt"), b"hello world\n");
}

/// R-HARN-6: the same image and script give the same bytes, every run.
#[test]
fn deterministic() {
    let mut o = opts(30);
    o.script = script::parse("1 key 3 down\n2 enc 1 -1\n3 pot 10\n4 midi 90 40 7f\n").unwrap();
    o.ram = vec![(0x01c0_0000, 0x1000, When::End)];
    o.lcd = vec![When::At(5_000), When::End];
    o.leds_every_us = Some(1_000);
    o.wav = true;
    o.ipb = true;
    o.flash_out = true;
    for name in ["audio", "keys", "lcd"] {
        let a = run(&image(name), &o).unwrap();
        let b = run(&image(name), &o).unwrap();
        assert_eq!(a.outcome, b.outcome);
        assert_eq!(a.instructions, b.instructions);
        let ha: Vec<_> = a.outputs.iter().map(|o| (o.name.clone(), formats::sha256(&o.data))).collect();
        let hb: Vec<_> = b.outputs.iter().map(|o| (o.name.clone(), formats::sha256(&o.data))).collect();
        assert_eq!(ha, hb, "{name}");
    }
}

fn fwtest(args: &[&str]) -> (i32, String) {
    let out = Command::new(env!("CARGO_BIN_EXE_fwtest")).args(args).env("FM1_TRACE", "1").output().unwrap();
    (out.status.code().unwrap_or(-1), String::from_utf8_lossy(&out.stdout).into_owned() + &String::from_utf8_lossy(&out.stderr))
}

/// R-HARN-4, R-HARN-5, R-HARN-7: the CLI's exit codes, golden files, and
/// result files (also that FM1_* variables change nothing: R-HARN-6).
#[test]
fn cli_exit_codes_golden_and_results() {
    let img = |n: &str| Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/images").join(format!("{n}.bin")).to_string_lossy().into_owned();
    let d = scratch("cli");
    let p = |s: &str| d.join(s).to_string_lossy().into_owned();
    assert_eq!(fwtest(&["run", &img("heartbeat"), "--ms", "5", "--out", &p("a")]).0, 0);
    assert_eq!(fwtest(&["run", &img("halt"), "--ms", "5", "--out", &p("b")]).0, 4);
    assert_eq!(fwtest(&["run", &img("halt"), "--ms", "5", "--out", &p("b2"), "--halt-ok"]).0, 0);
    assert_eq!(fwtest(&["run", &img("wild"), "--ms", "5", "--out", &p("c")]).0, 3);
    assert_eq!(fwtest(&["run", &img("hang"), "--ms", "20", "--out", &p("d"), "--watchdog", "0x01c00104:2"]).0, 5);
    assert_eq!(fwtest(&["run", &img("heartbeat"), "--out", &p("e")]).0, 2, "--ms missing");
    assert_eq!(fwtest(&["run", &img("heartbeat"), "--ms", "5", "--out", &p("a")]).0, 2, "out not empty");

    // golden: the first run's RAM capture is the golden; a second run matches it, a
    // changed golden does not
    let args = |o: &str, g: Option<&str>| {
        let mut v = vec!["run".to_string(), img("console"), "--ms".into(), "5".into(), "--console".into(), "--halt-ok".into(), "--out".into(), p(o)];
        if let Some(g) = g {
            v.push("--golden".into());
            v.push(p(g));
        }
        v
    };
    let run_args = |o: &str, g: Option<&str>| {
        let v = args(o, g);
        fwtest(&v.iter().map(String::as_str).collect::<Vec<_>>())
    };
    assert_eq!(run_args("g1", None).0, 0);
    std::fs::create_dir_all(d.join("golden")).unwrap();
    std::fs::copy(d.join("g1/console.txt"), d.join("golden/console.txt")).unwrap();
    assert_eq!(run_args("g2", Some("golden")).0, 0);
    std::fs::write(d.join("golden/console.txt"), b"hello there\n").unwrap();
    let (code, text) = run_args("g3", Some("golden"));
    assert_eq!(code, 1, "{text}");
    assert!(text.contains("golden console.txt"), "{text}");

    let result = std::fs::read_to_string(d.join("g3/result.json")).unwrap();
    for want in ["\"outcome\": \"halt\"", "\"exit_code\": 1", "\"result\": \"mismatch\"", "\"emulator_commit\""] {
        assert!(result.contains(want), "{want} in {result}");
    }
    let junit = std::fs::read_to_string(d.join("g3/junit.xml")).unwrap();
    assert!(junit.contains("tests=\"2\" failures=\"1\""), "{junit}");
    // identical bytes for an identical run (no times, no host paths in the results)
    assert_eq!(run_args("h1", Some("golden")).0, 1);
    for f in ["result.json", "junit.xml", "console.txt"] {
        assert_eq!(std::fs::read(d.join("g3").join(f)).unwrap(), std::fs::read(d.join("h1").join(f)).unwrap(), "{f}");
    }
}

/// R-HARN-1: the image format the firmware side builds against.
#[test]
fn boot_state_matches_the_manual() {
    let b = fwtest::machine::Board::boot(&[0u8; 16], None).unwrap();
    assert_eq!(b.cpu0.pc, 0x0200_0000);
    assert!(b.cpu0.user);
    assert_eq!(b.cpu0.regs[0], 0x01c7_fc00);
    assert_eq!(b.cpu0.sp, 0);
    assert_eq!(b.soc.ram.len(), 1 << 20);
}
