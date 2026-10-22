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
- First method (pull request #12): the lowest non-zero word of the stack
  captured at the end of the run, relying on fwtest's zeroed RAM.
- Experiment (our own, in fwtest through `tools/fwtest`), asked for by
  the owner after the first record showed 0: a test build whose function
  writes a 1 KiB local array and reads it back. Written with `0x5A5A5A5A`
  the mark read 1 024 bytes; written with zeros it read **0**. The
  compiler saved nothing at the frame's bottom, so the first method could
  not see stack written as zero, which is common (cleared buffers,
  counters at 0). It is replaced.
- Reasoning (the fix): `sb_stack_fill` in `crt0.S` fills the unused
  stack, from `__stack_limit` up to the current `sp`, with `0x4B415453`
  ("STAK"); the mark is the lowest word that no longer holds it. It is
  assembly because it needs `sp`, and a leaf, so it uses no stack itself
  (a call keeps its return address in `rets`). `main` calls it once,
  right after starting TIMER4: everything before the time base starts
  counts against R-BOOT-3's 10 µs, and the fill takes about 2 050
  cycles (8.5 µs), so it can't run in `_start`. After the time base
  starts it costs only a later first pass of the heartbeat loop, which the
  catch-up count absorbs (the boot suite still passes, the end within
  10 µs). Nothing before it uses the stack (below). Cost: 28 bytes of
  code, and 2 047 instructions once, +0.57% per heartbeat period. An image
  without the pattern at the stack's bottom (an older record's) is still
  read the first way, and the record says which method it used.
- Test: C-PERF-PROBES builds `SB_PROBE_STACK`, a 1 KiB frame written
  with zeros and read back, and fails unless the mark is at least 1 024
  bytes by the pattern. It reads 1 024.
- Why the firmware itself reads 0 (its disassembly, `objdump -d` of our
  own `app.elf` in the build container): `sp` is written once (`sp = r1`
  in `_start`) and read once (`r1 = sp + 0` in `sb_stack_fill`). There is
  no push (`[--sp] = …`), no pop, no `sp`-relative load or store, and no
  `sp +=` frame anywhere. `_start` calls `sb_start`, which calls `main`,
  which calls `sb_stack_fill`. Each `call` puts the return address in
  `rets`, and neither `sb_start` nor `main` returns (both `noreturn`), so
  neither saves `rets`. All their variables fit in registers, and
  `console_write` is inlined. Probe builds show the method sees the
  first real use: with `SB_PROBE_SLOW`, `main` saves `rets` before
  calling the probe, and the mark reads 4 bytes.
