/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The store (store.h; docs/DESIGN-NOTES.md, M7; docs/STORE-FORMAT.md):
 * SPI0's flash commands (HW-47), the ring of sectors and its records.
 */

#include "store.h"
#include "WL82.h"

/* HW-47: SPI0's CON bit 12 makes a transfer receive into BUF, bit 15
 * reads 1 when a byte is done, writing bit 14 clears it; the chip select
 * is PD0, low to select. The chip's commands. */
#define SPI_RX       (1u << 12)
#define SPI_CLEAR    (1u << 14)
#define SPI_DONE     (1u << 15)
#define CS_PIN       1u
#define CMD_READ     0x03u
#define CMD_STATUS   0x05u
#define CMD_WREN     0x06u
#define CMD_PROGRAM  0x02u
#define CMD_ERASE    0x20u
#define CMD_ID       0x9Fu
#define STATUS_BUSY  0x01u
/* How long a command may keep the chip busy before it counts as failed:
 * far past the longest erase (12 ms, HW-77). */
#define BUSY_LIMIT_TICKS (3000u * 24000u)

/* The formats (docs/STORE-FORMAT.md). */
#define SECTOR_MAGIC  0x31534253u   /* "SBS1" in memory order */
#define FORMAT        1u
#define RECORD_MAGIC  0xA5u
#define HEADER        12u           /* a record's header */
#define BLOCK         16u           /* records start on a 16-byte boundary */
/* The largest record: a firmware kind's part (BR-9), larger than the
 * base's (a patch, 112 bytes). */
#define RECORD_MAX    ((HEADER + STORE_FW_TAG + STORE_FW_PART + 4 + BLOCK - 1) / BLOCK * BLOCK)
#define NONE          0xFFFFFFFFu

/* The keys: each user slot, then the selection, the settings and the
 * reset record. A key's newest valid record: its sequence number and
 * chip offset (0: none, as no record starts at offset 0). */
#define KEY_SELECTION STORE_SLOTS
#define KEY_SETTINGS  (STORE_SLOTS + 1u)
#define KEY_RESET     (STORE_SLOTS + 2u)
#define KEYS          (STORE_SLOTS + 3u)
/* Since clean-1027 (BR-9) the firmware kinds' parts follow the base's
 * keys, STORE_FW_KEYS of them, each the newest record of one part of one
 * kind and id (fwk: which, its part count and its write's tag), a place
 * free while its addr is 0. */
#define ALL_KEYS      (KEYS + STORE_FW_KEYS)
static struct { u32 seq, addr; } key[ALL_KEYS];
static struct { u8 kind, id, part, parts; u32 tag; } fwk[STORE_FW_KEYS];
volatile struct sb_store_fw_record sb_store_fw;

/* The sectors' sequence numbers as start-up found them, and the ring. */
static u32 sector_seq[STORE_SECTORS];
static u8 sector_valid[STORE_SECTORS];
static u32 head = NONE, head_seq, append, next_seq = 1;

static u8 sector_buf[STORE_SECTOR] __attribute__((aligned(4)));
static u8 record_buf[RECORD_MAX], check_buf[RECORD_MAX];
/* A sector's header, read or about to be written (static: main's stack
 * is small, R-PERF-3). */
static u8 h[BLOCK];

volatile struct sb_store_record sb_store __attribute__((section(".beacon.store")));

#if defined(SB_TEST_STORE_CUT)
/* The power cut test build (tools/fw-suite.py): two words at this chip
 * offset, below the store, which only the test's flash file writes: the
 * commands to send whole, then the bytes of the next page program to send
 * before the cut (0: none). The cut is a halt with interrupts off. */
#define CUT_PARAM 0xE8000u
static u32 cut_after = NONE, cut_bytes;
#endif

/* --- CRC-32 (the common one: reflected, polynomial 0xEDB88320, all ones
 * in and out), by nibbles. ------------------------------------------- */
