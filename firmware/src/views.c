/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The instrument's screens (M8a; ui.h has the split between the engine,
 * which owns the state, and main, which draws). They replace M3's panel
 * screen at the first event or MIDI note, as it replaced the test screen.
 *
 * Every screen has the same frame: a header (the program's number and
 * name, the mode, the octave), a body that is the screen's own, an event
 * line (the store's results, MIDI's notes, buttons not in use yet), and
 * the bottom strip, which names what KNOB1 to KNOB4 do on this screen
 * and shows their values. Each part is redrawn only when what it shows
 * changed, and only its rows are sent, in frames: at most one frame a
 * FRAME_MS, and at most DRAW_TICKS of drawing in any one audio block
 * (panel.c's rule since M5), so drawing never takes the voices' time.
 * tools/fw-suite.py checks the screens against golden images; the layout
 * here and the goldens go together.
 */

#include "sb.h"
#include "input.h"
#include "audio.h"
#include "fm.h"
#include "midi.h"
#include "ui.h"

volatile struct sb_ui_record sb_ui __attribute__((section(".beacon.ui")));

#define BLACK   RGB565(0, 0, 0)
#define WHITE   RGB565(31, 63, 31)
#define DARK    RGB565(6, 12, 6)
#define GREY    RGB565(12, 24, 12)
#define YELLOW  RGB565(31, 63, 0)
#define CYAN    RGB565(0, 63, 31)

/* The frame (rows). */
#define HEAD_Y   0u
#define HEAD_H   26u    /* text at 4, a line at 24 */
#define BODY_Y   26u
#define BODY_H   164u
#define MSG_Y    190u
#define MSG_H    12u    /* text at 192 */
#define STRIP_Y  202u
#define STRIP_H  38u    /* a line at 203, names at 207, values (scale 2) at 220 */
#define COLUMN_W 60u

/* --- Text ------------------------------------------------------------ */

static u32 put(char *b, u32 n, const char *t)
{
    while (*t)
        b[n++] = *t++;
    return n;
}

/* v in decimal at b[n], with + for positive values when sign is set;
 * returns the new length. */
static u32 decimal(char *b, u32 n, int v, int sign)
{
    char d[8];
    u32 k = 0, u = (u32)(v < 0 ? -v : v);

    if (v < 0)
        b[n++] = '-';
    else if (v > 0 && sign)
        b[n++] = '+';
    do {
        d[k++] = (char)('0' + u % 10);
        u /= 10;
    } while (u && k < 7);
    while (k)
        b[n++] = d[--k];
    return n;
}

/* Pads b to w characters and ends it. */
static void pad(char *b, u32 n, u32 w)
{
    while (n < w)
        b[n++] = ' ';
    b[w] = 0;
}

static int same(const char *a, const char *b)
{
    while (*a && *a == *b) {
        a++;
        b++;
    }
    return *a == *b;
}

static void copy_text(char *to, const char *from)
{
    while ((*to++ = *from++))
        ;
}

/* --- What the screen shows: worked out from the engine's state -------- */

static struct fm_ui ui;                 /* the state as last taken */
static u8 prog[FM_PATCH_BYTES];         /* the program's bytes, then */
static u32 program, algorithm, mono, octave, user_used, ui_seen = 0xFFFFFFFFu;
static s32 knob_value[4];

/* The state when it holds still (the engine may change it meanwhile). */
static void take(void)
{
    const u8 *p;
    u32 s, i;

    do {
        s = fm_ui.seq;
        ui.screen = fm_ui.screen;
        ui.op = fm_ui.op;
        ui.page = fm_ui.page;
        ui.row = fm_ui.row;
        ui.env = fm_ui.env;
        ui.confirm = fm_ui.confirm;
        ui.knobs = fm_ui.knobs;
        p = fm_program_bytes();
        for (i = 0; i < FM_PATCH_BYTES; i++)
            prog[i] = p[i];
        program = sb_fm.patch;
        algorithm = sb_fm.algorithm;
        mono = sb_fm.mono;
        octave = sb_audio.engine[SYNTH_OCTAVE];
        user_used = fm_user_used();
        knob_value[0] = sb_fm.pitch_knob;
        knob_value[1] = (s32)sb_fm.glide;
        knob_value[2] = sb_fm.depth;
        knob_value[3] = sb_fm.feedback;
    } while (s != fm_ui.seq);
    ui.seq = s;
}

/* The header: "001 NAME" ("U01 NAME" for a user slot), the mode, the
 * octave ("O+1"). */
static char head_text[3][17], head_drawn[3][17];

static void head_work(void)
{
    u32 n = 0, i, p = program, u = p - FM_PATCHES + 1u;

    if (p < FM_PATCHES) {
        n = put(head_text[0], 0, "00");
        head_text[0][n++] = (char)('1' + p);
    } else {
        head_text[0][n++] = 'U';
        head_text[0][n++] = (char)('0' + u / 10);
        head_text[0][n++] = (char)('0' + u % 10);
    }
    head_text[0][n++] = ' ';
    for (i = 0; i < 12 && prog[FMP_NAME + i]; i++)
        head_text[0][n++] = (char)prog[FMP_NAME + i];
    pad(head_text[0], n, 16);
    n = put(head_text[1], 0, mono ? "MONO" : "POLY");
    head_text[1][n] = 0;
    n = put(head_text[2], 0, (s32)octave ? "O" : "O+");
    n = decimal(head_text[2], n, (int)(s32)octave, 1);
    pad(head_text[2], n, 3);
}

/* The bottom strip: four names and four values. */
static char strip_name[4][11], strip_value[4][6];
static char strip_name_drawn[4][11], strip_value_drawn[4][6];

static void strip_set(u32 k, const char *name, int v, int sign)
{
    u32 n = put(strip_name[k], 0, name);

    pad(strip_name[k], n, 10);
    n = decimal(strip_value[k], 0, v, sign);
    pad(strip_value[k], n, 5);
}

static void strip_work(void)
{
    /* The M5 controls (since M8a's later parts, the setting "Knobs:
     * direct"): pitch, glide, modulation depth, feedback. */
    strip_set(0, "PITCH", knob_value[0], 1);
    strip_set(1, "GLIDE", knob_value[1], 0);
    strip_set(2, "DEPTH", knob_value[2], 1);
    strip_set(3, "FDBK", knob_value[3], 1);
}

/* The body's signature: when it changes, the body is drawn again. */
static u32 body_sig, body_sig_marked;

static u32 mix(u32 h, u32 v)
{
    return (h ^ v) * 16777619u;
}

static u32 body_work(void)
{
    u32 h = 2166136261u, i;

    h = mix(h, ui.screen);
    h = mix(h, ui.op);
    h = mix(h, ui.page);
    h = mix(h, ui.row);
    h = mix(h, ui.env);
    h = mix(h, ui.confirm);
    h = mix(h, ui.knobs);
    h = mix(h, algorithm);
    h = mix(h, user_used);
    h = mix(h, midi_settings.local);
    for (i = 0; i < FM_PATCH_BYTES; i++)
        h = mix(h, prog[i]);
    if (ui.screen == UI_SETTINGS) {
        const u8 *s = (const u8 *)&midi_settings;
        for (i = 0; i < sizeof midi_settings; i++)
            h = mix(h, s[i]);
    }
    return h;
}

/* --- Drawing ------------------------------------------------------------ */

/* Sends rows of the frame buffer to the panel, and counts them. */
static void send(u32 y, u32 h)
{
    lcd_send_rows(y, h);
    sb_ui.rows_sent += h;
}


static void text(u32 x, u32 y, const char *t, u32 fg, u32 scale)
{
    gfx_text(x, y, t, fg, BLACK, scale);
}

static void draw_head(void)
{
    u32 i;

    gfx_fill(0, HEAD_Y, SCREEN_W, HEAD_H, BLACK);
    text(4, 4, head_text[0], WHITE, 2);
    text(SCREEN_W - 4 - 4 * FONT_CELL, 4, head_text[1], CYAN, 1);
    text(SCREEN_W - 4 - 3 * FONT_CELL, 13, head_text[2], CYAN, 1);
    gfx_fill(0, HEAD_Y + 24, SCREEN_W, 1, GREY);
    for (i = 0; i < 3; i++)
        copy_text(head_drawn[i], head_text[i]);
}

/* The whole strip when a name changed (a new screen or page), else
 * only the values that changed, and only their rows sent. */
static void draw_strip(void)
{
    u32 k, names = 0, y = STRIP_Y, h = STRIP_H;

    for (k = 0; k < 4; k++)
        names |= !same(strip_name[k], strip_name_drawn[k]);
    if (names) {
        gfx_fill(0, STRIP_Y, SCREEN_W, STRIP_H, BLACK);
        gfx_fill(0, STRIP_Y + 1, SCREEN_W, 1, GREY);
    } else {
        y = STRIP_Y + 18;
        h = 2 * FONT_H;
    }
    for (k = 0; k < 4; k++) {
        if (names)
            text(k * COLUMN_W + 2, STRIP_Y + 5, strip_name[k], WHITE, 1);
        if (names || !same(strip_value[k], strip_value_drawn[k]))
            text(k * COLUMN_W, STRIP_Y + 18, strip_value[k], YELLOW, 2);
        copy_text(strip_name_drawn[k], strip_name[k]);
        copy_text(strip_value_drawn[k], strip_value[k]);
    }
    send(y, h);
}

/* The event line: the last message, padded. */
static char line[41];

static void draw_line(void)
{
    gfx_fill(0, MSG_Y, SCREEN_W, MSG_H, BLACK);
    text(4, MSG_Y + 2, line, WHITE, 1);
}

/* --- The algorithm, drawn as boxes and lines -------------------------- */

/* Where each operator sits: its row is how many operators lie between it
 * and the output (carriers 0, at the bottom); a modulator takes its
 * destination's column, or the next free one to the right. */
struct layout {
    u8 col[FM_OPS], row[FM_OPS];
    u8 cols, rows;
};

static void lay_out(u32 alg, struct layout *l)
{
    const struct fm_algorithm *a = &fm_algorithms[alg];
    u8 used[FM_OPS][FM_OPS];
    u32 i, c, r, carriers = 0;

    for (r = 0; r < FM_OPS; r++)
        for (c = 0; c < FM_OPS; c++)
            used[r][c] = 0;
    l->cols = l->rows = 1;
    for (i = 0; i < FM_OPS; i++) {
        if (a->dest[i] == FM_TO_OUT) {
            r = 0;
            c = carriers++;
        } else {
            r = l->row[a->dest[i]] + 1u;
            c = l->col[a->dest[i]];
            while (c < FM_OPS - 1 && used[r][c])
                c++;
        }
        used[r][c] = 1;
        l->row[i] = (u8)r;
        l->col[i] = (u8)c;
        if (c + 1 > l->cols)
            l->cols = (u8)(c + 1);
        if (r + 1 > l->rows)
            l->rows = (u8)(r + 1);
    }
}

/* The algorithm in the box x, y, w, h: each operator a numbered box,
 * a line from each modulator to the operator it modulates, a short line
 * below each carrier, and a hook beside the operator with the feedback.
 * The selected operator (sel < FM_OPS) is filled. */
static void draw_algorithm(u32 alg, u32 x, u32 y, u32 w, u32 h, u32 sel)
{
    const struct fm_algorithm *a = &fm_algorithms[alg];
    struct layout l;
    u32 cw, ch, bw, bh, i, bx[FM_OPS], by[FM_OPS];

    lay_out(alg, &l);
    cw = w / l.cols;
    ch = h / l.rows;
    if (cw > 40)
        cw = 40;
    if (ch > 30)
        ch = 30;
    bw = cw - 8;
    bh = ch - 10 < 12 ? ch - 4 : ch - 10;
    for (i = 0; i < FM_OPS; i++) {
        bx[i] = x + l.col[i] * cw + (cw - bw) / 2;
        by[i] = y + h - (l.row[i] + 1u) * ch + (ch - bh) / 2;
    }
    for (i = 0; i < FM_OPS; i++) {
        if (a->dest[i] == FM_TO_OUT)
            gfx_fill(bx[i] + bw / 2, by[i] + bh, 1, (ch - bh) / 2, GREY);
        else
            gfx_line((int)(bx[i] + bw / 2), (int)(by[i] + bh), (int)(bx[a->dest[i]] + bw / 2),
                     (int)by[a->dest[i]] - 1, GREY);
    }
    for (i = 0; i < FM_OPS; i++) {
        u32 on = i == sel, fg = on ? BLACK : WHITE, bg = on ? YELLOW : DARK;
        gfx_fill(bx[i], by[i], bw, bh, bg);
        gfx_frame(bx[i], by[i], bw, bh, on ? YELLOW : GREY);
        if (bh >= FONT_H + 2)
            gfx_glyph(bx[i] + (bw - FONT_CELL) / 2, by[i] + (bh - FONT_H) / 2, '1' + i, fg, bg, 1);
        if (i == a->feedback_op) {
            gfx_fill(bx[i] + bw, by[i] + 2, 3, 1, CYAN);
            gfx_fill(bx[i] + bw + 2, by[i] + 2, 1, bh - 4, CYAN);
            gfx_fill(bx[i] + bw, by[i] + bh - 3, 3, 1, CYAN);
        }
    }
}

/* --- The bodies ---------------------------------------------------------- */

static const u8 *op_bytes(u32 i)
{
    return prog + FM_OP_OFFSET + FM_OP_BYTES * i;
}

static int s8v(u8 x)
{
    return x > 127 ? (int)x - 256 : (int)x;
}

/* A ratio (x 256) as "2.00", or a fixed frequency (1/4 Hz) as "440Hz". */
static u32 freq_text(char *b, u32 n, const u8 *o)
{
    u32 f = (u32)o[FMO_FREQ] | (u32)o[FMO_FREQ + 1] << 8, c;

    if (o[FMO_MODE]) {
        n = decimal(b, n, (int)(f / 4), 0);
        return put(b, n, "Hz");
    }
    n = decimal(b, n, (int)(f >> 8), 0);
    b[n++] = '.';
    c = ((f & 255u) * 100u + 128u) >> 8;
    b[n++] = (char)('0' + c / 10);
    b[n++] = (char)('0' + c % 10);
    return n;
}

static void body_patch(void)
{
    char b[24];
    u32 n;

    draw_algorithm(algorithm - 1u, 4, BODY_Y + 6, 120, 110, FM_OPS);
    n = put(b, 0, "ALG ");
    n = decimal(b, n, (int)algorithm, 0);
    b[n] = 0;
    text(136, BODY_Y + 10, b, WHITE, 2);
    n = put(b, 0, "feedback ");
    n = decimal(b, n, prog[FMP_FEEDBACK], 0);
    b[n] = 0;
    text(136, BODY_Y + 34, b, GREY, 1);
    /* Local control off (M6b): the panel plays MIDI out only. */
    if (!midi_settings.local)
        text(136, BODY_Y + 50, "LOCAL OFF", YELLOW, 1);
}

static void body_edit(void)
{
    const u8 *o = op_bytes(ui.op);
    char b[41];
    u32 n;

    n = put(b, 0, "ALG ");
    n = decimal(b, n, (int)algorithm, 0);
    n = put(b, n, "   OP");
    n = decimal(b, n, ui.op + 1, 0);
    n = put(b, n, " selected");
    b[n] = 0;
    text(4, BODY_Y + 4, b, WHITE, 1);
    draw_algorithm(algorithm - 1u, 4, BODY_Y + 16, 232, 120, ui.op);
    n = put(b, 0, "ratio ");
    n = freq_text(b, n, o);
    n = put(b, n, "  level ");
    n = decimal(b, n, o[FMO_LEVEL], 0);
    n = put(b, n, "  detune ");
    n = decimal(b, n, s8v(o[FMO_DETUNE]), 1);
    b[n] = 0;
    text(4, BODY_Y + 146, b, GREY, 1);
}

static void body_env(void)
{
    const u8 *o = op_bytes(ui.op);
    char b[41];
    u32 n, i;

    n = put(b, 0, "ENV  OP");
    n = decimal(b, n, ui.op + 1, 0);
    b[n] = 0;
    text(4, BODY_Y + 4, b, WHITE, 1);
    n = put(b, 0, "rates");
    for (i = 0; i < 4; i++) {
        b[n++] = ' ';
        n = decimal(b, n, o[FMO_RATE + i], 0);
    }
    n = put(b, n, "  levels");
    for (i = 0; i < 3; i++) {
        b[n++] = ' ';
        n = decimal(b, n, o[FMO_ENV_LEVEL + i], 0);
    }
    b[n] = 0;
    text(4, BODY_Y + 20, b, GREY, 1);
}

/* The settings, one row each: a name, then the value. */
#define SETTING_ROWS 6u

static void setting_row(u32 r, char *b)
{
    static const char *const names[SETTING_ROWS] = {
        "MIDI in channel", "MIDI out channel", "Thru", "Local control", "Bend range", "Store",
    };
    u32 n = put(b, 0, r == ui.row ? "> " : "  "), u, k;

    n = put(b, n, names[r]);
    while (n < 22)
        b[n++] = ' ';
    switch (r) {
    case 0:
        n = midi_settings.channel == MIDI_OMNI ? put(b, n, "omni") : decimal(b, n, midi_settings.channel, 0);
        break;
    case 1:
        n = decimal(b, n, midi_settings.out_channel, 0);
        break;
    case 2:
        n = put(b, n, midi_settings.thru ? "on" : "off");
        break;
    case 3:
        n = put(b, n, midi_settings.local ? "on" : "off");
        break;
    case 4:
        n = decimal(b, n, midi_settings.bend_range, 0);
        break;
    default:
        for (u = user_used, k = 0; u; u &= u - 1)
            k++;
        n = decimal(b, n, (int)k, 0);
        n = put(b, n, "/16 used");
        break;
    }
    b[n] = 0;
}

static void body_settings(void)
{
    char b[41];
    u32 r;

    text(4, BODY_Y + 4, "SETTINGS", WHITE, 1);
    for (r = 0; r < SETTING_ROWS; r++) {
        setting_row(r, b);
        text(4, BODY_Y + 20 + 12 * r, b, r == ui.row ? YELLOW : WHITE, 1);
    }
}

/* The body's contents, over a body the band parts have cleared. */
static void draw_body(void)
{
    switch (ui.screen) {
    case UI_EDIT:
        body_edit();
        break;
    case UI_ENV:
        body_env();
        break;
    case UI_SETTINGS:
        body_settings();
        break;
    default:
        body_patch();
        break;
    }
}

/* --- Frames within the drawing budget (panel.c's rule since M5) ------- */
#define FRAME_MS   16u
#define DRAW_TICKS 4352u   /* an eighth of a block: 64 frames of 544 */

/* What is marked to draw, in the order drawn. A body is cleared in four
 * bands, drawn into the frame buffer as one part, then sent in four
 * bands, so no part takes much more than the budget. */
#define BANDS       4u
#define BAND_H      (BODY_H / BANDS)
#define ITEM_HEAD   (1u << 0)
#define ITEM_CLEAR0 1u            /* bits 1 to 4: the body's bands cleared */
#define ITEM_BODY   (1u << 5)
#define ITEM_SEND0  6u            /* bits 6 to 9: the body's bands sent */
#define ITEM_LINE   (1u << 10)
#define ITEM_STRIP  (1u << 11)
#define ITEM_BODY_ALL (((1u << BANDS) - 1u) << ITEM_CLEAR0 | ITEM_BODY)

static u32 dirty, shown, in_frame, frame_beat, draw_block, spent;

static void draw_item(u32 bit)
{
    if (bit == 0) {
        draw_head();
        send(HEAD_Y, HEAD_H);
    } else if (bit < 5) {
        gfx_fill(0, BODY_Y + (bit - ITEM_CLEAR0) * BAND_H, SCREEN_W, BAND_H, BLACK);
    } else if (bit == 5) {
        draw_body();
        dirty |= ((1u << BANDS) - 1u) << ITEM_SEND0;
    } else if (bit < 10) {
        send(BODY_Y + (bit - ITEM_SEND0) * BAND_H, BAND_H);
    } else if (bit == 10) {
        draw_line();
        send(MSG_Y, MSG_H);
    } else {
        draw_strip();
    }
}

/* Starts a frame once FRAME_MS have passed since the last began, and
 * draws what is marked until it is all drawn or this block's drawing
 * time is spent; otherwise asks the tick to wake main again: for the
 * frame, or for the rest of it a millisecond on. */
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
        sb_ui.frames++;
    }
    while (dirty) {
        u32 bit = 0, t, d;

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
        d = sb_now() - t;
        spent += d;
        sb_ui.items++;
        if (d > sb_ui.item_max) {
            sb_ui.item_max = d;
            sb_ui.item_max_part = bit;
        }
        if (spent > sb_ui.block_max)
            sb_ui.block_max = spent;
        if (spent > DRAW_TICKS && d < spent)
            sb_ui.over++;
    }
    in_frame = 0;
}

