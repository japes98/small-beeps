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
R-STORE-12, R-BUILD-3, R-BUILD-4, R-BUILD-5).

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
- **Starting without the base's screens.** Build with
  `--define SB_NO_START_SCREENS` as well and main skips its bring-up
  screens (BR-16): it sends a black frame before the display goes on,
  shows neither the address pattern nor the test screen, and calls your
  first serve as soon as the display is on, about 130 ms after start-up
  instead of 500 (the controller's own start, 125 ms, stays).
  `sb_beacon.screen` is `SB_SCREEN_BLANK` until you set your own; there
  is no heartbeat to stop. It needs `SB_ENGINE_EXTERNAL` (`--platform`
  gives it): without it the build stops with an error.
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

How much fits: by default the store's region is three sectors (12 KiB).
With nothing else in it, it holds and rewrites one payload of up to
3 920 bytes; beside the base's own full store (its 16 user slots, the
selection and the settings) about 2.4 KB. `store_put` returns
`STORE_ERR_FULL` past what fits, before writing anything, and what was
there stays. For more, choose a larger region (below). `store_reset()`
voids everything (a factory reset). docs/STORE-FORMAT.md has the bytes.

**Where the store goes.** The store's region is yours to choose (R-STORE-12).
By default it is the three sectors at `0xFC000` to `0xFEFFF`, which the
stock layout leaves unused (HW-80); the stock firmware's user patch
region below it (`0xEA000` to `0xFBFFF`) is never touched. To choose
another, set the symbol pair `STORE_BASE` (a chip offset) and
`STORE_SIZE` (bytes) in your linker script, before it includes the
platform's:

```
/* src/my.ld */
STORE_BASE = 0x80000;     /* 16 sectors from 0x80000 */
STORE_SIZE = 0x10000;

INCLUDE platform.ld

ASSERT(my_record == 0x01C00870, "my record must follow the store's")
```

The store's code is the same in any region; it reads the pair as link
symbols (`sb_store_base` and `sb_store_size`, which `nm app.elf` shows).
The build checks the region on both links (the raw image and the
package's, whose image is 0x120 bytes longer) and prints it, here for an
image of about 110 KiB:

```
app.elf: store region 0x80000 to 0x8FFFF, 16 sectors (the image ends at 0x1F7C7)
app-pkg.elf: store region 0x80000 to 0x8FFFF, 16 sectors (the image ends at 0x1F8E7)
```

It refuses a region, saying what is wrong and where one of that size
would fit, if it:

- doesn't start on a 4 KiB sector boundary, or isn't whole sectors;
- is smaller than 3 sectors (the store's minimum) or larger than 128
  (`STORE_SECTORS_MAX`, what the store keeps track of);
- overlaps your image (it starts at chip offset `0x4000`), or the boot
  area below it;
- crosses the end of the app area at `0x94000`, or lies past it in the
  stock layout: the VM region (`0x94000` to `0xE8FFF`: it holds the
  stock firmware's settings and is where an update stages its loader, so
  a store there could be lost or break an update), the Bluetooth sector,
  the stock user patch region, or the chip's last sector (its per-unit
  key, which must never be erased).

So a region goes either in the app area after your image, or in the
unused three sectors. `0x94000` is where the stock layout's app area
ends (HW-80); the hardware facts give the app area's start but no fixed
end, so this is the conservative reading until SR-11 is answered. For
example, 5 sectors from `0x10000` with the same image:

```
app.elf: store region: the region (0x10000 to 0x14FFF) overlaps the image, which ends at chip offset 0x1F7C7: start it at 0x20000 or later
app.elf: store region: where it would fit: a region of 5 sectors fits in the app area after the image, from 0x20000 to 0x8F000 at the latest; the unused region 0xFC000 to 0xFEFFF holds 3 (the default, STORE_BASE 0xFC000, STORE_SIZE 0x3000)
FAIL: the store's region doesn't fit (above; tools/store-region.pl)
```

How large: saves are atomic, so a rewrite needs room for the old payload
and the new one beside everything else live. The rule: everything live
plus the new payload's records must fit in the region's sectors but one
(the ring keeps one free to move on), each sector holding 4 080 bytes
of records, a part's record (512 bytes for a full one) never split
across two; a 4 096-byte payload is 9 parts, 4 288 bytes as records. In
practice, from the store's model (`tools/store.py`) over random
histories:

| Region | One payload, alone: the largest | One payload beside the base's full store | 4 096-byte payloads, each rewritable: alone (beside the base's full store) |
|-------:|-----:|-----:|-----:|
| 3 sectors (the default) | 3 920 bytes | 2 444 bytes | none |
| 4 sectors | 5 396 | 4 284 | 1 (1) |
| 5 sectors | 5 904 (the most a payload takes) | 5 904 | 2 (2) |
| 16 sectors | 5 904 | 5 904 | 12 (11) |

**A worked example: 16 sectors for several 4 096-byte records.** Say your
firmware keeps eight 4 096-byte records (kinds `0x80`, ids 0 to 7: a
bank of samples, say) and rewrites any of them at any time. Today's
three sectors can't rewrite even one. Sixteen sectors (64 KiB) keep
twelve, each rewritable, so eight leaves room to grow. Put them where
your image can grow into the space below them: high in the app area,
from `0x80000` (the script above), they leave your image room to grow to
496 KiB (it starts at `0x4000`), and 64 KiB of the app area above them
free; the build will refuse the region the day the image reaches it. Everything else is as before:

