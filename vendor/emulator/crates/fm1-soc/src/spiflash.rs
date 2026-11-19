//! SPI0 (0x11C00) driving the external SPI NOR flash.
//!
//! The firmware talks to the flash directly (with the SFC/XIP switched off)
//! for JEDEC probing, status reads, sector erase and page program — the
//! stock app in `norflash_*`, Felucca in `hal/fm1_flash.h`. Register use as
//! seen there: CON bit15 = transfer pending (set when a byte transfer
//! completes), bit14 = clear pending (write), bit12 = direction (1 = rx),
//! bit3 = enable; BUF holds the byte to send / the byte received. Chip
//! select is PD0, driven as a GPIO by the firmware.
//!
//! The flash is a 1 MiB part reporting JEDEC `85 60 14` (Puya, as on real
//! units). Commands modelled: 9F (JEDEC id), 4B (unique id), 05/35 (status
//! 1/2), 06/04 (WREN/WRDI), 03/0B (read / fast read), 81 (256-byte page
//! erase), 20 (4 KiB erase), 52 (32 KiB erase), D8 (64 KiB erase), 60/C7
//! (chip erase), 02 (page program). As the part's datasheet has them:
//! an erase or program needs WREN first and starts when CS goes high; a
//! page program wraps within its 256-byte page (of more than 256 bytes the
//! last 256 count) and only clears bits. With `timing` set, an erase or
//! program then keeps the chip busy for that long: status 1 bit 0 (WIP)
//! reads 1 and WEL stays 1 until it ends, and every command but the status
//! reads is ignored meanwhile. Without it (the default) they finish at once.
//! The bytes change when the operation starts; `power_cut` puts back the
//! part not yet done.
//!
//! Block protection: `status` holds the status registers' non-volatile bits
//! as the chip powered up (status 1 bits 2-7, status 2), read back by 05 and
//! 35. An erase or program whose range holds a byte BP0-BP4 and CMP protect
//! (`protected`, the table both parts share) is ignored wholly: nothing
//! changes, it isn't logged or counted, the chip doesn't go busy, and WEL
//! stays as it was. The status register writes (01, 31) aren't modelled.
//!
//! Power cuts (FM1_FLASH_CUT=N): the Nth erase or page program is cut half way (the first
//! half of its bytes changed, the rest as before), and nothing after it reaches the chip, as if
//! the power went there. With fm1-live's `--flash FILE` the next run boots from what was left.

pub const SPI0_BASE: u32 = 0x11c00;
pub const FLASH_SIZE: usize = 1 << 20;
pub const PAGE: usize = 256;

/// How long an erase or a page program keeps the chip busy, in CPU cycles (0: no time).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct FlashTiming {
    pub program: u64,
    pub erase: u64,
}

/// One erase or page program the chip started: when, which command, which bytes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FlashOp {
    pub start: u64,
    pub end: u64,
    pub cmd: u8,
    pub base: usize,
    pub len: usize,
}

pub struct SpiFlash {
    pub mem: Vec<u8>,
    pub con: u32,
    pub buf: u32,
    cs_low: bool,
    cmd: u8,
    nbytes: usize,
    addr: u32,
    wel: bool,
    /// bytes in the current command (after the opcode), for address assembly
    pending_prog: Vec<u8>,
    /// FM1_FLASH_TRACE: log each command on CS release
    trace: bool,
    /// JEDEC / unique-id reads
    pub jedec: [u8; 3],
    /// The flash range the last erase or page program changed (`Soc` mirrors it into the XIP
    /// window), taken by the reader.
    pub changed: Option<(usize, usize)>,
    /// Persistence generation, independent of the range consumed by XIP synchronization.
    pub revision: u32,
    /// Erases and page programs so far (the power-cut points)
    pub ops: u32,
    /// FM1_FLASH_CUT: the op that is cut half way; none reach the chip after it
    pub cut_at: Option<u32>,
    /// Busy times; the default finishes every operation at once.
    pub timing: FlashTiming,
    /// The cycle now, set by the bus before each access (the busy state's clock).
    pub now: u64,
    /// The chip is busy until this cycle (the last operation's end).
    pub busy_until: u64,
    /// The operation in progress (or the last one) and the bytes it replaced.
    current_op: Option<(FlashOp, Vec<u8>)>,
    /// Every erase and page program started, in order.
    pub log: Vec<FlashOp>,
    /// The command now selected was sent while busy: ignored to its end.
    ignored: bool,
    /// Status registers 1 and 2 as at power-up (BP0-BP4 in 1, CMP in 2); WIP and WEL come
    /// from the chip's state.
    pub status: [u8; 2],
}

