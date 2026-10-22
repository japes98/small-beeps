<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Design notes

From M0d on, each firmware design choice is explained here: what was chosen,
the `HARDWARE-SPEC.md` facts (by their IDs) and first principles it follows
from, and the alternatives considered. A clean-room claim is stronger when
every choice can be traced to the spec and to reasoning, not to someone
else's code.

Format for each entry:

```
## <date> <milestone>: <the choice>
- Facts: HARDWARE-SPEC IDs (and PROVENANCE IDs) it relies on
- Reasoning: why, from first principles
- Alternatives: what else was considered, and why not
```

## Entries

### 2026-10-21 M0a: build flags only (no firmware yet)
- Facts: none from the hardware spec (it doesn't exist yet). PROVENANCE P-1
  (the toolchain).
- Reasoning: freestanding C11 (`-std=c11 -ffreestanding -nostdlib`) means
  the firmware brings everything it runs, so no toolchain or SDK library code
  of unknown licence ends up in our binaries. `-Os` because flash and RAM are
  small. `-g` with `-fdebug-prefix-map` keeps debug info useful without
  embedding absolute paths, so builds are reproducible.
- Alternatives: the toolchain's newlib C library (rejected: unknown terms in
  this distribution, and more than we need).

### 2026-10-22 M0d: memory layout
- Facts: HW-1 (the image runs from its first byte at `0x02000000`), HW-5
  (the code window shows the flash chip from offset `0x4000`, so at most
  1 MiB less 16 KiB), HW-6 (main RAM is 512 KiB from `0x01C00000` on the
  chip; its top holds the SDK's boot and update area and the vector table),
  HW-4 (the block r0 points to at `0x01C7FC00` in fwtest), HW-7 (fwtest has
  1 MiB of main RAM and two more banks, not known on the chip, Q-1),
  HW-18 (the vector table at `0x01C7FE00`). `firmware/app.ld`.
- Reasoning: code and constants run in place from the image (the window
  is readable and executable), so only data that changes takes RAM. RAM is
  limited to what the chip has and stops at `0x01C7FC00`: that keeps the
  r0 block (wanted later for booting on the chip, Q-11), the SDK's reserved
  area and the vector table out of reach of anything this image does,
  which R-BOOT-5's golden capture checks. Order in RAM: the beacon first,
  at a fixed address the tests name; then zeroed data; then initialised
  data, whose bytes the image carries right after the code; the stack at
  the top. The beacon and `.bss` are one contiguous range, so startup
  clears both with one loop. The linker script asserts the fixed
  addresses and that data never reaches the stack.
- Alternatives: using fwtest's larger RAM (rejected: an image that only
  fits fwtest proves less); putting the beacon in `.data` (rejected: its
  address would move whenever data is added).

### 2026-10-22 M0d: the stack
- Facts: HW-2 (every register but r0 is 0 at entry, both stack pointers
  included: no stack until the image sets one), HW-3 (core 0 starts in user
  mode; interrupts would switch to `ssp`, emulator-only), the compiler's
  data layout for pi32v2 (no type is aligned to more than 4 bytes; P-13).
- Reasoning: the first instruction sets `sp` to `0x01C7FC00`, before any C
  runs; 4 KiB is reserved below it. M0d's C uses a few words at most (the
  compiler keeps `sb_start` and `main` in registers), so 4 KiB is ample
  and cheap. The top is 8-byte aligned, more than the data layout needs,
  so nothing changes if 8-byte types arrive. Only the user-mode `sp` is
  set: M0d takes no interrupts, so `ssp` is left for M1, which must set it
  before enabling them (HW-3).
- Alternatives: a stack at the very top of RAM (rejected: it would run
  through the reserved area and the vector table).

### 2026-10-22 M0d: startup order
- Facts: HW-1, HW-2; the image layout above.
- Reasoning: `crt0.S` is the only assembly, and does only what C can't:
  set `sp` and call `sb_start`. `sb_start` (C) copies initialised data from
  the image to RAM, clears zeroed data and the beacon, and calls `main`.
  Clearing matters on the chip even though fwtest starts with RAM at zero
  (HW-7). `main` checks one initialised and one zeroed variable and writes
  the marker only if both are right (otherwise a different marker), so the
  marker proves the runtime as well as the boot. Should `sb_start` ever
  return, `crt0.S` stops on purpose with interrupts off and a jump to
  itself, which fwtest reports as a halt. r0's block pointer (HW-4) is not
  used yet.