static const u32 crc_nibble[16] = {
    0x00000000u, 0x1DB71064u, 0x3B6E20C8u, 0x26D930ACu, 0x76DC4190u, 0x6B6B51F4u,
    0x4DB26158u, 0x5005713Cu, 0xEDB88320u, 0xF00F9344u, 0xD6D6A3E8u, 0xCB61B38Cu,
    0x9B64C2B0u, 0x86D3D2D4u, 0xA00AE278u, 0xBDBDF21Cu,
};

static u32 crc32(const u8 *p, u32 n)
{
    u32 c = 0xFFFFFFFFu;

    while (n--) {
        c ^= *p++;
        c = c >> 4 ^ crc_nibble[c & 0xF];
        c = c >> 4 ^ crc_nibble[c & 0xF];
    }
    return ~c;
}

static u32 rd32(const u8 *p)
{
    return (u32)p[0] | (u32)p[1] << 8 | (u32)p[2] << 16 | (u32)p[3] << 24;
}

static void wr32(u8 *p, u32 v)
{
    p[0] = (u8)v;
    p[1] = (u8)(v >> 8);
    p[2] = (u8)(v >> 16);
    p[3] = (u8)(v >> 24);
}

/* --- SPI0 and the chip's commands (HW-47) ---------------------------- */
static void select(void)
{
    JL_PORTD->OUT &= ~CS_PIN;
}

static void deselect(void)
{
    JL_PORTD->OUT |= CS_PIN;
}

/* One byte out, and its time on the bus. */
static void clock_byte(u32 b)
{
    JL_SPI0->BUF = b;
    while (!(JL_SPI0->CON & SPI_DONE))
        ;
    JL_SPI0->CON |= SPI_CLEAR;
}

/* A byte in. The read of BUF is always used: fwtest 0.5.0 can run a
 * dual-issue pair around a read whose result is unused wrongly
 * (HARNESS.md, "Instructions"), so the send side never reads it. */
static u32 xfer(u32 b)
{
    clock_byte(b);
    return JL_SPI0->BUF & 0xFFu;
}

static void send(u32 b)
{
    JL_SPI0->CON &= ~SPI_RX;
    clock_byte(b);
}

static void command(u32 cmd, u32 addr)
{
    select();
    send(cmd);
    send(addr >> 16 & 0xFFu);
    send(addr >> 8 & 0xFFu);
    send(addr & 0xFFu);
}

static void read(u32 addr, u8 *buf, u32 n)
{
    command(CMD_READ, addr);
    JL_SPI0->CON |= SPI_RX;
    while (n--)
        *buf++ = (u8)xfer(0xFFu);
    JL_SPI0->CON &= ~SPI_RX;
    deselect();
}

#if defined(SB_TEST_STORE_BUSY)
/* The busy test build: each command keeps main as long as the part's
 * longest (HW-77: a 4 KiB erase 12 ms, a page program 3 ms); fwtest's
 * chip is never busy (HW-82). */
#define BUSY_ERASE_TICKS   (12u * 24000u)
#define BUSY_PROGRAM_TICKS (3u * 24000u)
static void busy_for(u32 ticks)
{
    u32 t = sb_now();

    while (sb_now() - t < ticks)
        ;
}
#endif

/* Waits while the chip says it is busy; 0 when it is done. Interrupts
 * stay on all the while, and everything they run is in RAM. */
static int wait_ready(void)
{
    u32 t = sb_now(), status, d;

    do {
        select();
        send(CMD_STATUS);
        JL_SPI0->CON |= SPI_RX;
        status = xfer(0xFFu);
        JL_SPI0->CON &= ~SPI_RX;
        deselect();
        d = sb_now() - t;
    } while ((status & STATUS_BUSY) && d < BUSY_LIMIT_TICKS);
    return status & STATUS_BUSY ? -1 : 0;
}

static void write_enable(void)
{
    select();
    send(CMD_WREN);
    deselect();
}

