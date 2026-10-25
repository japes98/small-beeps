/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Drawing into the frame buffer: fill, frames, lines, pixels and text.
 * The buffer is the panel's 240 x 240 pixels, row by row from the top
 * left, each pixel's RGB565 colour stored high byte first, the order the
 * panel takes them (HW-27, HW-31), so lcd.c can send it as it is
 * (docs/DESIGN-NOTES.md, M2). Everything is clipped to the screen.
 */

#include "sb.h"

/* In .bss: startup clears it. 4-byte aligned for the DMA and for
 * writing two pixels at a time. */
u16 sb_fb[SCREEN_W * SCREEN_H] __attribute__((aligned(4)));

/* A colour as it is stored: its two bytes swapped (the core is
 * little-endian). */
static u32 stored(u32 colour)
{
    return (colour >> 8 & 0xFFu) | (colour & 0xFFu) << 8;
}

void gfx_fill(u32 x, u32 y, u32 w, u32 h, u32 colour)
{
    u32 c = stored(colour), pair = c | c << 16, i;

    if (x >= SCREEN_W || y >= SCREEN_H)
        return;
    if (w > SCREEN_W - x)
        w = SCREEN_W - x;
    if (h > SCREEN_H - y)
        h = SCREEN_H - y;
    for (; h; h--, y++) {
        u16 *p = &sb_fb[y * SCREEN_W + x];
        i = w;
        if (i && ((u32)p & 2)) {
            *p++ = c;
            i--;
        }
        for (; i >= 2; i -= 2, p += 2)
            *(u32 *)p = pair;
        if (i)
            *p = c;
    }
}

/* A one-pixel outline of the rectangle. */
void gfx_frame(u32 x, u32 y, u32 w, u32 h, u32 colour)
{
    if (!w || !h)
        return;
    gfx_fill(x, y, w, 1, colour);
    gfx_fill(x, y + h - 1, w, 1, colour);
    gfx_fill(x, y, 1, h, colour);
    gfx_fill(x + w - 1, y, 1, h, colour);
}

void gfx_pixel(u32 x, u32 y, u32 colour)
{
    if (x < SCREEN_W && y < SCREEN_H)
        sb_fb[y * SCREEN_W + x] = stored(colour);
}

/* From (x0, y0) to (x1, y1), both ends included: each step moves one
 * pixel along the longer axis and, when the error accumulated in the
 * other axis passes half a pixel, one along that too. */
void gfx_line(int x0, int y0, int x1, int y1, u32 colour)
{
    int dx = x1 > x0 ? x1 - x0 : x0 - x1, sx = x1 > x0 ? 1 : -1;
    int dy = y1 > y0 ? y1 - y0 : y0 - y1, sy = y1 > y0 ? 1 : -1;
    int err = dx - dy;

    for (;;) {
        gfx_pixel((u32)x0, (u32)y0, colour);
        if (x0 == x1 && y0 == y1)
            return;
        if (2 * err > -dy) {
            err -= dy;
            x0 += sx;
        }
        if (2 * err < dx) {
            err += dx;
            y0 += sy;
        }
    }
}

/* One character cell, FONT_CELL x FONT_H pixels times scale, with every
 * pixel written: the glyph's in fg, the rest (the spacing column too) in
 * bg. A character outside the font draws as a filled box. The cell must
 * lie on the screen. */
void gfx_glyph(u32 x, u32 y, u32 c, u32 fg, u32 bg, u32 scale)
{
    static const u8 box[FONT_H] = { 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0 };
    const u8 *rows = c >= FONT_FIRST && c <= FONT_LAST ? font_glyphs[c - FONT_FIRST] : box;
    u32 f = stored(fg), b = stored(bg), r, i, j, k;

    if (x + FONT_CELL * scale > SCREEN_W || y + FONT_H * scale > SCREEN_H)
        return;
    if (scale == 1) {
        /* Since M5 (DESIGN-NOTES.md, "the screen's cost"): two pixels a
         * store, each pair's colours looked up by its two bits (the left
         * pixel is the lower address, so the low half). A cell at an odd
         * x has a single pixel at each end and two pairs between. */
        u32 pair[4] = { b | b << 16, b | f << 16, f | b << 16, f | f << 16 };
        u32 odd = x & 1;

        for (r = 0; r < FONT_H; r++) {
            u16 *p = &sb_fb[(y + r) * SCREEN_W + x];
            u32 bits = (u32)rows[r] << 1;   /* bit 5 is the left column */
            if (!odd) {
                u32 *w = (u32 *)p;
                w[0] = pair[bits >> 4 & 3];
                w[1] = pair[bits >> 2 & 3];
                w[2] = pair[bits & 3];
            } else {
                u32 *w = (u32 *)(p + 1);
                p[0] = bits >> 5 & 1 ? f : b;
                w[0] = pair[bits >> 3 & 3];
                w[1] = pair[bits >> 1 & 3];
                p[5] = bits & 1 ? f : b;
            }
        }
        return;
    }
    if (scale == 2 && !(x & 1)) {
        /* Since M8a: each glyph pixel is a pair, one store, and the
         * row below a copy of the row (the screens' large text). */
        for (r = 0; r < FONT_H; r++) {
            u32 *w = (u32 *)&sb_fb[(y + 2 * r) * SCREEN_W + x];
            u32 bits = (u32)rows[r] << 1, fp = f | f << 16, bp = b | b << 16;
            for (i = 0; i < FONT_CELL; i++)
                w[i] = bits >> (FONT_CELL - 1 - i) & 1 ? fp : bp;
            for (i = 0; i < FONT_CELL; i++)
                w[i + SCREEN_W / 2] = w[i];
        }
        return;
    }
    for (r = 0; r < FONT_H; r++) {
        u16 *line = &sb_fb[(y + r * scale) * SCREEN_W + x];
        u32 bits = (u32)rows[r] << 1;   /* bit FONT_CELL - 1 is the left column */
        u16 *p = line;
        for (i = FONT_CELL; i; i--) {
            u32 v = bits >> (i - 1) & 1 ? f : b;
            for (k = scale; k; k--)
                *p++ = v;
        }
        /* The other scale - 1 rows repeat this one: two pixels at a time
         * when the cell starts on a word and is an even width. */
        for (j = 1; j < scale; j++) {
            if (!((u32)line & 3) && !(FONT_CELL * scale & 1)) {
                u32 *src = (u32 *)line, *dst = (u32 *)&line[j * SCREEN_W];
                for (i = FONT_CELL * scale / 2; i; i--)
                    *dst++ = *src++;
            } else {
                for (i = 0; i < FONT_CELL * scale; i++)
                    line[j * SCREEN_W + i] = line[i];
            }
        }
    }
}

/* Text from (x, y), one cell per character, stopping at the screen's
 * right edge. Returns the x just past the last cell drawn. */
u32 gfx_text(u32 x, u32 y, const char *text, u32 fg, u32 bg, u32 scale)
{
    for (; *text && x + FONT_CELL * scale <= SCREEN_W; text++, x += FONT_CELL * scale)
        gfx_glyph(x, y, (u8)*text, fg, bg, scale);
    return x;
}
