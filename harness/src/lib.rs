// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 japes98
//! fwtest: runs a raw image in the vendored emulator and reports what it did
//! (docs/HARNESS.md is the user's manual; nothing here is visible to the
//! firmware side except through it).

pub mod decode;
pub mod formats;
pub mod golden;
pub mod machine;
pub mod midi;
pub mod run;
pub mod script;

use formats::{Case, Json};
use run::{Options, Outcome, When};
use std::path::{Path, PathBuf};

/// The vendored emulator's upstream commit (vendor/emulator/UPSTREAM.md).
pub const EMULATOR_COMMIT: &str = "43ed5580064885e93bc8d20be931ae950d10cd4f";

pub mod exit {
    pub const OK: i32 = 0;
    pub const GOLDEN_MISMATCH: i32 = 1;
    pub const USAGE: i32 = 2;
    pub const FAULT: i32 = 3;
    pub const HALT: i32 = 4;
    pub const HANG: i32 = 5;
    pub const TRAP: i32 = 6;
}

pub const USAGE: &str = "\
usage:
  fwtest run IMAGE --ms MS --out DIR [options]
  fwtest run PACKAGE --package --ms MS --out DIR [options]
  fwtest suite FILE --out DIR
  fwtest decode FILE
  fwtest version

run options:
  --package              the input is an update package (.fwsc), booted as the
                         package path does
  --script FILE          timed inputs (keys, encoders, pot, MIDI)
  --flash FILE           initial contents of the flash chip
  --ram ADDR:LEN@WHEN    save LEN bytes of RAM at ADDR (hex with 0x, or decimal)
  --lcd WHEN             save the screen as PNG
  --leds-every MS        sample the LEDs every MS into leds.csv
  --flash-out            save the flash chip at the end (flash.bin)
  --flash-log            the erases and programs started (flash-ops.csv)
  --power-cut MS         end the run at MS as a power cut, saving flash.bin
  --wav                  save the audio output (audio.wav)
  --ipb                  instructions per audio block (ipb.csv)
  --console              save the debug console bytes (console.txt)
  --midi-out             save the MIDI output (midi-out.csv, midi-out.txt)
  --watchdog ADDR:MS     a hang if the word at ADDR stays the same for MS
  --halt-ok              a halt counts as success
  --golden DIR           compare the outputs with the golden files in DIR
WHEN is a time in ms (up to three decimals) or `end`.