/// The protected area for BP4-BP0 (status 1 bits 6-2) with CMP 0, as `(BP mask, BP value,
/// first byte, end)`, the first matching row winning: both parts' table, row for row (an
/// empty range protects nothing; CMP 1 protects the rest of the chip).
const PROTECT: [(u8, u8, usize, usize); 19] = [
    (0b00111, 0b00000, 0, 0),
    (0b00110, 0b00110, 0, FLASH_SIZE),
    (0b10111, 0b00101, 0, FLASH_SIZE),
    (0b11111, 0b00001, FLASH_SIZE - 0x10000, FLASH_SIZE),
    (0b11111, 0b00010, FLASH_SIZE - 0x20000, FLASH_SIZE),
    (0b11111, 0b00011, FLASH_SIZE - 0x40000, FLASH_SIZE),
    (0b11111, 0b00100, FLASH_SIZE - 0x80000, FLASH_SIZE),
    (0b11111, 0b01001, 0, 0x10000),
    (0b11111, 0b01010, 0, 0x20000),
    (0b11111, 0b01011, 0, 0x40000),
    (0b11111, 0b01100, 0, 0x80000),
    (0b11111, 0b10001, FLASH_SIZE - 0x1000, FLASH_SIZE),
    (0b11111, 0b10010, FLASH_SIZE - 0x2000, FLASH_SIZE),
    (0b11111, 0b10011, FLASH_SIZE - 0x4000, FLASH_SIZE),
    (0b11110, 0b10100, FLASH_SIZE - 0x8000, FLASH_SIZE),
    (0b11111, 0b11001, 0, 0x1000),
    (0b11111, 0b11010, 0, 0x2000),
    (0b11111, 0b11011, 0, 0x4000),
    (0b11110, 0b11100, 0, 0x8000),
];

impl SpiFlash {
    pub fn new() -> Self {
        Self {
            mem: vec![0xff; FLASH_SIZE],
            con: 0,
            buf: 0,
            cs_low: false,
            cmd: 0,
            nbytes: 0,
            addr: 0,
            wel: false,
            pending_prog: Vec::new(),
            jedec: [0x85, 0x60, 0x14],
            trace: std::env::var_os("FM1_FLASH_TRACE").is_some(),
            changed: None,
            revision: 0,
            ops: 0,
            cut_at: std::env::var("FM1_FLASH_CUT").ok().and_then(|v| v.parse().ok()),
            timing: FlashTiming::default(),
            now: 0,
            busy_until: 0,
            current_op: None,
            log: Vec::new(),
            ignored: false,
            status: [0; 2],
        }
    }

    /// Load a flash image at offset 0 (the rest stays erased).
    pub fn load(&mut self, image: &[u8]) {
        let n = image.len().min(self.mem.len());
        self.mem[..n].copy_from_slice(&image[..n]);
    }

    pub fn busy(&self) -> bool { self.cs_low }

