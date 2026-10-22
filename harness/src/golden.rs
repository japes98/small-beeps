// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 japes98
//! Golden files (docs/HARNESS.md, "Golden files"): every file in the golden
//! folder must match the output of the same name, byte for byte, unless a
//! `<name>.tolerance` file beside it allows a documented difference.

use crate::formats;
use std::path::Path;

#[derive(Debug, Clone, PartialEq)]
pub struct Check {
    pub name: String,
    /// None: matches. Some: why not.
    pub problem: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum Tolerance {
    Exact,
    /// PNG: each colour channel of each pixel may differ by this much.
    PixelDiff(u8),
    /// WAV: each sample may differ by this much (same length and format).
    SampleDiff(u16),
    /// CSV: same shape and text; each number may differ by this many
    /// percent of the golden value (at least 1 for a golden value of 0).
    RelPercent(u32),
}

fn tolerance(name: &str, text: &str) -> Result<Tolerance, String> {
    let w: Vec<&str> = text.split_whitespace().collect();
    let num = |s: &str| s.parse::<u32>().map_err(|_| format!("{name}.tolerance: bad number {s:?}"));
    let t = match w.as_slice() {
        [] => Tolerance::Exact,
        ["pixel-diff", n] if name.ends_with(".png") => Tolerance::PixelDiff(num(n)?.min(255) as u8),
        ["sample-diff", n] if name.ends_with(".wav") => Tolerance::SampleDiff(num(n)?.min(65535) as u16),
        ["rel-percent", n] if name.ends_with(".csv") => Tolerance::RelPercent(num(n)?),
        _ => return Err(format!("{name}.tolerance: expected `pixel-diff N` (.png), `sample-diff N` (.wav) or `rel-percent N` (.csv)")),
    };
    Ok(t)
}

fn compare(t: Tolerance, got: &[u8], want: &[u8]) -> Option<String> {
    if got == want {
        return None;
    }
    match t {
        Tolerance::Exact => Some(first_difference(got, want)),
        Tolerance::PixelDiff(max) => {
            let (g, w) = match (formats::png_read(got), formats::png_read(want)) {
                (Ok(g), Ok(w)) => (g, w),
                (Err(e), _) | (_, Err(e)) => return Some(e),
            };
            if (g.0, g.1) != (w.0, w.1) {
                return Some(format!("size {}x{}, golden {}x{}", g.0, g.1, w.0, w.1));
            }
            let worst = g.2.iter().zip(&w.2).map(|(a, b)| a.abs_diff(*b)).max().unwrap_or(0);
            (worst > max).then(|| format!("a pixel channel differs by {worst} (tolerance {max})"))
        }
        Tolerance::SampleDiff(max) => {
            let (g, w) = match (formats::wav_read(got), formats::wav_read(want)) {
                (Ok(g), Ok(w)) => (g, w),
                (Err(e), _) | (_, Err(e)) => return Some(e),
            };
            if (g.0, g.1, g.2.len()) != (w.0, w.1, w.2.len()) {
                return Some(format!("{} Hz x{} {} samples, golden {} Hz x{} {} samples", g.0, g.1, g.2.len(), w.0, w.1, w.2.len()));
            }
            let worst = g.2.iter().zip(&w.2).map(|(a, b)| a.abs_diff(*b)).max().unwrap_or(0);
            (worst > max).then(|| format!("a sample differs by {worst} (tolerance {max})"))
        }
        Tolerance::RelPercent(p) => {
            let (g, w) = (String::from_utf8_lossy(got), String::from_utf8_lossy(want));
            let (gl, wl): (Vec<&str>, Vec<&str>) = (g.lines().collect(), w.lines().collect());
            if gl.len() != wl.len() {
                return Some(format!("{} lines, golden {}", gl.len(), wl.len()));
            }
            for (i, (a, b)) in gl.iter().zip(&wl).enumerate() {
                let (ac, bc): (Vec<&str>, Vec<&str>) = (a.split(',').collect(), b.split(',').collect());
                if ac.len() != bc.len() {
                    return Some(format!("line {}: {} fields, golden {}", i + 1, ac.len(), bc.len()));
                }
                for (j, (x, y)) in ac.iter().zip(&bc).enumerate() {
                    match (x.parse::<i64>(), y.parse::<i64>()) {
                        (Ok(x), Ok(y)) => {
                            let allowed = (y.unsigned_abs() * p as u64 / 100).max(1);
                            if x.abs_diff(y) > allowed {
                                return Some(format!("line {} field {}: {x}, golden {y} (more than {p}%)", i + 1, j + 1));
                            }
                        }
                        _ if x != y => return Some(format!("line {} field {}: {x:?}, golden {y:?}", i + 1, j + 1)),
                        _ => {}
                    }
                }
            }
            None
        }
    }
}

fn first_difference(got: &[u8], want: &[u8]) -> String {
    let at = got.iter().zip(want).position(|(a, b)| a != b).unwrap_or(got.len().min(want.len()));
    format!("differs from byte {at} ({} bytes, golden {})", got.len(), want.len())
}

/// Compares `outputs` (name, bytes) with every golden file in `dir`.
pub fn check(dir: &Path, outputs: &[(String, Vec<u8>)]) -> Result<Vec<Check>, String> {
    let mut names: Vec<String> = std::fs::read_dir(dir)
        .map_err(|e| format!("cannot read golden folder {}: {e}", dir.display()))?
        .filter_map(|e| e.ok())
        .filter(|e| e.path().is_file())
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .filter(|n| !n.ends_with(".tolerance"))
        .collect();
    names.sort();
    let mut checks = Vec::new();
    for name in names {
        let want = std::fs::read(dir.join(&name)).map_err(|e| format!("cannot read golden {name}: {e}"))?;
        let tol = match std::fs::read_to_string(dir.join(format!("{name}.tolerance"))) {
            Ok(t) => tolerance(&name, &t)?,
            Err(_) => Tolerance::Exact,
        };
        let problem = match outputs.iter().find(|(n, _)| *n == name) {
            None => Some("no such output (ask for it, or remove the golden file)".to_string()),
            Some((_, got)) => compare(tol, got, &want),
        };
        checks.push(Check { name, problem });
    }
    Ok(checks)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_by_default() {
        assert_eq!(compare(Tolerance::Exact, b"abc", b"abc"), None);
        assert_eq!(compare(Tolerance::Exact, b"abd", b"abc").unwrap(), "differs from byte 2 (3 bytes, golden 3)");
    }

    #[test]
    fn csv_relative_tolerance() {
        let t = Tolerance::RelPercent(3);
        assert_eq!(compare(t, b"block,core0\n0,1029\n", b"block,core0\n0,1000\n"), None);
        assert!(compare(t, b"block,core0\n0,1031\n", b"block,core0\n0,1000\n").is_some());
        assert!(compare(t, b"block,core1\n0,1000\n", b"block,core0\n0,1000\n").is_some());
    }

    #[test]
    fn png_and_wav_tolerances() {
        let a = formats::png(2, 1, &[10, 20, 30, 40, 50, 60]);
        let b = formats::png(2, 1, &[12, 20, 30, 40, 50, 60]);
        assert_eq!(compare(Tolerance::PixelDiff(2), &a, &b), None);
        assert!(compare(Tolerance::PixelDiff(1), &a, &b).is_some());
        let (x, y) = (formats::wav(44100, 2, &[0, 5]), formats::wav(44100, 2, &[1, 5]));
        assert_eq!(compare(Tolerance::SampleDiff(1), &x, &y), None);
        assert!(compare(Tolerance::SampleDiff(0), &x, &y).is_some());
    }

    #[test]
    fn tolerance_must_fit_the_file_type() {
        assert!(tolerance("a.bin", "rel-percent 3").is_err());
        assert_eq!(tolerance("ipb.csv", "rel-percent 3\n").unwrap(), Tolerance::RelPercent(3));
    }
}
