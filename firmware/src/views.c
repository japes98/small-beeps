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
#define SETTING_ROWS 8u   /* the settings screen's rows (fm_play.c's ROW_*) */

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
        if (ui.knobs) {
            knob_value[0] = sb_fm.pitch_knob;
            knob_value[1] = (s32)sb_fm.glide;
            knob_value[2] = sb_fm.depth;
            knob_value[3] = sb_fm.feedback;
        } else {
            for (i = 0; i < 4; i++)
                knob_value[i] = sb_ui.macro[i];
        }
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

static void strip_text(u32 k, const char *name, const char *value)
{
    u32 n = put(strip_name[k], 0, name);

    pad(strip_name[k], n, 10);
    n = put(strip_value[k], 0, value);
    pad(strip_value[k], n, 5);
}

static const u8 *op_bytes(u32 i);
static u32 freq_text(char *b, u32 n, const u8 *o);
static int s8v(u8 x);

/* The operator view's strip (M8a part 3): the selected operator's values
 * on the page SELECT chose. */
static void strip_edit(void)
{
    const u8 *o = op_bytes(ui.op);
    char b[12];
    u32 n;

    if (ui.page == 0) {
        n = freq_text(b, 0, o);
        if (o[FMO_MODE])
            n -= 2;   /* the strip's 5 characters: no "Hz" */
        b[n] = 0;
        strip_text(0, o[FMO_MODE] ? "FREQ Hz" : "RATIO", b);
        strip_set(1, "LEVEL", o[FMO_LEVEL], 0);
        strip_set(2, "DETUNE", s8v(o[FMO_DETUNE]), 1);
        strip_set(3, "VELO", o[FMO_VELOCITY], 0);
    } else if (ui.page == 1) {
        strip_text(0, "MODE", o[FMO_MODE] ? "fixed" : "ratio");
        n = freq_text(b, 0, o);
        if (o[FMO_MODE])
            n -= 2;
        b[n] = 0;
        strip_text(1, "COARSE", b);
        strip_text(2, "FINE", b);
        strip_text(3, "", "");
    } else {
        strip_set(0, "PEAK", o[FMO_ENV_LEVEL], 0);
        strip_set(1, "D1 LEVEL", o[FMO_ENV_LEVEL + 1], 0);
        strip_set(2, "HOLD", o[FMO_ENV_LEVEL + 2], 0);
        strip_text(3, "", "");
    }
}

/* The settings' strip (M8a part 6): KNOB1 changes the row's value. */
static void strip_settings(void)
{
    static const char *const names[SETTING_ROWS] = {
        "IN CH", "OUT CH", "THRU", "LOCAL", "BEND", "KNOBS", "STORE", "RESET",
    };
    const struct midi_settings *m = &midi_settings;
    char b[8];
    u32 n = 0, r = ui.row < SETTING_ROWS ? ui.row : 0, k;

    switch (r) {
    case 0:
        n = m->channel == MIDI_OMNI ? put(b, 0, "omni") : decimal(b, 0, m->channel, 0);
        break;
    case 1:
        n = decimal(b, 0, m->out_channel, 0);
        break;
    case 2:
        n = put(b, 0, m->thru ? "on" : "off");
        break;
    case 3:
        n = put(b, 0, m->local ? "on" : "off");
        break;
    case 4:
        n = decimal(b, 0, m->bend_range, 0);
        break;
    case 5:
        n = put(b, 0, m->knobs ? "dir" : "macro");
        break;
    case 7:
        n = put(b, 0, ui.confirm ? "SAVE?" : "");
        break;
    }
    b[n] = 0;
    strip_text(0, r == 6 ? "" : names[r], r == 6 ? "" : b);
    for (k = 1; k < 4; k++)
        strip_text(k, "", "");
}

