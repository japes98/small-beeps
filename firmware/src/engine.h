/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The engine seam (BR-1; docs/DESIGN-NOTES.md, "Seams for firmwares
 * built on small-beeps"; docs/BUILDING-ON-SMALL-BEEPS.md). Built with
 * SB_ENGINE_EXTERNAL, main() leaves out the base's FM engine and its
 * store start-up and calls these three instead, which the firmware built
 * on the base defines. Without it main() runs the base's instrument, as
 * before, and nothing here is called.
 *
 * - sb_engine_init: once, where the base calls fm_init(): after the time
 *   base, the tick's and SPI1's handlers and the panel's scan are set up,
 *   before interrupts are on and before the audio starts. The engine
 *   starts its own parts here (MIDI in with midi_start(), the store with
 *   store_init(), ...). Interrupts are off: nothing it sets up runs yet.
 * - sb_engine_block: the block callback main hands to audio_start()
 *   (audio.h): run by core 0 in the audio interrupt, every block, with
 *   AUDIO_FRAMES stereo frames to fill. MIDI in (midi_poll, midi_read)
 *   and MIDI out (midi_out_send, midi_out_poll) are read and written
 *   from here, as the base's engine does.
 * - sb_engine_serve: from main's loop, once before the loop begins and
 *   then on each wake that found work (a change of sb_work, sb.h): the
 *   tick's whole seconds, the panel's events, the screen's next frame,
 *   and anything that adds one to sb_work. Long work (the store's flash
 *   writes, drawing) goes here, never in the block callback. Before it
 *   is called main has brought up the screen and shown the test screen;
 *   main keeps the heartbeat on it while sb_beacon.screen is
 *   SB_SCREEN_TEST, so an engine that draws its own sets another value.
 */

#ifndef ENGINE_H
#define ENGINE_H

#include "sb.h"

void sb_engine_init(void);
void sb_engine_block(s32 *out, u32 frames);
void sb_engine_serve(void);

#endif