    /// The bytes BP0-BP4 and CMP protect, as `first..end` (empty: none).
    pub fn protected(&self) -> (usize, usize) {
        let bp = (self.status[0] >> 2) & 0x1f;
        let (_, _, lo, hi) = *PROTECT.iter().find(|&&(m, v, _, _)| bp & m == v).expect("every BP setting has a row");
        if self.status[1] & 0x40 == 0 {
            (lo, hi)
        } else if lo == hi {
            (0, FLASH_SIZE)
        } else if lo == 0 && hi == FLASH_SIZE {
            (0, 0)
        } else if lo == 0 {
            (hi, FLASH_SIZE)
        } else {
            (0, lo)
        }
    }

    /// Does `base..base + len` hold a protected byte?
    fn guarded(&self, base: usize, len: usize) -> bool {
        let (lo, hi) = self.protected();
        base < hi && lo < base + len
    }

    /// Is an erase or program still in progress at cycle `now`?
    pub fn working(&self, now: u64) -> bool { now < self.busy_until }

    /// An operation that has ended clears WEL (as the chip does when its cycle completes).
    fn settle(&mut self) {
        if self.current_op.is_some() && self.now >= self.busy_until {
            self.current_op = None;
            self.wel = false;
        }
    }

    pub fn set_cs(&mut self, low: bool) {
        self.settle();
        if !low && self.cs_low && self.trace && self.nbytes > 0 {
            eprintln!("flash cmd {:02x} addr {:06x} bytes {}", self.cmd, self.addr, self.nbytes);
        }
        if low && !self.cs_low {
            self.cmd = 0;
            self.nbytes = 0;
            self.ignored = false;
            self.pending_prog.clear();
        }
        if !low && self.cs_low && !self.ignored && self.wel {
            // an erase or page program starts as CS goes high
            match (self.cmd, self.nbytes) {
                (0x02, n) if n > 4 => self.program(),
                (0x81, n) if n >= 4 => self.erase(PAGE),
                (0x20, n) if n >= 4 => self.erase(0x1000),
                (0x52, n) if n >= 4 => self.erase(0x8000),
                (0xd8, n) if n >= 4 => self.erase(0x10000),
                (0x60 | 0xc7, _) => {
                    self.addr = 0;
                    self.erase(FLASH_SIZE)
                }
                _ => {}
            }
        }
        if !low {
            self.pending_prog.clear();
        }
        self.cs_low = low;
    }

    /// One byte exchanged on MOSI; returns the byte on MISO.
    fn transfer(&mut self, out: u8) -> u8 {
        if !self.cs_low {
            return 0xff;
        }
        self.settle();
        let i = self.nbytes;
        self.nbytes += 1;
        if i == 0 {
            self.cmd = out;
            self.addr = 0;
            // busy: only the status reads are decoded
            if self.working(self.now) && !matches!(out, 0x05 | 0x35) {
                self.ignored = true;
                return 0xff;
            }
            match out {
                0x06 => self.wel = true,
                0x04 => self.wel = false,
                _ => {}
            }
            return 0xff;
        }
        if self.ignored {
            return 0xff;
        }
        let k = i - 1; // byte index after the opcode
        match self.cmd {
            0x9f => self.jedec.get(k).copied().unwrap_or(0xff),
            0x4b => {
                // 4 dummy bytes then a 16-byte unique id
                if k < 4 { 0xff } else { [0x46, 0x4d, 0x31, 0x2d][(k - 4) & 3] }
            }
            0x05 => (self.working(self.now) as u8) | if self.wel { 0x02 } else { 0x00 } | (self.status[0] & 0xfc),
            0x35 => self.status[1],
            0x03 | 0x0b | 0x81 | 0x20 | 0x52 | 0xd8 | 0x02 => {
                if k < 3 {
                    self.addr = (self.addr << 8) | out as u32;
                    0xff
                } else if self.cmd == 0x0b && k == 3 {
                    0xff // fast-read dummy byte
                } else if self.cmd == 0x02 {
                    self.pending_prog.push(out);
                    0xff
                } else if self.cmd == 0x03 || self.cmd == 0x0b {
                    let off = if self.cmd == 0x0b { k - 4 } else { k - 3 };
                    self.mem[(self.addr as usize + off) & (FLASH_SIZE - 1)]
                } else {
                    0xff
                }
            }
            _ => 0xff,
        }
    }