/* The envelope view's strip (M8a part 4). */
static void strip_env(void)
{
    static const char *const rates[4] = { "ATTACK", "DECAY1", "DECAY2", "RELEASE" };
    static const char *const levels[3] = { "PEAK", "D1 LEVEL", "HOLD" };
    static const char *const prates[4] = { "RATE1", "RATE2", "RATE3", "DEPTH" };
    static const char *const plevels[4] = { "P0", "P1", "P2", "P3" };
    const u8 *o = op_bytes(ui.op);
    u32 k;

    for (k = 0; k < 4; k++) {
        if (ui.env == 2 && k)
            strip_text(k, "", "");
        else if (ui.env == 2)
            strip_set(0, "GLIDE", prog[FMP_GLIDE], 0);
        else if (ui.env == 1 && !ui.page)
            strip_set(k, prates[k], k < 3 ? prog[FMP_PITCH_RATE + k] : s8v(prog[FMP_PITCH_DEPTH]), k == 3);
        else if (ui.env == 1)
            strip_set(k, plevels[k], s8v(prog[FMP_PITCH_LEVEL + k]), 1);
        else if (!ui.page)
            strip_set(k, rates[k], o[FMO_RATE + k], 0);
        else if (k < 3)
            strip_set(k, levels[k], o[FMO_ENV_LEVEL + k], 0);
        else
            strip_text(k, "", "");
    }
}

static void strip_work(void)
{
    static const char *const macros[4] = { "BRIGHT", "COLOR", "SHAPE", "MOTION" };
    u32 k;

    if (ui.screen == UI_EDIT) {
        strip_edit();
        return;
    }
    if (ui.screen == UI_ENV) {
        strip_env();
        return;
    }
    if (ui.screen == UI_SETTINGS) {
        strip_settings();
        return;
    }
    if (ui.knobs) {
        /* The setting "Knobs: direct": M5's controls, pitch, glide,
         * modulation depth, feedback. */
        strip_set(0, "PITCH", knob_value[0], 1);
        strip_set(1, "GLIDE", knob_value[1], 0);
        strip_set(2, "DEPTH", knob_value[2], 1);
        strip_set(3, "FDBK", knob_value[3], 1);
        return;
    }
    for (k = 0; k < 4; k++)
        strip_set(k, macros[k], knob_value[k], k != 3);
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
    /* What a body shows of the program: the operator view's values are
     * on its info line and strip, so an edit redraws only those. */
    if (ui.screen == UI_PATCH)
        h = mix(h, prog[FMP_FEEDBACK]);
    /* The envelope view's graph is its own part (graph_work). */
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
/* The operator boxes as last drawn on the operator view, for its live
 * levels (M8a part 3); and the width of each one's meter as drawn. */
static u32 box_x[FM_OPS], box_y[FM_OPS], box_w, box_h;
static u32 meter_drawn[FM_OPS];

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
    box_w = bw;
    box_h = bh;
    for (i = 0; i < FM_OPS; i++) {
        bx[i] = x + l.col[i] * cw + (cw - bw) / 2;
        by[i] = y + h - (h - l.rows * ch) / 2 - (l.row[i] + 1u) * ch + (ch - bh) / 2;
    }
    for (i = 0; i < FM_OPS; i++) {
        if (a->dest[i] == FM_TO_OUT)
            gfx_fill(bx[i] + bw / 2, by[i] + bh, 1, (ch - bh) / 2, GREY);
        else
            gfx_line((int)(bx[i] + bw / 2), (int)(by[i] + bh), (int)(bx[a->dest[i]] + bw / 2),
                     (int)by[a->dest[i]] - 1, GREY);
    }
    for (i = 0; i < FM_OPS; i++) {
        u32 on = i == sel, fg = WHITE, bg = DARK;
        gfx_fill(bx[i], by[i], bw, bh, bg);
        gfx_frame(bx[i], by[i], bw, bh, on ? YELLOW : GREY);
        if (on)
            gfx_frame(bx[i] + 1, by[i] + 1, bw - 2, bh - 2, YELLOW);
        if (bh >= FONT_H + 2)
            gfx_glyph(bx[i] + (bw - FONT_CELL) / 2, by[i] + (bh - FONT_H - 3) / 2, '1' + i, fg, bg, 1);
        box_x[i] = bx[i];
        box_y[i] = by[i];
        if (i == a->feedback_op) {
            gfx_fill(bx[i] + bw, by[i] + 2, 3, 1, CYAN);
            gfx_fill(bx[i] + bw + 2, by[i] + 2, 1, bh - 4, CYAN);
            gfx_fill(bx[i] + bw, by[i] + bh - 3, 3, 1, CYAN);
        }
    }
}

/* An operator's live level as a meter along the bottom of its box: the
 * gain's octaves below full scale, 48 dB over the meter's width. */
