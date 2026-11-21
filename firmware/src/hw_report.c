/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The report log (SB_HW_REPORT, with SB_HW_FM1; BR-17, clean-br17-report1):
 * what the screens show, written to the flash as fixed records, so the
 * owner reads the whole flash back after a run and tools/report-decode.py
 * prints it, in place of photos. The screens stay as they are.
 *
 * - Where: a ring of HW_LOG_SECTORS sectors ending at 0x93FFF, the app
 *   area's end (HW-80), past the image: an install writes only its image's
 *   range (HW-110), a start writes nothing (HW-112), and the image must end
 *   below the ring (checked before each write). By the owner's unit
 *   observation of 2026-11-21 (docs/prompts/clean-br17-report1-unit.md) the
 *   flash there holds older data, so nothing is taken as blank: each sector
 *   is erased, and read back as erased, before its first record.
 * - A record: HW_LOG_REC bytes, words little-endian: the magic "SBRL", the
 *   layout (HW_LOG_LAYOUT) and the field count, a sequence number, the beat,
 *   the build's identity (16 bytes), a label (16 bytes), the fields, zeros
 *   to the end, and the CRC-32 of everything before it.
 * - The ring: at the first record of a run every slot is read; the next
 *   record follows the newest valid one (sequence one more), or goes in
 *   slot 0 with sequence 1 if none is valid. A record that starts a sector
 *   erases that sector first unless all of it reads erased; a record whose
 *   slot doesn't read erased (a write cut short, older data) moves to the
 *   next sector's start. So the oldest sector goes when the ring wraps, and
 *   the newest records stay.
 * - Each write takes the flash from the code window and gives it back as
 *   the store's counter does (hw_start3.c), names itself on the step row
 *   first ("report: writing #n"), and then says "saved #n" or what failed.
 */

#if defined(SB_HW_REPORT) && !defined(SB_HW_FM1)
#error "SB_HW_REPORT is the hardware build's report log: build it with SB_HW_FM1"
#endif

#include "sb.h"
#include "store.h"
#include "hw_fm1.h"

#if defined(SB_HW_FM1) && defined(SB_HW_REPORT)

#define REG(a) (*(volatile u32 *)(a))
#define C1_CON REG(0x01EEE004u)               /* HW-9 */
#define PER_SECTOR (4096u / HW_LOG_REC)
#define WORDS (HW_LOG_REC / 4u)

struct hw_report hw_rep;
static u32 rec[WORDS], chk[WORDS];
static char text[64];

extern const char __data_load[], __data_start[], __data_end[];

static u32 slot_addr(u32 s)
{
    return HW_LOG_BASE + s * HW_LOG_REC;
}

static int valid(const u32 *r)
{
    return r[0] == HW_LOG_MAGIC && store_crc32((const u8 *)r, HW_LOG_REC - 4u) == r[WORDS - 1u];
}

static int blank(const u32 *r)
{
    u32 i;

    for (i = 0; i < WORDS; i++)
        if (r[i] != 0xFFFFFFFFu)
            return 0;
    return 1;
}

/* The ring read once: the newest valid record, by sequence. */
static void scan(void)
{
    u32 s, best = 0, seq = 0, n = 0;

    for (s = 0; s < HW_LOG_SLOTS; s++) {
        store_raw_read(slot_addr(s), (u8 *)chk, HW_LOG_REC);
        if (!valid(chk))
            continue;
        if (!n || (int)(chk[2] - seq) > 0) {
            best = s;
            seq = chk[2];
        }
        n++;
    }
    hw_rep.found = n;
    hw_rep.slot = n ? (best + 1u) % HW_LOG_SLOTS : 0;
    hw_rep.seq = n ? seq + 1u : 1u;
    hw_rep.scanned = 1;
}

/* 0 if the sector holding slot s reads erased throughout. */
static int sector_blank(u32 s)
{
    u32 i, first = s - s % PER_SECTOR;

    for (i = 0; i < PER_SECTOR; i++) {
        store_raw_read(slot_addr(first + i), (u8 *)chk, HW_LOG_REC);
        if (!blank(chk))
            return 0;
    }
    return 1;
}