static void trace(u32 kind, u32 addr)
{
    u32 n = sb_store.trace_count;

    sb_store.trace[n % STORE_TRACE] = kind << 28 | addr;
    sb_store.trace_count = n + 1;
}

#if defined(SB_TEST_STORE_CUT)
static void cut(void)
{
    __asm__ volatile("cli");
    for (;;)
        ;
}
#endif

static int erase(u32 addr)
{
#if defined(SB_TEST_STORE_CUT)
    if (sb_store.commands == cut_after)
        cut();
#endif
    write_enable();
    command(CMD_ERASE, addr);
    deselect();
    sb_store.commands++;
    sb_store.erases++;
    trace(1, addr);
#if defined(SB_TEST_STORE_BUSY)
    busy_for(BUSY_ERASE_TICKS);
#endif
    return wait_ready();
}

/* Programs n bytes at addr, a page program for each page they touch. */
static int program(u32 addr, const u8 *data, u32 n)
{
    while (n) {
        u32 room = STORE_PAGE - addr % STORE_PAGE, k = n < room ? n : room, i, send_n = k;
#if defined(SB_TEST_STORE_CUT)
        if (sb_store.commands == cut_after) {
            if (!cut_bytes)
                cut();
            send_n = cut_bytes < k ? cut_bytes : k;
        }
#endif
        write_enable();
        command(CMD_PROGRAM, addr);
        for (i = 0; i < send_n; i++)
            send(data[i]);
        deselect();
#if defined(SB_TEST_STORE_CUT)
        if (sb_store.commands == cut_after)
            cut();
#endif
        sb_store.commands++;
        sb_store.programs++;
        trace(2, addr);
#if defined(SB_TEST_STORE_BUSY)
        busy_for(BUSY_PROGRAM_TICKS);
#endif
        if (wait_ready())
            return -1;
        addr += k;
        data += k;
        n -= k;
    }
    return 0;
}

/* Programs, then reads back: STORE_OK if every byte is as written. */
static int program_verify(u32 addr, const u8 *data, u32 n)
{
    u32 i;

    if (program(addr, data, n))
        return STORE_ERR_VERIFY;
    read(addr, check_buf, n);
    for (i = 0; i < n; i++)
        if (check_buf[i] != data[i])
            return STORE_ERR_VERIFY;
    return STORE_OK;
}

/* --- Records ---------------------------------------------------------- */
static u32 sector_addr(u32 s)
{
    return STORE_BASE + s * STORE_SECTOR;
}

static u32 next_sector(u32 s)
{
    return s == NONE ? 0 : (s + 1) % STORE_SECTORS;
}

static int key_of(u32 kind, u32 id)
{
    if (kind == STORE_PATCH)
        return id < STORE_SLOTS ? (int)id : -1;
    if (id)
        return -1;
    return kind == STORE_SELECTION ? (int)KEY_SELECTION : kind == STORE_SETTINGS ? (int)KEY_SETTINGS
         : kind == STORE_RESET ? (int)KEY_RESET : -1;
}

static u32 record_size(u32 len)
{
    return (HEADER + len + 4 + BLOCK - 1) / BLOCK * BLOCK;
}

static int fw_kind(u32 kind)
{
    return kind >= STORE_FW_KIND_FIRST && kind <= STORE_FW_KIND_LAST;
}

/* A record at p, with at most room bytes after it: its payload's length,
 * or -1 if it is not one (a bad magic or length, or its CRC fails). */
static int record_check(const u8 *p, u32 room)
{
    u32 len = (u32)p[4] | (u32)p[5] << 8;
    u32 max = fw_kind(p[1]) ? STORE_FW_TAG + STORE_FW_PART : STORE_MAX_PAYLOAD;

    if (p[0] != RECORD_MAGIC || len > max || record_size(len) > room)
        return -1;
    return crc32(p, HEADER + len) == rd32(p + HEADER + len) ? (int)len : -2;
}

/* Bytes from a record at addr to the end of its sector: the most a
 * read of it may take. */