static u32 meter_width(s32 g, u32 w)
{
    u32 lg, x;

    if (g <= 0)
        return 0;
    lg = 31u - (u32)__builtin_clz((u32)g);
    x = (30u - lg) * 16u - (lg >= 4 ? ((u32)g >> (lg - 4)) & 15u : 0);
    return x >= 128 ? 0 : (128 - x) * w / 128;
}

static void draw_meter(u32 i, u32 width)
{
    u32 x = box_x[i] + 3, y = box_y[i] + box_h - 5, w = box_w - 6;

    gfx_fill(x, y, w, 3, BLACK);
    gfx_fill(x, y, width, 3, CYAN);
    meter_drawn[i] = width;
}

/* --- The envelope view (M8a part 4) -------------------------------------
 * The envelope drawn to scale: each stage's width is its time code (a
 * code is 2^(t/8) ms, so the drawing's time axis is logarithmic, as the
 * codes are), the held stage a fixed width; height is the level code (an
 * eighth of an octave a step). A dot shows where the newest note is now;
 * the pixels under it are kept, so moving it redraws and sends two small
 * rectangles, never the graph. */
#define GRAPH_X 8u
#define GRAPH_Y (BODY_Y + 24u)
#define GRAPH_W 224u
#define GRAPH_H 112u
#define HOLD_W  36u
#define DOT     5u

static u32 gx[6], gy[6], gn;          /* the graph's points as drawn */
static int glevel[6];                 /* and their levels */
static u32 graph_sig, graph_sig_marked;

static u32 y_level(int level)         /* 0 to 127, bottom to top */
{
    return GRAPH_Y + GRAPH_H - 1u - (u32)level * (GRAPH_H - 1u) / 127u;
}

static u32 y_signed(int level)        /* -127 to 127 about the middle */
{
    return (u32)((int)(GRAPH_Y + GRAPH_H / 2u) - level * (int)(GRAPH_H / 2u - 1u) / 127);
}

static void graph_points(void)
{
    u32 i, total = 0, x = GRAPH_X, w[4];

    if (ui.env == 0) {
        const u8 *o = op_bytes(ui.op);
        int lv[6] = { 0, o[FMO_ENV_LEVEL], o[FMO_ENV_LEVEL + 1], o[FMO_ENV_LEVEL + 2], o[FMO_ENV_LEVEL + 2], 0 };
        for (i = 0; i < 4; i++)
            total += w[i] = o[FMO_RATE + i] + 8u;
        for (i = 0; i < 6; i++) {
            gx[i] = x;
            glevel[i] = lv[i];
            gy[i] = y_level(lv[i]);
            if (i < 3)
                x += w[i] * (GRAPH_W - HOLD_W) / total;
            else if (i == 3)
                x += HOLD_W;
            else
                x += w[3] * (GRAPH_W - HOLD_W) / total;
        }
        gn = 6;
    } else if (ui.env == 1) {
        /* P0 at the note on, P1, P2 held, P3 after the release. */
        int lv[5];
        lv[0] = s8v(prog[FMP_PITCH_LEVEL]);
        lv[1] = s8v(prog[FMP_PITCH_LEVEL + 1]);
        lv[2] = lv[3] = s8v(prog[FMP_PITCH_LEVEL + 2]);
        lv[4] = s8v(prog[FMP_PITCH_LEVEL + 3]);
        for (i = 0; i < 3; i++)
            total += w[i] = prog[FMP_PITCH_RATE + i] + 8u;
        for (i = 0; i < 5; i++) {
            gx[i] = x;
            glevel[i] = lv[i];
            gy[i] = y_signed(lv[i]);
            if (i < 2)
                x += w[i] * (GRAPH_W - HOLD_W) / total;
            else if (i == 2)
                x += HOLD_W;
            else
                x += w[2] * (GRAPH_W - HOLD_W) / total;
        }
        gn = 5;
    } else {
        /* Glide: from the last note's pitch to the new one's, over its
         * time code. */
        gx[0] = GRAPH_X;
        gy[0] = GRAPH_Y + GRAPH_H - 1u;
        gx[1] = GRAPH_X + (prog[FMP_GLIDE] + 8u) * (GRAPH_W - HOLD_W) / 135u;
        gy[1] = GRAPH_Y;
        gx[2] = GRAPH_X + GRAPH_W - 1u;
        gy[2] = GRAPH_Y;
        gn = 3;
    }
}