/* --- LEDs ---------------------------------------------------------------- */

static const u8 screen_button[UI_SCREENS] = { INPUT_HOME, INPUT_EDIT, INPUT_ENV, INPUT_GLO };
static const u8 op_key[FM_OPS] = {
    INPUT_KEY_OP1, INPUT_KEY_OP2, INPUT_KEY_OP3, INPUT_KEY_OP4, INPUT_KEY_OP5, INPUT_KEY_OP6,
};
static u8 led_level[INPUT_LEDS];
/* The screen and operator the LEDs show: main follows the same events
 * the engine does, in the same order, so it lights them as it takes each
 * event, without waiting for the engine's block (R-LED-3's lag holds). */
static u32 led_screen, led_op;

/* What control c's LED shows: held, fully lit; the screen's button, lit;
 * on the operator screens the selected operator's key at half. */
static u32 led_for(u32 c)
{
    if (input_value(c))
        return INPUT_LED_FULL;
    if (!shown)
        return 0;
    if (c == screen_button[led_screen])
        return INPUT_LED_FULL;
    if ((led_screen == UI_EDIT || led_screen == UI_ENV) && c == op_key[led_op])
        return INPUT_LED_FULL / 2;
    return 0;
}

static void led_update(u32 c)
{
    u32 v = led_for(c);

    if (v != led_level[c]) {
        led_level[c] = (u8)v;
        input_led(c, v);
        sb_ui.leds++;
    }
}

