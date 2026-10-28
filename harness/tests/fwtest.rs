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

/// HARNESS.md ("Input scripts", "MIDI clock in"): an event's bytes wait
/// behind bytes still on the wire, so a clock byte due mid-message
/// arrives after it; written inside the message, it arrives there.
#[test]
fn midi_bytes_queue_behind_the_wire() {
    let mut o = opts(10);
    o.script = script::parse("1 midi 90 3c 64\n1.1 midi f8\n3 midi 90 f8 3c 64\n").unwrap();
    o.ram = vec![
        (OUTBUF, 8, When::At(1_500)),
        (OUTBUF, 8, When::At(2_200)),
        (OUTBUF, 8, When::At(2_300)),
        (OUTBUF, 8, When::At(3_700)),
        (OUTBUF, 8, When::End),
    ];
    let r = run(&image("midi"), &o).unwrap();
    // 1.1 ms's clock byte would arrive at 1.42 on an idle wire; it waits for 0x64 (1.96)
    assert_eq!(output(&r, "ram-01c00200-8-1.500ms.bin"), &[0x90, 0, 0, 0, 0, 0, 0, 0]);
    assert_eq!(output(&r, "ram-01c00200-8-2.200ms.bin"), &[0x90, 0x3c, 0x64, 0, 0, 0, 0, 0]);
    assert_eq!(output(&r, "ram-01c00200-8-2.300ms.bin"), &[0x90, 0x3c, 0x64, 0xf8, 0, 0, 0, 0]);
    // inside the message: 0x90 at 3.32, 0xf8 at 3.64
    assert_eq!(output(&r, "ram-01c00200-8-3.700ms.bin"), &[0x90, 0x3c, 0x64, 0xf8, 0x90, 0xf8, 0, 0]);
    assert_eq!(output(&r, "ram-01c00200-8-end.bin"), &[0x90, 0x3c, 0x64, 0xf8, 0x90, 0xf8, 0x3c, 0x64]);
}