static u32 graph_work(void)
{
    u32 h = 2166136261u, i;

    if (ui.screen != UI_ENV)
        return 0;
    h = mix(h, ui.env);
    h = mix(h, ui.op);
    for (i = 0; i < FM_PATCH_BYTES; i++)
        h = mix(h, prog[i]);
    return h;
}

/* The dot as drawn, the pixels under it, and where it should be. */
static u32 dot_x, dot_y, dot_on;
static u16 dot_bg[DOT * DOT];
static u32 dot_want_x, dot_want_y, dot_want_on;
static char stage_text[6], stage_drawn[6];

/* clear: 0 when the body's bands have just cleared it. */
static void draw_graph(u32 clear)
{
    u32 i;

    graph_points();
    if (clear)
        gfx_fill(GRAPH_X, GRAPH_Y, GRAPH_W, GRAPH_H, BLACK);
    gfx_fill(GRAPH_X, ui.env == 1 ? y_signed(0) : GRAPH_Y + GRAPH_H - 1u, GRAPH_W, 1, DARK);
    for (i = 0; i + 1 < gn; i++)
        gfx_line((int)gx[i], (int)gy[i], (int)gx[i + 1], (int)gy[i + 1], CYAN);
    if (ui.env == 2) {
        char b[24];
        u32 n = put(b, 0, "glide ");
        n = decimal(b, n, prog[FMP_GLIDE], 0);
        b[n] = 0;
        text(GRAPH_X + GRAPH_W - 16 * FONT_CELL, GRAPH_Y + GRAPH_H - 20, b, GREY, 1);
    }
    dot_on = 0;
    graph_sig_marked = graph_sig;
}

/* The level code of the dot's envelope now: 0 to 127 for an operator's,
 * -127 to 127 for the pitch envelope. */
static int dot_level(void)
{
    s32 a = fm_env_dot.att;

    if (fm_env_dot.valid == 2)
        return a / 65536;
    if (fm_env_dot.stage == 0) {   /* the attack: a linear gain */
        u32 lg, x;
        if (a <= 0)
            return 0;
        lg = 31u - (u32)__builtin_clz((u32)a);
        x = (30u - lg) * 16u - (lg >= 4 ? ((u32)a >> (lg - 4)) & 15u : 0);
        return x >= 254 ? 0 : 127 - (int)(x / 2);
    }
    a = 127 - a / 8192;
    return a < 0 ? 0 : a;
}

/* Where the dot goes: along its stage's segment by how far its level has
 * come from the stage's start to its end (the held stage: its middle). */
static void dot_work(void)
{
    static const char *const op_stages[5] = { "A", "D1", "D2", "HOLD", "R" };
    static const char *const pitch_stages[3] = { "P1", "P2", "R" };
    u32 seg;
    int lv, from, to, frac;

    dot_want_on = 0;
    stage_text[0] = 0;
    if (!fm_env_dot.valid || ui.env == 2 || (fm_env_dot.valid == 2) != (ui.env == 1))
        return;
    lv = dot_level();
    if (ui.env == 0) {
        seg = fm_env_dot.stage;
        if (seg > 4)
            return;
        copy_text(stage_text, op_stages[seg]);
        if (seg == 3) {
            dot_want_x = (gx[3] + gx[4]) / 2;
            dot_want_y = y_level(lv);
            dot_want_on = 1;
        }
    } else {
        seg = fm_env_dot.stage > 2 ? 2 : fm_env_dot.stage;
        copy_text(stage_text, pitch_stages[seg]);
        if (seg == 2)
            seg = 3;   /* released: from the held end toward P3 */
    }
    if (!dot_want_on) {
        from = glevel[seg];
        to = glevel[seg + 1];
        frac = to == from ? 256 : (lv - from) * 256 / (to - from);
        frac = frac < 0 ? 0 : frac > 256 ? 256 : frac;
        dot_want_x = gx[seg] + (u32)((int)(gx[seg + 1] - gx[seg]) * frac / 256);
        dot_want_y = ui.env == 1 ? y_signed(lv) : y_level(lv);
        dot_want_on = 1;
    }
    dot_want_x = dot_want_x < GRAPH_X + 2 ? GRAPH_X : dot_want_x - 2;
    dot_want_y = dot_want_y < GRAPH_Y + 2 ? GRAPH_Y : dot_want_y - 2;
    if (dot_want_x > GRAPH_X + GRAPH_W - DOT)
        dot_want_x = GRAPH_X + GRAPH_W - DOT;
    if (dot_want_y > GRAPH_Y + GRAPH_H - DOT)
        dot_want_y = GRAPH_Y + GRAPH_H - DOT;
}