static void leds_for_state(void)
{
    u32 i;

    for (i = 0; i < UI_SCREENS; i++)
        led_update(screen_button[i]);
    for (i = 0; i < FM_OPS; i++)
        led_update(op_key[i]);
}

/* --- Serving ------------------------------------------------------------- */

/* Marks every part whose contents changed. */
static void work(void)
{
    u32 k;

    if (fm_ui.seq != ui_seen) {
        u32 screen = ui.screen;
        take();
        ui_seen = ui.seq;
        if (ui.screen != screen || !sb_ui.shows) {
            dirty |= ITEM_HEAD | ITEM_BODY_ALL | ITEM_LINE | ITEM_STRIP;
            sb_ui.shows++;
        }
        sb_ui.screen = ui.screen;
        sb_ui.seq = ui.seq;
    }
    head_work();
    for (k = 0; k < 3; k++)
        if (!same(head_text[k], head_drawn[k]))
            dirty |= ITEM_HEAD;
    strip_work();
    for (k = 0; k < 4; k++)
        if (!same(strip_name[k], strip_name_drawn[k]) || !same(strip_value[k], strip_value_drawn[k]))
            dirty |= ITEM_STRIP;
    /* Marked once a change: its parts may take several blocks. */
    body_sig = body_work();
    if (body_sig != body_sig_marked) {
        body_sig_marked = body_sig;
        dirty |= ITEM_BODY_ALL;
    }
}