    /// One more erase / program: Some(true) done whole, Some(false) cut half way, None after the cut.
    fn op(&mut self) -> Option<bool> {
        self.ops += 1;
        match self.cut_at {
            Some(c) if self.ops > c => None,
            Some(c) if self.ops == c => Some(false),
            _ => Some(true),
        }
    }

    /// Has the power been cut (FM1_FLASH_CUT reached)?
    pub fn cut(&self) -> bool { self.cut_at.is_some_and(|c| self.ops >= c) }

    /// The chip starts an operation on `base..base + len`: keep what it replaces, time it.
    fn start(&mut self, cmd: u8, base: usize, len: usize, cycles: u64) {
        let op = FlashOp { start: self.now, end: self.now + cycles, cmd, base, len };
        self.current_op = Some((op, self.mem[base..base + len].to_vec()));
        self.busy_until = op.end;
        self.log.push(op);
    }

    /// Page program: the bytes wrap within the page (later ones win), and only clear bits.
    fn program(&mut self) {
        if self.guarded(self.addr as usize & !(PAGE - 1) & (FLASH_SIZE - 1), PAGE) {
            return;
        }
        let n = match self.op() { Some(true) => self.pending_prog.len(), Some(false) => self.pending_prog.len() / 2, None => 0 };
        let page = self.addr as usize & !(PAGE - 1) & (FLASH_SIZE - 1);
        self.start(0x02, page, PAGE, self.timing.program);
        let mut data = [None; PAGE];
        for (i, b) in self.pending_prog.iter().take(n).enumerate() {
            data[(self.addr as usize + i) & (PAGE - 1)] = Some(*b);
        }
        for (o, b) in data.iter().enumerate() {
            if let Some(b) = b {
                self.mem[page + o] &= *b;
            }
        }
        if n > 0 {
            self.changed = Some((page, page + PAGE));
            self.revision = self.revision.wrapping_add(1);
        }
    }

    fn erase(&mut self, size: usize) {
        if self.guarded((self.addr as usize) & !(size - 1) & (FLASH_SIZE - 1), size) {
            return;
        }
        let n = match self.op() { Some(true) => size, Some(false) => size / 2, None => 0 };
        let base = (self.addr as usize) & !(size - 1) & (FLASH_SIZE - 1);
        self.start(self.cmd, base, size, self.timing.erase);
        if n == 0 {
            return;
        }
        for b in &mut self.mem[base..(base + n).min(FLASH_SIZE)] {
            *b = 0xff;
        }
        self.changed = Some((base, (base + n).min(FLASH_SIZE)));
        self.revision = self.revision.wrapping_add(1);
    }

    /// The power goes at cycle `now`: an operation in progress keeps only the part done by
    /// then (its first bytes, in proportion to the time gone), the rest as it was before.
    /// Returns that operation and how many of its bytes were done.
    pub fn power_cut(&mut self, now: u64) -> Option<(FlashOp, usize)> {
        self.now = now;
        let (op, before) = self.current_op.take()?;
        if now >= op.end {
            self.wel = false;
            return None;
        }
        let done = ((op.len as u128 * (now - op.start) as u128) / (op.end - op.start) as u128) as usize;
        self.mem[op.base + done..op.base + op.len].copy_from_slice(&before[done..]);
        self.changed = Some((op.base, op.base + op.len));
        self.revision = self.revision.wrapping_add(1);
        self.busy_until = now;
        self.wel = false;
        Some((op, done))
    }

    pub fn read(&mut self, addr: u32) -> u32 {
        match addr - SPI0_BASE {
            0x0 => self.con,
            0x8 => self.buf,
            _ => 0,
        }
    }