static u32 room_at(u32 addr)
{
    u32 r = STORE_SECTOR - (addr - STORE_BASE) % STORE_SECTOR;

    return r < RECORD_MAX ? r : RECORD_MAX;
}

static void count_live(void)
{
    u32 k, n = 0, f = 0;

    for (k = 0; k < ALL_KEYS; k++)
        n += key[k].addr != 0;
    for (k = KEYS; k < ALL_KEYS; k++)
        f += key[k].addr != 0;
    sb_store.live = n;
    sb_store_fw.parts_live = f;
}

/* The key of a firmware kind's part: its place, or a free one if alloc
 * (filled in), or -1. */
static int fw_key(u32 kind, u32 id, u32 part, int alloc)
{
    u32 i;

    for (i = 0; i < STORE_FW_KEYS; i++)
        if (key[KEYS + i].addr && fwk[i].kind == kind && fwk[i].id == id && fwk[i].part == part)
            return (int)(KEYS + i);
    if (!alloc)
        return -1;
    for (i = 0; i < STORE_FW_KEYS; i++)
        if (!key[KEYS + i].addr) {
            fwk[i].kind = (u8)kind;
            fwk[i].id = (u8)id;
            fwk[i].part = (u8)part;
            return (int)(KEYS + i);
        }
    return -1;
}

static int blank(const u8 *p, u32 n)
{
    while (n--)
        if (*p++ != 0xFFu)
            return 0;
    return 1;
}

/* Reads one valid sector whole and takes its records into the keys. For
 * the head, also where its erased tail begins. */
static void scan(u32 s)
{
    u32 off = BLOCK, end = BLOCK;

    read(sector_addr(s), sector_buf, STORE_SECTOR);
    while (off + BLOCK <= STORE_SECTOR) {
        const u8 *p = sector_buf + off;
        int len, k;
        u32 seq;

        if (blank(p, BLOCK)) {
            off += BLOCK;
            continue;
        }
        len = record_check(p, STORE_SECTOR - off);
        if (len < 0) {
            if (len == -2)
                sb_store.crc_bad++;
            else
                sb_store.skipped++;
            off += BLOCK;
            end = off;
            continue;
        }
        seq = rd32(p + 8);
        if (seq >= next_seq)
            next_seq = seq + 1;
        if (fw_kind(p[1]))
            /* A firmware kind's part (BR-9): its index below its count,
             * its tag in its payload's first word. */
            k = p[6] < p[7] && p[7] <= STORE_FW_PARTS && (u32)len >= STORE_FW_TAG
                ? fw_key(p[1], p[2], p[6], 1) : -1;
        else
            k = key_of(p[1], p[2]);
        if (k < 0)
            sb_store.unknown++;
        else if (seq > key[k].seq || !key[k].addr) {
            key[k].seq = seq;
            key[k].addr = sector_addr(s) + off;
            if (k >= (int)KEYS) {
                fwk[k - KEYS].parts = p[7];
                fwk[k - KEYS].tag = rd32(p + HEADER);
            }
        }
        off += record_size((u32)len);
        end = off;
    }
    if (s == head)
        append = end;
}

