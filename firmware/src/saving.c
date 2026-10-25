/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * What the firmware keeps in the store (M7; docs/DESIGN-NOTES.md, M7):
 * at start-up the user slots, the settings (migrated from older versions)
 * and the selection; from main's loop, the patches saved and the resets
 * from the panel (fm_saved_seq, fm_reset_seq), and the selection and the
 * settings once they have stayed changed for STORE_SETTLE_S seconds.
 */

#include "store.h"
#include "fm.h"
#include "midi.h"

_Static_assert(FM_USER_SLOTS == STORE_SLOTS, "one store slot for each user slot");
_Static_assert(FM_PATCH_BYTES <= STORE_MAX_PAYLOAD, "a patch fits a record");
_Static_assert(sizeof(struct midi_settings) <= STORE_MAX_PAYLOAD, "the settings fit a record");
_Static_assert(FM_PROGRAMS <= 255, "a program fits the selection's byte");

/* The settings' version 1 (M6a): the first 4 + 2 * MIDI_CC_ROUTES bytes
 * of version 2, which added the out channel, thru and local control. */
#define SETTINGS_V1_BYTES (4u + 2u * MIDI_CC_ROUTES)

/* What the store holds now, to see what changed, and since when. */
static struct midi_settings settings_kept;
static u32 selection_kept, reset_seen, save_seen[STORE_SLOTS];
static u32 selection_since, settings_since, second_seen;
static u8 buf[STORE_MAX_PAYLOAD];
/* The settings as read or about to be written: static, as main's stack
 * is small (R-PERF-3). */
static struct midi_settings s;
u32 store_message_slot;

static int same(const void *a, const void *b, u32 n)
{
    const u8 *x = a, *y = b;

    while (n--)
        if (*x++ != *y++)
            return 0;
    return 1;
}

static void copy(void *to, const void *from, u32 n)
{
    u8 *x = to;
    const u8 *y = from;

    while (n--)
        *x++ = *y++;
}

/* Every field in range, as midi.h gives them. */
static int settings_ok(const struct midi_settings *m)
{
    u32 i;

    if (m->version != MIDI_SETTINGS_VERSION || m->channel > 16 || m->bend_range > 24
        || m->routes > MIDI_CC_ROUTES || m->out_channel < 1 || m->out_channel > 16 || m->thru > 1
        || m->local > 1 || m->knobs > 1)
        return 0;
    for (i = 0; i < MIDI_CC_ROUTES; i++)
        if (m->cc[i].cc > 119 || m->cc[i].to > MIDI_TO_KNOB4)
            return 0;
    return 1;
}

/* The settings record: version 3 as it is; version 2 (M6b's; its last
 * byte, always 0, is version 3's knobs: the macros) and version 1 (M6a's)
 * into version 3, with its defaults for what they lacked. */
static void load_settings(void)
{
    u32 version;
    int n = store_get(STORE_SETTINGS, 0, buf, sizeof buf, &version);

    midi_settings_default(&s);
    if (n == (int)sizeof s && version == MIDI_SETTINGS_VERSION) {
        copy(&s, buf, sizeof s);
    } else if (n == (int)sizeof s && version == 2 && buf[0] == 2) {
        copy(&s, buf, sizeof s);
        s.version = MIDI_SETTINGS_VERSION;
        sb_store.loaded |= 4u;
    } else if (n == (int)SETTINGS_V1_BYTES && version == 1 && buf[0] == 1) {
        copy(&s, buf, SETTINGS_V1_BYTES);
        s.version = MIDI_SETTINGS_VERSION;
        sb_store.loaded |= 4u;
    } else {
        return;
    }
    if (settings_ok(&s)) {
        copy(&midi_settings, &s, sizeof s);
        sb_store.loaded |= 2u;
    }
}

void store_boot(void)
{
    u32 slot, version;
    int n;

    store_init();
    for (slot = 0; slot < STORE_SLOTS; slot++) {
        n = store_get(STORE_PATCH, slot, buf, sizeof buf, &version);
        if (n == (int)FM_PATCH_BYTES && version == FM_PATCH_VERSION && fm_user_set(slot, buf))
            sb_store.loaded |= 1u << (8 + slot);
    }
    load_settings();
    n = store_get(STORE_SELECTION, 0, buf, sizeof buf, &version);
    if (n == (int)sizeof(struct store_selection) && version == STORE_SELECTION_VERSION
        && fm_program_set(buf[0]))
        sb_store.loaded |= 1u;
    copy(&settings_kept, &midi_settings, sizeof settings_kept);
    selection_kept = sb_fm.patch;
    for (slot = 0; slot < STORE_SLOTS; slot++)
        save_seen[slot] = fm_saved_seq[slot];
    reset_seen = fm_reset_seq;
    second_seen = sb_seconds;
}

/* Main's loop, on any work. Returns a message for the screen, or 0. */
const char *store_serve(void)
{
    const char *said = 0;
    u32 now = sb_seconds, slot;

    /* A reset first: the saves made before it are void, and only those
     * made since are written. */
    if (fm_reset_seq != reset_seen) {
        reset_seen = fm_reset_seq;
        sb_store.resets++;
        said = store_reset() == STORE_OK ? "factory defaults" : "RESET FAILED";
        store_message_slot = 0;
        copy(&settings_kept, &midi_settings, sizeof settings_kept);
        selection_kept = sb_fm.patch;
    }
    for (slot = 0; slot < STORE_SLOTS; slot++) {
        u32 seq = fm_saved_seq[slot], epoch;
        int r;

        if (seq == save_seen[slot])
            continue;
        /* The engine may save the slot again while this copies: copy
         * until its sequence number holds still. */
        do {
            seq = fm_saved_seq[slot];
            epoch = fm_saved_reset[slot];
            copy(buf, fm_user_patch(slot), FM_PATCH_BYTES);
        } while (seq != fm_saved_seq[slot]);
        save_seen[slot] = seq;
        if (epoch != reset_seen)
            continue;
        r = store_put(STORE_PATCH, slot, FM_PATCH_VERSION, buf, FM_PATCH_BYTES);
        sb_store.saves++;
        if (r != STORE_OK)
            sb_store.save_fail++;
        said = r == STORE_OK ? "saved to slot " : "SAVE FAILED, slot ";
        store_message_slot = slot + 1;
    }
    if (now == second_seen)
        return said;
    second_seen = now;
    /* The selection and the settings: written once they have stayed
     * changed for STORE_SETTLE_S whole seconds (store.h). */
    if (sb_fm.patch == selection_kept) {
        selection_since = now;
    } else if (now - selection_since >= STORE_SETTLE_S) {
        struct store_selection sel = { (u8)sb_fm.patch, { 0, 0, 0 } };
        if (store_put(STORE_SELECTION, 0, STORE_SELECTION_VERSION, (const u8 *)&sel, sizeof sel) == STORE_OK)
            selection_kept = sel.program;
        sb_store.auto_writes++;
        selection_since = now;
    }
    if (same(&midi_settings, &settings_kept, sizeof settings_kept)) {
        settings_since = now;
    } else if (now - settings_since >= STORE_SETTLE_S) {
        copy(&s, &midi_settings, sizeof s);
        if (settings_ok(&s) && store_put(STORE_SETTINGS, 0, MIDI_SETTINGS_VERSION, (const u8 *)&s,
                                         sizeof s) == STORE_OK)
            copy(&settings_kept, &s, sizeof s);
        sb_store.auto_writes++;
        settings_since = now;
    }
    return said;
}
