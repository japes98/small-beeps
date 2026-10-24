<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# M8 proposal: from engine to instrument

A proposal for the owner to review, written at the end of M7. Nothing
here is built yet. It uses only what the firmware and the panel already
offer, and facts already in HARDWARE-SPEC.md. Decisions wanted are at
the end.

## What we start from

- **Panel** (HW-36): a 240 x 240 colour screen; eight knobs (MASTER, a
  pot; SELECT, PRESETS, ALGORITHM and KNOB1 to KNOB4, encoders with
  detents); 14 buttons (OCT-, OCT+, FX, SEL, ENV, LFO, EDIT, GLO, HOME,
  SAVE, ARP, SEQ, PLAY/STOP, REC), each with an LED; 27 keys, each with an
  LED, ten raised keys carrying second labels: OP1 to OP6, PIT, GLO,
  MONO, POLY.
- **Engine** (M5 to M7): six operators, ten algorithms, 16 voices on two
  cores, a pitch envelope, mono with glide, MIDI in and out, 9 test
  patches, 16 user slots kept in flash.
- **Today's controls:** PRESETS picks a program, ALGORITHM the algorithm,
  KNOB1 to KNOB4 are pitch, glide, modulation depth and feedback; SEL
  with MONO or POLY sets the mode; SAVE with a key saves.

## Four rules

1. **One screen at a time; HOME always goes back** to the patch view.
2. **The bottom strip names what KNOB1 to KNOB4 do** on every screen,
   with their values, so the knobs are never a guess.
3. **Some knobs never change meaning:** MASTER is volume, PRESETS the
   program, OCT- and OCT+ the octave, everywhere.
4. **The screen shows the sound,** not only numbers: the algorithm
   drawn with each operator's level moving as it plays, and a spectrum
   of what comes out.

## The screens

### Patch view (HOME)

```
+--------------------------------------+
| 012  GLASS BELL           POLY  O+0  |
|                                      |
|  [alg 5]   .:|||||:.  .|.            |
|  1>2 3>4   spectrum, live            |
|  5>6                                 |
|--------------------------------------|
| BRIGHT  COLOR   SHAPE   MOTION       |
|  +12     -3      +40      8          |
+--------------------------------------+
```

The program and its name, the mode and octave; a small picture of the
algorithm; the live spectrum. KNOB1 to KNOB4 are the four macros
(below). ALGORITHM changes the algorithm, as now.

### Operator and algorithm view (EDIT)

```
+--------------------------------------+
| ALG 5            OP3 selected        |
|  [1]-->[2]                           |
|   ##     #       ## = level now      |
|  [3]==>[4]   (selected: double line) |
|   ###    ##                          |
|  [5]-->[6]~ (~ feedback)             |
|   #      #####                       |
|--------------------------------------|
| RATIO   LEVEL   DETUNE  VELO         |
|  2.00    104     +3      4           |
+--------------------------------------+
```

The algorithm drawn as boxes and arrows, carriers at the bottom. Under
each box a bar shows that operator's level now (the loudest voice), so
you see a modulator decay while the note sounds. SEL with OP1 to OP6
picks the operator, whose key LED stays lit; KNOB1 to KNOB4 edit it.
SELECT steps through the operator's other pages (mode and fixed
frequency; the envelope's levels).

### Envelope view (ENV)

```
+--------------------------------------+
| ENV  OP3                  stage: D1  |
|      /\                              |
|     /  \___                          |
|    /       \_______    o <- now      |
|   /                \                 |
|--------------------------------------|
| ATTACK  DECAY1  DECAY2  RELEASE      |
|   12      40      70      55         |
+--------------------------------------+
```

The selected operator's envelope drawn to scale (time codes are
logarithmic, so the drawing is too), and a dot where the last note is
now. SELECT switches the knobs to the three levels. SEL with PIT shows
the pitch envelope instead; SEL with GLO, the glide.

### Settings (GLO)

```
+--------------------------------------+
| SETTINGS                             |
| > MIDI in channel     omni           |
|   MIDI out channel    1              |
|   Thru                off            |
|   Local control       on             |
|   Bend range          2              |
|   Knobs               macros         |
|   Store               5/16 used      |
|   Factory reset       hold SAVE      |
|--------------------------------------|
| SELECT: row    KNOB1: change         |
+--------------------------------------+
```

Every setting in `struct midi_settings`, plus the knobs' mode (macros or
the M5 controls) and the store's state. Changes are kept as M7 keeps
them (2 s after the last change).

### Save (SAVE)

```
+--------------------------------------+
| SAVE  GLASS BELL  to slot:           |
|  1 PAD A   2 ---    3 ---    4 BASS  |
|  5 ---     6 ---    7 ---    8 ---   |
|  9 ---    10 ---   11 ---   12 ---   |
| 13 ---    14 ---   15 ---   16 ---   |
|--------------------------------------|
| SELECT: slot  SAVE: write  HOME: no  |
+--------------------------------------+
```

M7's shortcut (SAVE held with a key) stays; the screen adds names, a
slot picker and a confirmation before overwriting a slot in use.

## The controls

