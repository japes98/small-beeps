// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 japes98
//! Output formats written by hand (no third-party crates): PNG (stored
//! deflate blocks, so the same pixels always give the same bytes), WAV, JSON
//! and JUnit XML.

/// CRC-32 (IEEE, as PNG uses it).
pub fn crc32(data: &[u8]) -> u32 {
    let mut c = 0xffff_ffffu32;
    for &b in data {
        c ^= b as u32;
        for _ in 0..8 {
            c = if c & 1 != 0 { 0xedb8_8320 ^ (c >> 1) } else { c >> 1 };
        }
    }
    !c
}

fn adler32(data: &[u8]) -> u32 {
    let (mut a, mut b) = (1u32, 0u32);
    for &x in data {
        a = (a + x as u32) % 65521;
        b = (b + a) % 65521;
    }
    (b << 16) | a
}

fn chunk(out: &mut Vec<u8>, kind: &[u8; 4], data: &[u8]) {
    out.extend_from_slice(&(data.len() as u32).to_be_bytes());
    let start = out.len();
    out.extend_from_slice(kind);
    out.extend_from_slice(data);
    let crc = crc32(&out[start..]);
    out.extend_from_slice(&crc.to_be_bytes());
}

/// An 8-bit RGB PNG of `w` x `h` pixels (`rgb` row-major, 3 bytes a pixel).
pub fn png(w: u32, h: u32, rgb: &[u8]) -> Vec<u8> {
    let mut raw = Vec::with_capacity((w as usize * 3 + 1) * h as usize);
    for row in rgb.chunks(w as usize * 3) {
        raw.push(0); // filter: none
        raw.extend_from_slice(row);
    }
    let mut z = vec![0x78, 0x01];
    let mut blocks = raw.chunks(65535).peekable();
    while let Some(b) = blocks.next() {
        z.push(if blocks.peek().is_none() { 1 } else { 0 });
        z.extend_from_slice(&(b.len() as u16).to_le_bytes());
        z.extend_from_slice(&(!(b.len() as u16)).to_le_bytes());
        z.extend_from_slice(b);
    }
    z.extend_from_slice(&adler32(&raw).to_be_bytes());
    let mut out = b"\x89PNG\r\n\x1a\n".to_vec();
    let mut ihdr = Vec::new();
    ihdr.extend_from_slice(&w.to_be_bytes());
    ihdr.extend_from_slice(&h.to_be_bytes());
    ihdr.extend_from_slice(&[8, 2, 0, 0, 0]);
    chunk(&mut out, b"IHDR", &ihdr);
    chunk(&mut out, b"IDAT", &z);
    chunk(&mut out, b"IEND", &[]);
    out
}

/// Reads back a PNG that `png` wrote: (width, height, rgb). Other PNGs
/// (compressed, other colour types) are refused.
pub fn png_read(data: &[u8]) -> Result<(u32, u32, Vec<u8>), String> {
    if data.len() < 8 || &data[..8] != b"\x89PNG\r\n\x1a\n" {
        return Err("not a PNG".into());
    }
    let (mut at, mut w, mut h, mut z) = (8usize, 0u32, 0u32, Vec::new());
    while at + 12 <= data.len() {
        let len = u32::from_be_bytes(data[at..at + 4].try_into().unwrap()) as usize;
        let kind = &data[at + 4..at + 8];
        let body = data.get(at + 8..at + 8 + len).ok_or("truncated PNG")?;
        match kind {
            b"IHDR" => {
                w = u32::from_be_bytes(body[0..4].try_into().unwrap());
                h = u32::from_be_bytes(body[4..8].try_into().unwrap());
                if body[8..13] != [8, 2, 0, 0, 0] {
                    return Err("only 8-bit RGB PNGs written by fwtest can be compared".into());
                }
            }
            b"IDAT" => z.extend_from_slice(body),
            _ => {}
        }
        at += 12 + len;
    }
    let mut raw = Vec::new();
    let mut p = 2usize;
    loop {
        let hdr = *z.get(p).ok_or("truncated PNG data")?;
        if hdr & 6 != 0 {
            return Err("compressed PNG: only PNGs written by fwtest can be compared".into());
        }
        let n = u16::from_le_bytes(z.get(p + 1..p + 3).ok_or("truncated PNG data")?.try_into().unwrap()) as usize;
        raw.extend_from_slice(z.get(p + 5..p + 5 + n).ok_or("truncated PNG data")?);
        p += 5 + n;
        if hdr & 1 != 0 {
            break;
        }
    }
    let stride = w as usize * 3 + 1;
    if raw.len() != stride * h as usize {
        return Err("PNG size does not match its header".into());
    }
    let mut rgb = Vec::with_capacity(w as usize * 3 * h as usize);
    for row in raw.chunks(stride) {
        if row[0] != 0 {
            return Err("filtered PNG: only PNGs written by fwtest can be compared".into());
        }
        rgb.extend_from_slice(&row[1..]);
    }
    Ok((w, h, rgb))
}

