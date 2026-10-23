/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The Plaits demo's only door into the vendored Plaits voice
 * (vendor/plaits/, docs/DESIGN-NOTES.md, M4b): a C interface, so the
 * demo's glue (plaits_demo.c, bench.c) is C like the rest of the firmware
 * and only plaits_voice.cc is C++.
 */

#ifndef PLAITS_VOICE_H
#define PLAITS_VOICE_H

#ifdef __cplusplus
extern "C" {
#endif

#define PLAITS_ENGINES   24   /* Plaits' engines, in its own order */
#define PLAITS_RENDER    16   /* frames a render; Plaits takes up to 24 */
#define PLAITS_VOICES    2    /* voices the demo can hold: one a core */

/* What Plaits plays: its patch, as its panel would set it. Parameters are
 * 0 to 1; note is a MIDI note at Plaits' own rate (plaits_demo.c adds the
 * offset for ours); trigger is a gate (1 while a key is held). */
struct plaits_params {
    int engine;
    float note;
    float harmonics;
    float timbre;
    float morph;
    float decay;
    float lpg_colour;
    int trigger;
};

/* Sets voice v (0 to PLAITS_VOICES - 1) up, with its own buffer. */
void plaits_voice_init(unsigned v);
/* Renders frames (at most PLAITS_RENDER) of voice v: out[2n] is Plaits'
 * main output, out[2n + 1] its auxiliary one, 16-bit. */
void plaits_voice_render(unsigned v, const struct plaits_params *p, short *out, unsigned frames);

#ifdef __cplusplus
}
#endif

#endif
