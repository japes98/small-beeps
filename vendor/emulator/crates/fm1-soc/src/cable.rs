//! A USB host on the first USB core's cable (fwtest's `--usb`).
//!
//! Off by default: the core's access port then answers as before (every access done at once,
//! the interrupt flags 0, no bus event). On, a host is on the cable: once the firmware has the
//! PHY on (CON0 bit 0) and the core's POWER byte (index 1) has bit 6 set, the host resets the
//! bus, enumerates the device over endpoint 0, configures it, and then moves USB MIDI event
//! packets: the script's packets to the MIDI streaming interface's bulk OUT endpoint, the
//! device's bulk IN packets to a log.
//!
//! From the sources: the block's words (CON0, the port, the endpoints' DMA addresses and
//! counts), the core's byte registers by index, the bits' names, the interrupts (SOF 8, the
//! controller 9) and the 4 bytes the DMA writes past a full received packet. Everything else
//! here, the order of a transfer's steps above all, is the model's own: it is permissive and
//! logs what it doesn't expect rather than refusing it.

use std::collections::VecDeque;

/// The core's register block and its access port.
pub const BLOCK: u32 = 0x11800;

/// Frames a millisecond apart, at the full-speed frame rate.
const FRAME_EVERY_MS: u64 = 1;
/// From the connect to the bus reset, and from the reset to the first request.
const SETTLE_FRAMES: u32 = 10;
/// A request the device doesn't finish in this many frames is given up.
const ANSWER_FRAMES: u32 = 200;
/// The address the host gives the device.
const GIVEN_ADDRESS: u8 = 1;
/// From the set-address request's status stage to the host's check of `FADDR`: the device sets
/// its address once the status stage is done, and the host waits this many frames for it.
const ADDRESS_FRAMES: u32 = 2;
/// CON0 bits 16 and 17 (`DM_SE`, `DP_SE`).
const LINES: u32 = 3 << 16;
/// With no host the two lines' bits change from read to read (HARDWARE-SPEC HW-176, HW-177);
/// fwtest steps through these, one a read, so they never read steadily 0.
const NO_HOST_LINES: [u32; 4] = [1 << 16, 3 << 16, 2 << 16, 0];

/// Endpoint `ep`'s DMA words: (count, transmit address, receive address), as offsets in the
/// block. Endpoint 0 has one address for both directions.
fn dma_words(ep: usize) -> (u32, u32, u32) {
    match ep {
        0 => (0x08, 0x18, 0x18),
        1 => (0x0c, 0x1c, 0x20),
        2 => (0x10, 0x24, 0x28),
        3 => (0x14, 0x2c, 0x30),
        _ => (0x34, 0x38, 0x3c),
    }
}