/// 16-bit PCM WAV, interleaved samples.
pub fn wav(rate: u32, channels: u16, samples: &[i16]) -> Vec<u8> {
    let data_len = samples.len() as u32 * 2;
    let mut out = Vec::with_capacity(44 + data_len as usize);
    out.extend_from_slice(b"RIFF");
    out.extend_from_slice(&(36 + data_len).to_le_bytes());
    out.extend_from_slice(b"WAVEfmt ");
    out.extend_from_slice(&16u32.to_le_bytes());
    out.extend_from_slice(&1u16.to_le_bytes());
    out.extend_from_slice(&channels.to_le_bytes());
    out.extend_from_slice(&rate.to_le_bytes());
    out.extend_from_slice(&(rate * channels as u32 * 2).to_le_bytes());
    out.extend_from_slice(&(channels * 2).to_le_bytes());
    out.extend_from_slice(&16u16.to_le_bytes());
    out.extend_from_slice(b"data");
    out.extend_from_slice(&data_len.to_le_bytes());
    for s in samples {
        out.extend_from_slice(&s.to_le_bytes());
    }
    out
}

/// Reads a 16-bit PCM WAV's header fields and samples.
pub fn wav_read(data: &[u8]) -> Result<(u32, u16, Vec<i16>), String> {
    if data.len() < 12 || &data[0..4] != b"RIFF" || &data[8..12] != b"WAVE" {
        return Err("not a WAV file".into());
    }
    let (mut at, mut fmt, mut samples) = (12usize, None, None);
    while at + 8 <= data.len() {
        let len = u32::from_le_bytes(data[at + 4..at + 8].try_into().unwrap()) as usize;
        let body = data.get(at + 8..at + 8 + len).ok_or("truncated WAV")?;
        match &data[at..at + 4] {
            b"fmt " if len >= 16 => {
                let bits = u16::from_le_bytes([body[14], body[15]]);
                if u16::from_le_bytes([body[0], body[1]]) != 1 || bits != 16 {
                    return Err("only 16-bit PCM WAV files can be compared".into());
                }
                fmt = Some((u32::from_le_bytes(body[4..8].try_into().unwrap()), u16::from_le_bytes([body[2], body[3]])));
            }
            b"data" => samples = Some(body.chunks(2).map(|c| i16::from_le_bytes([c[0], *c.get(1).unwrap_or(&0)])).collect()),
            _ => {}
        }
        at += 8 + len + (len & 1);
    }
    let (rate, ch) = fmt.ok_or("WAV without a format chunk")?;
    Ok((rate, ch, samples.ok_or("WAV without data")?))
}

/// A JSON value, written with keys in insertion order and no floats, so the
/// same results always give the same bytes.
#[derive(Debug, Clone, PartialEq)]
pub enum Json {
    Null,
    Bool(bool),
    Int(i64),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

impl Json {
    pub fn obj(pairs: Vec<(&str, Json)>) -> Json {
        Json::Obj(pairs.into_iter().map(|(k, v)| (k.to_string(), v)).collect())
    }

    pub fn str(s: impl Into<String>) -> Json {
        Json::Str(s.into())
    }

    pub fn write(&self, out: &mut String, indent: usize) {
        let pad = |n: usize| "  ".repeat(n);
        match self {
            Json::Null => out.push_str("null"),
            Json::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
            Json::Int(i) => out.push_str(&i.to_string()),
            Json::Str(s) => escape_json(s, out),
            Json::Arr(a) if a.is_empty() => out.push_str("[]"),
            Json::Arr(a) => {
                out.push_str("[\n");
                for (i, v) in a.iter().enumerate() {
                    out.push_str(&pad(indent + 1));
                    v.write(out, indent + 1);
                    out.push_str(if i + 1 < a.len() { ",\n" } else { "\n" });
                }
                out.push_str(&pad(indent));
                out.push(']');
            }
            Json::Obj(o) if o.is_empty() => out.push_str("{}"),
            Json::Obj(o) => {
                out.push_str("{\n");
                for (i, (k, v)) in o.iter().enumerate() {
                    out.push_str(&pad(indent + 1));
                    escape_json(k, out);
                    out.push_str(": ");
                    v.write(out, indent + 1);
                    out.push_str(if i + 1 < o.len() { ",\n" } else { "\n" });
                }
                out.push_str(&pad(indent));
                out.push('}');
            }
        }
    }

