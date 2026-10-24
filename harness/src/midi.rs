// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 japes98
//! The MIDI output's capture (docs/HARNESS.md, "MIDI output"): the bytes
//! with their times (`midi-out.csv`) and the messages they make
//! (`midi-out.txt`), decoded by the MIDI 1.0 rules: running status, real-time
//! bytes anywhere, system exclusive up to F7.

/// `ms` with three decimals, from microseconds.
fn ms(us: u64) -> String {
    format!("{}.{:03}", us / 1000, us % 1000)
}

/// `ms,byte` and one row per byte: its time (when its stop bit ended) and
/// the byte as two hex digits.
pub fn csv(sent: &[(u64, u8)]) -> String {
    let mut s = String::from("ms,byte\n");
    for (us, b) in sent {
        s.push_str(&format!("{},{:02x}\n", ms(*us), b));
    }
    s
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect::<Vec<_>>().join(" ")
}

/// Data bytes a status byte takes (channel and system common messages).
fn data_len(status: u8) -> usize {
    match status & 0xf0 {
        0xc0 | 0xd0 => 1,
        0x80..=0xe0 => 2,
        _ => match status {
            0xf1 | 0xf3 => 1,
            0xf2 => 2,
            _ => 0,
        },
    }
}

fn channel_message(msg: &[u8]) -> String {
    let ch = (msg[0] & 0x0f) + 1;
    let (a, b) = (msg[1], msg.get(2).copied().unwrap_or(0));
    match msg[0] & 0xf0 {
        0x80 => format!("note-off ch {ch} key {a} vel {b}"),
        0x90 => format!("note-on ch {ch} key {a} vel {b}"),
        0xa0 => format!("poly-pressure ch {ch} key {a} value {b}"),
        0xb0 => format!("control-change ch {ch} ctrl {a} value {b}"),
        0xc0 => format!("program-change ch {ch} program {a}"),
        0xd0 => format!("channel-pressure ch {ch} value {a}"),
        _ => format!("pitch-bend ch {ch} value {}", (b as u32) << 7 | a as u32),
    }
}

fn system_message(msg: &[u8]) -> String {
    match msg[0] {
        0xf1 => format!("mtc-quarter-frame {:02x}", msg[1]),
        0xf2 => format!("song-position {}", (msg[2] as u32) << 7 | msg[1] as u32),
        0xf3 => format!("song-select {}", msg[1]),
        0xf6 => "tune-request".into(),
        0xf8 => "clock".into(),
        0xfa => "start".into(),
        0xfb => "continue".into(),
        0xfc => "stop".into(),
        0xfe => "active-sensing".into(),
        0xff => "reset".into(),
        b => format!("undefined {b:02x}"),
    }
}

/// One line per message: the time of its last byte, then the message.
/// Lines also say `(running status)` for a message sent without its
/// status byte, and name what breaks the rules: `stray-data`,
/// `sysex-unterminated`, `incomplete` (at the end).
pub fn decode(sent: &[(u64, u8)]) -> String {
    let mut out = String::new();
    let mut line = |us: u64, text: String| out.push_str(&format!("{} {}\n", ms(us), text));
    let mut running: Option<u8> = None;
    let mut msg: Vec<u8> = Vec::new();
    let mut implied = false;
    let mut sysex: Option<Vec<u8>> = None;
    let mut last_us = 0;
    for &(us, b) in sent {
        // what a byte cuts short ends with the byte before it
        let prev_us = last_us;
        last_us = us;
        if b >= 0xf8 {
            line(us, system_message(&[b]));
            continue;
        }
        if let Some(sx) = sysex.as_mut() {
            if b < 0x80 {
                sx.push(b);
                continue;
            }
            let mut sx = sysex.take().unwrap();
            if b == 0xf7 {
                sx.push(b);
                line(us, format!("sysex {} ({} bytes)", hex(&sx), sx.len()));
                continue;
            }
            line(prev_us, format!("sysex-unterminated {}", hex(&sx)));
        }
        if b >= 0x80 {
            if !msg.is_empty() {
                line(prev_us, format!("incomplete {}", hex(&msg)));
                msg.clear();
            }
            implied = false;
            match b {
                0xf0 => {
                    running = None;
                    sysex = Some(vec![b]);
                    continue;
                }
                0xf7 => {
                    line(us, "stray-data f7".into());
                    continue;
                }
                0xf1..=0xf6 => running = None,
                _ => running = Some(b),
            }
            msg.push(b);
        } else if msg.is_empty() {
            match running {
                Some(s) => {
                    msg.push(s);
                    implied = true;
                }
                None => {
                    line(us, format!("stray-data {b:02x}"));
                    continue;
                }
            }
            msg.push(b);
        } else {
            msg.push(b);
        }
        if msg.len() == 1 + data_len(msg[0]) {
            let text = if msg[0] < 0xf0 { channel_message(&msg) } else { system_message(&msg) };
            line(us, if implied { format!("{text} (running status)") } else { text });
            msg.clear();
            implied = false;
        }
    }
    if let Some(sx) = sysex {
        line(last_us, format!("incomplete {}", hex(&sx)));
    } else if !msg.is_empty() {
        line(last_us, format!("incomplete {}", hex(&msg)));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn at(bytes: &[u8]) -> Vec<(u64, u8)> {
        bytes.iter().enumerate().map(|(i, &b)| (320 * (i as u64 + 1), b)).collect()
    }

    #[test]
    fn csv_has_times_and_hex() {
        assert_eq!(csv(&at(&[0x90, 0x3c])), "ms,byte\n0.320,90\n0.640,3c\n");
    }

    #[test]
    fn channel_messages_and_running_status() {
        let got = decode(&at(&[0x90, 60, 100, 62, 90, 0x80, 60, 0, 0xc1, 5, 0xe0, 0, 64, 0xb2, 7, 127, 0xd0, 3, 0xa0, 60, 9]));
        assert_eq!(got, "\
0.960 note-on ch 1 key 60 vel 100
1.600 note-on ch 1 key 62 vel 90 (running status)
2.560 note-off ch 1 key 60 vel 0
3.200 program-change ch 2 program 5
4.160 pitch-bend ch 1 value 8192
5.120 control-change ch 3 ctrl 7 value 127
5.760 channel-pressure ch 1 value 3
6.720 poly-pressure ch 1 key 60 value 9
");
    }

    #[test]
    fn real_time_inside_a_message_and_system_common() {
        let got = decode(&at(&[0x90, 60, 0xf8, 100, 0xf2, 0x10, 0x01, 61, 0xf6, 0xff]));
        assert_eq!(got, "\
0.960 clock
1.280 note-on ch 1 key 60 vel 100
2.240 song-position 144
2.560 stray-data 3d
2.880 tune-request
3.200 reset
");
    }

    #[test]
    fn sysex() {
        let got = decode(&at(&[0xf0, 0x43, 0x10, 0xf8, 0x01, 0xf7, 0xf0, 0x7d, 0x90, 60, 1, 0xf7]));
        assert_eq!(got, "\
1.280 clock
1.920 sysex f0 43 10 01 f7 (5 bytes)
2.560 sysex-unterminated f0 7d
3.520 note-on ch 1 key 60 vel 1
3.840 stray-data f7
");
    }

    #[test]
    fn incomplete_at_the_end_and_before_a_status() {
        assert_eq!(decode(&at(&[0x90, 60, 0xc0])), "0.640 incomplete 90 3c\n0.960 incomplete c0\n");
        assert_eq!(decode(&at(&[0xf0, 1])), "0.640 incomplete f0 01\n");
        assert_eq!(decode(&[]), "");
    }
}
