<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Building your own firmware on small-beeps

small-beeps is a base: a platform that starts the chip and runs the
panel, the screen, the audio output, MIDI in and out and the flash store,
plus an FM instrument that uses it. You can keep the platform as it is and
put your own engine where the instrument was, in your own repository,
without changing a file of the base. This guide shows how, from an empty
repository to a firmware running in fwtest and in the F-Emulator app.

Everything here is MIT-licensed, like the rest of small-beeps: keep its
`LICENSE` and `NOTICE` with your copy. The seams this guide uses are
described in more depth in docs/DESIGN-NOTES.md, "Seams for firmwares
built on small-beeps", and their requirements are in docs/REQUIREMENTS.md
(R-ENG-1, R-PLAT-1, R-CORE-1, R-RT-1, R-MIDI-8, R-MIDIOUT-9, R-STORE-10, R-STORE-11,
R-BUILD-3, R-BUILD-4).

## 1. Set up

You need git, Docker (any host; the build and the tests run as
linux/amd64 containers) and Python 3.9 or later.

```sh
mkdir my-firmware && cd my-firmware && git init
git submodule add https://github.com/japes98/small-beeps base
mkdir src
sh base/tools/build.sh image      # once: the pinned build image, made locally
```

`build.sh image` builds the base's build image on your machine: a pinned
Debian with the chip's toolchain, downloaded from its vendor and checked
against its SHA-256 (docs/TOOLCHAIN.md). The image and the toolchain are
never published anywhere; keep them out of your repository too.

Your repository then holds `base/` (the base, unmodified, at a commit you
choose) and `src/` (your sources). Everything below runs from your
repository's root.

## 2. Write your engine

Your engine is three functions (`base/firmware/src/engine.h`):

```c
#include "audio.h"
#include "engine.h"
#include "input.h"
#include "midi.h"
#include "midi_out.h"

void sb_engine_init(void)
{
    midi_settings_default(&midi_settings);   /* MIDI's settings: out on channel 1, ... */
    midi_start();                            /* the UART, for MIDI in and out */
}

void sb_engine_block(s32 *out, u32 frames)
{
    struct input_event e;
    struct midi_msg m;
    u32 n;

    while (input_read_audio(&e))
        ;                                    /* the panel's events: keys, encoders, the pot */
    midi_poll();
    while (midi_read(&m))
        ;                                    /* MIDI in's messages */
    for (n = 0; n < frames; n++)
        out[2 * n] = out[2 * n + 1] = 0;     /* your sound: 24-bit, left then right */
    midi_out_poll();                         /* send what you queued */
}

void sb_engine_serve(void)
{
    /* slow work: the screen, the store, a SysEx you received */
}
```

| Function | When | Where it runs |
|----------|------|---------------|
| `sb_engine_init` | once, at start-up, before interrupts are on and the audio starts | core 0, main |
| `sb_engine_block` | every audio block: `AUDIO_FRAMES` (64) stereo frames, 1.45 ms | core 0, the audio interrupt |
| `sb_engine_serve` | once before main's loop, then whenever something added work | core 0, main's loop |

- **The block callback must keep up**: a block is 1.45 ms of core 0's
  time, shared with the tick and the panel's scan. Do the sound and the
  quick reactions here, nothing that waits.
- **Waking main.** Main sleeps between interrupts and calls your serve
  when `sb_work` (`sb.h`) changed: the tick adds one each whole second,
  the panel's scan one per event. Add one yourself (`sb_work++`) from the
  block callback when you leave main work, as a finished SysEx message.
- **The screen.** Main brings the screen up and shows a test screen with
  a heartbeat. To draw your own, set `sb_beacon.screen` to another value
  (`SB_SCREEN_PANEL`, `sb.h`), so main stops drawing the heartbeat, then
  draw into the frame buffer with `gfx_*` and send rows with
  `lcd_send_rows()` or a rectangle with `lcd_send_rect()` (`sb.h`; wait
  for `lcd_busy()` to be 0 first), from your serve.
- **C++** works too: name the file `.cc`. The platform's runtime has
  `memcpy`, `memmove`, `memset`, `<algorithm>`, `<string.h>`,
  `<inttypes.h>`, `<stddef.h>`, `<math.h>` and what virtual classes and
  static objects need (`base/firmware/runtime/`); there is no heap, no
  exceptions and no RTTI. Static objects' constructors run before your
  init.

## 3. What the platform gives you

