/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The live panel screen (M3): every control's state, drawn from the input
 * layer's events, with each button's and key's LED lit while it is held,
 * so the whole panel can be tried by hand. It replaces the test screen at
 * the first event (docs/DESIGN-NOTES.md, M3, "The panel screen"); after
 * that only what events changed is redrawn and only those rows are sent,
 * since M5 in frames, within a drawing budget (below).
 * tools/fw-suite.py checks it against golden images; the layout here and
 * the goldens go together.
 */

#include "sb.h"
#include "input.h"
#include "audio.h"

#define BLACK   RGB565(0, 0, 0)
#define WHITE   RGB565(31, 63, 31)
#define DARK    RGB565(6, 12, 6)
#define GREY    RGB565(12, 24, 12)
#define YELLOW  RGB565(31, 63, 0)
#define ORANGE  RGB565(31, 40, 0)
#define CYAN    RGB565(0, 63, 31)

/* Buttons: 36 x 13 boxes. */
#define BUTTON_W 36u
#define BUTTON_H 13u
/* Knobs: two rows of four cells, 57 pixels wide, name then value. */
#define KNOB_W   57u
#define BAR_Y    122u
#define BAR_W    232u
/* The keyboard: 16 lower keys 13 pixels wide every 14, raised keys 9
 * wide over the gaps. */
#define KEYS_Y   132u
#define LOWER_H  52u
#define RAISED_H 30u
#define EVENT_Y  190u

static const char button_names[14][5] = {
    "OCT-", "OCT+", "FX", "SEL", "ENV", "LFO", "EDIT", "GLO",
    "HOME", "SAVE", "ARP", "SEQ", "PLAY", "REC",
};
/* Knobs in screen order, and their names. */
static const u8 knob_order[8] = {
    INPUT_SELECT, INPUT_PRESETS, INPUT_ALGORITHM, INPUT_MASTER,
    INPUT_KNOB1, INPUT_KNOB2, INPUT_KNOB3, INPUT_KNOB4,
};
static const char knob_names[8][10] = {
    "MASTER", "SELECT", "PRESETS", "ALGORITHM", "KNOB1", "KNOB2", "KNOB3", "KNOB4",
};
/* KEY1 to KEY27 from left to right: a lower key's number (0 to 15), or
 * 0x80 | the lower key a raised key follows (HW-36: raised keys in groups
 * of 3, 2, 3, 2, 1). */
static const u8 key_shape[27] = {
    0, 0x80, 1, 0x81, 2, 0x82, 3, 4, 0x84, 5, 0x85, 6, 7, 0x87,
    8, 0x88, 9, 0x89, 10, 11, 0x8B, 12, 0x8C, 13, 14, 0x8E, 15,
};
static const char *const kind_names[5] = { "", "press", "release", "turn", "move" };

static u32 shown;

static void button_place(u32 id, u32 *x, u32 *y)
{
    if (id < 2) {
        *x = 6 + id * 38;
        *y = 50;
    } else {
        *x = 6 + (id - 2) % 6 * 38;
        *y = 18 + (id - 2) / 6 * 16;
    }
}

static u32 length(const char *s)
{
    u32 n = 0;

    while (s[n])
        n++;
    return n;
}

/* Writes v in decimal at b, with a + for positive values when sign is
 * set; returns the characters written (at most 7). */
static u32 decimal(char *b, int v, int sign)
{
    char d[8];
    u32 n = 0, i = 0, u = (u32)(v < 0 ? -v : v);

    if (v < 0)
        b[i++] = '-';
    else if (v > 0 && sign)
        b[i++] = '+';
    do {
        d[n++] = (char)('0' + u % 10);
        u /= 10;
    } while (u && n < 6);
    while (n)
        b[i++] = d[--n];
    return i;
}

static void draw_button(u32 id)
{
    u32 x, y, down = (u32)input_value(id);
    const char *name = button_names[id];

    button_place(id, &x, &y);
    gfx_fill(x, y, BUTTON_W, BUTTON_H, down ? YELLOW : DARK);
    gfx_text(x + (BUTTON_W - length(name) * FONT_CELL) / 2, y + 3, name,
             down ? BLACK : WHITE, down ? YELLOW : DARK, 1);
}