/* The first event, MIDI note or message: the patch view replaces the
 * test screen. */
static void show(void)
{
    shown = 1;
    sb_beacon.screen = SB_SCREEN_PANEL;
    sb_ui.marker = UI_MARKER;
    leds_for_state();
    frame_beat = sb_beacon.beats - FRAME_MS;
    gfx_fill(0, 0, SCREEN_W, SCREEN_H, BLACK);
    work();
}

static void message(const char *t, u32 number)
{
    u32 n = put(line, 0, t);

    if (number)
        n = decimal(line, n, (int)number, 0);
    pad(line, n, 38);
    sb_ui.messages++;
    dirty |= ITEM_LINE;
}

void view_message(const char *text, u32 number)
{
    message(text, number);
    if (!shown)
        show();
    draw_frame();
}

/* "MIDI <channel> note <note> on <velocity>", or "... off" (since M6a). */
static void midi_line(u32 m)
{
    char b[41];
    u32 n = put(b, 0, "MIDI "), velocity = m & 0x7Fu;

    n = decimal(b, n, (int)(m >> 16 & 15u) + 1, 0);
    n = put(b, n, " note ");
    n = decimal(b, n, (int)(m >> 8 & 0x7Fu), 0);
    n = put(b, n, velocity ? " on " : " off");
    if (velocity)
        n = decimal(b, n, (int)velocity, 0);
    b[n] = 0;
    message(b, 0);
}