/* Makes hw_rep.slot writable: 0, or an error (hw_rep.last_err's). */
static u32 prepare(void)
{
    u32 s = hw_rep.slot;

    if (s % PER_SECTOR) {
        store_raw_read(slot_addr(s), (u8 *)chk, HW_LOG_REC);
        if (blank(chk))
            return 0;
        s = (s - s % PER_SECTOR + PER_SECTOR) % HW_LOG_SLOTS;
        hw_rep.slot = s;
    }
    if (!sector_blank(s) && store_raw_erase(slot_addr(s)))
        return 3;
    return 0;
}

static void copy16(u32 *w, const char *s)
{
    u8 *b = (u8 *)w;
    u32 i;

    for (i = 0; i < 16; i++) {
        b[i] = (u8)*s;
        if (*s)
            s++;
    }
}

/* The fields, in tools/report_decode.py's FIELDS[2] order. */
static u32 fields(u32 *w)
{
    u32 n = 0;

    w[n++] = hw_core1_count;
    w[n++] = C1_CON;
    w[n++] = hw3.count;
    w[n++] = (u32)hw3.put_result;
    w[n++] = hw3.win_con;
    w[n++] = hw3.id;
    w[n++] = hw3.status1;
    w[n++] = hw3.status2;
    w[n++] = hw_rep.found;
    w[n++] = hw_rep.fails;
#if defined(SB_HW_AUDIO1)
    n += hw_audio_report(w + n);
#endif
    return n;
}

static void say(const char *what, u32 seq)
{
    char *p = text;
    const char *s = what;
    u32 d = 1000000000u;

    while (*s)
        *p++ = *s++;
    while (d > 1 && seq < d)
        d /= 10;
    for (; d; d /= 10)
        *p++ = (char)('0' + seq / d % 10);
    *p = 0;
    hw_step(text);
}

void hw_report_save(const char *label)
{
    u32 image_end = 0x4000u + (u32)__data_load - 0x02000000u + (u32)(__data_end - __data_start);
    u32 err = 0, i, n;

    say("report: writing #", hw_rep.scanned ? hw_rep.seq : 0);
    if (image_end + 4096u > HW_LOG_BASE) {
        err = 2;
    } else if (hw_flash_take()) {
        err = 1;
    } else {
        if (!hw_rep.scanned)
            scan();
        err = prepare();
        if (!err) {
            for (i = 0; i < WORDS; i++)
                rec[i] = 0;
            n = fields(rec + HW_LOG_HEAD);
            rec[0] = HW_LOG_MAGIC;
            rec[1] = HW_LOG_LAYOUT | n << 16;
            rec[2] = hw_rep.seq;
            rec[3] = sb_beacon.beats;
            copy16(rec + 4, HW_BUILD_ID);
            copy16(rec + 8, label);
            rec[WORDS - 1u] = store_crc32((const u8 *)rec, HW_LOG_REC - 4u);
            if (store_raw_program(slot_addr(hw_rep.slot), (const u8 *)rec, HW_LOG_REC)) {
                err = 4;
            } else {
                store_raw_read(slot_addr(hw_rep.slot), (u8 *)chk, HW_LOG_REC);
                for (i = 0; i < WORDS && chk[i] == rec[i]; i++)
                    ;
                if (i < WORDS)
                    err = 5;
            }
            /* The slot is used either way: the next record goes after it. */
            hw_rep.slot = (hw_rep.slot + 1u) % HW_LOG_SLOTS;
        }
        hw_flash_give();
    }
    hw_rep.last_err = err;
    if (err) {
        hw_rep.fails++;
        say(err == 1 ? "report: NOT saved, no flash #" : err == 2 ? "report: NOT saved, image long #" :
            err == 3 ? "report: NOT saved, erase #" : err == 4 ? "report: NOT saved, program #" :
            "report: NOT saved, verify #", hw_rep.seq);
        /* A slot written to keeps its number, so no two records share one. */
        if (err >= 4)
            hw_rep.seq++;
        return;
    }
    say("report: saved #", hw_rep.seq);
    hw_rep.saved++;
    hw_rep.seq++;
}

#endif