| Control | Everywhere | Patch | EDIT | ENV | Settings |
|---|---|---|---|---|---|
| MASTER | volume | | | | |
| PRESETS | program | | | | |
| ALGORITHM | | algorithm | algorithm | | |
| SELECT | | | operator page | rates / levels | row |
| KNOB1-4 | | macros | operator | stage times | value (KNOB1) |
| OCT- / OCT+ | octave | | | | |
| HOME, EDIT, ENV, GLO, SAVE | go to that screen | | | | |
| SEL + OP1-6 | | | pick operator | pick operator | |
| SEL + PIT / GLO | | | | pitch env / glide | |
| SEL + MONO / POLY | mode (as now) | | | | |
| PLAY/STOP | audition note (the test tone today) | | | | |
| FX, LFO, ARP, SEQ, REC | reserved for later milestones: the event line says so | | | | |

SEL is the shift key: held, the raised keys do what their second label
says and play no note. Keys without SEL always play. LEDs: the screen's
button lit; the selected operator's key at half brightness; held keys
fully lit, as now.

## The four macros (KNOB1 to KNOB4 in the patch view)

Each macro moves several of the patch's values at once, as an offset
over the stored patch (as KNOB1 to KNOB4 do today), so turning it back
returns the patch exactly. Each is sent and received as one MIDI
controller (16 to 19, as now).

- **BRIGHT** (brightness): every modulator's level up or down together,
  so the index and the upper partials rise or fall. Today's KNOB3,
  renamed.
- **COLOR** (harmonic to metallic): the modulators' ratios move from
  their whole-number values towards inharmonic ones (a fixed table of
  targets per ratio, so the sweep is the same on every patch), and
  feedback rises a little at the metallic end.
- **SHAPE** (pluck to pad): the carriers' envelopes. At one end a fast
  attack, a short decay and little sustain; at the other a slow attack,
  full sustain and a long release. The middle is the patch as stored.
- **MOTION:** vibrato depth, plus a small spread of detune across the
  carriers, so a held note moves and widens.

The M5 controls (pitch, glide, depth, feedback) stay available as a
setting ("Knobs: direct"), for tests and for players who want them.

## Presets: a bank of our own

- **How many:** 64 presets in 8 categories of 8: keys, bass, bells and
  mallets, brass and winds, pads, leads, plucks and strings, percussion
  and effects. They sit in the image, after the 9 test patches; the 16
  user slots stay as M7 made them.
- **How they are made:** written from scratch in `tools/fm_patch.py`,
  as the test patches are: ratios, levels and envelopes chosen by ear
  and by reasoning (a bell's inharmonic ratios, a bass's short
  modulator decay), each with a line saying what it is for. Never
  derived from anyone's factory sounds: no voice banks or SysEx dumps are
  opened, converted or compared, and no names are borrowed. Each preset's
  history is its commits.
- **How they are tested,** each one in fwtest, by a tool of our own:
  - valid by `fm_patch.problems()`, and all 16 voices sounding within
    the loaded budget;
  - a reference note: no clipping, no DC, no click at note on or off,
    loudness within 3 dB of a target, so the bank plays at one level;
  - its category's shape: a bass has most of its energy below 300 Hz, a
    pad no attack faster than 50 ms, a pluck decays by 30 dB within 2 s;
  - a golden WAV of the reference note, so any change shows;
  - and the owner listens before the bank is merged.

## Costs

From M5 to M7's measurements (fwtest): a block is 64 frames, 1.451 ms,
about 348 000 core cycles at 240 MHz. Under the heaviest input, core 0
spends about 110 000 instructions a block (32%), core 1 about 22%, and
the screen may take at most 4 352 time base ticks a block, about 43 500
instructions (12.5%). On the chip the panel's bus needs at least 60.8 ms
for a whole frame (DESIGN-NOTES, M2), so live views redraw small regions,
never the whole screen.

| Live view | Core 0, each update | At 30 updates a second | Panel bus, at 30 a second |
|---|---:|---:|---:|
| Spectrum: 256-point real FFT of the output, 64 bars, 240 x 40 pixels | about 15 000 instructions (FFT with the float unit, window, magnitudes) | about 650 a block, 0.2% | 10.1 ms an update: 30% |
| Algorithm: 6 level bars of 30 x 20 pixels | about 10 000 | about 430 a block, 0.1% | 3.8 ms an update: 11% |
| Envelope dot | under 2 000 | under 100 a block | under 1% |

So the live views together cost under 1% of core 0 on average, and each
update fits in one block's drawing budget. The bus is the limit: both
live views at 30 updates a second take about 41% of it (at 20, about
28%), which leaves room for the knobs' 16 ms frames. The proposal: 30
updates a second on the patch view's spectrum alone, 20 when the
algorithm's bars show too. RAM: about 2 KiB for the FFT's buffers
(the output's last 256 samples, copied by the engine each block). The
engine adds one small record for the views: each operator's loudest
level, written once a block. Nothing moves to core 1.

## Questions for the owner

1. **Buttons:** HW-36 lists 14 buttons (OCT- and OCT+ included); the
   prompt said twelve. The table uses all 14. Right?
2. **Shift key:** SEL as shift (it already is with MONO and POLY), or
   hold the screen's own button?
3. **Macros on save:** stay offsets (the saved patch is the stored one;
   the macros come back to zero), or be written into the patch on SAVE?
4. **Sizes:** 64 presets and 16 user slots? More user slots (64, say)
   need the store's next format, since their records would outgrow one
   sector.
5. **Spectrum:** on the patch view by default? Log or linear frequency?
6. **Factory reset:** keep M7's hold of SAVE and HOME, or move it into
   Settings with a confirmation?
7. **Reserved buttons** (FX, LFO, ARP, SEQ, REC): which comes next after
   M8?
