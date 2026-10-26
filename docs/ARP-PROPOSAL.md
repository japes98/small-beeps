<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# ARP proposal: an arpeggiator on the ARP button

A proposal for the owner to review, written at the end of M8a. Nothing
here is built. The owner answered its questions on 2026-10-25 (recorded
by session owner-answers-1025, at the end); the text above them follows
the answers. It uses only what the firmware and the panel already
offer (HW-36's ARP button and its LED, the engine's note events, MIDI
in and out from M6a and M6b, the screens from M8a) and no new hardware
fact. The owner's answer to the M8 proposal put it next after M8: ARP,
then SEQ (then FX, docs/PLAN.md).

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

A short press of the ARP button turns the arpeggiator on or off (its LED
lit while on); holding it shows the arpeggiator's screen (answer 3). The
screen
is like EDIT and ENV, with the bottom strip:

| Knob | What | Range |
|---|---|---|
| KNOB1 | RATE | 1/2, dotted 1/4, 1/4, dotted 1/8, 1/8, 1/8T, dotted 1/16, 1/16, 1/16T, 1/32 (answer 2) |
| KNOB2 | MODE | the six above |
| KNOB3 | OCTAVES | 1 to 4 |
| KNOB4 | GATE | how long each note sounds: 10% to 100% of its step |

SELECT pages to: SWING (0 to 75%), LATCH (on: notes keep playing after
the keys are let go, until the next chord), TEMPO (40 to 240 BPM, when
the clock is internal), and the MIDI out setting (the arpeggiated notes,
or the keys held; answer 4). The CLOCK page (internal or MIDI) proposed
here is superseded: the arpeggiator follows MIDI clock whenever it
arrives (answer 6).

SEL with a key keeps working as in M8a (operator picks, MONO, POLY).
PRESETS, MASTER, OCT- and OCT+ keep their meanings; OCT moves the notes
the arpeggiator plays as it moves keys.

## Timing

- **The clock:** the engine counts audio blocks (1.451 ms) and samples
  within them, so a step falls on its sample, not on the next block: at
  120 BPM a sixteenth is 125 ms, 5 514.7 frames; the error never grows
  (a fractional accumulator, as the pitch's).
- **MIDI clock in** (0xF8, 24 a beat; Start, Stop, Continue): while MIDI
  clock arrives, each 0xF8 advances the step count by 1/24 of a beat;
  the rate between clocks is smoothed over the last 24 for steps that
  fall between them. When it stops, the internal tempo takes over
  (answer 6). M6a's parser already passes realtime bytes through
  without disturbing other messages.
- **Swing** delays every second step by its share of a step.

## MIDI out

- **The notes the arpeggiator plays go out** as note ons and offs on the
  out channel, so another instrument follows it; the keys held are not
  sent (they are its input, not notes). A setting sends the keys held
  instead (answer 4).
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
- **Settings:** the arpeggiator's settings are saved with each patch
  (answer 5); how the patch format carries them is the firmware side's
  design (docs/PATCH-FORMAT.md, docs/STORE-FORMAT.md).
- **Screen:** the ARP screen is drawn as the others (M8a's parts); a
  live part shows the step's note.

## Tests

- Each mode's order for a known chord, from MIDI out's capture (exact).
- The steps' timing: each note on's first byte within a block of its
  ideal time at several tempos, and no drift over a minute.
- MIDI clock in at 120 and 90 BPM: the steps follow; Start, Stop and
  Continue; the internal tempo takes over when the clock stops.
- Latch, octaves, gate (each note off at its share of the step), swing.
- Local control off: notes out, nothing played; ARP off: every note it
  started ends.
- Costs: the loaded measure with the arpeggiator at its fastest.

## The owner's answers (2026-10-25)

The questions were:

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

The owner's answers (recorded by session owner-answers-1025,
docs/prompts/owner-answers-1025.md):

1. **Modes:** all six: UP, DOWN, UP/DOWN, ORDER, RANDOM, CHORD.
2. **Rates:** 1/2, dotted 1/4, 1/4, dotted 1/8, 1/8, 1/8T, dotted 1/16,
   1/16, 1/16T, 1/32. No whole notes.
3. **The ARP button:** a short press turns the arpeggiator on or off;
   holding it shows the ARP screen.
4. **MIDI out:** the arpeggiated notes by default, with a setting to send
   the keys held instead.
5. **Keeping it:** the arpeggiator's settings are saved with each patch.
6. **Clock:** follow incoming MIDI clock automatically, falling back to
   the internal tempo when it stops.

Left to the firmware side's design (made in its ARP work, #132;
docs/DESIGN-NOTES.md, "ARP"):

- **When the clock has stopped.** A MIDI Stop, a silence with no 0xF8
  (and how long), or both; and what a Start, a Stop or a Continue does
  to the pattern and to notes still sounding.
- **Moving between the two clocks.** Whether the internal tempo, when it
  takes over, starts from the MIDI clock's last tempo or from the
  patch's TEMPO; and where in the step the pattern carries on.
- **Per patch.** Which settings travel with a patch (on or off, LATCH,
  TEMPO, the MIDI out setting) and which stay with the instrument;
  presets saved before ARP get the defaults.