void store_init(void)
{
    u32 t = sb_now(), s, k, best = 0;

    deselect();
    select();
    send(CMD_ID);
    JL_SPI0->CON |= SPI_RX;
    sb_store.part = xfer(0xFFu) << 16;
    sb_store.part |= xfer(0xFFu) << 8;
    sb_store.part |= xfer(0xFFu);
    JL_SPI0->CON &= ~SPI_RX;
    deselect();
#if defined(SB_TEST_STORE_CUT)
    read(CUT_PARAM, h, 8);
    cut_after = rd32(h);
    cut_bytes = rd32(h + 4);
#endif
    for (s = 0; s < STORE_SECTORS; s++) {
        read(sector_addr(s), h, BLOCK);
        sector_valid[s] = rd32(h) == SECTOR_MAGIC && h[8] == FORMAT && crc32(h, 12) == rd32(h + 12);
        sector_seq[s] = sector_valid[s] ? rd32(h + 4) : 0;
        if (sector_valid[s]) {
            sb_store.valid_sectors++;
            if (head == NONE || sector_seq[s] > best) {
                best = sector_seq[s];
                head = s;
            }
        }
    }
    head_seq = best;
    for (s = 0; s < STORE_SECTORS; s++)
        if (sector_valid[s])
            scan(s);
    /* A reset voids every record older than it, the firmware kinds' too. */
    if (key[KEY_RESET].addr)
        for (k = 0; k < ALL_KEYS; k++)
            if (k != KEY_RESET && key[k].addr && key[k].seq < key[KEY_RESET].seq) {
                key[k].addr = 0;
                sb_store.voided++;
            }
    /* A firmware kind's part not of its payload's newest write (another
     * tag than part 0's, another count, or past it) is not live. */
    for (k = KEYS; k < ALL_KEYS; k++) {
        const int h = key[k].addr && fwk[k - KEYS].part
            ? fw_key(fwk[k - KEYS].kind, fwk[k - KEYS].id, 0, 0) : -1;
        if (key[k].addr && fwk[k - KEYS].part
            && (h < 0 || fwk[h - KEYS].tag != fwk[k - KEYS].tag || fwk[h - KEYS].parts != fwk[k - KEYS].parts
                || fwk[k - KEYS].part >= fwk[k - KEYS].parts)) {
            key[k].addr = 0;
            sb_store_fw.stale++;
        }
    }
    count_live();
    sb_store.head = head;
    sb_store.head_seq = head_seq;
    sb_store.append = head == NONE ? 0 : append;
    sb_store.next_seq = next_seq;
    sb_store.init_ticks = sb_now() - t;
    sb_store.marker = STORE_MARKER;
}

/* A firmware kind's payload (BR-9): every part of its newest write, in
 * order, or -1. */
static int get_fw(u32 kind, u32 id, u8 *buf, u32 max, u32 *version)
{
    int h = fw_key(kind, id, 0, 0), k, len;
    u32 part, i, n = 0;

    if (h < 0)
        return -1;
    for (part = 0; part < fwk[h - KEYS].parts; part++) {
        k = fw_key(kind, id, part, 0);
        if (k < 0 || fwk[k - KEYS].tag != fwk[h - KEYS].tag || fwk[k - KEYS].parts != fwk[h - KEYS].parts)
            return -1;
        read(key[k].addr, check_buf, room_at(key[k].addr));
        len = record_check(check_buf, room_at(key[k].addr));
        if (len < (int)STORE_FW_TAG || rd32(check_buf + HEADER) != fwk[h - KEYS].tag
            || n + (u32)len - STORE_FW_TAG > max)
            return -1;
        for (i = STORE_FW_TAG; i < (u32)len; i++)
            buf[n++] = check_buf[HEADER + i];
        if (!part)
            *version = check_buf[3];
    }
    return (int)n;
}

int store_get(u32 kind, u32 id, u8 *buf, u32 max, u32 *version)
{
    int k = key_of(kind, id), len;
    u32 i;

    if (fw_kind(kind))
        return id <= 255 ? get_fw(kind, id, buf, max, version) : -1;
    if (k < 0 || !key[k].addr)
        return -1;
    read(key[k].addr, check_buf, room_at(key[k].addr));
    len = record_check(check_buf, room_at(key[k].addr));
    if (len < 0 || (u32)len > max)
        return -1;
    for (i = 0; i < (u32)len; i++)
        buf[i] = check_buf[HEADER + i];
    *version = check_buf[3];
    return len;
}

