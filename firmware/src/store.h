/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The store (M7): our own record store in the flash chip's user region,
 * for the user patches, the patch selection and the settings
 * (docs/DESIGN-NOTES.md, M7, has the design; docs/STORE-FORMAT.md the
 * bytes; tools/store.py reads and writes the same format).
 *
 * - The region is STORE_SECTORS sectors of 4 KiB, used as a ring: one
 *   sector at a time takes new records (the head); the others hold older
 *   ones. Each sector starts with a header holding its sequence number,
 *   one more than the sector used before it.
 * - A record holds a kind, an id (the slot), its payload's version, its
 *   length, a sequence number and a CRC-32 over all of it. Of the records
 *   with the same kind and id, the newest whose CRC holds is the one read.
 *   A record that fails is ignored, and so is anything else that is not
 *   erased: a sector is read whole, in 16-byte steps, and the head takes
 *   new records only after its last byte that is not erased.
 * - A write never changes a byte already written: a record is appended,
 *   so the previous copy stays readable until the new one is complete.
 * - When the head is full, the next sector in the ring becomes the head
 *   (erased first); the records still live in the sector after that, the
 *   oldest, are copied into the new head, so that sector holds nothing
 *   live by the time the ring comes round to erase it. Every sector is
 *   erased in turn: the wear is spread over the region.
 * - Main is the only caller: it reads at start-up (store_init, then
 *   store_get) and writes from its loop (store_put); the interrupts and
 *   core 1 never wait for the flash, and since M7 nothing runs from the
 *   code window (firmware/app.ld).
 * - Every flash access goes through SPI0 (HW-47); the window is never
 *   read for the store.
 * - Since clean-1027 (BR-9) kinds STORE_FW_KIND_FIRST to
 *   STORE_FW_KIND_LAST are kept for firmwares built on the base: any id
 *   (0 to 255), a payload of up to STORE_FW_MAX bytes, written as up to
 *   STORE_FW_PARTS records of STORE_FW_PART bytes (its parts) and read
 *   whole or not at all (below).
 */

#ifndef STORE_H
#define STORE_H

#include "sb.h"

/* The region: the stock layout's unused region, chip offsets 0xFC000 to
 * 0xFEFFF, 3 sectors (HW-80: out of the boot area, the Bluetooth sector,
 * the stock firmware's user patch region, which it leaves as it is, and
 * the per-unit last sector; where our image sits on the chip is M9's, so
 * this stays one definition). Since M8a; M7's store took the user patch
 * region (docs/DESIGN-NOTES.md, M8a, has why three sectors are enough).
 * firmware/app.ld keeps the image clear of both. */
#define STORE_BASE       0xFC000u    /* chip offset */
#define STORE_SIZE       0x3000u
#define STORE_SECTOR     4096u
#define STORE_SECTORS    (STORE_SIZE / STORE_SECTOR)
#define STORE_PAGE       256u        /* a page program's reach */

/* Record kinds, ids and payload versions. */
#define STORE_PATCH      1u   /* id: user slot 0 to STORE_SLOTS - 1; a patch (PATCH-FORMAT.md) */
#define STORE_SELECTION  2u   /* id 0: struct store_selection */
#define STORE_SETTINGS   3u   /* id 0: struct midi_settings (midi.h), its version as the record's */
#define STORE_RESET      4u   /* id 0, no payload: every older record is void */
#define STORE_SLOTS      16u
#define STORE_MAX_PAYLOAD 112u

/* Kinds for firmwares built on the base (BR-9; docs/STORE-FORMAT.md):
 * store_put and store_get take them with any id from 0 to 255 and a
 * payload of up to STORE_FW_MAX bytes. The store writes it as parts,
 * records of up to STORE_FW_PART bytes of it, each after a tag (the
 * write's own number, STORE_FW_TAG bytes), in order; it reads every part
 * of the newest write together, or nothing, never a mix of two writes:
 * cut short (power lost), a write leaves the old payload until its
 * first part is whole, then none until it is written again.
 * Replacing a payload needs room for one new part beside everything
 * live. Today's three sectors hold, and rewrite as often as asked, one
 * payload of up to 5 396 bytes with nothing else stored (a 4 096-byte
 * one with room to spare); beside the base's full store (16 user slots,
 * the selection and the settings, saved in between) how much fits
 * depends on how the records fall in the sectors: 2 952 bytes in every
 * history tools/store.py's model tried, 4 096 not reliably
 * (docs/DESIGN-NOTES.md, "Storage for large records"). Past what fits a
 * write is refused (STORE_ERR_FULL). STORE_FW_KEYS parts are kept track
 * of at once. A reset voids these kinds too. */
#define STORE_FW_KIND_FIRST 0x80u
#define STORE_FW_KIND_LAST  0xFEu
#define STORE_FW_TAG     4u
#define STORE_FW_PART    492u        /* a part's record: 512 bytes */
#define STORE_FW_PARTS   12u
#define STORE_FW_MAX     (STORE_FW_PARTS * STORE_FW_PART)   /* 5 904 */
#define STORE_FW_KEYS    32u