/* Puts back what was under the dot, draws it where it should be, and
 * sends both small rectangles; and the stage's name beside the title. */
static void dot_move(void)
{
    u32 r, i;

    if (dot_on) {
        for (r = 0; r < DOT; r++)
            for (i = 0; i < DOT; i++)
                sb_fb[(dot_y + r) * SCREEN_W + dot_x + i] = dot_bg[r * DOT + i];
        lcd_send_rect(dot_x, dot_y, DOT, DOT);
        dot_on = 0;
    }
    if (dot_want_on) {
        dot_x = dot_want_x;
        dot_y = dot_want_y;
        for (r = 0; r < DOT; r++)
            for (i = 0; i < DOT; i++)
                dot_bg[r * DOT + i] = sb_fb[(dot_y + r) * SCREEN_W + dot_x + i];
        gfx_fill(dot_x, dot_y, DOT, DOT, YELLOW);
        lcd_send_rect(dot_x, dot_y, DOT, DOT);
        dot_on = 1;
    }
    if (!same(stage_text, stage_drawn)) {
        char b[12];
        u32 n = put(b, 0, stage_text[0] ? "stage " : "");
        n = put(b, n, stage_text);
        pad(b, n, 10);
        text(SCREEN_W - 4 - 10 * FONT_CELL, BODY_Y + 4, b, YELLOW, 1);
        lcd_send_rect(SCREEN_W - 4 - 10 * FONT_CELL, BODY_Y + 4, 10 * FONT_CELL, FONT_H);
        copy_text(stage_drawn, stage_text);
    }
}

/* --- The patch view's spectrum (M8a part 5; spectrum.c) -------------- */
#define SPEC_X  8u
#define SPEC_Y  (BODY_Y + 124u)
#define SPEC_H  40u
#define SPEC_MS 33u    /* about 30 transforms a second, at most */
static u8 bars_new[SPEC_BARS], bars_drawn[SPEC_BARS];

/* all: the whole area (the body is drawn); else only the bars that
 * moved, each as the column between its old height and its new. */