/// HARNESS.md ("MIDI output"): UART1's transmit side. Bytes from a DMA or a
/// BUF write go out one per 320 us, after any still going; nothing with the
/// UART off; the transmit pending (and its interrupt) when the last has
/// gone. The capture: each byte with its time, and the messages.
#[test]
fn transmits_midi() {
    let mut o = opts(8);
    o.midi_out = true;
    o.ram = vec![(OUT0, 0x24, When::End)];
    let r = run(&image("midiout"), &o).unwrap();
    assert_eq!(r.outcome, Outcome::Completed);
    assert_eq!(r.midi_out_dropped, 1, "the BUF write with the UART off");
    let csv = String::from_utf8(output(&r, "midi-out.csv").to_vec()).unwrap();
    assert_eq!(csv, "ms,byte\n0.320,90\n0.640,3c\n0.960,64\n1.280,3e\n1.600,50\n3.320,f8\n\
4.321,80\n4.641,3c\n4.961,00\n5.281,fe\n");
    let txt = String::from_utf8(output(&r, "midi-out.txt").to_vec()).unwrap();
    assert_eq!(txt, "0.960 note-on ch 1 key 60 vel 100\n1.600 note-on ch 1 key 62 vel 80 (running status)\n\
3.320 clock\n4.961 note-off ch 1 key 60 vel 0\n5.281 active-sensing\n");
    let w = words(output(&r, "ram-01c00100-24-end.bin"));
    assert_eq!((w[0], w[1]), (0x600d_d00e, 3), "one transmit interrupt per transfer, the queued byte's included");
    // entered as the last byte's stop bit ends (TIMER4: 24 counts a microsecond), pending set
    for (k, us) in [1_600u32, 3_320, 5_281].into_iter().enumerate() {
        let t = w[2 + 2 * k];
        assert!(t >= us * 24 && t < us * 24 + 24 * 2, "entry {k} at {t}, want about {us} us");
        assert_eq!(w[3 + 2 * k], 0x8005);
    }
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

/// HARNESS.md ("USB"): the USB core's access port answers at once (bit 15
/// set), a read gives the byte last written to its index, and the
/// interrupt flags (indexes 2-6) read 0 (vendor patch 0012; fwtest 0.6.0
/// never set bit 15, so every access waited out the firmware's timeout).
#[test]
fn usb_port_answers() {
    let mut o = opts(1);
    o.ram = vec![(OUT0, 40, When::End)];
    o.halt_ok = true;
    let r = run(&image("usbport"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-28-end.bin"));
    assert_eq!(&w[0..2], &[0, 0x8b5a], "a write: done at once");
    assert_eq!(&w[2..4], &[0, 0xcb5a], "a read of index 11: its byte");
    assert_eq!(&w[4..6], &[0, 0x86ff], "a write to an interrupt flag");
    assert_eq!(&w[6..8], &[0, 0xc600], "a read of index 6: nothing pending");
    assert_eq!(&w[8..10], &[0, 0xc100], "a read of an index never written: 0");
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
    // (an erase and a program, each waited for: 15 ms)
    let mut o = opts(50);
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

/// R-HARN-12: a dual-issue pair whose two halves write the same register
/// keeps the head's result, as the vendor compiler's code expects (vendor
/// patch 0011; fwtest 0.5.0 kept the second half's).
#[test]
fn pair_head_wins_over_its_second_half() {
    let mut o = opts(1);
    o.ram = vec![(OUT0, 16, When::End)];
    o.halt_ok = true;
    let r = run(&image("pairwaw"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    assert_eq!(words(output(&r, "ram-01c00100-10-end.bin")), vec![0x0008_0300, 0x78, 0x56, 0x34]);
}

/// SR-10: a store with a base update whose stored register is the base
/// stores the base as it was, in every form the vendor assembler takes
/// (selfstore.S), and in the vendor compiler's own code for C that stores a
/// pointer where it then points (selfc.c, built with the firmware's flags).
/// fwtest 0.8.0 stored the moved base in the pre-increment forms with an
/// immediate step.
#[test]
fn stores_of_the_base_keep_its_old_value() {
    let mut o = opts(1);
    o.ram = vec![(OUT0, 120, When::End)];
    o.halt_ok = true;
    let r = run(&image("selfstore"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-78-end.bin"));
    // case k: (the base before, its width, the step it moves by)
    let cases: [(&str, i32, u32, i32); 15] = [
        ("[++r4=748] = r4", -748, 4, 748),
        ("[++r1=8] = r1", -8, 4, 8),
        ("[++r1=-8] = r1", 8, 4, -8),
        ("[r1++=8] = r1", 0, 4, 8),
        ("[r4++=-4] = r4", 0, 4, -4),
        ("[r1++=4] = r1", 0, 4, 4),
        ("[++r1=r2] = r1", -8, 4, 8),
        ("[r1++=r2] = r1", 0, 4, 8),
        ("h[++r2=8] = r2", -8, 2, 8),
        ("h[++r1=-8] = r1", 8, 2, -8),
        ("h[r5++=2] = r5", 0, 2, 2),
        ("h[++r1=r2] = r1", -8, 2, 8),
        ("b[++r3=8] = r3", -8, 1, 8),
        ("b[r6++=1] = r6", 0, 1, 1),
        ("b[r1++=r2] = r1", 0, 1, 8),
    ];
    for (k, (form, before, width, step)) in cases.into_iter().enumerate() {
        let a = OUT0 + 8 * k as u32;
        let base = a.wrapping_add(before as u32);
        let mask = if width == 4 { u32::MAX } else { (1u32 << (8 * width)) - 1 };
        assert_eq!(w[2 * k], base & mask, "{form}: stores the base as it was");
        assert_eq!(w[2 * k + 1], base.wrapping_add(step as u32), "{form}: the moved base");
    }

    let mut o = opts(1);
    o.ram = vec![(OUT0, 40, When::End)];
    o.halt_ok = true;
    let r = run(&image("selfc"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-28-end.bin"));
    const BUF: u32 = 0x01c0_0400;
    assert_eq!((w[0], w[1]), (BUF, BUF + 748), "pre_w: [++r0=748] = r0");
    assert_eq!((w[2], w[3]), (BUF + 800, BUF + 808), "post_w: [r0++=8] = r0");
    assert_eq!((w[4], w[5]), ((BUF + 840) & 0xffff, BUF + 848), "pre_h: h[++r0=8] = r0");
    assert_eq!((w[6], w[7]), ((BUF + 880) & 0xff, BUF + 888), "pre_b: b[++r0=8] = r0");
    assert_eq!((w[8], w[9]), (BUF + 920 + 748, BUF + 920 + 748), "moved: the moved pointer");
}

/// The toolchain audit (session spec-isa-audit): C for which the pinned
/// compiler emits forms fwtest 0.9.0 could not run (isac.c, built with the
/// firmware's flags): floorf, ceilf and truncf, `__fp16` conversions, a
/// word in memory shifted by a register and cleared by a mask, and zcmp;
/// and one it ran wrongly, the 64-bit load whose index is scaled by 8.
#[test]
fn forms_the_compiler_emits() {
    let mut o = opts(5);
    o.ram = vec![(OUT0, 64, When::End)];
    o.halt_ok = true;
    let r = run(&image("isac"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-40-end.bin"));
    let f = |x: f32| x.to_bits();
    assert_eq!(&w[0..5], &[f(-3.0), f(-2.0), f(-2.0), f(7.0), f(-0.0)], "floorf, ceilf, truncf");
    // 0.1 to half is 0x2e66, 65520 rounds to infinity; 0x2e66 back is 0.0999755859375
    assert_eq!(w[5], 0x7c00_2e66, "float to __fp16");
    assert_eq!(w[6], f(0.099_975_586), "__fp16 to float");
    assert_eq!(&w[7..11], &[0x0000_f0f0, 1, 0xc000_0000, 0x0000_f00f], "<<=, >>=, >>>= and &= ~ in memory");
    assert_eq!((w[11], w[12]), (0x3f, 0x3f), "d[rB+rI<<3]");
    assert_eq!(&w[13..16], &[1, 0, u32::MAX], "zcmp");
}

/// The toolchain audit: forms only the assembler emits that fwtest 0.9.0
/// could not run or ran wrongly (isaasm.S): the float to integer
/// conversions rounding to even, up and down, the float rounding to even,
/// fcmp and the ten flag branches after it, ifne after testset, and a
/// word in memory shifted by 32.
#[test]
fn forms_only_the_assembler_emits() {
    let mut o = opts(1);
    o.ram = vec![(OUT0, 80, When::End)];
    o.halt_ok = true;
    let r = run(&image("isaasm"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-50-end.bin"));
    assert_eq!(&w[0..7], &[2, (-2i32) as u32, (-3i32) as u32, 2, 3, 2, (-2.0f32).to_bits()], "rounding conversions");
    // fcmp 1.0, 2.0: eq ne cs cc hi ls ge lt gt le
    assert_eq!(&w[7..17], &[0, 1, 0, 1, 0, 1, 0, 1, 0, 1], "flag branches after fcmp");
    assert_eq!(w[17], 1, "ifne after testset of a free byte");
    assert_eq!((w[18], w[19]), (0, u32::MAX), "<<= 32 and >>>= 32 in memory");
}

/// The toolchain audit: forms only the assembler emits whose result the
/// printed form leaves no choice in (isaregs.S): half moves, sat8 of a
/// half, the bit-field extract and insert with the field in a register,
/// the saturating shift in memory, the high half stored, the special
/// registers retx, sr4 and sspn, and the 4-byte push / pop of a list of
/// them.
#[test]
fn registers_halves_and_fields() {
    let mut o = opts(1);
    o.ram = vec![(OUT0, 64, When::End)];
    o.halt_ok = true;
    let r = run(&image("isaregs"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-40-end.bin"));
    assert_eq!(&w[0..2], &[0x1111_abcd, 0x0004_2222], "half moves");
    assert_eq!(&w[2..4], &[0xabcd_ff80, 0x0000_0004], "sat8 of a half");
    assert_eq!(&w[4..7], &[0xf8, 0xffff_fff8, 0xffff_f12f], "u/sextra and insert, the field in a register");
    assert_eq!(&w[7..9], &[0x7fff_ffff, 0x8000_0000], "<<<= in memory");
    assert_eq!(w[9], 0x0000_beef, "h[rB+rI<<1] = rS.h");
    assert_eq!(&w[10..13], &[0x1234, 0x5678, 0xaa], "sr4, sspn, retx");
    assert_eq!(&w[13..16], &[16, 0x1234, 0xbb], "push and pop of special registers");
}

/// The toolchain audit: forms only the assembler emits whose syntax is
/// explicit but a detail of whose result the toolchain leaves open
/// (isaops.S; HARDWARE-SPEC Q-31 to Q-33): the pair shifts rounding up, to
/// nearest with ties up, to even and toward zero; the memory multiplies; the
/// npc loads; rev16.
#[test]
fn forms_with_an_open_detail() {
    let mut o = opts(1);
    o.ram = vec![(OUT0, 68, When::End)];
    o.halt_ok = true;
    let r = run(&image("isaops"), &o).unwrap();
    assert!(matches!(r.outcome, Outcome::Halt { .. }), "{:?}", r.outcome);
    let w = words(output(&r, "ram-01c00100-44-end.bin"));
    // 2.5: up 3, round 3, even 2, zero 2; -1.5: up -1, round -1, even -2, zero -1
    assert_eq!(&w[0..4], &[3, 3, 2, 2], "rounding shifts, unsigned");
    assert_eq!(&w[4..8], &[-1i32 as u32, -1i32 as u32, -2i32 as u32, -1i32 as u32], "rounding shifts, signed");
    assert_eq!(&w[8..12], &[-15i32 as u32, u32::MAX, 327_660, 0x01c0_0408], "[rA ++= i]*rB, h[..]*rB");
    assert_eq!(&w[12..14], &[-14i32 as u32, u32::MAX], "[rA ++= i]*[rB ++= j]");
    assert_eq!(&w[14..16], &[0x600d_f00d, 0x5a5a_a5a5], "npc loads");
    assert_eq!(w[16], 0x5678_1234, "rev16");
}

fn fault_text(r: &fwtest::run::Report) -> (u32, u32, String) {
    match &r.outcome {
        Outcome::Fault { core, pc, what } => (*core, *pc, what.clone()),
        o => panic!("not a fault: {o:?}"),
    }
}

/// R-HARN-3: while the flash chip is busy, running code in the window or
/// reading it ends the run as a fault; code and handlers in RAM run on.
#[test]
fn flash_busy_and_the_window() {
    let r = run(&image("flashcall"), &opts(20)).unwrap();
    let (core, pc, what) = fault_text(&r);
    assert_eq!(core, 0);
    assert!((0x0200_0000..0x0210_0000).contains(&pc), "{pc:#x}");
    assert!(what.starts_with("ran code in the code window while the flash chip was busy"), "{what}");
    assert!(r.end_us < 1_000, "at once, not at the erase's end: {}", r.end_us);

    let mut o = opts(20);
    o.ram = vec![(OUT0, 8, When::End)];
    let r = run(&image("flashload"), &o).unwrap();
    let (core, pc, what) = fault_text(&r);
    assert_eq!(core, 0);
    assert!((0x01c4_0000..0x01c5_0000).contains(&pc), "the RAM routine: {pc:#x}");
    assert_eq!(what, "read the code window at 0x02000000 while the flash chip was busy (an erase or program in progress)");
    assert_eq!(words(output(&r, "ram-01c00100-8-end.bin"))[0], 0, "never ran past the read");

    // a helper in the window, already run (so decoded), called from RAM
    // just after an erase starts
    let mut o = opts(20);
    o.ram = vec![(OUT0, 12, When::End)];
    let r = run(&image("flashhelper"), &o).unwrap();
    let (core, pc, what) = fault_text(&r);
    assert_eq!(core, 0);
    assert!((0x0200_0000..0x0210_0000).contains(&pc), "{pc:#x}");
    assert!(what.starts_with("ran code in the code window while the flash chip was busy"), "{what}");
    assert_eq!(words(output(&r, "ram-01c00100-c-end.bin")), vec![0, 0, 4]);

    // a TIMER0 handler in RAM runs through a 12 ms erase and a 3 ms program;
    // moved to the window, the next tick during an erase is a fault
    let mut o = opts(60);
    o.ram = vec![(OUT0, 32, When::End)];
    let r = run(&image("flashirq"), &o).unwrap();
    let w = words(output(&r, "ram-01c00100-20-end.bin"));
    assert_eq!(w[0], 0x600d);
    assert_eq!((w[2] / 24_000, w[3] / 24_000), (12, 3), "erase and program in ms of TIMER4: {:?}", &w[2..4]);
    assert_eq!((w[4], w[5]), (12, 15), "ticks taken during them");
    let (_, pc, what) = fault_text(&r);
    assert!((0x0200_0000..0x0210_0000).contains(&pc) && what.starts_with("ran code in the code window"), "{pc:#x} {what}");
    assert_eq!((w[6], w[7]), (0, 0));
}

/// R-HARN-3: the flash persists across runs through files, `--flash-log`
/// lists the operations, and `--power-cut` keeps the part done of the
/// operation it interrupts.
#[test]
fn flash_persists_and_power_cuts() {
    let img = image("flashkeep");
    let mut o = opts(80);
    o.ram = vec![(OUT0, 8, When::End)];
    o.flash_out = true;
    o.flash_log = true;
    o.halt_ok = true;
    let first = run(&img, &o).unwrap();
    assert_eq!(words(output(&first, "ram-01c00100-8-end.bin")), vec![0xffff_ffff, 0x600d]);
    let chip = output(&first, "flash.bin").to_vec();
    assert_eq!(&chip[0x80000..0x80004], &[1, 0, 0, 0]);
    assert!(chip[0x80004..0x81000].iter().all(|&b| b == 0));
    let log = String::from_utf8(output(&first, "flash-ops.csv").to_vec()).unwrap();
    let rows: Vec<&str> = log.lines().collect();
    assert_eq!(rows[0], "start_ms,end_ms,command,offset,bytes");
    assert_eq!(rows.len(), 17, "16 page programs: {log}");
    assert!(rows[1].ends_with(",02,0x080000,256") && rows[16].ends_with(",02,0x080f00,256"), "{log}");

    // the second run reads 1, erases the sector and programs 2
    o.flash_in = Some(chip.clone());
    let second = run(&img, &o).unwrap();
    assert_eq!(words(output(&second, "ram-01c00100-8-end.bin")), vec![1, 0x600d]);
    assert_eq!(&output(&second, "flash.bin")[0x80000..0x80004], &[2, 0, 0, 0]);
    let log = String::from_utf8(output(&second, "flash-ops.csv").to_vec()).unwrap();
    let erase: Vec<&str> = log.lines().nth(1).unwrap().split(',').collect();
    assert_eq!(&erase[2..], &["20", "0x080000", "4096"], "{log}");
    let start_us = (erase[0].parse::<f64>().unwrap() * 1000.0).round() as u64;

    // cut a quarter of the way through that erase: its first 1 KiB erased
    let mut c = Options { ms_us: start_us + 3_000, flash_in: Some(chip), power_cut: true, ..Default::default() };
    c.ram = vec![(OUT0, 8, When::End)];
    let cut = run(&img, &c).unwrap();
    let done = match cut.outcome {
        Outcome::PowerCut { op: Some((0x20, 0x80000, 4096, done)) } => done,
        ref o => panic!("{o:?}"),
    };
    assert!((1000..1100).contains(&done), "{done}");
    let f = output(&cut, "flash.bin");
    assert!(f[0x80000..0x80000 + done].iter().all(|&b| b == 0xff), "the part done");
    assert!(f[0x80000 + done..0x81000].iter().all(|&b| b == 0), "the rest as before");
    assert_eq!(words(output(&cut, "ram-01c00100-8-end.bin"))[1], 0, "the image never finished");

    // a cut with nothing in progress, and the chip saved without --flash-out
    let c = Options { ms_us: 5_000, power_cut: true, ..Default::default() };
    let r = run(&image("heartbeat"), &c).unwrap();
    assert_eq!(r.outcome, Outcome::PowerCut { op: None });
    assert_eq!(output(&r, "flash.bin").len(), 0x100000);
}

/// R-HARN-3: `--power-cut` on the command line: exit 0, `power-cut` as a
/// suite expectation, and not with `--ms`.
#[test]
fn power_cut_command_line() {
    let d = scratch("powercut");
    let img = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/images/flashkeep.bin");
    let (code, text) = fwtest(&["run", img.to_str().unwrap(), "--power-cut", "20", "--out", d.join("a").to_str().unwrap()]);
    assert_eq!(code, 0, "{text}");
    assert!(d.join("a/flash.bin").exists());
    let result = std::fs::read_to_string(d.join("a/result.json")).unwrap();
    assert!(result.contains("\"outcome\": \"power-cut\""), "{result}");
    let (code, text) = fwtest(&["run", img.to_str().unwrap(), "--ms", "5", "--power-cut", "20", "--out", d.join("b").to_str().unwrap()]);
    assert_eq!(code, 2, "{text}");
    let (code, text) = fwtest(&["run", img.to_str().unwrap(), "--ms", "5", "--ms", "6", "--out", d.join("c").to_str().unwrap()]);
    assert_eq!(code, 2, "{text}");
    assert!(text.contains("--ms given twice"), "{text}");
}