/* Erases sector n and makes it the head, one past the head before it. */
static int open_sector(u32 n)
{
    int r;

    if (erase(sector_addr(n)))
        return STORE_ERR_VERIFY;
    wr32(h, SECTOR_MAGIC);
    wr32(h + 4, head_seq + 1);
    h[8] = FORMAT;
    h[9] = h[10] = h[11] = 0;
    wr32(h + 12, crc32(h, 12));
    r = program_verify(sector_addr(n), h, BLOCK);
    if (r)
        return r;
    head = n;
    head_seq++;
    append = BLOCK;
    sb_store.head = head;
    sb_store.head_seq = head_seq;
    return STORE_OK;
}

/* Keys whose newest record is in sector s. */
static u32 live_in(u32 s)
{
    u32 k, n = 0, a = sector_addr(s);

    for (k = 0; k < ALL_KEYS; k++)
        n += key[k].addr >= a && key[k].addr < a + STORE_SECTOR;
    return n;
}

/* Appends the record in record_buf (its sequence number filled in here)
 * to the head, which has room: STORE_OK once it reads back. The bytes are
 * spent whatever happens. */
static int append_record(int k, u32 len)
{
    u32 n = HEADER + len + 4, addr = sector_addr(head) + append;
    int r;

    wr32(record_buf + 8, next_seq);
    wr32(record_buf + HEADER + len, crc32(record_buf, HEADER + len));
    r = program_verify(addr, record_buf, n);
    append += record_size(len);
    sb_store.append = append;
    next_seq++;
    sb_store.next_seq = next_seq;
    if (r) {
        sb_store.verify_fail++;
        return r;
    }
    key[k].seq = next_seq - 1;
    key[k].addr = addr;
    sb_store.records++;
    return STORE_OK;
}

/* Copies every live record of the sector after the head into the head,
 * so the ring can erase it when it comes round. */
static int compact(void)
{
    u32 m = next_sector(head), a = sector_addr(m), k;
    int len, r;

    for (k = 0; k < ALL_KEYS; k++) {
        if (key[k].addr < a || key[k].addr >= a + STORE_SECTOR)
            continue;
        read(key[k].addr, record_buf, room_at(key[k].addr));
        len = record_check(record_buf, room_at(key[k].addr));
        if (len < 0) {
            /* It read well at start-up; never copy it wrong. */
            key[k].addr = 0;
            continue;
        }
        if (append + record_size((u32)len) > STORE_SECTOR)
            return STORE_ERR_FULL;
        r = append_record((int)k, (u32)len);
        if (r)
            return r;
        sb_store.copies++;
    }
    return STORE_OK;
}

/* Room in the head for a record of size bytes, the ring kept so the
 * sector after the head holds nothing live. */
static int make_room(u32 size)
{
    int r;

    if (head == NONE && (r = open_sector(0)) != STORE_OK)
        return r;
    if ((r = compact()) != STORE_OK)
        return r;
    if (append + size > STORE_SECTOR) {
        u32 n = next_sector(head);
        if (live_in(n))
            return STORE_ERR_FULL;
        if ((r = open_sector(n)) != STORE_OK)
            return r;
        if ((r = compact()) != STORE_OK)
            return r;
        if (append + size > STORE_SECTOR)
            return STORE_ERR_FULL;
    }
    return STORE_OK;
}

/* One record from payload (len bytes) after an optional tag: room made,
 * written, read back; twice if it read back wrong. */
static int put_record(int k, u32 kind, u32 id, u32 version, u32 part, u32 parts, const u32 *tag,
                      const u8 *payload, u32 len)
{
    int r = STORE_ERR_VERIFY, tries;
    u32 i, n = len + (tag ? STORE_FW_TAG : 0), at = HEADER;

    for (tries = 0; tries < 2 && r == STORE_ERR_VERIFY; tries++) {
        if ((r = make_room(record_size(n))) != STORE_OK)
            break;
        record_buf[0] = RECORD_MAGIC;
        record_buf[1] = (u8)kind;
        record_buf[2] = (u8)id;
        record_buf[3] = (u8)version;
        record_buf[4] = (u8)n;
        record_buf[5] = (u8)(n >> 8);
        record_buf[6] = (u8)part;
        record_buf[7] = (u8)parts;
        at = HEADER;
        if (tag) {
            wr32(record_buf + at, *tag);
            at += STORE_FW_TAG;
        }
        for (i = 0; i < len; i++)
            record_buf[at + i] = payload[i];
        r = append_record(k, n);
    }
    return r;
}