- Alternatives: the fill in `_start` (rejected: R-BOOT-3, above); a fill
  in C (rejected: C can't know `sp`, and would write over its own frame);
  keeping the non-zero method (rejected: the experiment).

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
    probe's hook moves with the per-beat work. A third, `SB_PROBE_STACK`,
    tests the stack measurement itself (the stack's high-water mark,
    above). The probes' code is in `firmware/src/probe.c` and three
    guarded calls in `main.c`; without the defines nothing of it is
    compiled, and `tools/build.sh --define` exists for these builds only.
- Alternatives: a golden `ipb.csv` with `rel-percent 3` (docs/HARNESS.md's
  example; for M4, when there are audio blocks); a stored per-commit
  number as the baseline (rejected: it would compare across fwtest
  versions).

### 2026-10-22 M1: clocks
- Facts: HW-11 (in fwtest the core runs one instruction a cycle at a fixed
  240 MHz and clock registers have no effect; on the chip the set-up is
  open, Q-2), HW-10 (in fwtest one bit of `SYS_DIV` releases core 1),
  HW-13 (TIMER4 counts 24 MHz).
- Reasoning: the spec allows no clock set-up on the chip yet, and in
  fwtest none is needed, so M1 writes no clock register (a guessed write,
  from register names alone, could release core 1 or misconfigure the
  chip) and asks for the procedure instead (SR-2). The clock it runs at is
  measured instead: `sb_clock_measure` (crt0.S, assembly so the
  instruction count is exact) reads TIMER4, runs 1 200 passes of a
  two-instruction loop, reads it again; between the reads are 2 402
  instructions, which at 240 MHz against 24 MHz is 240.2 ticks, so 240 or
  241 depending on where in a count the reads fall. Any other rate fails
  (R-CLK-1): 120 MHz would give 480, 480 MHz 120. The reads are 2 402
  instructions apart, never three within 64, so fwtest never treats the
  loop as waiting. Cost: about 2 400 instructions once (2.4 a period over
  the perf run's second).
- Experiment (ours, in fwtest): the boot case reads 241.
- Alternatives: setting the PLL from `WL82.h`'s register names (rejected:
  not in the spec, and no way to check it in fwtest); comparing instruction
  counts with `emulated_ms` in the tests only (rejected: the firmware would
  not know its own clock).

### 2026-10-22 M1: the tick
- Facts: HW-16 (TIMER0: `CON` bits 0-1 run it, bits 4-7 = 2 divide 24 MHz
  by 16, it interrupts on reaching `PRD` and starts again from 0, writing
  `CON` with bit 14 acknowledges; confirmed by E-3 with `PRD` 1500), HW-19
  (TIMER0 is source 4), HW-17 (the core tick timer fires every 10 ms in
  fwtest whatever `TTMR_PRD` says), HW-14, HW-15 (TIMER4 raises no
  interrupt in fwtest; TIMER5's clock select is ignored there).
- Reasoning: a 1 ms tick keeps M0's heartbeat period, the perf gate's
  unit, and is fine-grained enough for M2's screen and M3's scanning.
  TIMER0 at 1.5 MHz with `PRD` 1500 is the only 1 ms periodic interrupt
  the spec confirms; the core tick timer can't be set to 1 ms in fwtest,
  and TIMER5's clock selection is emulator-only. The acknowledge writes
  `0x4021`: bit 14 with the same run and prescaler bits, so the timer keeps
  running as configured.
- Experiment (ours, in fwtest): over one second, timed by TIMER4 at the
  handler's entry, TIMER0's 1 ms was 24 000.7 TIMER4 ticks on average with
  `PRD` 750, 1500 and 3000 alike (intervals of 24 000 and 24 001), a fixed
  surplus of about 7 core cycles a period rather than a rate error, and the
  same with an idling or a busy main loop. With the final handler every
  interval is 24 001 (jitter 0). So the tick is about 42 ppm slow against
  the time base in fwtest; on the chip it is unknown.
- So the heartbeat counts whole milliseconds of the time base, not ticks:
  each tick adds every whole millisecond that has passed since the last
  (M0d's catch-up), which stays exact whatever the tick's period does, on
  either side. Ticks are counted on the side, with the shortest and
  longest interval between two, for R-IRQ-1's period and jitter check:
  every interval within 24 000 ± 24 ticks (± 1 µs, 0.1%) and their spread
  within 24. Over a second ticks and beats then differ by at most one.
- Alternatives: counting ticks as beats (rejected: 42 ppm off in fwtest,
  and R-BOOT-3 is about the time base); the core tick timer (rejected:
  10 ms in fwtest); TIMER5 (rejected: emulator-only clock).

### 2026-10-22 M1: the vector table and handler conventions
- Facts: HW-18 (the handler of source n is the word at `0x01C7FE00 + 4n`,
  in RAM, written by the firmware; slot 126 is also core 1's start word),
  HW-20 (`ICFG00`-`ICFG31`: enable and priority, 4 bits a source), HW-21
  (both gates: `icfg` bit 8 and `sti`), HW-22 (a handler built with the
  toolchain's interrupt attribute enters and returns correctly; nesting
  only above the running priority; emulator-only), HW-3 (user mode, and an
  interrupt switches to `ssp`; emulator-only). The SDK's `hwi.h` (P-16):
  sources 0 to 2 are the debug, exception and system-call sources, and its
  `irq.h` shows the toolchain's `interrupt("")` attribute.
- Reasoning:
  - Handlers are C functions with the toolchain's `interrupt("")`
    attribute, which saves and restores what it uses (`psr`, `reti` and the
    registers it touches) and returns with `rti`; so the tick is plain C.
  - Every slot is written at startup: source 4 gets `sb_tick`, every other
    source its own 2-byte stub in crt0.S (`call sb_irq_stub_common`, 128
    in source order, 256 bytes). The common code works out the source from
    the return address the call left in `rets` and halts with a report, so
    an unexpected interrupt is named exactly, without reading any pending
    register the spec doesn't describe. The link fails if a stub isn't 2
    bytes. Slot 126 holds a stub like the others: core 1 stays parked (it
    is never released, so its start word is never needed).
  - All 32 `ICFG` words are written, so nothing a loader left enabled stays
    enabled. Only two sources are enabled: the tick at priority 1, and the
    exception source at 7. Nothing else is enabled, so nothing nests; when
    something needs to preempt the tick (M4's audio), priorities are set
    then.
  - Stacks: main runs in user mode on `sp`, interrupts on `ssp` (HW-3),
    each 2 KiB of the 4 KiB stack area, main's on top. `ssp` is set in
    `_start`, before anything could enable an interrupt.
- Experiment (ours, in fwtest): the attribute's code saves `{psr, reti}`
  and `{r5-r0}`, and a handler's `sp` was `ssp` less 32 bytes: so
  interrupts from user mode do run on `ssp`, and user mode may read and
  write `ssp` and `icfg` (HW-3, HW-21 confirmed by our own run). Every one
  of the 128 slots is checked against the image's symbols in the boot case.
- Alternatives: one shared handler for every unexpected source (rejected:
  it couldn't say which); reading `IPND0`-`IPND7` (`csfr.h`) to find the
  source (rejected: not in the spec, and fwtest may not model it); a
  supervisor-mode main on one stack (rejected: the spec doesn't say how to
  enter supervisor mode).

### 2026-10-22 M1: faults and stray interrupts
- Facts: HW-25 (the console), the halt rule of docs/HARNESS.md (a jump to
  itself with interrupts disabled), SR-1 (open).
- Reasoning: one way out, `sb_halt`: interrupts off, the reason, source
  and `reti` into the beacon, one console line of whole words,
  `HALT <stray|fault|stack> <source in hex> `, and a jump to itself, which
  fwtest reports as a halt. Nothing is resumed: a fault means the state
  can't be trusted. Sources 0 to 2 report `fault`, the others `stray`.
  - Stack guard: each stack's lowest word holds the fill pattern after
    `sb_stack_fill`, and every tick checks both. A stack that reached its
    last word is reported as `HALT stack 001` (main's) or `002` (the
    interrupt stack's), at most a millisecond later.
- Experiment (ours, in fwtest): a misaligned word load, a read of an
  unmapped address and a write to the code window all completed, the last
  two listed as unmodelled accesses; none raised source 1. An undecodable
  instruction ended the run with fwtest's own fault, exit 3, before any
  handler ran. So no deliberate CPU fault reaches our handler in fwtest:
  SR-1 asks what raises source 1 on the chip and whether fwtest can, and
  R-IRQ-5 stays open (not passed) until then. Meanwhile the suite has:
  `fault`, a test build overrunning main's stack (it halts at the next
  tick, `HALT stack 001`); `stray`, a test build raising software
  interrupt 7 (`HALT stray 07f`); and `badinsn`, the undecodable
  instruction, expected to end in fwtest's fault: a limit of the harness,
  not firmware behaviour.
- Alternatives: a fault test calling the fault handler directly (rejected:
  it would test nothing a real fault does).

### 2026-10-22 M1: idle, and timing the tests
- Facts: HW-24 (`idle` waits until something is due, and the pending
  interrupt is then taken), docs/HARNESS.md ("Time": a waiting core 0 lets
  time jump; a run is at most 1 024 instructions; captures, and the end,
  come late while it waits).
- Reasoning: everything happens in the tick handler, and `main` loops on
  `idle`, counting how often it returns. The idle count equal to the tick
  count (less the one in progress) shows the wait is really used. Waiting
  costs fwtest nothing, so instructions per period now measure work: 69.2
  in the perf run, against M0's polling loop's 358.9 (re-measured by the
  perf gate in the same run), a fall of 80.7%.
- Timing the tests exactly: with about 70 instructions a tick, one run
  of 1 024 instructions crosses 15 ticks, so captures come up to about
  15 ms late (the 1 ms capture is taken at 15 ms). The tests therefore
  check what the image recorded, not when it was captured:
  - the beacon's own time base values (consistency is exact: beats equal
    ticks divided by 24 000);
  - the tick intervals the handler measured (exact in fwtest: every one
    24 001);
  - the first tick's time, from the last tick's time base, the ticks taken
    and the shortest interval;
  - and `emulated_ms` for the end.
  The capture time bound is only a sanity check (30 ms, twice the worst
  seen).
  - A capture can land in the middle of the handler: the first runs caught
    `beats` new and `ticks` old. So the handler writes the pair twice, A
    then B, between two increments of `seq`. A capture splits at most one
    copy, so the test demands that at least one is consistent at every
    capture, and both when `seq` is even.
- Stack fill: moved to `_start`, before any C. In M1, `sb_console_write`
  is shared with `irq.c` and no longer inlined, and its disassembly saves
  `{rets, r6-r4}` on main's stack: 16 bytes used before the fill, which
  would have hidden them from the high-water mark. M0e kept the fill after
  the time base started because R-BOOT-3 then compared the time base with
  emulated time from the very start, within 10 µs; M1's end check is
  relative to the last tick instead, and the fill's 2 050 cycles (8.5 µs)
  only delay the time base's start. So the fill now comes first, covers
  both stacks whole, and `tools/perf.py` measures each from its own limit
  and adds the two (app.size's `irq_stack` says where they divide; older
  images are read as one stack). M1 uses 64 bytes in the perf run.
- Alternatives: keeping core 0 busy so captures are exact (rejected: it
  would defeat the idle wait, the point of M1).

### 2026-10-22 M1: core 1
- Facts: HW-9, HW-10 (core 1 runs only once released).
- Reasoning: nothing in M1 needs a second core, so core 1 stays parked:
  it is never released, `SYS_DIV` is never written, and every case checks
  that core 1 ran no instruction (R-BOOT-4). M4's audio may want it.