/* The knob in screen place i (0 to 7): its value, and for MASTER the bar
 * below the knobs; returns the value's first row. */
static u32 draw_knob(u32 i)
{
    u32 id = knob_order[i], x = 4 + i % 4 * 59, y = 80 + i / 4 * 26, n;
    int v = input_value(id);
    char b[10];

    n = decimal(b, v, id != INPUT_MASTER);
    while (n < 9)
        b[n++] = ' ';
    b[9] = 0;
    gfx_text(x, y, b, id == INPUT_MASTER ? CYAN : YELLOW, BLACK, 1);
    if (id == INPUT_MASTER) {
        u32 w = (u32)v * BAR_W / 1023;
        gfx_fill(4, BAR_Y, w, 6, CYAN);
        gfx_fill(4 + w, BAR_Y, BAR_W - w, 6, DARK);
    }
    return y;
}

static void draw_keys(void)
{
    u32 k, pass;

    /* The black around and between the lower keys (since M5 only that,
     * not the whole strip first: the keys cover the rest). */
    gfx_fill(0, KEYS_Y, 8, LOWER_H, BLACK);
    gfx_fill(8 + 14 * 16 - 1, KEYS_Y, SCREEN_W - (8 + 14 * 16 - 1), LOWER_H, BLACK);
    for (k = 0; k < 15; k++)
        gfx_fill(8 + 14 * k + 13, KEYS_Y, 1, LOWER_H, BLACK);
    /* Lower keys first, then the raised keys over them. */
    for (pass = 0; pass < 2; pass++) {
        for (k = 0; k < 27; k++) {
            u32 s = key_shape[k], down = (u32)input_value(INPUT_KEY1 + k);
            if (!(s & 0x80) && !pass)
                gfx_fill(8 + 14 * s, KEYS_Y, 13, LOWER_H, down ? ORANGE : WHITE);
            else if ((s & 0x80) && pass)
                gfx_fill(8 + 14 * ((s & 0x7F) + 1) - 5, KEYS_Y, 9, RAISED_H, down ? ORANGE : GREY);
        }
    }
}

/* "<control> <kind> <value>" for the last event. */
static void draw_event(const struct input_event *e)
{
    char b[41];
    const char *name;
    u32 n = 0, i;

    if (e->control < 14) {
        name = button_names[e->control];
    } else if (e->control < INPUT_MASTER) {
        name = "KEY";
    } else {
        name = knob_names[e->control - INPUT_MASTER];
    }
    for (i = 0; name[i]; i++)
        b[n++] = name[i];
    if (e->control >= INPUT_KEY1 && e->control <= INPUT_KEY27)
        n += decimal(&b[n], (int)(e->control - INPUT_KEY1 + 1), 0);
    b[n++] = ' ';
    for (i = 0; kind_names[e->kind < 5 ? e->kind : 0][i]; i++)
        b[n++] = kind_names[e->kind][i];
    if (e->kind == INPUT_TURN || e->kind == INPUT_MOVE) {
        b[n++] = ' ';
        n += decimal(&b[n], e->value, e->kind == INPUT_TURN);
    }
    while (n < 38)
        b[n++] = ' ';
    b[n] = 0;
    gfx_text(4, EVENT_Y, b, WHITE, BLACK, 1);
}

static void draw_all(void)
{
    u32 i;

    gfx_fill(0, 0, SCREEN_W, SCREEN_H, BLACK);
    gfx_text(4, 4, "small-beeps M3 panel", WHITE, BLACK, 1);
    for (i = 0; i < 14; i++)
        draw_button(i);
    for (i = 0; i < 8; i++) {
        gfx_text(4 + i % 4 * 59, 70 + i / 4 * 26, knob_names[knob_order[i] - INPUT_MASTER], WHITE, BLACK, 1);
        draw_knob(i);
    }
    draw_keys();
    screen_beat_all();
}