    pub fn to_text(&self) -> String {
        let mut s = String::new();
        self.write(&mut s, 0);
        s.push('\n');
        s
    }
}

fn escape_json(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
}

pub fn escape_xml(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&apos;"),
            c if (c as u32) < 0x20 && c != '\n' && c != '\t' => out.push_str(&format!("&#{};", c as u32)),
            c => out.push(c),
        }
    }
    out
}

/// One JUnit test case: name, and None (passed) or the failure message.
pub struct Case {
    pub name: String,
    pub failure: Option<String>,
}

/// JUnit XML for one suite of cases. No times: they would differ per run.
pub fn junit(suite: &str, cases: &[Case]) -> String {
    let failures = cases.iter().filter(|c| c.failure.is_some()).count();
    let mut s = String::from("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    s.push_str(&format!(
        "<testsuites tests=\"{}\" failures=\"{}\">\n  <testsuite name=\"{}\" tests=\"{}\" failures=\"{}\">\n",
        cases.len(), failures, escape_xml(suite), cases.len(), failures
    ));
    for c in cases {
        match &c.failure {
            None => s.push_str(&format!("    <testcase classname=\"{}\" name=\"{}\"/>\n", escape_xml(suite), escape_xml(&c.name))),
            Some(f) => s.push_str(&format!(
                "    <testcase classname=\"{}\" name=\"{}\">\n      <failure message=\"{}\"/>\n    </testcase>\n",
                escape_xml(suite), escape_xml(&c.name), escape_xml(f)
            )),
        }
    }
    s.push_str("  </testsuite>\n</testsuites>\n");
    s
}

/// SHA-256 (FIPS 180-4), for output hashes in the results.
pub fn sha256(data: &[u8]) -> String {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
    ];
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];
    let mut msg = data.to_vec();
    let bits = (data.len() as u64).wrapping_mul(8);
    msg.push(0x80);
    while msg.len() % 64 != 56 {
        msg.push(0);
    }
    msg.extend_from_slice(&bits.to_be_bytes());
    for block in msg.chunks(64) {
        let mut w = [0u32; 64];
        for i in 0..16 {
            w[i] = u32::from_be_bytes(block[4 * i..4 * i + 4].try_into().unwrap());
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16].wrapping_add(s0).wrapping_add(w[i - 7]).wrapping_add(s1);
        }
        let mut v = h;
        for i in 0..64 {
            let s1 = v[4].rotate_right(6) ^ v[4].rotate_right(11) ^ v[4].rotate_right(25);
            let ch = (v[4] & v[5]) ^ (!v[4] & v[6]);
            let t1 = v[7].wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
            let s0 = v[0].rotate_right(2) ^ v[0].rotate_right(13) ^ v[0].rotate_right(22);
            let maj = (v[0] & v[1]) ^ (v[0] & v[2]) ^ (v[1] & v[2]);
            let t2 = s0.wrapping_add(maj);
            v = [t1.wrapping_add(t2), v[0], v[1], v[2], v[3].wrapping_add(t1), v[4], v[5], v[6]];
        }
        for i in 0..8 {
            h[i] = h[i].wrapping_add(v[i]);
        }
    }
    h.iter().map(|x| format!("{x:08x}")).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sha256_known_values() {
        assert_eq!(sha256(b""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
        assert_eq!(sha256(b"abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
        assert_eq!(sha256(&[b'a'; 1000]), "41edece42d63e8d9bf515a9ba6932e1c20cbc9f5a5d134645adb5db1b9737ea3");
    }

    #[test]
    fn crc32_known_value() {
        assert_eq!(crc32(b"123456789"), 0xcbf4_3926);
    }

    #[test]
    fn png_round_trips() {
        let rgb: Vec<u8> = (0..300 * 250 * 3).map(|i| (i * 7 % 251) as u8).collect();
        let p = png(300, 250, &rgb);
        assert_eq!(png_read(&p).unwrap(), (300, 250, rgb));
    }

    #[test]
    fn wav_round_trips() {
        let s = [0i16, 1, -1, 32767, -32768, 1234];
        assert_eq!(wav_read(&wav(44100, 2, &s)).unwrap(), (44100, 2, s.to_vec()));
    }

    #[test]
    fn json_is_stable_and_escaped() {
        let j = Json::obj(vec![("a", Json::Int(-3)), ("b", Json::str("x\"y\n")), ("c", Json::Arr(vec![]))]);
        assert_eq!(j.to_text(), "{\n  \"a\": -3,\n  \"b\": \"x\\\"y\\n\",\n  \"c\": []\n}\n");
    }
}
