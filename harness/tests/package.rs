// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 japes98
//! fwtest's package path (`--package`, docs/HARNESS.md "Packages"), on test
//! packages this file makes: a packer written from docs/HARDWARE-SPEC.md
//! HW-87 to HW-91 alone, not from the emulator's reader and not from any
//! stock package. Its app is tests/images/pkgapp.bin (linked at 0x02000120).
//! tests/packages/pkgapp.fwsc, the suite's copy, must be what it makes.

use fwtest::run::{run, Options, Outcome, When};
use std::path::Path;

const OUT0: u32 = 0x01c0_0100;
const BOOT_BLOCK: u32 = 0x01c7_fc00;
const AREA: usize = 0x4000;

fn here(p: &str) -> std::path::PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests").join(p)
}

/// JieLi's CRC-16 (HW-87): polynomial 0x1021 from 0, most significant bit first.
fn crc16(b: &[u8]) -> u16 {
    let mut c = 0u16;
    for &x in b {
        c ^= (x as u16) << 8;
        for _ in 0..8 {
            c = if c & 0x8000 != 0 { (c << 1) ^ 0x1021 } else { c << 1 };
        }
    }
    c
}

/// The mask (HW-87), seeded with `k`.
fn mask(b: &mut [u8], mut k: u16) {
    for x in b {
        *x ^= k as u8;
        k = (k << 1) ^ if k & 0x8000 != 0 { 0x1021 } else { 0 };
    }
}

fn put16(b: &mut [u8], at: usize, v: u16) {
    b[at..at + 2].copy_from_slice(&v.to_le_bytes());
}

fn put32(b: &mut [u8], at: usize, v: u32) {
    b[at..at + 4].copy_from_slice(&v.to_le_bytes());
}

/// A 32-byte head (HW-89): data CRC, offset, length, attribute, last, name; its own
/// CRC over bytes 2-31 last.
fn head(name: &str, offset: usize, data: &[u8], len: usize, attr: u8, last: bool) -> [u8; 32] {
    let mut h = [0u8; 32];
    put16(&mut h, 2, crc16(data));
    put32(&mut h, 4, offset as u32);
    put32(&mut h, 8, len as u32);
    h[12] = attr;
    put16(&mut h, 14, last as u16);
    h[16..16 + name.len()].copy_from_slice(name.as_bytes());
    let c = crc16(&h[2..]);
    put16(&mut h, 0, c);
    h
}

/// The chip key from a key block (HW-90).
fn chip_key(b: &[u8; 32]) -> u16 {
    let mut s = (b[..16].iter().map(|&x| x as u32).sum::<u32>() % 256) as u8;
    if s >= 0xe0 {
        s = 0xaa;
    } else if s <= 0x10 {
        s = 0x55;
    }
    (0..16).filter(|&i| (b[16 + i] ^ b[15 - i]) < s).fold(0, |k, i| k | 1 << i)
}

/// What a test package may get wrong, one thing at a time.
#[derive(Clone)]
struct Spec {
    identity: &'static str,
    /// the app area's flash offset (HW-91: 0x4000)
    area: usize,
    /// app.bin's offset in the area (0x120, where pkgapp is linked to run)
    app_at: usize,
    app_name: &'static str,
    app_attr: u8,
    header_crc_ok: bool,
    key_crc_ok: bool,
    /// the flash image entry's length runs past the file
    truncated: bool,
}

const GOOD: Spec = Spec {
    identity: "SB-A1-TEST",
    area: AREA,
    app_at: 0x120,
    app_name: "app.bin",
    app_attr: 0x82,
    header_crc_ok: true,
    key_crc_ok: true,
    truncated: false,
};

/// Any 32 bytes make a key block; these give the key 0x0aee.
const KEY_BLOCK: [u8; 32] = *b"small-beeps test package key 01\0";