decode: FILE has one instruction per line, its bytes in hex as they lie in
memory; each output line is the hex, the length fwtest decodes it to (- if
none) and runs, no-decode, unsupported, trap or panic (docs/HARNESS.md,
\"Instructions\").";

/// Removes every FM1_* variable: upstream reads several to switch traces and
/// execution paths, which would break determinism (machine.rs).
pub fn scrub_environment() {
    let names: Vec<_> = std::env::vars_os().map(|(k, _)| k).filter(|k| k.to_string_lossy().starts_with("FM1_")).collect();
    for k in names {
        std::env::remove_var(k);
    }
}

fn version_json() -> Json {
    Json::obj(vec![("version", Json::str(env!("CARGO_PKG_VERSION"))), ("emulator_commit", Json::str(EMULATOR_COMMIT))])
}

fn number(s: &str) -> Result<u32, String> {
    let r = match s.strip_prefix("0x").or_else(|| s.strip_prefix("0X")) {
        Some(h) => u32::from_str_radix(&h.replace('_', ""), 16),
        None => s.parse::<u32>(),
    };
    r.map_err(|_| format!("bad number {s:?}"))
}

/// A parsed `run` command line.
pub struct RunArgs {
    pub image: PathBuf,
    pub out: PathBuf,
    pub golden: Option<PathBuf>,
    pub script: Option<PathBuf>,
    pub opt: Options,
}

fn read(path: &Path, what: &str) -> Result<Vec<u8>, String> {
    std::fs::read(path).map_err(|e| format!("cannot read {what} {}: {e}", path.display()))
}

/// Parses `run` arguments; relative paths are taken from `base`.
pub fn parse_run(args: &[String], base: &Path) -> Result<RunArgs, String> {
    let mut image = None;
    let mut out = None;
    let mut golden = None;
    let mut script_path = None;
    let mut ms = None;
    let mut opt = Options::default();
    let mut flash = None;
    let mut it = args.iter();
    let path = |s: &String| base.join(s);
    while let Some(a) = it.next() {
        let mut val = |name: &str| it.next().cloned().ok_or_else(|| format!("{name} needs a value"));
        match a.as_str() {
            "--ms" => {
                if ms.is_some() {
                    return Err(if opt.power_cut { "--power-cut sets the run's end: give it or --ms, not both" } else { "--ms given twice" }.into());
                }
                ms = Some(script::parse_ms(&val("--ms")?)?)
            }
            "--out" => out = Some(path(&val("--out")?)),
            "--script" => script_path = Some(path(&val("--script")?)),
            "--flash" => flash = Some(path(&val("--flash")?)),
            "--golden" => golden = Some(path(&val("--golden")?)),
            "--ram" => {
                let v = val("--ram")?;
                let (al, w) = v.split_once('@').ok_or("--ram needs ADDR:LEN@WHEN")?;
                let (a, l) = al.split_once(':').ok_or("--ram needs ADDR:LEN@WHEN")?;
                opt.ram.push((number(a)?, number(l)?, When::parse(w)?));
            }
            "--lcd" => opt.lcd.push(When::parse(&val("--lcd")?)?),
            "--leds-every" => {
                let us = script::parse_ms(&val("--leds-every")?)?;
                if us == 0 {
                    return Err("--leds-every must be more than 0".into());
                }
                opt.leds_every_us = Some(us);
            }
            "--watchdog" => {
                let v = val("--watchdog")?;
                let (a, m) = v.split_once(':').ok_or("--watchdog needs ADDR:MS")?;
                opt.watchdog = Some((number(a)?, number(m)? as u64));
            }
            "--flash-out" => opt.flash_out = true,
            "--flash-log" => opt.flash_log = true,
            "--power-cut" => {
                if ms.is_some() {
                    return Err(if opt.power_cut { "--power-cut given twice" } else { "--power-cut sets the run's end: give it or --ms, not both" }.into());
                }
                ms = Some(script::parse_ms(&val("--power-cut")?)?);
                opt.power_cut = true;
            }
            "--wav" => opt.wav = true,
            "--ipb" => opt.ipb = true,
            "--console" => opt.console = true,
            "--midi-out" => opt.midi_out = true,
            "--halt-ok" => opt.halt_ok = true,
            "--package" => opt.package = true,
            s if s.starts_with("--") => return Err(format!("unknown option {s}")),
            s if image.is_none() => image = Some(path(&s.to_string())),
            s => return Err(format!("unexpected argument {s:?}")),
        }
    }
    opt.ms_us = ms.ok_or("--ms (or --power-cut) is required")?;
    if opt.ms_us == 0 {
        return Err("--ms must be more than 0".into());
    }
    if let Some(f) = flash {
        opt.flash_in = Some(read(&f, "flash file")?);
    }
    if let Some(s) = &script_path {
        let text = String::from_utf8(read(s, "script")?).map_err(|_| "the script is not UTF-8 text".to_string())?;
        opt.script = script::parse(&text)?;
    }
    opt.lcd.sort();
    opt.lcd.dedup();
    Ok(RunArgs { image: image.ok_or("IMAGE is required")?, out: out.ok_or("--out is required")?, golden, script: script_path, opt })
}

/// The result of one run, before it is written out.
pub struct Done {
    pub exit: i32,
    pub json: Json,
    pub cases: Vec<Case>,
    pub outcome: String,
}

/// Runs, writes the outputs, result.json and junit.xml into `out`.
pub fn execute(a: &RunArgs, suite_name: &str) -> Result<Done, String> {
    let image = read(&a.image, "image")?;
    let report = run::run(&image, &a.opt)?;
    prepare_out(&a.out)?;
    for o in &report.outputs {
        std::fs::write(a.out.join(&o.name), &o.data).map_err(|e| format!("cannot write {}: {e}", o.name))?;
    }
    let outs: Vec<(String, Vec<u8>)> = report.outputs.iter().map(|o| (o.name.clone(), o.data.clone())).collect();
    let checks = match &a.golden {
        Some(d) => golden::check(d, &outs)?,
        None => Vec::new(),
    };
    let mismatch = checks.iter().any(|c| c.problem.is_some());
    let exit = match &report.outcome {
        Outcome::Fault { .. } => exit::FAULT,
        Outcome::Trap { .. } => exit::TRAP,
        Outcome::Hang { .. } => exit::HANG,
        _ if mismatch => exit::GOLDEN_MISMATCH,
        Outcome::Halt { .. } if !a.opt.halt_ok => exit::HALT,
        _ => exit::OK,
    };
    let mut cases = vec![Case {
        name: "run".into(),
        failure: match (&report.outcome, a.opt.halt_ok) {
            (Outcome::Completed | Outcome::PowerCut { .. }, _) | (Outcome::Halt { .. }, true) => None,
            (o, _) => Some(format!("{}: {}", o.name(), o.detail())),
        },
    }];
    for c in &checks {
        cases.push(Case { name: format!("golden {}", c.name), failure: c.problem.clone() });
    }
    let script_hash = match &a.script {
        Some(p) => Json::str(formats::sha256(&read(p, "script")?)),
        None => Json::Null,
    };
    let json = Json::obj(vec![
        ("fwtest", version_json()),
        ("image", Json::obj(vec![
            ("name", Json::str(a.image.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default())),
            ("bytes", Json::Int(image.len() as i64)),
            ("sha256", Json::str(formats::sha256(&image))),
        ])),
        ("script_sha256", script_hash),
        ("run", run::report_json(&report)),
        ("golden", Json::Arr(checks.iter().map(|c| Json::obj(vec![
            ("name", Json::str(c.name.clone())),
            ("result", Json::str(if c.problem.is_none() { "match" } else { "mismatch" })),
            ("detail", c.problem.clone().map(Json::Str).unwrap_or(Json::Null)),
        ])).collect())),
        ("exit_code", Json::Int(exit as i64)),
    ]);
    std::fs::write(a.out.join("result.json"), json.to_text()).map_err(|e| format!("cannot write result.json: {e}"))?;
    std::fs::write(a.out.join("junit.xml"), formats::junit(suite_name, &cases)).map_err(|e| format!("cannot write junit.xml: {e}"))?;
    Ok(Done { exit, json, cases, outcome: report.outcome.name().to_string() })
}

fn prepare_out(out: &Path) -> Result<(), String> {
    if out.exists() {
        let mut entries = std::fs::read_dir(out).map_err(|e| format!("cannot read {}: {e}", out.display()))?;
        if entries.next().is_some() {
            return Err(format!("--out {} is not empty", out.display()));
        }
    }
    std::fs::create_dir_all(out).map_err(|e| format!("cannot create {}: {e}", out.display()))
}

/// `fwtest suite FILE --out DIR`: each line `NAME EXPECT IMAGE [run options]`.
pub fn suite(file: &Path, out: &Path) -> Result<i32, String> {
    let text = String::from_utf8(read(file, "suite")?).map_err(|_| "the suite is not UTF-8 text".to_string())?;
    let base = file.parent().unwrap_or(Path::new("."));
    let suite_name = file.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_else(|| "suite".into());
    prepare_out(out)?;
    let mut cases = Vec::new();
    let mut results = Vec::new();
    let mut all_ok = true;
    for (n, raw) in text.lines().enumerate() {
        let line = raw.split('#').next().unwrap_or("").trim();
        if line.is_empty() {
            continue;
        }
        let w: Vec<String> = line.split_whitespace().map(String::from).collect();
        if w.len() < 3 {
            return Err(format!("suite line {}: expected `NAME EXPECT IMAGE [options]`", n + 1));
        }
        let (name, expect) = (&w[0], &w[1]);
        if !["completed", "halt", "fault", "trap", "hang", "power-cut"].contains(&expect.as_str()) || !name.chars().all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_') {
            return Err(format!("suite line {}: bad name or expectation (completed, halt, fault, trap, hang, power-cut)", n + 1));
        }
        let mut args = w[2..].to_vec();
        args.push("--out".into());
        args.push(out.join(name).to_string_lossy().into_owned());
        // the case folder is under `out`, not `base`: give it absolute
        let mut ra = parse_run(&args, base).map_err(|e| format!("suite line {} ({name}): {e}", n + 1))?;
        ra.out = out.join(name);
        let d = execute(&ra, &format!("{suite_name}.{name}")).map_err(|e| format!("suite case {name}: {e}"))?;
        let golden_ok = d.cases.iter().skip(1).all(|c| c.failure.is_none());
        let ok = d.outcome == *expect && golden_ok;
        all_ok &= ok;
        cases.push(Case {
            name: name.clone(),
            failure: (!ok).then(|| {
                let mut f = format!("expected {expect}, got {}", d.outcome);
                for c in d.cases.iter().skip(1).filter(|c| c.failure.is_some()) {
                    f.push_str(&format!("; {}: {}", c.name, c.failure.as_deref().unwrap_or("")));
                }
                f
            }),
        });
        results.push(Json::obj(vec![("name", Json::str(name.clone())), ("expect", Json::str(expect.clone())), ("pass", Json::Bool(ok)), ("result", d.json)]));
    }
    let json = Json::obj(vec![("fwtest", version_json()), ("suite", Json::str(suite_name.clone())), ("pass", Json::Bool(all_ok)), ("cases", Json::Arr(results))]);
    std::fs::write(out.join("result.json"), json.to_text()).map_err(|e| format!("cannot write result.json: {e}"))?;
    std::fs::write(out.join("junit.xml"), formats::junit(&suite_name, &cases)).map_err(|e| format!("cannot write junit.xml: {e}"))?;
    Ok(if all_ok { exit::OK } else { exit::GOLDEN_MISMATCH })
}

