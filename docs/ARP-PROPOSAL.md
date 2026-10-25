<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# ARP proposal: an arpeggiator on the ARP button

A proposal for the owner to review, written at the end of M8a. Nothing
here is built. It uses only what the firmware and the panel already
offer (HW-36's ARP button and its LED, the engine's note events, MIDI
in and out from M6a and M6b, the screens from M8a) and no new hardware
fact. The owner's answer to the M8 proposal put it next after M8: ARP,
then SEQ. Decisions wanted are at the end.

## What it does

While ARP is on, the notes held (on the panel's keys or by MIDI in) are
not played as a chord: the arpeggiator plays them one at a time, in a
pattern, at a rate, over a range of octaves, for as long as they are
held (or latched). Each note it plays is an ordinary note on and note off
to the engine, so every patch, macro and voice rule applies as it does
to a key.

## Modes

| Mode | Order of the held notes |
|---|---|
| UP | lowest to highest, then again |
| DOWN | highest to lowest |
| UP/DOWN | up, then down, the ends not repeated |
| ORDER | the order they were pressed |
| RANDOM | a pseudo-random choice each step (a fixed generator, so a test can predict it) |
| CHORD | all of them together, each step (a rhythmic chord) |

Octaves: 1 to 4. The pattern runs through the held notes, then again an
octave up, up to the range, then starts again.

## Controls

The ARP button turns the arpeggiator on or off (its LED lit while on);
how it also reaches the arpeggiator's screen is question 3. The screen
is like EDIT and ENV, with the bottom strip:

| Knob | What | Range |
|---|---|---|
| KNOB1 | RATE | divisions of the beat: 1/4, 1/8, 1/8T, 1/16, 1/16T, 1/32 |
| KNOB2 | MODE | the six above |
| KNOB3 | OCTAVES | 1 to 4 |
| KNOB4 | GATE | how long each note sounds: 10% to 100% of its step |

SELECT pages to: SWING (0 to 75%), LATCH (on: notes keep playing after
the keys are let go, until the next chord), TEMPO (40 to 240 BPM, when
the clock is internal), CLOCK (internal or MIDI).

SEL with a key keeps working as in M8a (operator picks, MONO, POLY).
PRESETS, MASTER, OCT- and OCT+ keep their meanings; OCT moves the notes
the arpeggiator plays as it moves keys.

## Timing

- **The clock:** the engine counts audio blocks (1.451 ms) and samples
  within them, so a step falls on its sample, not on the next block: at
  120 BPM a sixteenth is 125 ms, 5 514.7 frames; the error never grows
  (a fractional accumulator, as the pitch's).
- **MIDI clock in** (0xF8, 24 a beat; Start, Stop, Continue): when the
  clock is MIDI, each 0xF8 advances the step count by 1/24 of a beat;
  the rate between clocks is smoothed over the last 24 for steps that
  fall between them. M6a's parser already passes realtime bytes through
  without disturbing other messages.
- **Swing** delays every second step by its share of a step.

## MIDI out

- **The notes the arpeggiator plays go out** as note ons and offs on the
  out channel, so another instrument follows it; the keys held are not
  sent (they are its input, not notes). A setting (question 4) could
  send the keys instead.
- **MIDI clock out**: when the clock is internal, 0xF8 24 times a beat
  and Start and Stop with the ARP button; when it follows MIDI clock, no
  clock out (thru passes it on if thru is on).
- Local control off: the arpeggiator still runs and its notes go out;
  the engine plays nothing (M6b's rule).

## What it costs

- **CPU:** a step is a few hundred instructions (choose a note, a note
  off for the last, a note on), at most 32 a second at 1/32 and 240 BPM
  with CHORD's notes, so under 0.1% of core 0; the clock is a few
  instructions a block.
- **RAM:** the held notes (up to 16, in pressed order and sorted), the
  pattern's place, the settings: under 100 bytes.
- **Settings:** the arpeggiator's settings join `struct midi_settings`
  in a new version (the store migrates), or a record of their own
  (question 5).
- **Screen:** the ARP screen is drawn as the others (M8a's parts); a
  live part shows the step's note.

## Tests

- Each mode's order for a known chord, from MIDI out's capture (exact).
- The steps' timing: each note on's first byte within a block of its
  ideal time at several tempos, and no drift over a minute.
- MIDI clock in at 120 and 90 BPM: the steps follow; Start and Stop.
- Latch, octaves, gate (each note off at its share of the step), swing.
- Local control off: notes out, nothing played; ARP off: every note it
  started ends.
- Costs: the loaded measure with the arpeggiator at its fastest.

## Questions for the owner

1. **Modes:** the six above, or fewer (UP, DOWN, UP/DOWN, RANDOM) to
   start?
2. **Rates:** the six divisions, or also whole notes, halves and
   dotted ones?
3. **The ARP button:** short press on or off, and hold it to show the ARP
   screen (as GLO shows the settings)? Or press for the screen and turn
   it on there?
4. **MIDI out:** send the arpeggiated notes (as proposed), the keys held,
   or a setting to choose?
5. **Keeping it:** the arpeggiator's settings saved with the other
   settings (one per instrument), or with each patch?
6. **Clock:** follow MIDI clock automatically when it arrives, or only
   when the setting says so?
