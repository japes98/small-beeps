/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Round 3's test file only (clean-r3-store, sections 3 and 4; SB_HW_TEST,
 * owner-only, never published): the save soak and its verdict, and the
 * trap on purpose. The release has none of it.
 *
 * - The soak: SAVE and KEY16 held together for 3 s save user slot 16
 *   again and again, patch A and patch B in turn ("SAVING n" in large
 *   text), until power-off. A and B are test patches 1 and 2 (patches.c),
 *   so both are whole, valid and known.
 * - The verdict: at the next power-on, once the store is read, slot 16 as
 *   the store gives it: "SLOT 16: A", "SLOT 16: B", "SLOT 16: BROKEN"
 *   (no whole patch, or one that isn't valid), "SLOT 16: OTHER" (a whole
 *   patch that is neither, as the slot held before a soak's first save)
 *   or "SLOT 16: EMPTY", with the store's counts, held 3 s; then a record
 *   in the log ("Slot16 A" and so on) and the usual start.
 * - The trap: OCT- and OCT+ held together for 3 s put TIMER0's handler
 *   back to its stub, so its next tick halts as an interrupt nothing
 *   handles: the red screen with the cause and the address (hw_fm1.c).
 */

#include "sb.h"
#include "input.h"
#include "fm.h"
#include "ui.h"
#include "store.h"
#include "hw_fm1.h"
#include "hw_audio_int.h"

#if defined(SB_HW_FM1) && defined(SB_HW_TEST)

#define SOAK_SLOT   15u                 /* user slot 16 */
#define SOAK_A      1u                  /* test patches (fm_patches) */
#define SOAK_B      2u
#if defined(SB_TEST_SHORT_HOLD)
#define HOLD_MS     300u                /* fwtest's build: the holds a tenth as long */
#else
#define HOLD_MS     3000u
#endif
#define SRC_TIMER0  4u                  /* main.c's */

void sb_irq_unhandle(u32 source);

struct hw_soak hw_soak;

static u8 slot_buf[STORE_MAX_PAYLOAD];

static int equal(const u8 *a, const u8 *b, u32 n)
{
    while (n--)
        if (*a++ != *b++)
            return 0;
    return 1;
}

static char *put_text(char *p, const char *s)
{
    while (*s)
        *p++ = *s++;
    *p = 0;
    return p;
}

static char *put_number(char *p, u32 v)
{
    char d[10];
    u32 k = 0;

    do {
        d[k++] = (char)('0' + v % 10u);
        v /= 10u;
    } while (v);
    while (k)
        *p++ = d[--k];
    *p = 0;
    return p;
}

/* After store_boot: slot 16's verdict, shown 3 s, then logged. */
void hw_soak_verdict(void)
{
    static const char *const words[5] = { "EMPTY", "A", "B", "OTHER", "BROKEN" };
    static const char *const labels[5] = { "Slot16 empty", "Slot16 A", "Slot16 B", "Slot16 other", "Slot16 BROKEN" };
    char t[24], *p;
    u32 version, v;
    int n = -1;

    if (store_up && !hw_flash_take()) {
        n = store_get(STORE_PATCH, SOAK_SLOT, slot_buf, sizeof slot_buf, &version);
        hw_flash_give();
    }
    if (n < 0)
        v = 0;
    else if (n != (int)FM_PATCH_BYTES || !fm_patch_valid(slot_buf))
        v = 4;
    else if (equal(slot_buf, fm_patches[SOAK_A], FM_PATCH_BYTES))
        v = 1;
    else if (equal(slot_buf, fm_patches[SOAK_B], FM_PATCH_BYTES))
        v = 2;
    else
        v = 3;
    hw_soak.verdict = v;
    gfx_fill(0, 0, SCREEN_W, SCREEN_H, RGB565(0, 0, 0));
    gfx_text(6, 10, "SLOT 16:", RGB565(31, 63, 31), RGB565(0, 0, 0), 3);
    gfx_text(6, 44, words[v], v == 1 || v == 2 ? RGB565(0, 63, 0) : v == 4 ? RGB565(31, 0, 0)
                                                                          : RGB565(31, 63, 0),
             RGB565(0, 0, 0), 3);
    p = put_text(t, "RECORDS ");
    p = put_number(p, sb_store.live);
    gfx_text(6, 100, t, RGB565(31, 63, 31), RGB565(0, 0, 0), 2);
    p = put_text(t, "SECTORS ");
    p = put_number(p, sb_store.valid_sectors);
    gfx_text(6, 120, t, RGB565(31, 63, 31), RGB565(0, 0, 0), 2);
    p = put_text(t, "CRC BAD ");
    p = put_number(p, sb_store.crc_bad);
    gfx_text(6, 140, t, RGB565(31, 63, 31), RGB565(0, 0, 0), 2);
    p = put_text(t, "SKIPPED ");
    p = put_number(p, sb_store.skipped);
    gfx_text(6, 160, t, RGB565(31, 63, 31), RGB565(0, 0, 0), 2);
    (void)p;
    lcd_wait();
    lcd_send_rows(0, SCREEN_H);
    lcd_wait();
    sb_wait_ms(HOLD_MS);
    report(labels[v]);
}

/* Main woken at beat b, unless it will be sooner (views.c's rule). */
static void wake(u32 b)
{
    if (!sb_wake_at || (int)(b - sb_wake_at) < 0)
        sb_wake_at = b;
}

/* From the panel's serve (main.c's hw_panel_serve), each wake. */
void hw_soak_serve(void)
{
    u32 now = sb_beacon.beats;
    const u8 *patch;
    int r;

    if (input_value(INPUT_OCT_DOWN) && input_value(INPUT_OCT_UP)) {
        if (!hw_soak.oct_since)
            hw_soak.oct_since = now ? now : 1;
        else if (now - hw_soak.oct_since >= HOLD_MS)
            sb_irq_unhandle(SRC_TIMER0);
        wake(now + 50u);
    } else {
        hw_soak.oct_since = 0;
    }
    if (!hw_soak.on) {
        if (input_value(INPUT_SAVE) && input_value(INPUT_KEY(16))) {
            if (!hw_soak.since)
                hw_soak.since = now ? now : 1;
            else if (now - hw_soak.since >= HOLD_MS)
                hw_soak.on = 1;
        } else {
            hw_soak.since = 0;
        }
        if (!hw_soak.on) {
            if (hw_soak.since)
                wake(now + 50u);
            return;
        }
    }
    /* One save a wake, A then B, until power-off. */
    patch = fm_patches[hw_soak.n & 1u ? SOAK_B : SOAK_A];
    r = store_put_kept(STORE_PATCH, SOAK_SLOT, FM_PATCH_VERSION, patch, FM_PATCH_BYTES);
    if (r == STORE_OK) {
        hw_soak.n++;
        view_message("SAVING ", hw_soak.n);
    } else {
        hw_soak.fails++;
        view_message("SOAK FAILED ", hw_soak.fails);
    }
    wake(now + 1u);
}

#endif