/// What the device's memory and words look like to the host: the SoC lends itself.
pub trait Wire {
    fn word(&mut self, addr: u32) -> u32;
    fn peek(&mut self, addr: u32) -> u8;
    fn poke(&mut self, addr: u32, b: u8);
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Stage {
    /// No host, or the device hasn't connected.
    Waiting,
    /// Connected at frame `n`: the reset comes `SETTLE_FRAMES` later.
    Connected(u32),
    /// Reset at frame `n`: requests start `SETTLE_FRAMES` later.
    Reset(u32),
    /// Enumerating: request `i` of the list.
    Asking(usize),
    /// Request `i` set the address, its status stage done at frame `n`: `FADDR` is checked
    /// `ADDRESS_FRAMES` later.
    Addressing(usize, u32),
    /// Configured: MIDI moves.
    Running,
    /// Enumeration stopped (a stall, no answer, or a descriptor the host can't use).
    Stopped,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Turn {
    /// The setup packet is waiting for the device to take it.
    Offered,
    /// Taken; the data stage (IN) or the status stage is next.
    Taken,
}

#[derive(Debug, Clone)]
struct Request {
    what: &'static str,
    setup: [u8; 8],
    /// Bytes to read in the data stage (0: no data stage).
    want: usize,
}

#[derive(Debug, Default, Clone)]
pub struct Found {
    pub vendor: Option<u16>,
    pub product: Option<u16>,
    pub manufacturer: Option<String>,
    pub prod_str: Option<String>,
    pub serial: Option<String>,
    pub address: Option<u8>,
    pub configuration: Option<u8>,
    /// The MIDI streaming interface's bulk endpoints: (OUT to the device, IN from it).
    pub midi_out_ep: Option<u8>,
    pub midi_in_ep: Option<u8>,
}

#[derive(Default)]
pub struct Cable {
    /// `--usb`: a host is on the cable.
    pub on: bool,
    /// The core's common byte registers, indexes 0 to 15.
    common: [u8; 16],
    /// Indexes 16 to 27 for each of endpoints 0 to 4 (selected by index 14).
    per_ep: [[u8; 12]; 5],
    sof_flag: bool,
    /// CON0's reads with no host, for the lines' bits.
    no_host_reads: u32,
    frame: u32,
    pub next_frame: u64,
    stage: Option<Stage>,
    turn: Option<Turn>,
    asked_at: u32,
    data_end_seen: bool,
    got: Vec<u8>,
    requests: Vec<Request>,
    device_desc: Vec<u8>,
    config_desc: Vec<u8>,
    /// Event packets from the script, waiting for the device: (due cycle, packet).
    pub to_device: VecDeque<(u64, [u8; 4])>,
    /// A bulk OUT packet is waiting in the device's buffer.
    out_busy: bool,
    /// What the host found.
    pub found: Found,
    /// The log: (cycle, what happened).
    pub log: Vec<(u64, String)>,
    /// The device's event packets: (cycle, packet).
    pub from_device: Vec<(u64, [u8; 4])>,
    /// Packets sent to the device, and event packets in them.
    pub sent_packets: u64,
    pub sent_events: u64,
    /// What the host didn't expect.
    pub problems: Vec<String>,
}

impl Cable {
    fn stage(&self) -> Stage {
        self.stage.unwrap_or(Stage::Waiting)
    }

    fn ep_sel(&self) -> usize {
        (self.common[14] as usize & 0xf).min(4)
    }

    fn note(&mut self, now: u64, s: String) {
        self.log.push((now, s));
    }

    fn problem(&mut self, now: u64, s: String) {
        self.note(now, format!("problem: {s}"));
        self.problems.push(s);
    }

    /// The controller's interrupt: an enabled flag is up and CON0 bit 11 is set.
    pub fn controller_irq(&self, con0: u32) -> bool {
        let c = &self.common;
        let any = (c[2] & c[7]) | (c[3] & c[8]) | (c[4] & c[9]) | (c[5] & c[10]) | (c[6] & c[11]);
        self.on && con0 & (1 << 11) != 0 && any != 0
    }

    /// The SOF interrupt: a frame has started and CON0 bit 10 is set.
    pub fn sof_irq(&self, con0: u32) -> bool {
        self.on && con0 & (1 << 10) != 0 && self.sof_flag
    }

    /// CON0 as read. With no host, the stored word with the lines' bits (16, 17) changing from
    /// read to read. With the host, the two pending bits (13 SOF, 14 the controller), and the
    /// lines' bits as the host holds them: 0 until the device connects, then bit 17 (`DP_SE`)
    /// set and bit 16 clear (HW-177; HW-182, one reading after the set-up).
    pub fn con0_read(&mut self, stored: u32) -> u32 {
        if !self.on {
            let lines = NO_HOST_LINES[self.no_host_reads as usize % NO_HOST_LINES.len()];
            self.no_host_reads = self.no_host_reads.wrapping_add(1);
            return (stored & !LINES) | lines;
        }
        let mut v = stored & !((1 << 13) | (1 << 14) | LINES);
        if self.connected(stored) {
            v |= 1 << 17;
        }
        if self.sof_flag {
            v |= 1 << 13;
        }
        if self.controller_irq(stored | (1 << 11)) {
            v |= 1 << 14;
        }
        v
    }

    /// A write to CON0: bit 12 clears the SOF pending.
    pub fn con0_write(&mut self, value: u32) {
        if value & (1 << 12) != 0 {
            self.sof_flag = false;
        }
    }

    /// A read through the access port (`index << 8`, bit 14 set): the byte.
    pub fn port_read(&mut self, index: usize) -> u8 {
        match index {
            // the interrupt flags clear when read
            2..=6 => std::mem::take(&mut self.common[index]),
            12 => self.frame as u8,
            13 => (self.frame >> 8) as u8 & 7,
            0..=15 => self.common[index],
            16..=27 => self.per_ep[self.ep_sel()][index - 16],
            _ => 0,
        }
    }

    /// A write through the access port.
    pub fn port_write(&mut self, now: u64, index: usize, b: u8) {
        let ep = self.ep_sel();
        match index {
            2..=6 | 12 | 13 => {}
            0..=15 => self.common[index] = b,
            // endpoint 0's CSR0
            17 if ep == 0 => {
                let r = &mut self.per_ep[0][1];
                if b & 0x40 != 0 {
                    *r &= !0x01;
                }
                if b & 0x80 != 0 {
                    *r &= !0x10;
                }
                if b & 0x04 == 0 {
                    *r &= !0x04;
                }
                if b & 0x08 != 0 {
                    self.data_end_seen = true;
                }
                if b & 0x02 != 0 {
                    *r |= 0x02;
                }
                if b & 0x20 != 0 {
                    *r = (*r & !0x20) | 0x04;
                    self.stall(now);
                }
            }
            // a transmit endpoint's TXCSR (low byte)
            17 => {
                let r = &mut self.per_ep[ep][1];
                let keep = *r & 0x01;
                *r = (b & !0x08) | keep | (b & 0x01);
                if b & 0x08 != 0 {
                    *r &= !0x01;
                }
            }
            // a receive endpoint's RXCSR (low byte): bit 0 written 0 frees the buffer
            20 => {
                let r = &mut self.per_ep[ep][4];
                let ready = *r & 0x01 != 0 && b & 0x01 != 0 && b & 0x10 == 0;
                *r = (b & !0x11) | if ready { 0x01 } else { 0 };
                if !ready && ep as u8 == self.found.midi_out_ep.unwrap_or(0xff) & 0xf {
                    self.out_busy = false;
                }
            }
            16..=27 => self.per_ep[ep][index - 16] = b,
            _ => {}
        }
    }

    fn stall(&mut self, now: u64) {
        if let (Stage::Asking(i), Some(_)) = (self.stage(), self.turn) {
            let what = self.requests[i].what;
            self.problem(now, format!("the device stalled {what}"));
            self.common[2] |= 1;
            self.stage = Some(Stage::Stopped);
            self.turn = None;
        }
    }

    /// The device has connected when the PHY is on and POWER's bit 6 is set.
    fn connected(&self, con0: u32) -> bool {
        con0 & 1 != 0 && self.common[1] & 0x40 != 0
    }

    /// One frame: called at `next_frame`.
    pub fn frame<W: Wire>(&mut self, now: u64, cycles_per_ms: u64, w: &mut W) {
        self.next_frame = now + FRAME_EVERY_MS * cycles_per_ms;
        if !self.on {
            return;
        }
        let con0 = w.word(BLOCK);
        match self.stage() {
            Stage::Waiting => {
                if self.connected(con0) {
                    self.note(now, "connect".into());
                    self.stage = Some(Stage::Connected(self.frame));
                }
                return;
            }
            _ if !self.connected(con0) && self.stage() != Stage::Stopped => {
                self.note(now, "disconnect".into());
                self.stage = Some(Stage::Waiting);
                self.turn = None;
                return;
            }
            _ => {}
        }
        self.frame = (self.frame + 1) & 0x7ff;
        self.sof_flag = true;
        self.common[6] |= 1 << 3;
        match self.stage() {
            Stage::Connected(at) if self.frame.wrapping_sub(at) & 0x7ff >= SETTLE_FRAMES => {
                self.note(now, "bus reset".into());
                self.common[0] = 0;
                self.common[6] |= 1 << 2;
                self.per_ep = [[0; 12]; 5];
                self.stage = Some(Stage::Reset(self.frame));
            }
            Stage::Reset(at) if self.frame.wrapping_sub(at) & 0x7ff >= SETTLE_FRAMES => {
                self.requests = vec![get_descriptor("get the device descriptor, 64 bytes", 1, 0, 64)];
                self.start(now, 0, w);
            }
            Stage::Asking(i) => self.step(now, i, w),
            Stage::Addressing(i, at) if self.frame.wrapping_sub(at) & 0x7ff >= ADDRESS_FRAMES => {
                let what = self.requests[i].what;
                if self.common[0] & 0x7f != GIVEN_ADDRESS {
                    self.problem(now, format!("FADDR is {} after {what} {GIVEN_ADDRESS}", self.common[0]));
                }
                self.found.address = Some(self.common[0] & 0x7f);
                self.note(now, format!("address {} checked", self.common[0] & 0x7f));
                if i + 1 < self.requests.len() {
                    self.start(now, i + 1, w);
                }
            }
            Stage::Running => self.midi(now, w),
            _ => {}
        }
    }

    fn start<W: Wire>(&mut self, now: u64, i: usize, w: &mut W) {
        self.stage = Some(Stage::Asking(i));
        let r = self.requests[i].clone();
        let (_, _, adr) = dma_words(0);
        let at = w.word(BLOCK + adr);
        for (k, b) in r.setup.iter().enumerate() {
            w.poke(at.wrapping_add(k as u32), *b);
        }
        self.per_ep[0][6] = 8;
        self.per_ep[0][1] |= 0x01;
        self.common[2] |= 1;
        self.turn = Some(Turn::Offered);
        self.asked_at = self.frame;
        self.data_end_seen = false;
        self.got.clear();
        self.note(now, format!("setup {} at {at:#010x}: {}", r.what, hex(&r.setup)));
    }

    fn step<W: Wire>(&mut self, now: u64, i: usize, w: &mut W) {
        let want = self.requests[i].want;
        match self.turn {
            Some(Turn::Offered) if self.per_ep[0][1] & 0x01 == 0 => {
                self.turn = Some(Turn::Taken);
                if want == 0 {
                    // no data stage: the status stage completes at once
                    self.common[2] |= 1;
                    self.finish(now, i, w);
                }
                return;
            }
            Some(Turn::Taken) if want > 0 && self.per_ep[0][1] & 0x02 != 0 => {
                let (cnt, _, adr) = dma_words(0);
                let n = (w.word(BLOCK + cnt) & 0x7ff) as usize;
                let at = w.word(BLOCK + adr);
                let n = n.min(64);
                for k in 0..n {
                    let b = w.peek(at.wrapping_add(k as u32));
                    self.got.push(b);
                }
                self.per_ep[0][1] &= !0x02;
                self.common[2] |= 1;
                self.note(now, format!("in {n} bytes from {at:#010x}"));
                if n < 64 || self.got.len() >= want || self.data_end_seen {
                    self.got.truncate(want);
                    self.finish(now, i, w);
                }
                return;
            }
            _ => {}
        }
        if self.frame.wrapping_sub(self.asked_at) & 0x7ff >= ANSWER_FRAMES {
            let what = self.requests[i].what;
            self.problem(now, format!("no answer to {what} within {ANSWER_FRAMES} ms"));
            self.stage = Some(Stage::Stopped);
            self.turn = None;
        }
    }

    /// Request `i` is done: look at what came back and ask the next.
    fn finish<W: Wire>(&mut self, now: u64, i: usize, w: &mut W) {
        self.turn = None;
        let what = self.requests[i].what;
        let got = std::mem::take(&mut self.got);
        self.note(now, format!("done {what}: {}", hex(&got)));
        match what {
            "get the device descriptor, 64 bytes" => {
                if got.len() < 8 || got[1] != 1 {
                    return self.give_up(now, "the device descriptor's first bytes");
                }
                self.requests.push(set_request("set the address", 5, GIVEN_ADDRESS as u16));
                self.requests.push(get_descriptor("get the device descriptor", 1, 0, 18));
            }
            "set the address" => {
                // the status stage is done: the device takes its address now, checked later
                self.stage = Some(Stage::Addressing(i, self.frame));
                return;
            }
            "get the device descriptor" => {
                if got.len() < 18 {
                    return self.give_up(now, "the device descriptor");
                }
                self.found.vendor = Some(u16::from_le_bytes([got[8], got[9]]));
                self.found.product = Some(u16::from_le_bytes([got[10], got[11]]));
                self.device_desc = got;
                self.requests.push(get_descriptor("get the configuration, 9 bytes", 2, 0, 9));
            }
            "get the configuration, 9 bytes" => {
                if got.len() < 9 || got[1] != 2 {
                    return self.give_up(now, "the configuration descriptor's header");
                }
                let total = u16::from_le_bytes([got[2], got[3]]);
                self.requests.push(get_descriptor("get the configuration", 2, 0, total));
            }
            "get the configuration" => {
                self.config_desc = got;
                self.read_configuration(now);
                self.requests.push(get_descriptor("get string 0", 3, 0, 255));
            }
            "get string 0" => {
                let d = self.device_desc.clone();
                for (idx, name) in [(d[14], "get the manufacturer"), (d[15], "get the product"), (d[16], "get the serial number")] {
                    if idx != 0 {
                        self.requests.push(get_descriptor(name, 3, idx, 255).with_language(&got));
                    }
                }
                let value = self.config_desc.get(5).copied().unwrap_or(1) as u16;
                self.requests.push(set_request("set the configuration", 9, value));
            }
            "get the manufacturer" => self.found.manufacturer = Some(utf16(&got)),
            "get the product" => self.found.prod_str = Some(utf16(&got)),
            "get the serial number" => self.found.serial = Some(utf16(&got)),
            "set the configuration" => {
                self.found.configuration = self.config_desc.get(5).copied();
                self.note(now, "configured".into());
                self.stage = Some(Stage::Running);
                return;
            }
            _ => {}
        }
        if i + 1 < self.requests.len() {
            self.start(now, i + 1, w);
        }
    }

    fn give_up(&mut self, now: u64, what: &str) {
        self.problem(now, format!("the host can't use {what}"));
        self.stage = Some(Stage::Stopped);
    }

    /// The MIDI streaming interface (class 1, subclass 3) and its bulk endpoints.
    fn read_configuration(&mut self, now: u64) {
        let d = &self.config_desc;
        let (mut k, mut in_midi) = (0usize, false);
        let (mut out_ep, mut in_ep) = (None, None);
        while k + 2 <= d.len() {
            let len = d[k] as usize;
            if len < 2 || k + len > d.len() {
                break;
            }
            match d[k + 1] {
                4 if len >= 9 => in_midi = d[k + 5] == 1 && d[k + 6] == 3,
                5 if len >= 7 && in_midi && d[k + 3] & 3 == 2 => {
                    if d[k + 2] & 0x80 != 0 {
                        in_ep = in_ep.or(Some(d[k + 2]));
                    } else {
                        out_ep = out_ep.or(Some(d[k + 2]));
                    }
                }
                _ => {}
            }
            k += len;
        }
        self.found.midi_out_ep = out_ep;
        self.found.midi_in_ep = in_ep;
        if out_ep.is_none() && in_ep.is_none() {
            self.problem(now, "no MIDI streaming interface with bulk endpoints in the configuration".into());
        }
    }

    /// Configured: the device's IN packets, then the script's packets out.
    fn midi<W: Wire>(&mut self, now: u64, w: &mut W) {
        if let Some(ep) = self.found.midi_in_ep {
            let n = (ep & 0xf) as usize;
            if (1..=4).contains(&n) && self.per_ep[n][1] & 0x01 != 0 {
                let (cnt, tadr, _) = dma_words(n);
                let len = (w.word(BLOCK + cnt) & 0x7ff) as usize;
                let at = w.word(BLOCK + tadr);
                let bytes: Vec<u8> = (0..len.min(512)).map(|k| w.peek(at.wrapping_add(k as u32))).collect();
                self.per_ep[n][1] &= !0x01;
                self.common[if n < 8 { 2 } else { 3 }] |= 1 << n;
                if len % 4 != 0 {
                    self.problem(now, format!("an IN packet of {len} bytes, not a whole number of event packets"));
                }
                for p in bytes.chunks_exact(4) {
                    if p != [0, 0, 0, 0] {
                        self.from_device.push((now, [p[0], p[1], p[2], p[3]]));
                    }
                }
                self.note(now, format!("in ep {n}: {}", hex(&bytes)));
            }
        }
        if let Some(ep) = self.found.midi_out_ep {
            let n = (ep & 0xf) as usize;
            if !(1..=4).contains(&n) || self.out_busy || self.per_ep[n][4] & 0x01 != 0 {
                return;
            }
            let max = match self.per_ep[n][3] as usize { 0 => 64, m => m.min(64) } / 4;
            let mut bytes = Vec::new();
            while bytes.len() / 4 < max.max(1) {
                match self.to_device.front() {
                    Some((at, p)) if *at <= now => {
                        bytes.extend_from_slice(p);
                        self.to_device.pop_front();
                    }
                    _ => break,
                }
            }
            if bytes.is_empty() {
                return;
            }
            let (_, _, radr) = dma_words(n);
            let at = w.word(BLOCK + radr);
            for (k, b) in bytes.iter().enumerate() {
                w.poke(at.wrapping_add(k as u32), *b);
            }
            // the DMA writes 4 bytes past the packet
            for k in 0..4 {
                w.poke(at.wrapping_add((bytes.len() + k) as u32), 0);
            }
            self.per_ep[n][6] = bytes.len() as u8;
            self.per_ep[n][7] = 0;
            self.per_ep[n][4] |= 0x01;
            self.common[4] |= 1 << n;
            self.out_busy = true;
            self.sent_packets += 1;
            self.sent_events += bytes.len() as u64 / 4;
            self.note(now, format!("out ep {n} at {at:#010x}: {}", hex(&bytes)));
        }
    }
}

fn get_descriptor(what: &'static str, kind: u8, index: u8, len: u16) -> Request {
    let l = len.to_le_bytes();
    Request { what, setup: [0x80, 6, index, kind, 0, 0, l[0], l[1]], want: len as usize }
}

fn set_request(what: &'static str, request: u8, value: u16) -> Request {
    let v = value.to_le_bytes();
    Request { what, setup: [0, request, v[0], v[1], 0, 0, 0, 0], want: 0 }
}

impl Request {
    /// A string in the device's first language (string 0's first code), or 0x0409.
    fn with_language(mut self, string0: &[u8]) -> Self {
        let (a, b) = if string0.len() >= 4 { (string0[2], string0[3]) } else { (0x09, 0x04) };
        self.setup[4] = a;
        self.setup[5] = b;
        self
    }
}

fn utf16(d: &[u8]) -> String {
    let n = (d.first().copied().unwrap_or(0) as usize).min(d.len());
    let units: Vec<u16> = d.get(2..n).unwrap_or(&[]).chunks_exact(2).map(|c| u16::from_le_bytes([c[0], c[1]])).collect();
    String::from_utf16_lossy(&units)
}

fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect::<Vec<_>>().join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    /// A device written in the test: memory and the block's words.
    #[derive(Default)]
    struct Dev {
        mem: HashMap<u32, u8>,
        words: HashMap<u32, u32>,
    }

    impl Wire for Dev {
        fn word(&mut self, addr: u32) -> u32 {
            *self.words.get(&addr).unwrap_or(&0)
        }
        fn peek(&mut self, addr: u32) -> u8 {
            *self.mem.get(&addr).unwrap_or(&0)
        }
        fn poke(&mut self, addr: u32, b: u8) {
            self.mem.insert(addr, b);
        }
    }

    const EP0_BUF: u32 = 0x01c1_0000;
    const OUT_BUF: u32 = 0x01c1_0100;
    const IN_BUF: u32 = 0x01c1_0200;

    fn descriptor(c: &Cable, d: &mut Dev, setup: &[u8]) -> Vec<u8> {
        let dev = vec![18, 1, 0, 2, 0, 0, 0, 64, 0x09, 0x12, 0x01, 0x00, 0, 1, 1, 2, 0, 1];
        let name = |s: &str| {
            let mut v = vec![2 + 2 * s.len() as u8, 3];
            for ch in s.encode_utf16() {
                v.extend_from_slice(&ch.to_le_bytes());
            }
            v
        };
        // configuration: one MIDI streaming interface, bulk OUT 1 and bulk IN 0x82
        let cfg = vec![
            9, 2, 39, 0, 1, 1, 0, 0x80, 50, //
            9, 4, 0, 0, 2, 1, 3, 0, 0, //
            7, 5, 0x01, 2, 64, 0, 0, //
            7, 5, 0x82, 2, 64, 0, 0, //
            7, 0x24, 1, 0, 1, 7, 0,
        ];
        let _ = (c, d);
        let len = u16::from_le_bytes([setup[6], setup[7]]) as usize;
        let mut v = match (setup[3], setup[2]) {
            (1, _) => dev,
            (2, _) => cfg,
            (3, 0) => vec![4, 3, 0x09, 0x04],
            (3, 1) => name("small-beeps"),
            (3, _) => name("small-beeps test"),
            _ => vec![],
        };
        v.truncate(len);
        v
    }

    /// The device's side of endpoint 0, as a firmware would do it, polled each frame.
    fn device_ep0(c: &mut Cable, d: &mut Dev) {
        c.port_write(0, 14, 0);
        let csr0 = c.port_read(17);
        if csr0 & 0x01 == 0 {
            return;
        }
        let setup: Vec<u8> = (0..8).map(|k| d.peek(EP0_BUF + k)).collect();
        match setup[1] {
            6 => {
                let v = descriptor(c, d, &setup);
                c.port_write(0, 17, 0x40);
                for (k, b) in v.iter().enumerate() {
                    d.poke(EP0_BUF + k as u32, *b);
                }
                d.words.insert(BLOCK + 0x08, v.len() as u32);
                c.port_write(0, 17, 0x0a);
            }
            5 => {
                c.port_write(0, 17, 0x48);
                c.port_write(0, 0, setup[2]);
            }
            _ => c.port_write(0, 17, 0x48),
        }
    }

    fn run(c: &mut Cable, d: &mut Dev, frames: u32) {
        for f in 0..frames {
            c.frame(f as u64, 1, d);
            device_ep0(c, d);
            // the device frees its OUT buffer once it has read it
            c.port_write(0, 14, 1);
            if c.port_read(20) & 1 != 0 {
                c.port_write(0, 20, 0);
            }
        }
    }

    fn plugged() -> (Cable, Dev) {
        let mut c = Cable { on: true, ..Default::default() };
        let mut d = Dev::default();
        d.words.insert(BLOCK, 1);
        d.words.insert(BLOCK + 0x18, EP0_BUF);
        d.words.insert(BLOCK + 0x20, OUT_BUF);
        d.words.insert(BLOCK + 0x24, IN_BUF);
        c.port_write(0, 1, 0x60);
        (c, d)
    }

    #[test]
    fn a_host_on_the_cable_enumerates_and_configures_the_device() {
        let (mut c, mut d) = plugged();
        run(&mut c, &mut d, 200);
        assert!(c.problems.is_empty(), "{:?}", c.problems);
        assert_eq!(c.found.vendor, Some(4617)); // pid.codes' vendor ID
        assert_eq!(c.found.product, Some(0x0001));
        assert_eq!(c.found.address, Some(GIVEN_ADDRESS));
        assert_eq!(c.found.manufacturer.as_deref(), Some("small-beeps"));
        assert_eq!(c.found.configuration, Some(1));
        assert_eq!((c.found.midi_out_ep, c.found.midi_in_ep), (Some(0x01), Some(0x82)));
        assert_eq!(c.stage(), Stage::Running);
    }

    #[test]
    fn midi_moves_both_ways_once_configured() {
        let (mut c, mut d) = plugged();
        c.to_device.push_back((0, [0x09, 0x90, 0x3c, 0x64]));
        c.to_device.push_back((0, [0x08, 0x80, 0x3c, 0x00]));
        run(&mut c, &mut d, 200);
        assert_eq!((c.sent_packets, c.sent_events), (1, 2));
        assert_eq!(d.peek(OUT_BUF + 1), 0x90);
        // the device sends a note on through endpoint 2
        for (k, b) in [0x09u8, 0x90, 0x40, 0x7f].iter().enumerate() {
            d.poke(IN_BUF + k as u32, *b);
        }
        d.words.insert(BLOCK + 0x10, 4);
        c.port_write(0, 14, 2);
        c.port_write(0, 17, 0x01);
        run(&mut c, &mut d, 2);
        assert_eq!(c.from_device.len(), 1);
        assert_eq!(c.from_device[0].1, [0x09, 0x90, 0x40, 0x7f]);
    }

    #[test]
    fn nothing_happens_without_the_host_or_the_connect() {
        let mut c = Cable::default();
        let mut d = Dev::default();
        c.frame(0, 1, &mut d);
        assert!(c.log.is_empty());
        let (mut c, mut d) = plugged();
        c.port_write(0, 1, 0);
        run(&mut c, &mut d, 50);
        assert!(c.log.is_empty());
        assert_eq!(c.port_read(6), 0);
    }

    /// A device that takes its address only once the set-address request's status stage is
    /// done (the controller's endpoint 0 flag after the request), or never.
    fn run_addressing(c: &mut Cable, d: &mut Dev, frames: u32, takes_it: bool) {
        let mut pending = None;
        for f in 0..frames {
            c.frame(f as u64, 1, d);
            if c.port_read(2) & 1 != 0 {
                if let Some(a) = pending.take() {
                    c.port_write(0, 0, a);
                }
            }
            c.port_write(0, 14, 0);
            if c.port_read(17) & 1 != 0 && d.peek(EP0_BUF + 1) == 5 {
                c.port_write(0, 17, 0x48);
                if takes_it {
                    pending = Some(d.peek(EP0_BUF + 2));
                }
                continue;
            }
            device_ep0(c, d);
        }
    }

    #[test]
    fn the_address_is_checked_after_the_status_stage() {
        let (mut c, mut d) = plugged();
        run_addressing(&mut c, &mut d, 200, true);
        assert!(c.problems.is_empty(), "{:?}", c.problems);
        assert_eq!(c.found.address, Some(GIVEN_ADDRESS));
        assert_eq!(c.stage(), Stage::Running);
        let (mut c, mut d) = plugged();
        run_addressing(&mut c, &mut d, 200, false);
        assert_eq!(c.problems, vec![format!("FADDR is 0 after set the address {GIVEN_ADDRESS}")]);
    }

    #[test]
    fn the_lines_wander_with_no_host_and_the_host_holds_them() {
        let mut c = Cable::default();
        let reads: Vec<u32> = (0..8).map(|_| c.con0_read(0x8001) & LINES).collect();
        assert!(reads.windows(2).all(|w| w[0] | w[1] != 0), "{reads:x?}");
        assert!(reads.iter().any(|r| *r != 0));
        assert_eq!(c.con0_read(0x8001) & !LINES, 0x8001);
        let mut c = Cable { on: true, ..Default::default() };
        assert_eq!(c.con0_read(0x8001 | LINES) & LINES, 0, "a host, the device not connected");
        c.port_write(0, 1, 0x60);
        assert_eq!(c.con0_read(0x8001) & LINES, 1 << 17, "connected: D+ high");
    }

    #[test]
    fn a_device_that_never_answers_is_reported() {
        let (mut c, mut d) = plugged();
        for f in 0..400 {
            c.frame(f, 1, &mut d);
        }
        assert_eq!(c.problems.len(), 1);
        assert!(c.problems[0].contains("no answer"));
    }
}