/* Since M5 the screen is drawn in frames (docs/DESIGN-NOTES.md, M5, "the
 * screen's cost"): an event sets its LED at once and marks what it
 * changed; what is marked is drawn at most once a FRAME_MS, and, item by
 * item, for at most DRAW_TICKS of time base ticks in any one audio block,
 * so the screen never takes the time the voices need. What is left waits
 * for the next block; the tick wakes main when a frame is due
 * (sb_wake_at). The first event still draws the whole panel at once. */
#define FRAME_MS   16u
#define DRAW_TICKS 4352u   /* an eighth of a block: 64 frames of 544 */

#define ITEM_KEYS  (1u << 14)    /* bits 0 to 13: the buttons */
#define ITEM_KNOB0 15u           /* bits 15 to 22: the knobs in screen order */
#define ITEM_EVENT (1u << 23)

static u32 dirty, in_frame, frame_beat, draw_block, spent;
static struct input_event last;

static void draw_item(u32 bit)
{
    if (bit < 14) {
        u32 x, y;
        draw_button(bit);
        button_place(bit, &x, &y);
        lcd_send_rows(y, BUTTON_H);
    } else if (bit == 14) {
        draw_keys();
        lcd_send_rows(KEYS_Y, LOWER_H);
    } else if (bit < 23) {
        u32 y = draw_knob(bit - ITEM_KNOB0);
        lcd_send_rows(y, FONT_H);
        if (knob_order[bit - ITEM_KNOB0] == INPUT_MASTER)
            lcd_send_rows(BAR_Y, 6);
    } else {
        draw_event(&last);
        lcd_send_rows(EVENT_Y, FONT_H);
    }
}

/* Starts a frame once FRAME_MS have passed since the last began, and
 * draws what is marked until it is all drawn or this block's drawing
 * time is spent; otherwise asks the tick to wake main again: for the
 * frame, or for the rest of it a millisecond on. The time base is read
 * once before and once after each item, hundreds of instructions apart,
 * so fwtest never takes it for waiting (docs/HARNESS.md, "Time"). */
static void draw_frame(void)
{
    u32 beats = sb_beacon.beats;

    if (!in_frame) {
        if (beats - frame_beat < FRAME_MS) {
            sb_wake_at = frame_beat + FRAME_MS;
            return;
        }
        in_frame = 1;
        frame_beat = beats;
    }
    while (dirty) {
        u32 bit = 0, t;

        if (sb_audio.blocks != draw_block) {
            draw_block = sb_audio.blocks;
            spent = 0;
        } else if (spent >= DRAW_TICKS) {
            sb_wake_at = beats + 1;
            return;
        }
        while (!(dirty >> bit & 1))
            bit++;
        dirty &= ~(1u << bit);
        t = sb_now();
        draw_item(bit);
        spent += sb_now() - t;
    }
    in_frame = 0;
}

/* Takes every queued event: its LED first (so it changes with the least
 * delay), then marks what it changed on the screen. */
void panel_serve(void)
{
    struct input_event e;

    while (input_read(&e)) {
        if (e.control < INPUT_LEDS)
            input_led(e.control, e.kind == INPUT_PRESS ? INPUT_LED_FULL : 0);
        if (!shown) {
            shown = 1;
            draw_all();
            draw_event(&e);
            lcd_send_rows(0, SCREEN_H);
            sb_beacon.screen = SB_SCREEN_PANEL;
            frame_beat = sb_beacon.beats;
            continue;
        }
        if (e.control < 14) {
            dirty |= 1u << e.control;
        } else if (e.control < INPUT_MASTER) {
            dirty |= ITEM_KEYS;
        } else {
            u32 i = 0;
            while (knob_order[i] != e.control)
                i++;
            dirty |= 1u << (ITEM_KNOB0 + i);
        }
        last = e;
        dirty |= ITEM_EVENT;
    }
    if (dirty)
        draw_frame();
}