static void draw_spectrum(u32 all)
{
    u32 j;

    if (all) {
        gfx_fill(SPEC_X, SPEC_Y, SPEC_BARS * 4u, SPEC_H, BLACK);
        gfx_fill(SPEC_X, SPEC_Y + SPEC_H - 1u, SPEC_BARS * 4u, 1, DARK);
    }
    for (j = 0; j < SPEC_BARS; j++) {
        u32 n = bars_new[j], d = all ? 0 : bars_drawn[j], x = SPEC_X + 4u * j;
        if (n > d)
            gfx_fill(x, SPEC_Y + SPEC_H - n, 3, n - d, CYAN);
        else if (n < d)
            gfx_fill(x, SPEC_Y + SPEC_H - d, 3, d - n, BLACK);
        bars_drawn[j] = (u8)n;
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
    draw_spectrum(1);
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
    n = put(b, n, "   page ");
    n = decimal(b, n, ui.page + 1, 0);
    n = put(b, n, "/3");
    b[n] = 0;
    text(4, BODY_Y + 4, b, WHITE, 1);
    draw_algorithm(algorithm - 1u, 4, BODY_Y + 16, 232, 120, ui.op);
    {
        u32 i;
        for (i = 0; i < FM_OPS; i++)
            draw_meter(i, meter_width(fm_op_level[i], box_w - 6));
    }
    (void)o;
}

/* The operator view's info line (its own part): the selected operator's
 * values on every page. */
#define INFO_Y (BODY_Y + 144)
static char info_text[41], info_drawn[41];

static void info_work(void)
{
    const u8 *o = op_bytes(ui.op);
    char *b = info_text;
    u32 n = 0;

    if (ui.screen == UI_SETTINGS) {
        put(b, 0, "settings");   /* the second half of the rows */
        b[8] = 0;
        return;
    }
    if (ui.screen != UI_EDIT) {
        b[0] = 0;
        return;
    }
    n = put(b, n, o[FMO_MODE] ? "fixed " : "ratio ");
    n = freq_text(b, n, o);
    n = put(b, n, " lvl ");
    n = decimal(b, n, o[FMO_LEVEL], 0);
    n = put(b, n, " det ");
    n = decimal(b, n, s8v(o[FMO_DETUNE]), 1);
    n = put(b, n, " vel ");
    n = decimal(b, n, o[FMO_VELOCITY], 0);
    pad(b, n, 38);
}

static void settings_rows(u32 first, u32 last);
#define SETTINGS_Y(r) (BODY_Y + 20u + 12u * (r))

static void draw_info(void)
{
    if (ui.screen == UI_SETTINGS) {
        /* Only ever after the body, whose bands cleared these rows: a
         * setting's change redraws the body. */
        u32 y = SETTINGS_Y(SETTING_ROWS / 2), h = SETTINGS_Y(SETTING_ROWS) + 4 + FONT_H - y;
        settings_rows(SETTING_ROWS / 2, SETTING_ROWS);
        send(y, h);
    } else {
        gfx_fill(0, INFO_Y, SCREEN_W, FONT_H, BLACK);
        text(4, INFO_Y, info_text, GREY, 1);
        send(INFO_Y, FONT_H);
    }
    copy_text(info_drawn, info_text);
}

static void body_env(void)
{
    char b[24];
    u32 n;

    if (ui.env == 0) {
        n = put(b, 0, "ENV  OP");
        n = decimal(b, n, ui.op + 1, 0);
    } else {
        n = put(b, 0, ui.env == 1 ? "PITCH ENV" : "GLIDE");
    }
    if (ui.env < 2)
        n = put(b, n, ui.page ? "  levels" : "  rates");
    b[n] = 0;
    text(4, BODY_Y + 4, b, WHITE, 1);
    draw_graph(0);
    stage_drawn[0] = 0;   /* the body cleared it */
}

/* The settings, one row each: a name, then the value. */

static void setting_row(u32 r, char *b)
{
    static const char *const names[SETTING_ROWS] = {
        "MIDI in channel", "MIDI out channel", "Thru", "Local control", "Bend range", "Knobs", "Store",
        "Factory reset",
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
    case 5:
        n = put(b, n, midi_settings.knobs ? "direct" : "macros");
        break;
    case 6:
        for (u = user_used, k = 0; u; u &= u - 1)
            k++;
        n = decimal(b, n, (int)k, 0);
        n = put(b, n, "/16 used");
        break;
    default:
        n = put(b, n, ui.confirm ? "SAVE: yes" : "KNOB1");
        break;
    }
    b[n] = 0;
}

/* Rows first to last - 1, and after the last row the footer. The body
 * draws the first half, the info line's part the rest (each within the
 * drawing budget). */

static void settings_rows(u32 first, u32 last)
{
    char b[41];
    u32 r;

    for (r = first; r < last; r++) {
        setting_row(r, b);
        text(4, SETTINGS_Y(r), b, r == ui.row ? YELLOW : WHITE, 1);
    }
    if (last == SETTING_ROWS)
        text(4, SETTINGS_Y(SETTING_ROWS) + 4, ui.confirm ? "Clear it all? SAVE: yes  HOME: no"
             : "SELECT: row   KNOB1: change", ui.confirm ? YELLOW : GREY, 1);
}

static void body_settings(void)
{
    text(4, BODY_Y + 4, "SETTINGS", WHITE, 1);
    settings_rows(0, SETTING_ROWS / 2);
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
#define ITEM_INFO   (1u << 12)    /* the operator view's info line (M8a part 3) */
#define ITEM_LIVE   (1u << 13)    /* the live parts: the operators' levels, the envelope's dot */
#define ITEM_GRAPH  (3u << 14)    /* the envelope view's graph (M8a part 4): cleared in two halves, */
#define ITEM_GRAPH_DRAW (1u << 16)  /* drawn, */
#define ITEM_GRAPH_SEND (1u << 17)  /* and sent */
#define ITEM_SPEC   (1u << 18)    /* the patch view's spectrum (M8a part 5): the transform, */
#define ITEM_SPEC2  (1u << 19)    /* in three parts, */
#define ITEM_SPEC3  (1u << 20)
#define ITEM_SPEC_DRAW (1u << 21) /* the bars drawn and sent */
/* The parts that send to the panel (the others only draw or compute). */
#define ITEM_SENDS (ITEM_HEAD | (((1u << BANDS) - 1u) << ITEM_SEND0) | ITEM_LINE | ITEM_STRIP | ITEM_INFO \
                    | ITEM_LIVE | ITEM_GRAPH_SEND | ITEM_SPEC_DRAW)
#define ITEM_BODY_ALL (((1u << BANDS) - 1u) << ITEM_CLEAR0 | ITEM_BODY)

static u32 dirty, shown, in_frame, frame_beat, draw_block, spent;

/* Asks the tick to wake main at beat b, unless it will sooner (since
 * M8a: the frames and the live parts each keep their own wake). */
static void wake_at(u32 b)
{
    if (!sb_wake_at || (int)(b - sb_wake_at) < 0)
        sb_wake_at = b;
}

/* The live parts (M8a part 3): each operator's meter that moved, drawn
 * and sent as its own rectangle. */
static u32 live_width[FM_OPS];

static void draw_live(void)
{
    u32 i, t = sb_now();

    if (ui.screen == UI_ENV)
        dot_move();
    else
        for (i = 0; i < FM_OPS; i++)
        if (live_width[i] != meter_drawn[i]) {
            draw_meter(i, live_width[i]);
            lcd_send_rect(box_x[i] + 3, box_y[i] + box_h - 5, box_w - 6, 3);
            sb_ui.rows_sent += 3;
        }
    t = sb_now() - t;
    sb_ui.live++;
    if (t > sb_ui.live_max)
        sb_ui.live_max = t;
}

/* The transform, and the bars marked if they moved; silence costs only
 * the look at the ring (and one last draw of the bars falling to 0). */
static u32 spec_ticks;

static void spectrum_part(u32 step)
{
    u32 t = sb_now(), j, moved = 0, top = 0;

    if (step == 0) {
        spec_ticks = 0;
        if (!spectrum_start()) {
            for (j = 0; j < SPEC_BARS; j++)
                bars_new[j] = 0;
            sb_ui.spec_silent++;
            goto bars;
        }
        spectrum_stages(0, 4);
        spec_ticks += sb_now() - t;
        dirty |= ITEM_SPEC2;
        return;
    }
    if (step == 1) {
        spectrum_stages(4, 7);
        spec_ticks += sb_now() - t;
        dirty |= ITEM_SPEC3;
        return;
    }
    spectrum_bars(bars_new, SPEC_H);
    spec_ticks += sb_now() - t;
    sb_ui.spec_updates++;
    if (spec_ticks > sb_ui.spec_max)
        sb_ui.spec_max = spec_ticks;
bars:
    for (j = 0; j < SPEC_BARS; j++) {
        moved |= bars_new[j] != bars_drawn[j];
        if (bars_new[j] > bars_new[top])
            top = j;
    }
    sb_ui.spec_peak = top | (u32)bars_new[top] << 16;
    if (moved)
        dirty |= ITEM_SPEC_DRAW;
}

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
    } else if (bit == 11) {
        draw_strip();
    } else if (bit == 12) {
        draw_info();
    } else if (bit == 13) {
        draw_live();
    } else if (bit < 16) {
        gfx_fill(GRAPH_X, GRAPH_Y + (bit - 14) * (GRAPH_H / 2), GRAPH_W, GRAPH_H / 2, BLACK);
        if (bit == 15)
            dirty |= ITEM_GRAPH_DRAW;
    } else if (bit == 16) {
        draw_graph(0);
        dirty |= ITEM_GRAPH_SEND;
    } else if (bit == 17) {
        send(GRAPH_Y, GRAPH_H);
    } else if (bit < 21) {
        spectrum_part(bit - 18);
    } else {
        draw_spectrum(0);
        send(SPEC_Y, SPEC_H);
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
            wake_at(frame_beat + FRAME_MS);
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
            wake_at(beats + 1);
            return;
        }
        while (!(dirty >> bit & 1))
            bit++;
        /* A part that sends waits for the bus to be free, in the next
         * block, rather than in lcd_wait (the spectrum's 40 rows take
         * about 10 ms of it). */
        if ((1u << bit) & ITEM_SENDS && lcd_busy()) {
            wake_at(beats + 1);
            return;
        }
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

