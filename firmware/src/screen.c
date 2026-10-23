/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * What the screen shows (docs/DESIGN-NOTES.md, M2): first the address
 * pattern, in which every pixel's colour says where it is, then the test
 * screen, which shows orientation, colour order, the edges, lines, the
 * font and the heartbeat. tools/fw-suite.py checks both from fwtest's
 * captures; their layouts here and there go together.
 */

#include "sb.h"

#define BLACK   RGB565(0, 0, 0)
#define WHITE   RGB565(31, 63, 31)
#define RED     RGB565(31, 0, 0)
#define GREEN   RGB565(0, 63, 0)
#define BLUE    RGB565(0, 0, 31)
#define YELLOW  RGB565(31, 63, 0)
#define CYAN    RGB565(0, 63, 31)
#define MAGENTA RGB565(31, 0, 31)
#define GREY    RGB565(16, 32, 16)

/* The heartbeat's place: digits at scale 2 in rows BEAT_Y to
 * BEAT_Y + 15, which lcd.c sends as one transfer. */
#define BEAT_Y      200u
#define BEAT_X      96u
#define BEAT_DIGITS 5u
#define BEAT_SCALE  2u

/* The address pattern: red is x / 8 (0 to 29), green y / 4 (0 to 59),
 * blue x mod 8 times 4 plus y mod 4 (0 to 31). No two pixels share a
 * colour, so a capture shows where each pixel landed. */
void screen_pattern(void)
{
    u32 x, y;

    for (y = 0; y < SCREEN_H; y++) {
        u16 *p = &sb_fb[y * SCREEN_W];
        for (x = 0; x < SCREEN_W; x++) {
            u32 c = RGB565(x >> 3, y >> 2, (x & 7) << 2 | (y & 3));
            p[x] = (u16)(c >> 8 | (c & 0xFF) << 8);
        }
    }
}

static u8 beat_digits[BEAT_DIGITS];

static void draw_beat_digit(u32 i)
{
    gfx_glyph(BEAT_X + i * FONT_CELL * BEAT_SCALE, BEAT_Y, '0' + beat_digits[i], GREEN, BLACK, BEAT_SCALE);
}

/* The test screen:
 * - a white border on the outermost pixels of all four edges;
 * - a 12 x 12 square in each corner, 3 pixels in: red top left, green top
 *   right, blue bottom left, yellow bottom right, each named beside it;
 * - the title, and three ramps (red 32 steps, green 64, blue 32), each
 *   step one more of that channel from 0, 192 pixels wide from x = 24;
 * - a white box with its diagonals and a cross of lines;
 * - every character of the font, in three rows;
 * - the heartbeat: seconds since the start, five digits. */
void screen_test(void)
{
    static const char *const rows[3] = {
        " !\"#$%&'()*+,-./0123456789:;<=>?",
        "@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_",
        "`abcdefghijklmnopqrstuvwxyz{|}~",
    };
    u32 i;

    gfx_fill(0, 0, SCREEN_W, SCREEN_H, BLACK);
    gfx_frame(0, 0, SCREEN_W, SCREEN_H, WHITE);
    gfx_fill(3, 3, 12, 12, RED);
    gfx_fill(SCREEN_W - 15, 3, 12, 12, GREEN);
    gfx_fill(3, SCREEN_H - 15, 12, 12, BLUE);
    gfx_fill(SCREEN_W - 15, SCREEN_H - 15, 12, 12, YELLOW);
    gfx_text(18, 5, "red", RED, BLACK, 1);
    gfx_text(SCREEN_W - 18 - 5 * FONT_CELL, 5, "green", GREEN, BLACK, 1);
    gfx_text(18, SCREEN_H - 13, "blue", BLUE, BLACK, 1);
    gfx_text(SCREEN_W - 18 - 6 * FONT_CELL, SCREEN_H - 13, "yellow", YELLOW, BLACK, 1);

    gfx_text(36, 20, "small-beeps M3", WHITE, BLACK, 2);
    for (i = 0; i < 32; i++) {
        gfx_fill(24 + 6 * i, 44, 6, 14, RGB565(i, 0, 0));
        gfx_fill(24 + 6 * i, 76, 6, 14, RGB565(0, 0, i));
    }
    for (i = 0; i < 64; i++)
        gfx_fill(24 + 3 * i, 60, 3, 14, RGB565(0, i, 0));

    gfx_frame(24, 96, 192, 64, WHITE);
    gfx_line(24, 96, 215, 159, CYAN);
    gfx_line(24, 159, 215, 96, MAGENTA);
    gfx_line(120, 100, 120, 155, GREY);
    gfx_line(28, 128, 211, 128, GREY);

    for (i = 0; i < 3; i++)
        gfx_text(24, 166 + 10 * i, rows[i], WHITE, BLACK, 1);

    for (i = 0; i < BEAT_DIGITS; i++)
        beat_digits[i] = 0;
    sb_beacon.shown = 0;
    screen_beat_all();
}

/* The heartbeat as it stands, label and every digit, in the same place
 * on every screen that shows it (the panel screen too, since M3), so
 * screen_beat can go on updating it there. */
void screen_beat_all(void)
{
    u32 i;

    gfx_text(24, BEAT_Y, "beat", WHITE, BLACK, BEAT_SCALE);
    for (i = 0; i < BEAT_DIGITS; i++)
        draw_beat_digit(i);
}

/* One second more: the digits that change are drawn again, and the
 * heartbeat's rows sent (main calls this once a second). */
void screen_beat(void)
{
    u32 t = sb_now(), i = BEAT_DIGITS;

    while (i--) {
        if (++beat_digits[i] < 10) {
            draw_beat_digit(i);
            break;
        }
        beat_digits[i] = 0;
        draw_beat_digit(i);
    }
    lcd_send_rows(BEAT_Y, FONT_H * BEAT_SCALE);
    sb_beacon.shown++;
    sb_beacon.beat_ticks = sb_now() - t;
}