    pub fn write(&mut self, addr: u32, value: u32) {
        match addr - SPI0_BASE {
            0x0 => {
                // bit14 clears the pending flag; bit15 itself is read-only
                let mut v = (value & !0x8000) | (self.con & 0x8000);
                if value & 0x4000 != 0 {
                    v &= !0xc000;
                }
                self.con = v;
            }
            0x8 => {
                // a BUF write starts one byte transfer (tx or, in rx mode, a
                // dummy out byte); the received byte lands in BUF with PND set
                let rx = self.transfer(value as u8);
                self.buf = if self.con & 0x1000 != 0 { rx as u32 } else { value & 0xff };
                self.con |= 0x8000;
            }
            _ => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cmd(f: &mut SpiFlash, bytes: &[u8]) -> Vec<u8> {
        f.set_cs(true);
        let r = bytes.iter().map(|&b| f.transfer(b)).collect();
        f.set_cs(false);
        r
    }

    fn status(f: &mut SpiFlash) -> u8 {
        cmd(f, &[0x05, 0xff])[1]
    }

    #[test]
    fn program_needs_wren_wraps_in_its_page_and_only_clears_bits() {
        let mut f = SpiFlash::new();
        cmd(&mut f, &[0x02, 0x08, 0x00, 0x10, 0x00]);
        assert_eq!(f.mem[0x80010], 0xff, "no WREN: ignored");
        cmd(&mut f, &[0x06]);
        cmd(&mut f, &[0x02, 0x08, 0x00, 0xfe, 0xf0, 0x0f, 0xaa, 0x55]);
        assert_eq!(&f.mem[0x800fe..0x80100], &[0xf0, 0x0f]);
        assert_eq!(&f.mem[0x80000..0x80002], &[0xaa, 0x55], "wrapped to the page's start");
        assert_eq!(f.mem[0x80100], 0xff, "the next page untouched");
        cmd(&mut f, &[0x06]);
        cmd(&mut f, &[0x02, 0x08, 0x00, 0x00, 0x3c]);
        assert_eq!(f.mem[0x80000], 0x28, "bits only cleared");
    }

    #[test]
    fn timed_erase_is_busy_ignores_commands_and_cuts_part_done() {
        let mut f = SpiFlash::new();
        f.timing = FlashTiming { program: 100, erase: 1000 };
        f.mem[0x1000..0x2000].fill(0);
        cmd(&mut f, &[0x06]);
        cmd(&mut f, &[0x20, 0x00, 0x10, 0x00]);
        assert_eq!(f.log, vec![FlashOp { start: 0, end: 1000, cmd: 0x20, base: 0x1000, len: 0x1000 }]);
        f.now = 10;
        assert_eq!(status(&mut f), 0x03, "WIP and WEL while busy");
        assert_eq!(cmd(&mut f, &[0x9f, 0, 0, 0]), vec![0xff; 4], "the ID read ignored while busy");
        cmd(&mut f, &[0x06]);
        cmd(&mut f, &[0x20, 0x00, 0x30, 0x00]);
        assert_eq!(f.log.len(), 1, "an erase sent while busy is ignored");
        let cut = f.power_cut(250);
        assert_eq!(cut.map(|(op, done)| (op.cmd, done)), Some((0x20, 0x400)));
        assert!(f.mem[0x1000..0x1400].iter().all(|&b| b == 0xff), "the first quarter erased");
        assert!(f.mem[0x1400..0x2000].iter().all(|&b| b == 0), "the rest as it was");
        assert_eq!(status(&mut f), 0x00);
    }

    #[test]
    fn each_protection_setting_covers_its_rows_area() {
        let mut f = SpiFlash::new();
        let area = |f: &mut SpiFlash, bp: u8, cmp: bool| {
            f.status = [bp << 2, if cmp { 0x40 } else { 0 }];
            f.protected()
        };
        let all = (0, FLASH_SIZE);
        for (bp, want) in [
            (0b00000, (0, 0)), (0b11000, (0, 0)),
            (0b00001, (FLASH_SIZE - 0x10000, FLASH_SIZE)), (0b00100, (0x80000, FLASH_SIZE)),
            (0b01001, (0, 0x10000)), (0b01100, (0, 0x80000)),
            (0b00101, all), (0b01101, all), (0b10110, all), (0b11111, all),
            (0b10001, (FLASH_SIZE - 0x1000, FLASH_SIZE)), (0b10011, (FLASH_SIZE - 0x4000, FLASH_SIZE)),
            (0b10100, (FLASH_SIZE - 0x8000, FLASH_SIZE)), (0b10101, (FLASH_SIZE - 0x8000, FLASH_SIZE)),
            (0b11001, (0, 0x1000)), (0b11011, (0, 0x4000)), (0b11101, (0, 0x8000)),
        ] {
            assert_eq!(area(&mut f, bp, false), want, "BP {bp:05b}, CMP 0");
        }
        assert_eq!(area(&mut f, 0b00001, true), (0, FLASH_SIZE - 0x10000), "CMP 1: the rest of the chip");
        assert_eq!(area(&mut f, 0b11001, true), (0x1000, FLASH_SIZE));
        assert_eq!(area(&mut f, 0b00000, true), all);
        assert_eq!(area(&mut f, 0b00111, true), (0, 0));
        for bp in 0..32u8 {
            let (lo, hi) = area(&mut f, bp, false);
            let (clo, chi) = area(&mut f, bp, true);
            assert_eq!((hi - lo) + (chi - clo), FLASH_SIZE, "BP {bp:05b}: CMP 1 protects what CMP 0 leaves");
        }
    }

    #[test]
    fn a_protected_erase_or_program_is_ignored() {
        let mut f = SpiFlash::new();
        f.timing = FlashTiming { program: 100, erase: 1000 };
        f.status = [0x04, 0x00]; // BP0: the top 64 KiB
        let sector = 0xfc000..0xfc000 + 0x1000;
        f.mem[sector.clone()].fill(0x5a);
        assert_eq!(status(&mut f), 0x04, "BP0 reads back");
        assert_eq!(cmd(&mut f, &[0x35, 0xff])[1], 0x00);
        cmd(&mut f, &[0x06]);
        cmd(&mut f, &[0x20, 0x0f, 0xc0, 0x00]);
        assert!(f.mem[sector].iter().all(|&b| b == 0x5a), "the erase ignored");
        assert_eq!(status(&mut f), 0x06, "not busy; WEL as it was");
        assert!(f.log.is_empty() && f.ops == 0 && f.changed.is_none());
        cmd(&mut f, &[0x02, 0x0f, 0xc0, 0x00, 0x00]);
        assert_eq!(f.mem[0xfc000], 0x5a, "the program ignored");
        cmd(&mut f, &[0x60]);
        assert_eq!(f.mem[0xfc000], 0x5a, "a chip erase ignored while anything is protected");
        cmd(&mut f, &[0x20, 0x0e, 0xf0, 0x00]);
        assert_eq!(f.log.len(), 1, "an erase below the protected area goes ahead");
        f.now = 1000;
        f.status = [0x00, 0x40]; // CMP with BP 0: the whole chip
        assert_eq!(cmd(&mut f, &[0x35, 0xff])[1], 0x40);
        cmd(&mut f, &[0x06]);
        cmd(&mut f, &[0xd8, 0x00, 0x00, 0x00]);
        assert_eq!(f.log.len(), 1, "ignored");
    }

    #[test]
    fn untimed_operations_finish_at_once() {
        let mut f = SpiFlash::new();
        cmd(&mut f, &[0x06]);
        cmd(&mut f, &[0xd8, 0x01, 0x00, 0x00]);
        assert_eq!(status(&mut f), 0x00);
        assert_eq!(f.power_cut(0), None);
    }
}