/// The CLI; returns the exit code.
pub fn main_with(args: &[String]) -> i32 {
    let fail = |e: String| {
        eprintln!("fwtest: {e}");
        exit::USAGE
    };
    match args.first().map(String::as_str) {
        Some("run") => match parse_run(&args[1..], Path::new("")).and_then(|a| execute(&a, "fwtest")) {
            Ok(d) => {
                println!("fwtest: {} (exit {})", d.outcome, d.exit);
                for c in d.cases.iter().filter(|c| c.failure.is_some()) {
                    println!("  FAIL {}: {}", c.name, c.failure.as_deref().unwrap_or(""));
                }
                d.exit
            }
            Err(e) => fail(e),
        },
        Some("suite") => {
            let (file, out) = match &args[1..] {
                [f, o, d] if o == "--out" => (PathBuf::from(f), PathBuf::from(d)),
                _ => return fail(format!("bad suite arguments\n{USAGE}")),
            };
            match suite(&file, &out) {
                Ok(code) => {
                    println!("fwtest suite: {}", if code == 0 { "PASS" } else { "FAIL" });
                    code
                }
                Err(e) => fail(e),
            }
        }
        Some("decode") => match &args[1..] {
            [f] => match std::fs::read_to_string(f).map_err(|e| format!("{f}: {e}")).and_then(|t| decode::report(&t)) {
                Ok(r) => {
                    print!("{r}");
                    exit::OK
                }
                Err(e) => fail(e),
            },
            _ => fail(format!("bad decode arguments\n{USAGE}")),
        },
        Some("version") | Some("--version") => {
            println!("fwtest {} (emulator {})", env!("CARGO_PKG_VERSION"), &EMULATOR_COMMIT[..12]);
            exit::OK
        }
        Some("help") | Some("--help") | Some("-h") => {
            println!("{USAGE}");
            exit::OK
        }
        _ => fail(USAGE.to_string()),
    }
}