/// The flash image (HW-89, HW-90): the flash header, two directory heads, the key
/// block and its CRC, then the app area, scrambled.
fn flash_image(app: &[u8], s: &Spec) -> Vec<u8> {
    const KEY_AT: usize = 0x100;
    let area_len = s.app_at + app.len();
    let mut f = vec![0xffu8; s.area + area_len];
    // the flash header: size for the programmer, VID, flash size, version,
    // alignment, reserved, options, PID; its CRC first
    let mut fh = [0u8; 32];
    fh[4..8].copy_from_slice(b"0.01");
    put32(&mut fh, 8, 0x10_0000);
    fh[16..32].copy_from_slice(b"small-beeps-test");
    let c = crc16(&fh[2..]);
    put16(&mut fh, 0, c);
    // the key block and its CRC
    f[KEY_AT..KEY_AT + 32].copy_from_slice(&KEY_BLOCK);
    let kc = crc16(&KEY_BLOCK) ^ if s.key_crc_ok { 0 } else { 0x0101 };
    put16(&mut f, KEY_AT + 32, kc);
    // the app area: its head, its directory (app.bin), the app
    let mut area = vec![0xffu8; area_len];
    area[s.app_at..].copy_from_slice(app);
    let dir = head(s.app_name, s.app_at, app, app.len(), s.app_attr, true);
    area[32..64].copy_from_slice(&dir);
    let ah = head("app_dir_head", 0, &area[32..], area_len, 0x81, false);
    area[..32].copy_from_slice(&ah);
    let key = chip_key(&KEY_BLOCK);
    for r in (0..area_len).step_by(32) {
        let end = (r + 32).min(area_len);
        mask(&mut area[r..end], key ^ (r / 4) as u16);
    }
    f[s.area..].copy_from_slice(&area);
    // the directory: the flash header, isd_config.ini, app_dir_head (last)
    let mut heads = [
        fh,
        head("isd_config.ini", KEY_AT, &f[KEY_AT..KEY_AT + 34], 34, 0, false),
        head("app_dir_head", s.area, &[], area_len, 0x81, true),
    ];
    for (i, h) in heads.iter_mut().enumerate() {
        mask(h, 0xffff);
        f[32 * i..32 * i + 32].copy_from_slice(h);
    }
    f
}

/// The package (HW-88): 20 header blocks, then the flash image as the one entry.
fn package(app: &[u8], s: &Spec) -> Vec<u8> {
    let flash = flash_image(app, s);
    let mut hdr = vec![0u8; 940];
    put16(&mut hdr, 8, 1);
    let mut entry = [0u8; 80];
    put32(&mut entry, 8, 940);
    put32(&mut entry, 12, flash.len() as u32 + if s.truncated { 1 } else { 0 });
    mask(&mut entry, 0xffff);
    hdr[64..144].copy_from_slice(&entry);
    let c = crc16(&hdr[2..64]) ^ if s.header_crc_ok { 0 } else { 1 };
    put16(&mut hdr, 0, c);
    mask(&mut hdr[..64], 0xffff);
    let id = s.identity.as_bytes();
    let mut file = Vec::with_capacity(960 + flash.len());
    for i in 0..20 {
        file.extend_from_slice(&hdr[47 * i..47 * i + 47]);
        file.push(id.get(i).map_or(0x7d, |&c| c.wrapping_add(i as u8 + 1)));
    }
    file.extend_from_slice(&flash);
    file
}

fn app() -> Vec<u8> {
    std::fs::read(here("images/pkgapp.bin")).unwrap()
}

fn opts(ms: u64) -> Options {
    Options { ms_us: ms * 1000, package: true, ..Default::default() }
}

fn output<'a>(r: &'a fwtest::run::Report, name: &str) -> &'a [u8] {
    &r.outputs.iter().find(|o| o.name == name).unwrap_or_else(|| panic!("no output {name}")).data
}

fn words(b: &[u8]) -> Vec<u32> {
    b.chunks(4).map(|c| u32::from_le_bytes(c.try_into().unwrap())).collect()
}

fn refused(s: &Spec, why: &str) {
    match run(&package(&app(), s), &opts(1)) {
        Err(e) => assert!(e.contains("the package is refused") && e.contains(why), "{e}"),
        Ok(r) => panic!("booted: {:?}", r.outcome),
    }
}