void view_serve(void)
{
    struct input_event e;
    u32 m;

    while (input_read(&e)) {
        u32 i;
        if (e.kind == INPUT_PRESS)
            for (i = 0; i < UI_SCREENS; i++)
                if (e.control == screen_button[i] && led_screen != i) {
                    led_screen = i;
                    if (shown)
                        leds_for_state();
                }
        if (e.control < INPUT_LEDS)
            led_update(e.control);
        /* The buttons later milestones take (docs/M8-PROPOSAL.md). */
        if (e.kind == INPUT_PRESS && (e.control == INPUT_FX || e.control == INPUT_LFO || e.control == INPUT_ARP
                                      || e.control == INPUT_SEQ || e.control == INPUT_REC)) {
            static const char *const later[5] = {
                "FX: in a later milestone", "LFO: in a later milestone", "ARP: in a later milestone",
                "SEQ: in a later milestone", "REC: in a later milestone",
            };
            u32 k = e.control == INPUT_FX ? 0 : e.control == INPUT_LFO ? 1 : e.control == INPUT_ARP ? 2
                  : e.control == INPUT_SEQ ? 3 : 4;
            message(later[k], 0);
        }
        if (!shown)
            show();
    }
    while (midi_screen_take(&m)) {
        midi_line(m);
        if (!shown)
            show();
    }
    if (!shown)
        return;
    work();
    if (dirty)
        draw_frame();
}
