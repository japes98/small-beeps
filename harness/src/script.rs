// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 japes98
//! The timed input script (docs/HARNESS.md, "Input scripts").
//!
//! One event per line, `<time> <what> ...`, times in emulated milliseconds
//! with up to three decimals. Events go into the SoC's own schedule
//! (`periph.script`), which applies each at its exact cycle. This format is
//! fwtest's own: upstream's `script::queue` and key names are not used.
//!
//!   <t> key <n> down | up | tap [<hold ms>]      key n (0..40); tap: down, then up
//!   <t> enc <n> <+clicks | -clicks>              encoder n (0..6), + is clockwise
//!   <t> pot <value>                              the pot's reading, 0..1023
//!   <t> midi <hex byte> [<hex byte> ...]         bytes into the MIDI input
//!
//! Key ids are `fm1_soc::periph`'s matrix ids (`Action::Key`), encoder ids
//! its `ENC` index, and the pot is ADC channel 4 (`adc_value[4]`).

use fm1_soc::Action;

pub const KEYS: u8 = 41;
pub const ENCODERS: u8 = 7;
const POT_CHANNEL: u8 = 4;
const DEFAULT_TAP_MS: u64 = 50;

#[derive(Debug, Clone, PartialEq)]
pub struct Event {
    /// Emulated cycle the event is due at.
    pub cycle: u64,
    pub action: Action,
}

/// Microseconds from `12`, `12.5`, `0.125` (milliseconds).
pub fn parse_ms(s: &str) -> Result<u64, String> {
    let bad = || format!("bad time {s:?} (milliseconds, up to three decimals)");
    let (whole, frac) = s.split_once('.').unwrap_or((s, ""));
    if whole.is_empty() || !whole.bytes().all(|b| b.is_ascii_digit()) || frac.len() > 3 || !frac.bytes().all(|b| b.is_ascii_digit()) {
        return Err(bad());
    }
    let w: u64 = whole.parse().map_err(|_| bad())?;
    let f: u64 = if frac.is_empty() { 0 } else { format!("{frac:0<3}").parse().map_err(|_| bad())? };
    w.checked_mul(1000).and_then(|x| x.checked_add(f)).ok_or_else(bad)
}

pub fn us_to_cycles(us: u64) -> u64 {
    us * (super::machine::CYCLES_PER_MS / 1000)
}

fn number(s: &str, what: &str, max: u64) -> Result<u64, String> {
    let v = s.parse::<u64>().map_err(|_| format!("bad {what} {s:?}"))?;
    if v > max {
        return Err(format!("{what} {v} is out of range (0..{max})"));
    }
    Ok(v)
}

/// Parses a whole script. Errors name the line.
pub fn parse(text: &str) -> Result<Vec<Event>, String> {
    let mut events = Vec::new();
    for (n, raw) in text.lines().enumerate() {
        let line = raw.split('#').next().unwrap_or("").trim();
        if line.is_empty() {
            continue;
        }
        parse_line(line, &mut events).map_err(|e| format!("script line {}: {e}", n + 1))?;
    }
    // stable: events at the same time keep the script's order
    events.sort_by_key(|e| e.cycle);
    Ok(events)
}

fn parse_line(line: &str, events: &mut Vec<Event>) -> Result<(), String> {
    let w: Vec<&str> = line.split_whitespace().collect();
    if w.len() < 2 {
        return Err("expected `<time> <event> ...`".into());
    }
    let at = parse_ms(w[0])?;
    let cycle = us_to_cycles(at);
    let mut push = |cycle: u64, action: Action| events.push(Event { cycle, action });
    match (w[1], &w[2..]) {
        ("key", [id, rest @ ..]) => {
            let id = number(id, "key", KEYS as u64 - 1)? as u8;
            match rest {
                ["down"] => push(cycle, Action::Key { id, down: true }),
                ["up"] => push(cycle, Action::Key { id, down: false }),
                ["tap"] | ["tap", _] => {
                    let hold = match rest.get(1) {
                        Some(h) => parse_ms(h)?,
                        None => DEFAULT_TAP_MS * 1000,
                    };
                    push(cycle, Action::Key { id, down: true });
                    push(us_to_cycles(at + hold), Action::Key { id, down: false });
                }
                _ => return Err("key: expected `key <n> down|up|tap [<hold ms>]`".into()),
            }
        }
        ("enc", [id, clicks]) => {
            let enc = number(id, "encoder", ENCODERS as u64 - 1)? as u8;
            let c = clicks.strip_prefix('+').unwrap_or(clicks);
            let clicks: i32 = c.parse().map_err(|_| format!("bad clicks {clicks:?} (e.g. +3 or -2)"))?;
            if clicks == 0 || clicks.abs() > 1000 {
                return Err("clicks must be 1..1000 either way".into());
            }
            push(cycle, Action::Enc { enc, clicks });
        }
        ("pot", [v]) => {
            let value = number(v, "pot value", 1023)? as u16;
            push(cycle, Action::Adc { ch: POT_CHANNEL, value });
        }
        ("midi", bytes) if !bytes.is_empty() => {
            for b in bytes {
                let v = u8::from_str_radix(b, 16).ok().filter(|_| b.len() == 2).ok_or_else(|| format!("bad MIDI byte {b:?} (two hex digits)"))?;
                push(cycle, Action::Midi { b: v });
            }
        }
        (other, _) => return Err(format!("unknown or malformed event {other:?} (key, enc, pot, midi)")),
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_every_event_kind_in_time_order() {
        let ev = parse("# a comment\n10 key 12 tap\n5 enc 2 -3\n5 pot 512\n0.5 midi 90 3c 64 # note\n").unwrap();
        let acts: Vec<_> = ev.iter().map(|e| (e.cycle, e.action.clone())).collect();
        let ms = super::super::machine::CYCLES_PER_MS;
        assert_eq!(acts, vec![
            (ms / 2, Action::Midi { b: 0x90 }), (ms / 2, Action::Midi { b: 0x3c }), (ms / 2, Action::Midi { b: 0x64 }),
            (5 * ms, Action::Enc { enc: 2, clicks: -3 }), (5 * ms, Action::Adc { ch: 4, value: 512 }),
            (10 * ms, Action::Key { id: 12, down: true }), (60 * ms, Action::Key { id: 12, down: false }),
        ]);
    }

    #[test]
    fn rejects_bad_lines_with_their_number() {
        for bad in ["x key 1 down", "1 key 41 down", "1 enc 7 +1", "1 enc 0 0", "1 pot 1024", "1 midi 9", "1 dance", "1.2345 pot 1"] {
            let e = parse(&format!("\n{bad}\n")).unwrap_err();
            assert!(e.starts_with("script line 2:"), "{bad}: {e}");
        }
    }

    #[test]
    fn times_take_three_decimals() {
        assert_eq!(parse_ms("12").unwrap(), 12_000);
        assert_eq!(parse_ms("12.5").unwrap(), 12_500);
        assert_eq!(parse_ms("0.125").unwrap(), 125);
        assert!(parse_ms("-1").is_err() && parse_ms("1.").is_ok() && parse_ms(".5").is_err());
    }
}