/* Marks every part whose contents changed: only after the engine's state
 * moved (the live parts' wakes find nothing to do here). */
static void work(void)
{
    u32 k;

    if (fm_ui.seq == ui_seen && sb_ui.shows)
        return;
    {
        u32 screen = ui.screen;
        take();
        ui_seen = ui.seq;
        if (ui.screen != screen || !sb_ui.shows) {
            dirty |= ITEM_HEAD | ITEM_BODY_ALL | ITEM_LINE | ITEM_STRIP;
            sb_ui.shows++;
        }
        sb_ui.screen = ui.screen;
        /* The engine feeds the spectrum only while the patch view shows. */
        spec_wanted = ui.screen == UI_PATCH;
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
    info_work();
    if (!same(info_text, info_drawn))
        dirty |= ITEM_INFO;
    graph_sig = graph_work();
    /* Marked once a change: its parts may take several blocks. */
    body_sig = body_work();
    if (body_sig != body_sig_marked) {
        body_sig_marked = body_sig;
        dirty |= ITEM_BODY_ALL;
        /* The info line lies in the body's last band. */
        info_drawn[0] = 0;
        if (info_text[0])
            dirty |= ITEM_INFO;
        /* A body draws its graph too. */
        graph_sig_marked = graph_sig;
    } else if (graph_sig != graph_sig_marked) {
        graph_sig_marked = graph_sig;
        dirty |= ITEM_GRAPH;
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

/* The live parts, at most every LIVE_MS while their screen shows and its
 * body is drawn. */
#define LIVE_MS 50u
static u32 live_beat;

static void live_work(void)
{
    u32 beats = sb_beacon.beats, i, any = 0;

    if (dirty & (ITEM_BODY_ALL | ITEM_GRAPH | ITEM_GRAPH_DRAW | ITEM_GRAPH_SEND | ITEM_SPEC | ITEM_SPEC2 | ITEM_SPEC3
                 | ITEM_SPEC_DRAW
                 | (((1u << BANDS) - 1u) << ITEM_SEND0)))
        return;
    if (ui.screen == UI_PATCH) {
        /* At rest, with the bars down, nothing to do until the next
         * event wakes main (a note starting is one). */
        if (spectrum_quiet()) {
            for (i = 0; i < SPEC_BARS && !bars_drawn[i]; i++)
                ;
            if (i == SPEC_BARS)
                return;
        }
        if (beats - live_beat < SPEC_MS) {
            wake_at(live_beat + SPEC_MS);
            return;
        }
        live_beat = beats;
        dirty |= ITEM_SPEC;
        wake_at(live_beat + SPEC_MS);
        return;
    }
    if (ui.screen != UI_EDIT && ui.screen != UI_ENV)
        return;
    if (beats - live_beat < LIVE_MS) {
        wake_at(live_beat + LIVE_MS);
        return;
    }
    live_beat = beats;
    if (ui.screen == UI_ENV) {
        dot_work();
        if (dot_want_on != dot_on || (dot_on && (dot_want_x != dot_x || dot_want_y != dot_y))
            || !same(stage_text, stage_drawn))
            dirty |= ITEM_LIVE;
        wake_at(live_beat + LIVE_MS);
        return;
    }
    for (i = 0; i < FM_OPS; i++) {
        live_width[i] = meter_width(fm_op_level[i], box_w - 6);
        any |= live_width[i] != meter_drawn[i];
    }
    if (any)
        dirty |= ITEM_LIVE;
    wake_at(live_beat + LIVE_MS);
}

/* The live parts' next turn, whatever the frames asked for meanwhile. */
static void live_rearm(void)
{
    if (ui.screen == UI_PATCH && !spectrum_quiet())
        wake_at(live_beat + SPEC_MS);
    else if (ui.screen == UI_PATCH && bars_drawn[0] | bars_drawn[SPEC_BARS / 2])
        wake_at(live_beat + SPEC_MS);
    else if (ui.screen == UI_EDIT || ui.screen == UI_ENV)
        wake_at(live_beat + LIVE_MS);
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
        /* SEL with OP1 to OP6 picks the operator (M8a part 3). */
        if (e.kind == INPUT_PRESS && input_value(INPUT_SEL))
            for (i = 0; i < FM_OPS; i++)
                if (e.control == op_key[i] && led_op != i) {
                    led_op = i;
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
    live_work();
    if (dirty)
        draw_frame();
    live_rearm();
}
