// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 japes98
//! One run: boot an image, feed the script, take the captures asked for,
//! stop on a fault, halt, hang or the time limit, and describe the outcome.

use crate::formats::{self, Json};
use crate::machine::{Board, Stop, CYCLES_PER_MS, SLICE};
use crate::script;
use std::collections::BTreeMap;

/// When a capture is taken: at an emulated time (microseconds), or at the end.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum When {
    At(u64),
    End,
}

impl When {
    pub fn parse(s: &str) -> Result<When, String> {
        if s == "end" { Ok(When::End) } else { script::parse_ms(s).map(When::At) }
    }

    /// The name part used in output file names: `12ms`, `12.500ms`, `end`.
    pub fn label(&self) -> String {
        match self {
            When::End => "end".into(),
            When::At(us) if us % 1000 == 0 => format!("{}ms", us / 1000),
            When::At(us) => format!("{}.{:03}ms", us / 1000, us % 1000),
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct Options {
    pub ms_us: u64,
    pub script: Vec<script::Event>,
    pub flash_in: Option<Vec<u8>>,
    pub ram: Vec<(u32, u32, When)>,
    pub lcd: Vec<When>,
    pub leds_every_us: Option<u64>,
    pub flash_out: bool,
    pub wav: bool,
    pub ipb: bool,
    pub console: bool,
    pub watchdog: Option<(u32, u64)>,
    pub halt_ok: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Outcome {
    Completed,
    Halt { pc: u32 },
    Fault { core: u32, pc: u32, what: String },
    Hang { addr: u32, ms: u64 },
}

impl Outcome {
    pub fn name(&self) -> &'static str {
        match self {
            Outcome::Completed => "completed",
            Outcome::Halt { .. } => "halt",
            Outcome::Fault { .. } => "fault",
            Outcome::Hang { .. } => "hang",
        }
    }

    pub fn detail(&self) -> String {
        match self {
            Outcome::Completed => "ran for the whole time asked".into(),
            Outcome::Halt { pc } => format!("core 0 jumped to itself with interrupts disabled at pc {pc:#010x}"),
            Outcome::Fault { core, pc, what } => format!("core {core} at pc {pc:#010x}: {what}"),
            Outcome::Hang { addr, ms } => format!("the watched word at {addr:#010x} did not change for {ms} ms"),
        }
    }
}

pub struct Output {
    pub name: String,
    pub data: Vec<u8>,
}

pub struct Report {
    pub outcome: Outcome,
    pub end_us: u64,
    pub instructions: (u64, u64),
    pub outputs: Vec<Output>,
    pub unmodelled: Vec<(u32, bool, u64)>,
    pub midi_dropped: u64,
}

const LEDS: usize = script::KEYS as usize;

fn lcd_png(board: &Board) -> Vec<u8> {
    // RGB565 to RGB888 as upstream's `write_bmp` does; the framebuffer as
    // written (inversion is the panel's native mode, see lcd.rs)
    let fb = &board.soc.lcd.fb;
    let mut rgb = Vec::with_capacity(fb.len() * 3);
    for &p in fb {
        rgb.push(((((p >> 11) & 0x1f) as u32) * 255 / 31) as u8);
        rgb.push(((((p >> 5) & 0x3f) as u32) * 255 / 63) as u8);
        rgb.push((((p & 0x1f) as u32) * 255 / 31) as u8);
    }
    formats::png(240, 240, &rgb)
}

/// Runs `image` with `opt`. Errors are bad input (a capture outside RAM).
pub fn run(image: &[u8], opt: &Options) -> Result<Report, String> {
    let mut board = Board::boot(image, opt.flash_in.as_deref())?;
    for e in &opt.script {
        board.soc.periph.script.push_back((e.cycle, e.action.clone()));
    }
    let end_cycle = script::us_to_cycles(opt.ms_us);
    // timed captures, in time order: (cycle, kind index)
    let mut timed: BTreeMap<u64, Vec<Capture>> = BTreeMap::new();
    for (i, (_, _, w)) in opt.ram.iter().enumerate() {
        if let When::At(us) = w {
            timed.entry(script::us_to_cycles(*us)).or_default().push(Capture::Ram(i));
        }
    }
    for w in &opt.lcd {
        if let When::At(us) = w {
            timed.entry(script::us_to_cycles(*us)).or_default().push(Capture::Lcd(*w));
        }
    }
    if let Some(every) = opt.leds_every_us {
        let mut t = every;
        while t <= opt.ms_us {
            timed.entry(script::us_to_cycles(t)).or_default().push(Capture::Leds(t));
            t += every;
        }
    }
    for (addr, len, _) in &opt.ram {
        if board.read_ram(*addr, *len).is_none() || *len == 0 {
            return Err(format!("--ram {addr:#010x}:{len:#x} is not inside RAM"));
        }
    }
    if let Some((addr, _)) = opt.watchdog {
        if board.word(addr).is_none() {
            return Err(format!("--watchdog address {addr:#010x} is not inside RAM"));
        }
    }

    let mut outputs: Vec<Output> = Vec::new();
    let mut led_rows: Vec<String> = Vec::new();
    let mut wd_last = opt.watchdog.and_then(|(a, _)| board.word(a));
    let mut wd_since = 0u64;
    let outcome = loop {
        let now = board.cycles();
        // captures due by now (taken at the first instruction boundary at or after their time)
        while let Some((&at, _)) = timed.first_key_value() {
            if at > now {
                break;
            }
            for c in timed.remove(&at).unwrap() {
                take(&mut board, &c, opt, &mut outputs, &mut led_rows);
            }
        }
        if let Some((addr, ms)) = opt.watchdog {
            let v = board.word(addr);
            if v != wd_last {
                wd_last = v;
                wd_since = now;
            } else if now - wd_since > ms * CYCLES_PER_MS {
                break Outcome::Hang { addr, ms };
            }
        }
        if now >= end_cycle {
            break Outcome::Completed;
        }
        let mut n = SLICE as u64;
        for bound in [Some(end_cycle), timed.first_key_value().map(|(c, _)| *c)].into_iter().flatten() {
            n = n.min(bound.saturating_sub(now).max(1));
        }
        match board.run(n as u32) {
            Ok(()) => {}
            Err(Stop::Halt { pc }) => break Outcome::Halt { pc },
            Err(Stop::Fault { core, pc, what }) => break Outcome::Fault { core, pc, what },
        }
    };

    // end-of-run captures
    for (i, (_, _, w)) in opt.ram.iter().enumerate() {
        if *w == When::End {
            take(&mut board, &Capture::Ram(i), opt, &mut outputs, &mut led_rows);
        }
    }
    if opt.lcd.contains(&When::End) {
        take(&mut board, &Capture::Lcd(When::End), opt, &mut outputs, &mut led_rows);
    }
    if opt.leds_every_us.is_some() {
        let mut s = String::from("ms");
        for i in 0..LEDS {
            s.push_str(&format!(",led{i}"));
        }
        s.push('\n');
        for r in &led_rows {
            s.push_str(r);
        }
        outputs.push(Output { name: "leds.csv".into(), data: s.into_bytes() });
    }
    if opt.flash_out {
        outputs.push(Output { name: "flash.bin".into(), data: board.soc.flash.mem.clone() });
    }
    if opt.wav {
        outputs.push(Output { name: "audio.wav".into(), data: formats::wav(44100, 2, &board.soc.periph.audio) });
    }
    if opt.ipb {
        let mut s = String::from("block,end_ms,core0,core1\n");
        let (mut p0, mut p1) = (0u64, 0u64);
        for (i, b) in board.blocks.iter().enumerate() {
            let us = b.cycle / (CYCLES_PER_MS / 1000);
            s.push_str(&format!("{},{}.{:03},{},{}\n", i, us / 1000, us % 1000, b.core0 - p0, b.core1.saturating_sub(p1)));
            p0 = b.core0;
            p1 = b.core1;
        }
        outputs.push(Output { name: "ipb.csv".into(), data: s.into_bytes() });
    }
    if opt.console {
        outputs.push(Output { name: "console.txt".into(), data: board.soc.console.clone() });
    }
    outputs.sort_by(|a, b| a.name.cmp(&b.name));

    let mut seen: BTreeMap<(u32, bool), u64> = BTreeMap::new();
    for a in board.soc.unknown_accesses() {
        *seen.entry((a.addr, a.is_write)).or_default() += 1;
    }
    let cyc_us = CYCLES_PER_MS / 1000;
    Ok(Report {
        outcome,
        end_us: board.cycles() / cyc_us,
        instructions: board.instructions(),
        outputs,
        unmodelled: seen.into_iter().map(|((a, w), n)| (a, w, n)).collect(),
        midi_dropped: board.soc.periph.midi_dropped(),
    })
}

enum Capture {
    Ram(usize),
    Lcd(When),
    Leds(u64),
}

fn take(board: &mut Board, c: &Capture, opt: &Options, outputs: &mut Vec<Output>, led_rows: &mut Vec<String>) {
    match c {
        Capture::Ram(i) => {
            let (addr, len, w) = opt.ram[*i];
            let data = board.read_ram(addr, len).expect("checked at start");
            outputs.push(Output { name: format!("ram-{addr:08x}-{len:x}-{}.bin", w.label()), data });
        }
        Capture::Lcd(w) => outputs.push(Output { name: format!("lcd-{}.png", w.label()), data: lcd_png(board) }),
        Capture::Leds(t) => {
            // per mille of the time since the last sample each LED was lit
            let duty = board.soc.periph.led_take();
            let mut row = When::At(*t).label().trim_end_matches("ms").to_string();
            for d in duty.iter().take(LEDS) {
                row.push_str(&format!(",{}", (d * 1000.0).round() as u32));
            }
            row.push('\n');
            led_rows.push(row);
        }
    }
}

/// The run's part of result.json.
pub fn report_json(r: &Report) -> Json {
    let outs = r.outputs.iter().map(|o| Json::obj(vec![
        ("name", Json::str(o.name.clone())),
        ("bytes", Json::Int(o.data.len() as i64)),
        ("sha256", Json::str(formats::sha256(&o.data))),
    ])).collect();
    let unmod = r.unmodelled.iter().take(256).map(|(a, w, n)| Json::obj(vec![
        ("address", Json::str(format!("{a:#010x}"))),
        ("access", Json::str(if *w { "write" } else { "read" })),
        ("count", Json::Int(*n as i64)),
    ])).collect();
    Json::obj(vec![
        ("outcome", Json::str(r.outcome.name())),
        ("detail", Json::str(r.outcome.detail())),
        ("emulated_ms", Json::str(format!("{}.{:03}", r.end_us / 1000, r.end_us % 1000))),
        ("instructions", Json::obj(vec![("core0", Json::Int(r.instructions.0 as i64)), ("core1", Json::Int(r.instructions.1 as i64))])),
        ("midi_bytes_dropped", Json::Int(r.midi_dropped as i64)),
        ("unmodelled_accesses", Json::Arr(unmod)),
        ("outputs", Json::Arr(outs)),
    ])
}