All from `base/firmware/src/`, all yours to call:

| Part | Header | What |
|------|--------|------|
| The panel | `input.h` | events (`input_read_audio` in the block callback, `input_read` in main), each control's value (`input_value`), the LEDs (`input_led`) |
| Audio | `audio.h` | the block size and rate; your block callback fills the buffer |
| The screen | `sb.h` | `gfx_fill`, `gfx_text`, `gfx_line`, ...; `lcd_send_rows`, `lcd_send_rect`, `lcd_busy` |
| MIDI in | `midi.h` | `midi_start`, `midi_poll` and `midi_read` (whole messages, from the block callback); `midi_sysex_tap` (System Exclusive's bytes, below) |
| MIDI out | `midi_out.h` | below, section 7 |
| The store | `store.h` | `store_init` (once, in your init), `store_get`, `store_put`, `store_reset`, below |
| Core 1 | `core1.h` | `sb_core1_start(entry, stack_top)`; `sb_lock`, `sb_unlock`, `sb_shared`, `sb_publish` to hand it work |
| Time | `sb.h` | `sb_now()` (24 MHz), `sb_ticks()`, `sb_wait_ms()` (main only), the heartbeat in `sb_beacon` |

**System Exclusive in.** `midi_sysex_tap(fn)` sets a function MIDI in's
parser calls for each byte of a System Exclusive message:
`MIDI_SYSEX_BEGIN`, each `MIDI_SYSEX_DATA` byte, then `MIDI_SYSEX_END` or
`MIDI_SYSEX_CUT`. It runs in the block callback: keep the bytes in a
buffer of your own and, at the end, add one to `sb_work`; work on them in
your serve. Messages of any length come through (tested with 4 104 data
bytes).

**The store.** Kinds `0x80` to `0xFE` are yours, any id from 0 to 255,
and a payload of up to 5 904 bytes each (`STORE_FW_MAX`):

```c
store_init();                                     /* in your init */
n = store_get(0x80, 0, buf, sizeof buf, &version);  /* -1: none */
r = store_put(0x80, 0, 1, buf, len);              /* from your serve: it waits for the flash */
```

A save is atomic: if the power goes at any moment during a `store_put`,
the next start finds the whole old payload or the whole new one, never
neither and never a mix (R-STORE-11). The store keeps the old payload
until the new one is written and read back, so a rewrite needs room for
both. Write from your serve, never from the block callback (a write
takes the flash for some milliseconds).

How much fits: the store's region today is three sectors (12 KiB). With
nothing else in it, it holds and rewrites one payload of up to 3 920
bytes; beside the base's own full store (its 16 user slots, the
selection and the settings) about 1.6 KB. `store_put` returns
`STORE_ERR_FULL` past what fits, before writing anything, and what was
there stays. A 4 096-byte payload needs a larger region: 4 sectors if you
store nothing else, 5 beside the base's full store; where it goes on a
unit is not decided yet (docs/DESIGN-NOTES.md, clean-1028).
`store_reset()` voids everything (a factory reset). docs/STORE-FORMAT.md
has the bytes.

## 4. Your records in RAM

Tests read state at fixed RAM addresses. The platform keeps its records
at the start of RAM (`base/firmware/platform.ld`) and keeps two places
for an engine's:

- the engine's slot, `0x01C00590`: one record of at most 64 bytes, in
  section `.beacon.engine0`;
- after the store's record, from `0x01C00870`: sections
  `.beacon.engine1` to `.beacon.engine4`, then `.beacon.engine`, in that
  order, any size.

```c
volatile struct my_record my_record __attribute__((section(".beacon.engine1")));
```

Write a linker script of your own that includes the platform's and
asserts where your records landed, so a change shows at link time:

```
/* src/my.ld */
INCLUDE platform.ld

ASSERT(my_record == 0x01C00870, "my record must follow the store's")
```

## 5. Build

```sh
sh base/tools/build.sh build --out out --platform --src src --ld src/my.ld
```