```c
for (id = 0; id < 8; id++)
    n = store_get(0x80, id, rec, sizeof rec, &version);   /* at start-up */
r = store_put(0x80, id, 1, rec, 4096);                    /* from your serve */
```

A larger region costs some time at start-up: `store_init` reads every
sector, and those holding your kinds' records three times. Measured in
fwtest:

| Region | Holding | `store_init` |
|-------:|---------|-------------:|
| 3 sectors (the default) | the base's own records | 0.28 ms |
| 3 sectors (the default) | the base's records, a 10-byte and a 1 500-byte payload | 1.1 ms |
| 5 sectors | the base's records and one 4 096-byte payload | 2.2 ms |
| 16 sectors | the base's records and eleven 4 096-byte payloads | 18 ms |

It runs once: call it in your init, before the audio starts.
And a save in a nearly full region may move the ring on several sectors
(an erase each, up to 12 ms on the chip, HW-77) before it has room. Three
things to know about a region in the app area:

- It is yours from the first start: the store finds it erased (or
  holding what it holds) and formats sectors as it needs them. Moving the
  region later starts an empty store; nothing moves your data for you.
- Your own `.fwsc` package writes nothing past your image (section 6),
  but whether an update erases the rest of the app area is not yet known
  (SR-11). Until it is answered, treat a store there as surviving your
  own builds in fwtest and the app, not yet as surviving an update on a
  unit.
- The stock firmware's package covers the whole app area (`0x00000` to
  `0x93FFF`, HW-80), so returning a unit to the stock firmware erases a
  store there; the default region survives it.

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
| `--define SB_NO_START_SCREENS` | with `SB_ENGINE_EXTERNAL`: start on a black screen, without the address pattern, the test screen and their 500 ms (section 2, "Starting without the base's screens") |
| `--leave-out FILE` | a base source left out (`firmware/src/...`), to replace it with your own |
| `--cflags DIR FLAGS` | FLAGS for the C files under DIR (a `--src` folder or a folder inside one), after the firmware's flags; the base's own files never get them |
| `--cxxflags DIR FLAGS` | the same for the C++ (`.cc`) files under DIR |
| `--asflags DIR FLAGS` | the same for the assembly (`.S`) files under DIR |

**Flags for your own folders.** Your code can have flags of its own, folder
by folder, while the base's files keep the base's (R-BUILD-5):

```sh
sh base/tools/build.sh build --out out --platform --src src --ld src/my.ld \
    --cflags src "-DMY_BOARD=2 -Wno-sign-compare" \
    --cflags src/vendor/dsp "-O2 -w -Iinclude" \
    --cxxflags src "-std=c++17"
```

- A file gets the flags of every folder it is under, in the order you
  gave them, after the firmware's own (so `-O2` here replaces the
  firmware's `-Os` for `src/vendor/dsp`, and its `-w` silences the
  warnings the firmware's `-Werror` would stop on).
- `--cflags` is for `.c` files only, `--cxxflags` for `.cc`, `--asflags`
  for `.S` (which are run through the preprocessor, so `-D` works there).
- A path in `-I`, `-isystem` or `-iquote` is from the folder the flags are
  for, and is joined to it: `-Iinclude`, not `-I include`.
- Taken: `-D`, `-U`, `-O`, `-W`, `-w`, `-f`, `-m`, `-std=`, `-I`,
  `-isystem`, `-iquote`, `-g`, `-pedantic`, `-ansi`, as words of letters,
  digits and `_ = + . , / : -`. Refused, so the build stays deterministic
  and inside its container: absolute paths and `..`, `-fdebug-prefix-map`
  and its kin, `-fprofile...`, `-fplugin...`, `-Wa,`, `-Wp,`, `-Wl,`,
  and anything else (`-o`, `-c`, `-x`, `-include`, `-target`, `@file`, ...).
- Your code is built for the SDK's CPU and float, whatever its flags:
  CPU r3, with the chip's single-precision float instructions (`fprev1`,
  as the base is built) or without float instructions (`-mno-fprev1`).
  Other `-m` flags are yours. The build reads each file's flags as the
  compiler does (its `-###` reading, the same the write-back check uses),
  so `-mcpu=`, `-mfprev2`, `-msimd`, a `-target-feature` and any flag
  with the same effect are all caught, and it stops before compiling any
  of your files, naming the folder, what the flag does and the fix:

  ```
  build: --cxxflags src: src/dsp/fir.cc would be built for double-precision float (fprev2), which the SDK's flags exclude and fwtest doesn't run (from -mfprev2).
  build:   Fix: take that out of --cxxflags src. Every --src folder is built for the SDK's CPU, r3, with its single-precision float (fprev1, as the base is) or without float instructions (-mno-fprev1); other -m flags are yours to set (BR-11; docs/BUILDING-ON-SMALL-BEEPS.md, section 5).
  FAIL: a folder's flags build for another CPU or other features than the SDK's (above)
  ```

  Refused alike: another CPU (`-mcpu=r4`, even `r3s`), SIMD (`-msimd`),
  and any other feature the toolchain has. fwtest
  runs what the SDK's flags give (R-HARN-14), not these.
- `-mllvm` is refused outright (exit 2, before anything is built): it
  passes options straight to the compiler's code generator, past the
  reading above, so nothing could vouch for what it builds.
- `--define NAME` stays the way to set something for every file, the
  base's included.

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
message names the file, the function and the instruction. It reads each
object as it was compiled, with the CPU and float features your flags
gave it (`-mfprev1`, or a folder's own `-m` flags), and it refuses code
it can't read at all (`unreadable`), rather than guess past it.

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