#define STORE_SELECTION_VERSION 1u
struct store_selection {
    u8 program;       /* the program the panel or MIDI chose: 0 to FM_PROGRAMS - 1 */
    u8 reserved[3];   /* 0 */
};

/* How often each kind may be written (docs/DESIGN-NOTES.md, M7, "Wear"):
 * the selection and the settings at most once in STORE_SETTLE_S
 * seconds, and only when they changed; a patch only when the player
 * saves it; a reset only when the player asks for one. */
#define STORE_SETTLE_S   2u

/* Results of store_put and store_reset. */
#define STORE_OK         0
#define STORE_ERR_ARG    -1   /* a kind, id or length out of range */
#define STORE_ERR_FULL   -2   /* no sector could be freed without losing a live record */
#define STORE_ERR_VERIFY -3   /* what was read back differed, twice */
#define STORE_ERR_PART   -4   /* the chip is not the part the store knows (HW-76): never written */
#define STORE_PART       0x856014u   /* the JEDEC ID of the P25Q80H (HW-76, HW-77) */

/* The firmware kinds' counts (BR-9), for the tests, by its symbol (the
 * store's record below ends where the next begins). */
struct sb_store_fw_record {
    u32 parts_live;     /* parts kept track of */
    u32 stale;          /* parts found at start-up not of their payload's newest write */
    u32 payloads;       /* payloads written whole since start-up */
    u32 parts_written;  /* parts written since start-up */
};
extern volatile struct sb_store_fw_record sb_store_fw;

/* Reads the region and finds every key's newest valid record. */
void store_init(void);
/* Copies the newest valid record of (kind, id) to buf (up to max bytes);
 * returns its length and sets *version, or -1 if there is none. For a
 * firmware kind, the newest whole payload. */
int store_get(u32 kind, u32 id, u8 *buf, u32 max, u32 *version);
/* Appends a record; STORE_OK once it is written and read back. */
int store_put(u32 kind, u32 id, u32 version, const u8 *payload, u32 len);
/* A reset record: every record before it is void (factory defaults). */
int store_reset(void);

/* saving.c: what the firmware keeps (M7). store_boot reads the store
 * into the engine and the settings at start-up, after fm_init and before
 * the audio starts; store_serve, from main's loop, writes what the panel
 * saved or reset, and the selection and the settings once they have
 * stayed changed, and returns a message for the screen (with
 * store_message_slot, 1 to STORE_SLOTS, or 0), or 0. */
void store_boot(void);
const char *store_serve(void);
extern u32 store_message_slot;

/* The store's record, after MIDI out's (firmware/app.ld), for the tests
 * (tools/fw-suite.py reads this layout). Times in time base ticks. */
#define STORE_MARKER 0x374F5453u   /* "STO7" in memory order */
#define STORE_TRACE  32u
struct sb_store_record {
    u32 marker;
    u32 part;           /* the JEDEC ID read at start-up (STORE_PART: the store writes) */
    u32 valid_sectors;  /* sectors with a valid header at start-up */
    u32 head;           /* the head sector, or 0xFFFFFFFF: none yet */
    u32 head_seq;
    u32 append;         /* the head's next free offset; STORE_SECTOR: full */
    u32 next_seq;       /* the next record's sequence number */
    u32 live;           /* keys with a valid record */
    u32 init_ticks;     /* store_init's time */
    u32 crc_bad;        /* records whose CRC failed, at start-up */
    u32 skipped;        /* other 16-byte blocks neither erased nor a record, at start-up */
    u32 unknown;        /* valid records of a kind or id this firmware doesn't know */
    u32 voided;         /* valid records older than the newest reset */
    u32 records;        /* records appended since start-up */
    u32 copies;         /* of which copies of live records (compaction) */
    u32 erases;         /* sector erases */
    u32 programs;       /* page programs */
    u32 verify_fail;    /* records that read back wrong */
    u32 refused;        /* store_put calls refused (STORE_ERR_*) */
    s32 last_result;    /* the last store_put's or store_reset's */
    u32 put_max;        /* the longest store_put */
    u32 commands;       /* erase and program commands sent (the cut test counts them) */
    /* Kept by main (main.c's store_serve), not by the store: */
    u32 saves;          /* patches saved from the panel */
    u32 save_fail;      /* of which failed */
    u32 resets;         /* factory resets from the panel */
    u32 auto_writes;    /* selection and settings written when they changed */
    u32 loaded;         /* bit 0: selection, 1: settings, 2: settings migrated, 3: a patch migrated (ARP), 8 + n: slot n */
    u32 trace_count;    /* commands traced; the last is trace[(trace_count - 1) % STORE_TRACE] */
    u32 trace[STORE_TRACE];   /* each command: kind << 28 | chip offset (1 erase, 2 program) */
};
extern volatile struct sb_store_record sb_store;

#endif