| Option | What |
|--------|------|
| `--platform` | leaves out the base's instrument (its FM engine, presets, arpeggiator, screens and saving), builds with `SB_ENGINE_EXTERNAL`, links with `platform.ld` |
| `--src DIR` | every `.c`, `.S` and `.cc` under DIR, built with the firmware's flags and `-I DIR`; repeat it for more folders (not a folder holding `base/`) |
| `--ld SCRIPT` | your linker script (in `base/` or in a `--src` folder) |
| `--define NAME` | `-DNAME` for every source (yours and the base's) |
| `--leave-out FILE` | a base source left out (`firmware/src/...`), to replace it with your own |

The outputs, in `out/`:

- `app.bin`: the raw image (linked at `0x02000000`), what fwtest and the
  app run;
- `app-pkg.bin`: the same code linked at `0x02000120`, for a `.fwsc`
  package (section 6);
- `app.elf`, `app-pkg.elf`: with symbols, for finding things;
- `app.size`: code, data, RAM and stack in bytes;
- `SHA256SUMS`.

The build is deterministic: the same sources give the same bytes, from
any folder on any machine. It refuses an object holding a store that
writes back into its own base register (`[++rN=k] = rN`, ...), as what
the chip does then is still open (R-BUILD-3); if your code trips it, the
message names the file, the function and the instruction.

## 6. Test with fwtest, run in the app

**fwtest** runs your image in an emulator of the chip, from its pinned
container image: keys, encoders, the pot and MIDI in from a script; the
screen, the audio, MIDI out, RAM and the flash chip out.

```sh
sh base/tools/fwtest run out/app.bin --ms 3000 --out out/t1 \
    --script tests/keys.txt --wav --midi-out --lcd 2500 \
    --ram 0x01c00870:64@end
```

Paths must be inside the folder you run it from (your repository's
root). docs/HARNESS.md (`base/docs/HARNESS.md`) is its manual: the script
format, every output, the flash chip's timing and power cuts
(`--flash`, `--flash-out`, `--power-cut`), golden files and suites. The
base's own tests of these seams are a working example:
`base/tools/seams_suite.py` with its test engine in
`base/tests/seams/engine/`.

**The F-Emulator app** runs the same image:

- the bare image: open `out/app.bin` in the app;
- or a package: pack the package link into a `.fwsc` and check it with
  the reader fwtest also uses:

  ```sh
  python3 base/tools/fwsc.py pack out/app-pkg.bin --version 0.1.0 \
      --identity my-firmware-0.1.0 --out out/my-firmware.fwsc
  python3 base/tools/fwsc.py out/my-firmware.fwsc
  sh base/tools/fwtest run out/my-firmware.fwsc --package --ms 2000 --out out/t2
  ```

  The identity is at most 19 characters and must not begin with another
  board's name (`fwsc.py` says which).

## 7. MIDI out

**What the base sends for you:** nothing, once you build with
`--platform`. The base's instrument sends the panel's notes, knobs and
program changes, passes MIDI thru and sends the arpeggiator's clock; all
of that is the instrument's, and goes with it. The platform only sends
what your engine queues.

**Sending your own:**

- Call `midi_start()` in your init (it turns the UART on for both
  directions) and `midi_settings_default(&midi_settings)` (the out
  channel, 1, comes from there).
- From the block callback, queue messages with `midi_out_channel(kind,
  d1, d2)` (on the out channel) or `midi_out_send(&msg)` (any status),
  and call `midi_out_poll()` once a block (twice, at the start and after
  your events, gets a message out sooner). Nothing waits for the wire:
  the queue holds 32 messages, merges a newer controller value into a
  waiting one, keeps room for note offs, and drops what doesn't fit,
  never leaving a note hanging (`midi_out.h` has the rules).
- Running status is used for you.
- Thru is yours to do, if you want it: hand what `midi_read()` gives you
  to `midi_out_send()`.

**Raw bytes** (a System Exclusive message, a dump): from your serve,
`midi_out_raw(buf, len)` streams them as they are, 12 bytes at a time
whenever the wire is free; the buffer must stay as it is until
`midi_out_raw_busy()` returns 0. Queued messages wait until the stream
has gone, except realtime ones (a clock), which go out between its
transfers so they keep their time. 4 096 bytes take 1.3 s of the wire;
the queue fills meanwhile if you keep queueing, so send little else
while a long stream runs.

On the FM-1 itself these bytes reach no socket (it has no MIDI out
jack); in the app, and on the boards that have one, they go out.

## 8. Keeping up with the base

Move `base/` to a newer commit when you want its fixes
(`git -C base pull`, then commit the submodule). The seams are meant to
stay as they are; a change to one is noted in docs/DESIGN-NOTES.md and
its requirement. Run your tests again after each update: the build and
fwtest are pinned by the base, so a result changes only when the base or
your code does.