- Alternatives: copying data in assembly (rejected: more assembly for no
  gain, as C can run as soon as `sp` is set); no zeroing (rejected: relies
  on fwtest's start state).

### 2026-10-22 M0d: the marker and the console
- Facts: HW-26 (a word at a fixed RAM address is visible through `--ram`
  and `--watchdog`), HW-25 (`DBG_MSG` at `0x01EEE244` appends each word
  written to fwtest's console; confirmed by E-2), Q-5 (the SDK marks
  `DBG_MSG` read-only, and whether it does anything on the chip is open).
- Reasoning: the beacon is four words at `0x01C00000`: the marker
  `0x44304253` ("SB0D" in memory order), the beat count, the time base
  value of the last pass, and the period. Tests read it with `--ram`. The
  console line `small-beeps M0d` is a second, human-readable sign that
  `main` ran, written as whole words (HW-25). The SDK's struct declares
  `DBG_MSG` read-only, so it is written through our own pointer at the
  spec's address; on the chip the write may go nowhere (Q-5), and nothing
  depends on it.
- Alternatives: the console only (rejected: Q-5).

### 2026-10-22 M0d: how the heartbeat is timed
- Facts: HW-12 (TIMER4's registers), HW-13 (in fwtest, TIMER4 counts at
  24 MHz once `CON` bit 0 is set; confirmed by E-3), HW-14 (its value when
  stopped and its response to writes: emulator-only), docs/HARNESS.md
  ("Time": a core that waits lets time jump, and captures can come late).
- Reasoning: no interrupts before M1, so `main` polls TIMER4. It sets
  `CON` bit 0, notes `CNT`, and then uses only differences of `CNT`, so it
  relies on nothing in HW-14; unsigned subtraction stays right across a
  32-bit wrap. One beat is 24 000 ticks (1 ms). Each pass counts every
  whole period that has passed (a catch-up loop, not one beat per pass), so
  the count is right however late a pass runs, and stores the time base
  value in the beacon. A beat count that is a pure function of the time
  base can be checked exactly: `beats == ticks / 24000`.
- Experiment (our own, in fwtest through `tools/fwtest`): fwtest treats
  this loop as waiting even though it stores to RAM on every pass: a
  100 ms run took about 36 000 instructions, and captures came 0.2 to
  1.6 ms after the time asked. The heartbeat stays right (above), and the
  stored ticks let the tests check timing regardless: each capture must
  show the right beats for its ticks, taken at most 5 ms late, and at the
  end of a one-second run the ticks must agree with fwtest's emulated time
  within 10 µs (R-BOOT-3, `tools/fw-suite.py`). That end check also
  confirms HW-13's rate on our own.
- Alternatives: a busy loop that keeps core 0 running so captures are
  exact (rejected: it would burn every cycle, and the stored ticks make it
  unnecessary); the tick timer or TIMER5 with interrupts (M1).

### 2026-10-22 M0d: emulator-only facts
- Facts: HW-3, HW-10, HW-14, HW-22 (the emulator-only entries M0d could
  touch).
- Reasoning: M0d relies on none of them. It takes no interrupts (HW-3,
  HW-22), never releases core 1 (HW-10; R-BOOT-4 checks core 1 never ran),
  and uses only differences of TIMER4 (HW-14). Every fact it does rely on
  is confirmed (HW-1, HW-2, HW-4 to HW-7, HW-12, HW-13, HW-25, HW-26), so
  no extra black-box test of an emulator-only fact is needed; the
  heartbeat's end check (above) re-confirms HW-13 independently.

### 2026-10-22 M0d: build
- Facts: P-1 (the toolchain), P-13 (our compile and link experiments).
- Reasoning: `tools/build.sh` compiles every `.c` and `.S` in
  `firmware/src/` in sorted order and links with `firmware/app.ld`.
  - `-nostdinc`: no C library headers either; `sb.h` defines the few types
    used, and the SDK's register headers are the only outside includes.
  - `-fno-common`: zeroed globals go to `.bss`, where startup clears them,
    not to common symbols.
  - `--no-undefined` and `--orphan-handling=error`: the link fails on any
    missing function (such as a compiler helper we don't provide) and on
    any section the script doesn't place. M0d needs no compiler helpers.
  - Assembly is built without `-g`, which would record the source path.
  - The raw image is the `.text` section then the `.data` section, each
    extracted with `objcopy` and joined: this `objcopy` takes one section
    per run, and `ld --oformat binary` resolved a data address wrongly in
    a trial (`0x01C00000` for a variable at `0x01C00014`). The build checks
    the joined image's length against the layout's.
  - `app.size` (code, data, bss, image, stack) is a build output, so the
    record carries it (C-FW-SIZE). First size: code 252, data 4, bss 20,
    image 256, stack 4096 bytes.
  - Objects are built in the container's `/tmp`, so the outputs are just
    `app.bin`, `app.elf` and `app.size`.
- Alternatives: `ld --oformat binary` (rejected, above).
- `firmware/src/placeholder.c` is removed: nothing uses it any more.

### 2026-10-22 M0e: what is measured, and where
- Facts: docs/HARNESS.md ("Time": one instruction of core 0 is one cycle,
  waiting costs almost no instructions; "Outputs": `result.json`'s
  instruction counts; RAM all zero at the start), the layout in
  `firmware/app.ld` (the beacon at `0x01C00000`, the stack's top at
  `0x01C7FC00`).
- Reasoning: `tools/perf.py` (check C-PERF) measures every build A:
  - size from `app.size`: code, data, bss, the raw image, the stack
    reserved; static RAM is data plus bss;
  - a one-second run of its own in fwtest, with fixed, minimal options:
    `--ms 1000`, the beacon and the whole stack captured at the end, no
    watchdog and no other captures. Captures change when fwtest looks at
    a waiting core 0, and with that the count, so the perf run is kept
    apart from the boot suite, where captures are added freely;
  - speed: core 0's instructions in that run divided by the beats the
    beacon shows at its end: instructions per heartbeat period. This is
    the stand-in R-PERF-2 tracks until audio. In M4 the period becomes the
    audio block (fwtest's `--ipb`), and `PERIOD` in `tools/perf.py`
    changes with it.
- What the stand-in measures today: mostly the heartbeat's polling loop as
  fwtest schedules a waiting core (M0d's entry "how the heartbeat is
  timed"). An experiment adding 20 volatile loop passes per beat raised
  the count from 356.9 to 439.5 per period: more work shows, but less than
  its own cost, because fewer polling passes fit. Until M1 replaces
  polling with interrupts and waiting, read the number as "the loop plus
  the work per beat", not as work alone.
- Alternatives: the heartbeat case of `tests/fw/boot.suite` (rejected:
  its captures and watchdog would make the count move with the tests);
  counting from the start of `main` (not possible: fwtest gives one count
  per run).

### 2026-10-22 M0e: the stack's high-water mark
- Facts: docs/HARNESS.md (main RAM is all zero when the image starts),
  `firmware/app.ld` (4 KiB of stack below `0x01C7FC00`), R-BOOT-3 (the
  time base must agree with emulated time within 10 µs at the end of a
  one-second run, so everything before `main` starts the timer counts).
- Reasoning: the whole stack is captured at the end of the perf run, and
  the lowest non-zero word marks the deepest the stack ever went. No
  firmware change is needed. It can read too low only if the deepest
  words ever written were all zero; a frame that saves a return address or
  a register usually leaves something non-zero at its bottom.
- M0d's firmware uses no stack at all: `crt0.S` sets `sp`, and the
  compiler keeps `sb_start` and `main` in registers (a call keeps its
  return address in a register, not on the stack; seen in the
  disassembly). The mark is 0 bytes.
- Alternatives: filling the stack with a pattern in `crt0.S` before
  `sb_start` (rejected for now: at two instructions a word, 4 KiB takes
  about 2 050 cycles, 8.5 µs, most of R-BOOT-3's 10 µs before the timer
  starts, and it would grow with the stack); a fill in C (rejected: it
  would write over its own frame).

### 2026-10-22 M0e: the gates and their tests
- Facts: none from the hardware spec.
- Reasoning:
  - Budgets: `config/budgets.json` names the milestone whose budgets are
    in force, and each budget (code, static RAM, stack high-water) must
    hold. M0's: code 512 bytes (252 used), static RAM 64 (24), stack
    high-water 256 (0). About twice what M0 uses, so small fixes fit, and
    M1 sets its own in a pull request of its own.
  - Speed: instructions per period may rise by at most 3% against the
    latest record of a main commit. The baseline's own `app.bin`, kept in
    every record's `outputs/`, is run again with this checkout's fwtest
    and options in the same check, so a new fwtest image or new options
    never pass for a change of the firmware. Integers are compared exactly
    (a rise of exactly 3% passes). A fall of more than 3% is reported as
    IMPROVED, in the record and in the CI run's summary on the pull
    request. CI finds the baseline on the `records` branch, and fails if
    it can't read the branch; a clean folder, which may not have the
    records' files, says "no baseline" and compares nothing.
  - Tests of the gates (C-PERF-PROBES): the firmware built with
    `SB_PROBE_SLOW` (20 volatile loop passes per beat) must fail the speed
    gate and nothing else; built with `SB_PROBE_BIG` (a 1 KiB table, 256
    bytes of zeroed data, a 512-byte stack frame) it must fail each of the
    three budgets, and nothing else. Both are measured against the
    unmodified build in the same run, not against the records branch, so
    they test the gates whether or not a baseline exists. The bigger
    probe's budgets are the unmodified build's own sizes, not
    `config/budgets.json`'s, so raising a budget (M1 will) never makes the
    probe pass; the slower probe's budgets are its own sizes, so only its
    speed is under test. When M1 replaces the polling heartbeat, the slow
    probe's hook moves with the per-beat work. The probes' code is in
    `firmware/src/probe.c` and two guarded calls in `main.c`; without the
    defines nothing of it is compiled (the image is byte for byte M0d's),
    and `tools/build.sh --define` exists for these builds only.
- Alternatives: a golden `ipb.csv` with `rel-percent 3` (docs/HARNESS.md's
  example; for M4, when there are audio blocks); a stored per-commit
  number as the baseline (rejected: it would compare across fwtest
  versions).