/* A firmware kind's payload (BR-9): its parts in order, each tagged with
 * the next sequence number as the first is begun; then the parts past
 * the new count are no longer live. A write that stops part way leaves
 * the old payload until its first part is whole, then none (never a mix
 * of two writes) until it is written again. */
static int put_fw(u32 kind, u32 id, u32 version, const u8 *payload, u32 len)
{
    u32 parts = len ? (len + STORE_FW_PART - 1) / STORE_FW_PART : 1, part, free = 0, i, tag = next_seq;
    int k, r;

    /* Places for every part first, so a write never stops for want of one. */
    for (i = 0; i < STORE_FW_KEYS; i++)
        free += !key[KEYS + i].addr;
    for (part = 0; part < parts; part++)
        free += fw_key(kind, id, part, 0) >= 0;
    if (free < parts)
        return STORE_ERR_FULL;
    for (part = 0; part < parts; part++) {
        u32 n = len - part * STORE_FW_PART < STORE_FW_PART ? len - part * STORE_FW_PART : STORE_FW_PART;

        if (!part)
            tag = next_seq;
        k = fw_key(kind, id, part, 1);
        r = put_record(k, kind, id, version, part, parts, &tag, payload + part * STORE_FW_PART, n);
        if (r != STORE_OK)
            return r;
        fwk[k - KEYS].parts = (u8)parts;
        fwk[k - KEYS].tag = tag;
        sb_store_fw.parts_written++;
    }
    for (part = parts; part < STORE_FW_PARTS; part++)
        if ((k = fw_key(kind, id, part, 0)) >= 0)
            key[k].addr = 0;
    sb_store_fw.payloads++;
    return STORE_OK;
}

static int put(u32 kind, u32 id, u32 version, const u8 *payload, u32 len)
{
    int k = key_of(kind, id);

    if (version > 255 || (fw_kind(kind) ? id > 255 || len > STORE_FW_MAX : k < 0 || len > STORE_MAX_PAYLOAD))
        return STORE_ERR_ARG;
    /* Only a part whose rules and times are known is written (HW-76). */
    if (sb_store.part != STORE_PART)
        return STORE_ERR_PART;
    if (fw_kind(kind))
        return put_fw(kind, id, version, payload, len);
    return put_record(k, kind, id, version, 0, 0, 0, payload, len);
}

int store_put(u32 kind, u32 id, u32 version, const u8 *payload, u32 len)
{
    u32 t = sb_now(), d;
    int r = put(kind, id, version, payload, len);

    d = sb_now() - t;
    if (d > sb_store.put_max)
        sb_store.put_max = d;
    if (r != STORE_OK)
        sb_store.refused++;
    sb_store.last_result = r;
    count_live();
    return r;
}

int store_reset(void)
{
    int r = store_put(STORE_RESET, 0, 0, 0, 0);
    u32 k;

    if (r == STORE_OK)
        for (k = 0; k < ALL_KEYS; k++)
            if (k != KEY_RESET)
                key[k].addr = 0;
    count_live();
    return r;
}

#if defined(SB_TEST_STORE_WIPE)
/* The wipe test build (tools/fw-suite.py): once main runs, erases the
 * image's own sectors, from chip offset 0x4000 to the image's end, so
 * that anything still read through the code window reads erased flash
 * (docs/DESIGN-NOTES.md, M7). */
extern u32 __data_load[], __data_start[], __data_end[];

void sb_test_store_wipe(void)
{
    u32 end = 0x4000u + ((u32)__data_load - 0x02000000u) + ((u32)__data_end - (u32)__data_start), a;

    for (a = 0x4000u; a < end; a += STORE_SECTOR)
        erase(a);
}
#endif