/// R-HARN-13: a package made from HW-87 to HW-91 boots: the app runs at
/// 0x02000120 and reads its table through its own address, r0 points at the
/// boot block, and the flash chip holds the flash image from offset 0.
#[test]
fn a_package_boots_its_app() {
    let pkg = package(&app(), &GOOD);
    let mut o = opts(2);
    o.ram = vec![(OUT0, 20, When::End), (BOOT_BLOCK, 56, When::End)];
    o.flash_out = true;
    let r = run(&pkg, &o).unwrap();
    assert_eq!(r.outcome, Outcome::Completed, "{:?}", r.outcome);
    let p = r.package.as_ref().unwrap();
    assert_eq!((p.identity.as_str(), p.area, p.entry), ("SB-A1-TEST", 0x4000, 0x0200_0120));
    let w = words(output(&r, "ram-01c00100-14-end.bin"));
    assert_eq!(w[0], 0x600d_f00d);
    assert!((0x0200_0120..0x0200_0120 + app().len() as u32).contains(&w[1]), "the table at {:#x}", w[1]);
    assert_eq!(w[2], 0xaaaa_aaaa, "the table read through its address");
    assert!(w[4] > 0, "the counter runs");
    // the boot block: the flash header's copy, the window's flash offset, the app's
    // address, then (chip ID, trim, address) 0, then the flash header unmasked
    let b = output(&r, "ram-01c7fc00-38-end.bin");
    assert_eq!(&words(&b[..24])[..], &[BOOT_BLOCK + 24, 0x4000, 0x0200_0000, 0, 0, 0]);
    assert_eq!(&b[24 + 4..24 + 8], b"0.01");
    assert_eq!(&b[24 + 16..24 + 32], b"small-beeps-test");
    let chip = output(&r, "flash.bin");
    assert_eq!(&chip[..pkg.len() - 960], &pkg[960..], "the chip holds the flash image from 0");
    assert!(chip[pkg.len() - 960..].iter().all(|&x| x == 0xff), "the rest erased");
}

/// R-HARN-13: `--flash` gives the chip's starting bytes; the package's flash
/// image is written over them from offset 0, and the rest is kept.
#[test]
fn a_package_over_a_saved_chip() {
    let pkg = package(&app(), &GOOD);
    let mut saved = vec![0x5au8; 0x10_0000];
    saved[..4].copy_from_slice(b"OLD!");
    let mut o = opts(1);
    o.flash_in = Some(saved);
    o.flash_out = true;
    let r = run(&pkg, &o).unwrap();
    assert_eq!(r.outcome, Outcome::Completed, "{:?}", r.outcome);
    let chip = output(&r, "flash.bin");
    assert_eq!(&chip[..pkg.len() - 960], &pkg[960..]);
    assert!(chip[pkg.len() - 960..].iter().all(|&x| x == 0x5a));
}

/// R-HARN-13: booted at an address other than the one it was linked for, the
/// app reads other bytes as its table (the window does map the area from 0x4000).
#[test]
fn an_app_at_the_wrong_offset_reads_the_wrong_table() {
    let s = Spec { app_at: 0x100, ..GOOD };
    let mut o = opts(2);
    o.ram = vec![(OUT0, 20, When::End)];
    let r = run(&package(&app(), &s), &o).unwrap();
    assert_eq!(r.package.as_ref().unwrap().entry, 0x0200_0100);
    if r.outcome == Outcome::Completed {
        let w = words(output(&r, "ram-01c00100-14-end.bin"));
        assert_ne!(w[2], 0xaaaa_aaaa, "the sum must not come out right");
    }
}

/// R-HARN-13: each check refuses the package, with what failed.
#[test]
fn bad_packages_are_refused() {
    refused(&Spec { header_crc_ok: false, ..GOOD }, "not an FM-1 update package");
    refused(&Spec { truncated: true, ..GOOD }, "truncated");
    refused(&Spec { key_crc_ok: false, ..GOOD }, "key block's CRC");
    refused(&Spec { app_name: "app.bix", ..GOOD }, "no app.bin");
    refused(&Spec { app_attr: 0x80, ..GOOD }, "not 0x82");
    refused(&Spec { area: 0x5000, ..GOOD }, "not 0x4000");
    refused(&Spec { identity: "SMK-37 test", ..GOOD }, "another board");
    // a raw image is not a package
    assert!(matches!(run(&app(), &opts(1)), Err(e) if e.contains("the package is refused")));
}

/// The suite's package (tests/harness.suite) is this file's. Regenerate with
/// `FWTEST_WRITE_PACKAGES=1 cargo test --test package`.
#[test]
fn the_committed_package_is_current() {
    let path = here("packages/pkgapp.fwsc");
    let pkg = package(&app(), &GOOD);
    if std::env::var_os("FWTEST_WRITE_PACKAGES").is_some() {
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(&path, &pkg).unwrap();
    }
    assert!(std::fs::read(&path).unwrap() == pkg, "{} is stale", path.display());
}
