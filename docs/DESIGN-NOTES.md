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
- Experiment (ours, in fwtest): the boot case reads 240 (241 in an earlier build whose reads fell elsewhere in a count). The counter's address comes from C (the SDK's `JL_TIMER4`), so the assembly holds no address.
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

### 2026-10-22 M2: speed in two parts, startup and steady state
- Facts: docs/HARNESS.md ("Time": instruction counts leave out the time a
  waiting core 0 skips; a run's end comes late while the image idles);
  the owner's decision in session M2 (R-PERF-2).
- Reasoning: until M2, speed was one one-second run's instructions over its
  beats, so one-off work at startup counted as if it were per-period work.
  M2 draws the whole screen at startup, hundreds of thousands of
  instructions, which against M1's 69.2 a period would fail the 3% gate
  by design while the per-period work hardly changes. So `tools/perf.py`
  runs each image twice, for 1 250 and 2 250 ms, and takes:
  - steady state: the longer run's instructions less the shorter's, over
    the beats gained between their ends;
  - startup: the shorter run's instructions beyond its beats at that rate.
  Both get a budget per milestone, raised only by their own pull request.
  The 3% gate applies to steady state only, and only against a record
  made under the same steady-state budget: raising that budget is the
  deliberate, reviewed way to accept more work per period.
- Why 1 250 and 2 250 ms: the window between them is one whole second
  long, and both ends are at least 50 ms from a whole tenth of a second
  (a test checks this). Work timed on whole seconds or tenths (M2's
  heartbeat on screen) then falls inside the window whole, never at its
  ends, even though an end comes up to about 30 ms late while the image
  idles. Measured on M1's firmware: the ends came at 1 263.074 and
  2 255.115 ms, 992 beats apart; steady state exactly 64.000 a period
  (the probes' windows, 1 003 and 1 008 beats, gave the same), startup
  5 193 instructions. M1's old figure, 69.2, was the two mixed.
- M1's new budgets: startup 8 192 instructions, steady state 72 a period
  (about 58% and 12% above what M1 measures; the 3% gate, not the budget,
  catches small rises).
- The probes: the slower build must fail the speed gate and the
  unmodified build's steady state as its budget; the bigger build (whose
  extra work runs at startup) must fail each size budget and the
  unmodified build's startup as its budget.
- perf-history.csv keeps its header (its writer refuses any other, and it
  is never rewritten), so its instruction columns now hold the steady
  state, and its `period` column says `heartbeat-steady` from M2 on.
- Alternatives (the owner chose among them): resetting the baseline when a
  milestone's firmware first lands (it hides the startup cost from every
  gate); steady state alone with no startup budget (startup could then
  grow unchecked); one absolute budget for the mixed measure (startup
  would hide per-period regressions).

### 2026-10-22 M2: bringing up the panel
- Facts: HW-27 (an ST7789V-family controller, 16-bit pixels), HW-29 and
  HW-30 (bytes through `BUF`, DMA through `ADR` and `CNT`, PC8 for data or
  command), HW-31 (the commands fwtest acts on), HW-32 and the datasheet
  (P-22: 5 ms after `SWRESET`, 120 ms after one sent in sleep mode before
  `SLPOUT`, 5 ms after `SLPOUT`; `0x3A` `0x55` for 16-bit pixels;
  `MADCTL`'s bits, page 215).
- Our sequence (`lcd_init`, then `main`): software reset; 120 ms, because
  after power-up the controller is in sleep mode, which covers the 5 ms
  too; sleep out; 5 ms; 16-bit pixels; `MADCTL` 0 (rows top to bottom,
  columns left to right, not exchanged, refresh top to bottom, RGB order);
  the first whole frame (the address pattern) while the display is still
  off, so nothing undefined is ever shown; display on. Each delay is
  waited on the tick (`sb_wait_ms` waits one beat more than asked, since
  the first may be nearly over), so it holds on the chip too, where
  fwtest doesn't check it. The 125 ms cost nothing in instructions: the
  core idles.
- What is left out, and why: the panel's reset pin, backlight pin, SPI1's
  clock, mode and pins, and the panel's offset in the controller's
  240 x 320 memory are unknown (Q-6; SR-3 asks). Writing guesses would
  either touch registers fwtest doesn't model (every case fails on an
  unmodelled access) or set the chip up wrongly. `SPI_CON` in `lcd.c` is
  the one place their bits will go. Display inversion isn't sent: whether
  this panel needs it is part of Q-6, and fwtest shows pixels as written
  either way (HW-31). Only bit 8 of `JL_PORTC->OUT` is ever changed, by
  read-modify-write, so M3 can share the port.

### 2026-10-22 M2: the frame buffer and sending it
- Facts: HW-29 (DMA from RAM; a finished transfer can raise source 16;
  E-5 confirms 480-byte transfers), HW-31 (pixels high byte first,
  filling the window row by row), HW-6 (512 KiB of RAM on the chip),
  HW-19 and HW-20 (source 16, priorities).
- Layout: one buffer of the panel's 240 x 240 pixels, row by row from the
  top left, each pixel's RGB565 colour stored high byte first: exactly the
  bytes the panel takes after a memory write, so any run of whole rows is
  one contiguous block DMA can send as it is, with no conversion and no
  copy. 115 200 bytes, in `.bss` (cleared at startup like any zeroed data,
  about 58 000 instructions; the pattern then writes every pixel).
- Sending (`lcd_send_rows`): the window (column and row address set),
  memory write, then the rows by DMA. Up to 16 rows (7 680 bytes) go as
  one transfer whose end the next command polls; more go as a chain of
  16-row chunks, each started by SPI1's interrupt (source 16) when the
  one before ends, so the core is free while a frame goes out. A whole
  frame is 15 chunks. 16 rows is a guess at a safe transfer length: E-5
  confirms 480 bytes, and the chip's limit on `CNT` is asked in SR-3.
- The tick is above SPI1 in priority (1 against 0), and nothing nests, so
  a tick waits at most for one SPI1 handler: about 40 instructions, well
  inside the ±24 time base ticks (240 cycles) the tick's timing allows.
  The flood test (R-LCD-5) sends whole frames back to back for a second:
  every interval stays 24 001 or 24 002.
- Cost: in fwtest a transfer finishes at once (HW-29), so a whole frame
  is only the core's work: 6.3 µs from the window to the last chunk
  started (about 1 000 instructions), recorded as `frame_update_us`. On
  the chip the bytes take time: at the datasheet's fastest serial write
  (66 ns a bit, page 43) a whole frame is at least 921 600 bits, 60.8 ms,
  during which the core is free; the real figure waits for SPI1's clock
  (SR-3).
- fwtest raises source 16 at the end of every DMA transfer while the
  source is enabled, bit 13 or not (our experiment, P-20); HW-29 says bit
  13 enables it. So the handler acknowledges a transfer it didn't chain
  (the polled one) and marks it done, which is right under either
  behaviour; SR-3 reports the difference.
- `lcd_wait` spins rather than idling: an interrupt ending the last chunk
  between the test and an `idle` made the core sleep until the next tick,
  once a frame (the flood test found it: 999 frames a second instead of
  over 200 000). Only a command that must follow a frame still going out
  ever waits.
- Alternatives: 8-bit colour with a palette (57 600 bytes, but every pixel
  converted on the way out, so no straight DMA); two buffers (twice the
  RAM, for tearing-free updates M2 doesn't need); sending a dirty
  rectangle row by row (a transfer per row; the heartbeat is cheaper as
  whole rows, one transfer).

### 2026-10-22 M2: drawing, and our own font
- Fill and frames write two pixels a word where they can; lines step one
  pixel along the longer axis and move along the other when the
  accumulated error passes half a pixel; text writes every pixel of each
  character cell (glyph and background), so text needs no clearing first.
  Everything is clipped to the screen.
- The font is ours (P-21): printable ASCII on a 5 x 8 grid in a 6 x 8
  cell, capitals and digits in rows 0 to 6, descenders in row 7. It is
  written in `font.c` as rows of `#` and `.`, which the compiler folds
  into one byte a row (760 bytes), so anyone can see each glyph in the
  source. Characters outside it draw as a filled box.

### 2026-10-22 M2: the screens, and what they prove
- The address pattern (first): red = column / 8, green = row / 4, blue =
  (column mod 8) x 4 + row mod 4. No two pixels share a colour, so
  fw-suite.py decodes fwtest's capture and checks every one of the 57 600
  pixels against the formula: orientation, colour order and every pixel's
  address at once (R-LCD-2).
- The test screen (from 500 ms): a white border on every edge pixel;
  12 x 12 corner squares, red top left, green top right, blue bottom left,
  yellow bottom right, each named beside it; red, green and blue ramps
  (32, 64 and 32 steps from 0); a box with diagonals and a cross of lines;
  every glyph of the font; the title; the heartbeat. fw-suite.py checks
  the border, corners and ramps pixel by pixel on its own (a mirrored,
  upside-down or BGR picture fails), and the whole picture against a
  golden image (R-LCD-3).
- Captures come late while the image idles (up to about 15 ms here), so
  each screen stays up for hundreds of milliseconds around its capture
  times (300, 800 and 1 500 ms), and the heartbeat changes only on whole
  seconds.

### 2026-10-22 M2: the heartbeat on screen, within 3% a period
- The heartbeat's seconds, five digits at twice the font's size, are
  drawn when a second is up, and only their 16 rows are sent, as one
  transfer: 5.75 µs of the core a second. Only the digits that change are
  drawn again.
- Finding the second without costing a period anything: `main`'s idle
  loop counts its wakes in a register (one a tick: in steady state nothing
  else wakes it) and compares with the next second's count. That is three
  instructions a period, as M1's loop (`idle`, a memory increment, a jump)
  was; a first version that stored the count every time cost one more,
  64 to 65 a period, which with the heartbeat's drawing went over the 3%
  gate (+3.9%). The count goes to the beacon once a second with the ticks
  taken then, so R-IRQ-1 is still checked exactly.
- Result: steady state 65.415 instructions a period against M1's 64.000
  (+2.2%): the heartbeat's drawing and sending, about 1 400 instructions a
  second. Startup 1 036 288 (the two screens and clearing the buffer).

### 2026-10-22 M2: the tests' timing
- The two heartbeat cases differ only in length (1.25 and 2.25 s), so
  their difference is the steady state, as in perf.py; R-IRQ-1's 100
  instructions a tick is checked there, since the whole run's count is now
  mostly startup.
- Startup clears `.bss` before `main` starts the time base, so the time
  base starts about 0.24 ms after fwtest's clock (it was 8 µs). The end
  check's slack now grows with the image's `.bss` (at most 3 cycles a
  word: 2 measured), from `app.size` (P-20).
- The screen case captures the beacon with each picture; the beacon's
  `shown` seconds must equal the heartbeat's whole seconds (R-LCD-4).

### 2026-10-23 M3: the first record under a raised budget is no baseline
- Facts: R-PERF-1 and R-PERF-2 (a budget is raised only by a pull request
  of its own; the 3% gate compares steady state against the latest main
  record made under the same steady-state budget).
- The problem: M3's scanning costs hundreds of instructions a period, so
  its steady-state budget is raised first, in its own pull request. That
  pull request's merge gets a record under the new budget that still holds
  M2's firmware (about 65 a period). As the latest record under the same
  budget, it would be the firmware pull request's baseline, and the gate
  would fail it by design, by about a thousand percent.
- The owner's decision (session M3): `tools/perf.py` does not compare
  against the first record made under a steady-state budget, the one whose
  own baseline's record was made under another budget or none. The change
  is still reported (NOT COMPARED, with the figures and why), every budget
  still holds, and the record after it is a baseline again, so only the
  first firmware after a raise goes ungated, and the raise itself was
  reviewed in its own pull request.
- Alternatives: raising the budget and the firmware in one pull request
  (against R-PERF-1's rule); keeping the old budget active until the
  firmware lands (the firmware would fail the old budget); comparing
  firmware images to spot a budget-only merge (more machinery for the
  same answer).

### 2026-10-23 M3: scanning the panel
- Facts: HW-33 (11 columns through two cascaded shift registers on PA1,
  PA3, PA4; a column selected while its bit is 0), HW-34 (6 rows on PA0,
  PA5-PA8, PB7, 0 while closed), HW-35 to HW-39 (where each key and
  encoder contact is), HW-42 (an LED lit while its column is selected
  and its row's LED line, PA9, PA10, PH6 or PH9, is high), HW-48 (TIMER0
  to TIMER3, prescaler setting 2, the acknowledge restarts the count),
  HW-19, HW-20, HW-22 (sources and priorities); `WL82.h`'s port, timer
  and ADC structs (P-24).
- The scan (`input.c`): TIMER1 interrupts every 83.3 µs (125 counts of
  1.5 MHz), 12 slots a millisecond. In slot k (0 to 10) column k is
  selected and its LEDs lit; slot 11 selects none. Each interrupt:
  - acknowledges first, so the period stays 125 counts plus about one
    time base tick;
  - reads the rows of the column the slot before selected, which have
    had the whole slot to settle;
  - selects the next column with one shift and one latch: a single 0 is
    shifted in before column 0 and walks one place a shift (each shift
    moves every bit up one), and the shift after column 10 leaves no
    column selected. The 16 bits are loaded with ones once at start,
    since their state at power-up is unknown. The LED lines go low before
    the shift and latch and high after, so no LED is lit on the wrong
    column;
  - then works on what it read.
- Why 12 slots a millisecond: the LEDs share the columns, so every column
  must have the same time selected (a burst of all columns at once would
  leave one column lit almost all the time). An encoder's contacts change
  2 ms apart in fwtest (HW-38), and each encoder's two contacts are in
  neighbouring columns, so a whole scan must come well inside 2 ms; 1 ms
  sees every state twice.
- Priorities: the tick stays at 1, the scan is at 0 with SPI1, so by
  HW-22 (emulator-only) the tick may preempt the scan. What was measured:
  with all seven encoders turning, a chord and a pot sweep, every tick
  interval stayed 24 001 or 24 002 time base ticks. That doesn't tell
  preemption from slots short enough not to matter; either way the tick
  kept its timing. Nothing
  the tick and the scan share needs a lock: both only add to `sb_work`,
  and main reacts to any change of it.
- No pin is set up (directions, pull-ups, drive): fwtest needs none and
  the chip's are open (Q-7), and a write to a register fwtest doesn't
  model would fail every case. The scan owns PA1, PA3, PA4, PA9, PA10,
  PH6 and PH9, and keeps the ports' other bits as they were at start.
- Inputs are served from main's idle loop, which starts after the test
  screen at 500 ms. Events before then wait in the queue (64), and the
  tests start their inputs at 700 ms.

### 2026-10-23 M3: keys, and what the matrix can tell apart
- Debounce: each column keeps its last 4 readings of its key rows, a
  byte each in one word. A key's state changes when all 4 agree and
  differ from it, so a change is reported in the 4th scan that sees it:
  2.8 to 4.1 ms after the contact settles (measured), and a bounce or a
  glitch shorter than 3 ms is never reported. When all 4 readings equal
  the state, a slot spends one compare on its column's keys.
- What it can tell apart in fwtest: every key on its own, any number held
  at once (each reported), keys held in the same columns as turning
  encoders (the encoders still count exactly), and three corners of a
  rectangle in the matrix with no ghost at the fourth (keys 5, 34 and 11
  held: key 35 never appeared). So fwtest models a matrix with a diode per
  key, or none of the cross-currents a plain matrix has.
- What it can't, and what the chip may do: whether the board has diodes
  is part of Q-7. Without them, with three corners of a rectangle held,
  selecting the fourth corner's column connects its row to that column
  through the other three keys, and the fourth key reads closed whether
  or not it is pressed: a ghost no scan can tell from a real press. The
  outcome also depends on how strongly the shift registers drive the
  columns that are not selected (open). If the board has no diodes, the
  fix is in `keys()`: a new press that would complete a rectangle of held
  keys is held back until one of the others is released. That is not
  written now, because fwtest cannot show the case. Also not told apart:
  a press and release within 3 ms (debounce), and the order of two
  changes in different columns within one scan (each is stamped with the
  slot that saw it).

### 2026-10-23 M3: encoders, the pot and the LEDs
- Encoders: decoded from their contacts with no debounce. Each odd column's
  slot has both of an encoder's contacts (A read one slot earlier). A
  table turns each change of (A, B) into +1 along clockwise's order (B
  closes, A closes, B opens, A opens: HW-38), -1 against it, or 0 for no
  change or both at once. Back at rest (both open), at least +2 is a
  detent clockwise and at most -2 one the other way, so one missed or
  bounced state still counts right, and a bounce that goes back counts
  nothing. One event per detent, at its last change, 0.6 to 1.1 ms after
  it.
- No acceleration in the input layer. fwtest turns every detent at one
  speed (8 ms), so it couldn't test a curve, and engines want different
  curves. Each event carries its time, so a consumer can scale by the
  time since the previous detent; a shared helper can come when two
  consumers need the same curve.
- The pot: read once a scan, in the blank slot, by polling. The interrupt
  (HW-60, confirmed in fwtest by SR-3 since; HW-41 before) is not needed:
  the scan already comes once a millisecond. A conversion started in one
  scan is read in the next, which gives the chip time to convert (fwtest
  converts at once). The mean of the last 4 readings is reported when it
  moves more than 3 from the last value reported, or reaches 0 or 1023,
  so both ends are reachable however the dead band falls. A reading
  wandering by 2 either side gives no event. A step gives up to 4 events
  as the mean moves, the first within 0.9 ms and the new value within
  3.9 ms.
- LEDs: lit with their column, so fully on is 1 slot in 12, 83.3
  thousandths of the time in `leds.csv`. Brightness is lit in n of 8
  scans (n = 0 to 8 from levels 0 to 255), spread out in bit-reversed
  order so a half-lit LED flickers at 500 Hz, not 125. `input_led` writes
  8 words (one per scan of the 8), each holding both ports' LED bits for
  one slot. The scan reads one word a slot. A test build measured every
  step within 1.2 thousandths of n/8 × 83.3. One `leds.csv` sample's
  share varies with where its interval falls in the scan, more so when a
  sample comes late while the core idles, so the keys test checks the
  mean share over a hold, and that every sample in it is lit.

### 2026-10-23 M3: the input API
- `firmware/src/input.h` is the API later milestones and other engines
  build on, kept small:
  - `input_read(&e)`, one event at a time from one queue;
  - `input_value(control)`, the state now;
  - `input_led(control, level)`.
  An event is 8 bytes: control, kind (press, release, turn, move), a
  signed value (1 or 0, ±1 a detent, the pot's 0 to 1023), and its time
  in time base ticks (24 a µs) since main started the time base. The
  time wraps every 178.9 s, so consumers compare times by difference.
- Control IDs are named after the printed labels (HW-36) and fixed:
  - the 14 buttons are 0 to 13;
  - the 27 keys are `INPUT_KEY1` to `INPUT_KEY27`, left to right, 14 to
    40, with aliases for the ten second labels of the raised keys
    (`INPUT_KEY_OP1` and so on). The raised key `GLO` is `INPUT_KEY_GLO`,
    apart from the button `INPUT_GLO`; the 16 lower keys have no label of
    their own;
  - the knobs are 41 to 48, `MASTER` (the pot) first.
  The buttons' and keys' IDs equal fwtest's key numbers (HW-37), but the
  knobs' don't follow fwtest's encoder numbers. If the board's wiring
  turns out different (Q-7), only `input.c`'s tables change.
- The queue holds 64 events. When full, new events are dropped (the
  oldest kept) and counted, since the oldest ones are what a consumer is
  about to read. Every event is also logged, with counters and every
  control's value, in the input record right after the beacon
  (`0x01C00060`, 1 264 bytes), for the tests.
- Main reacts to `sb_work`, which the tick changes at each whole second
  and the scan with each event. Its idle loop now wakes 13 times a tick
  (the tick and 12 slots). A wake that finds nothing costs about 6
  instructions, against M2's 3, and the heartbeat's seconds are counted
  by the tick, not by counting wakes.

### 2026-10-23 M3: the panel screen
- From the first event on, the panel screen replaces the test screen:
  - the 14 buttons as labelled boxes, filled while held;
  - the 8 knobs by name, with the encoders' positions and the pot's
    value and bar;
  - the 27 keys as a keyboard, 16 lower keys with the 11 raised keys
    over them in groups of 3, 2, 3, 2 and 1 (HW-36);
  - the last event;
  - the heartbeat, in the same place as on the test screen.
- Until a control is touched the screens are M2's, so M2's tests and
  timing stand, and the perf runs (no input) measure scanning, not
  drawing.
- Each event lights or darkens its LED first, then redraws only what it
  changed and sends only those rows: a button's 13 rows, a knob's 8, the
  keyboard's 52 as a chain, and the event line's 8.
- From an event to its LED: main set every LED within 1.0 µs of its
  event's time stamp. A test build (`SB_TEST_LED_SHOW`), whose scan stamps
  when it first drives an LED just set, measured at most 0.916 ms more
  over the keys script. The event is decided in the slot after its
  column's, so its LED waits about 11 slots for that column to come round
  again: 0.917 ms from event to LED at most, within one scan.

### 2026-10-23 M3: which fwtest number is which control, confirmed
- The keys case presses each of fwtest's keys 0 to 40 alone. Each gave
  exactly one press and one release for the control at the contact HW-35
  gives, and lit only the LED with its number. The encoders case turns
  each of encoders 0 to 6 one detent each way, and each gave its control
  (HW-39), +1 for `+`.
- So fwtest's numbers, the matrix contacts, the LEDs and our IDs agree,
  by our own black-box test. Which printed label each number is (HW-37,
  HW-39, HW-61) comes only from the emulator model. fwtest has no labels
  to test it against, so it is to be confirmed by hand on the app's
  panel screen: press each control and see its name.

### 2026-10-23 M3: what scanning costs, and cheaper ways considered
- Measured in fwtest with builds that leave one part out (`SB_COST_NO_*`
  in `input.c`; P-25), in instructions a 1 ms period, steady state at
  rest:

  | Part | Instructions a period |
  |------|-----------------------|
  | the M2 firmware, with the tick's new second check | 69.5 |
  | the scan's fixed cost: 12 interrupt entries and exits, acknowledges, row reads, column select, the slot count, and main's 12 extra wakes | 533 |
  | keys (debounce check per column) | 127 |
  | encoders (contact check per odd column) | 94 |
  | the pot (one reading and filter a scan) | 27 |
  | LEDs (one table word and two port writes a slot) | 142 |
  | total | 992 |

  Against M2's 65.4. On the chip that is 0.41% of core 0 at 240 MHz.
  Packing both ports' LED bits into one word and keeping this scan's row
  of them saved 21 a period. The compiled slot is about 80 instructions,
  so a large saving needs fewer interrupts, not tighter code.
- A slower scan: at 1.5 ms (8 slots a millisecond) the cost falls by about
  a third, but:
  - key latency becomes 4.5 to 6 ms, past R-KEY-2's 4.5;
  - an encoder state of 2 ms is seen once instead of twice, leaving no
    margin;
  - LED refresh falls to 667 Hz.
  At 2 ms or slower, encoder states can be missed. Not clearly better.
- Interrupt-driven scanning (no scan while nothing happens): the spec
  gives no pin-change interrupt, so a press can't wake the core. The LEDs
  need the scan whenever one is lit, and a turning encoder needs a sample
  every 2 ms. It would be possible only if the chip has pin-change
  interrupts (a spec request), and only while every LED is dark and
  nothing is held. Not possible now.
- A burst scan while every LED is dark (all 11 columns in one interrupt a
  millisecond) would save about 11 interrupts and 11 wakes, an estimated
  400 a period, but only then. It would add a second scanning path to
  test, and rows would get far less time to settle between columns on the
  chip (unknown, Q-7). Not clearly better: left as an option for when the
  board's timing is known.

### 2026-10-23 M3: the tests' timing
- Latency is measured exactly, by letting the firmware stamp its own
  times (docs/HARNESS.md, "Getting exact timing"):
  - each event carries the time base count of the slot that decided it;
  - the input record keeps the longest delay from an event to main's
    `input_led`.
  A stamp counts from when main started the time base, which is up to
  the start slack (R-BOOT-3, about 0.38 ms with this `.bss`) after
  fwtest's zero. So each latency is checked as a range: from the script's
  time of the change to the stamp, plus 0 to the slack. A limit holds
  only if the whole range is inside it.
- Golden lists hold each case's events as control, kind and value, never
  times, which move with any change of code. Several controls changing
  at once (a chord) are decided in one scan in the order of their
  columns from wherever the scan was, which also moves with the code, so
  such a run is compared sorted; one control's events keep their order. The panel screen's golden
  image is captured at 1 030 ms, long after its events, and
  `leds.csv` is checked with bounds rather than a golden file.

### 2026-10-23 M3: the pre-raise image is no baseline (replaces the first-record rule)
- What happened: after the M3 budgets merged (#41), the owner merged the
  barrier tools' change (#43) before the firmware (#42). #43's record runs
  M2's firmware under the M3 budget and is not the first record under it,
  so under the first-record rule it would have gated the firmware at +3%
  against M2's 65 a period. It didn't, by luck of timing: #43's records job
  ran before the records of the merges before it were written, so its own
  baseline was still a record under the old budget, and it looked first.
- The owner's rule: a main record is a speed baseline only if its firmware
  image differs from the image of the last record before the current
  steady-state budget was raised. `tools/perf.py` walks main's records
  newest first down to the last one made under another budget (the
  pre-raise record), skips every record under the current budget whose
  image has that record's SHA-256, and names them in the baseline note
  (`choose_baseline`). It reads only each record's own budget and image,
  never which baseline that record happened to use, so the order records
  are written in no longer matters.
- What it gives: before the firmware merges, the baseline falls back to
  the pre-raise record, under another budget, so the change is reported
  and not gated; after it merges, the firmware's record (and any later
  record holding its image) is the baseline, gated at 3%. A revert to the
  pre-raise image under the raised budget is skipped too, since it runs
  the firmware the raise wasn't for.
- Tests: an unrelated merge between the raise and the firmware, records
  written out of order, and the firmware's record as the next baseline,
  in a made-up repository and records branch.

### 2026-10-23 M4: the polled transfer's interrupt path removed
- Facts: HW-59 (from fwtest 0.2.0, a transfer that finishes while SPI1's
  `CON` bit 13 is clear raises nothing), Q-15 (the chip, open).
- What was there: M2 found fwtest raising source 16 at the end of every
  transfer, bit 13 or not, so `lcd_spi_done` also acknowledged a polled
  transfer it hadn't chained (M2, "the frame buffer and sending it").
  fwtest 0.2.0 fixed that (SR-3), and the firmware no longer gets that
  interrupt.
- Evidence that the path is unused: a build whose path halted instead
  (`HALT stray 010`) passed the whole fw suite, every case with the
  outcome expected, the flood test (whole frames back to back for a
  second, polled and chained transfers), the keys, chords, encoders and
  pot scripts with the panel screen's partial updates, and the screen
  cases. So the branch is gone, and the handler only chains.
- On the chip, too: every polled transfer starts with a `CON` write that
  clears bit 13 and acknowledges anything pending, and every chain
  starts with one that acknowledges before setting bit 13, so whichever
  way Q-15 is answered, no polled transfer raises source 16.

### 2026-10-23 M4: the audio output
- Facts: HW-43 (`JL_ALNK0`'s registers, source 11), HW-44 (the buffer at
  `ADR3`, two halves of `LEN` words, left and right alternating, 24-bit
  signed samples sign-extended), HW-45 (`CON0` bit 11 runs it, a frame
  every 544 ticks of 24 MHz, bit 15 the half playing, `CON2` bit 7 a half
  finished and bit 3 its clear, source 11 per half), HW-46 (fwtest reads a
  half when it finishes), HW-19 and HW-20 (the source, its priority), the
  SDK's `WL82.h` (`JL_ALNK0`'s struct). Q-9 (the chip's codec, bits, clock
  and true rate) is open, so nothing here sets up a clock or a codec.
- **Rate:** 24 MHz / 544 = 44 117.647 Hz, the only rate HW-45 gives.
  fwtest's WAV header says 44 100 Hz; every pitch and every measurement
  uses the true rate (taking 44 100 would put every pitch 0.69 cents off).
- **Block:** 64 stereo frames (`LEN` 128), 1.451 ms: 348 160 cycles of core
  0. The buffer is two blocks, 1 KiB. When half h finishes, the other
  starts playing and the engine refills h, which plays next: a sample
  computed now plays one to two blocks later (1.45 to 2.90 ms), and an
  input event waits at most one block for the next refill, so from an
  event's time stamp to its sound is at most two blocks (measured: 1.6 to
  2.9 ms, R-AUD-6). From a key's contact, add M3's debounce (2.5 to
  4.5 ms): measured 4.8 to 6.8 ms. 32 frames would halve that and double
  the interrupts and their fixed costs; 128 would double it. 64 is
  below the 10 ms a player feels on a keyboard, with the per-block costs
  small against the work.
- **Where the engine runs:** in source 11's handler, at priority 0, the
  lowest. The input scan and SPI1 move to 1 and the tick to 2, so the
  tick still preempts everything (its ±1 µs holds: R-IRQ-1, R-AUD-3), the
  scan keeps its 83.3 µs slots while the engine works, and main's drawing
  (which can take longer than a block) never delays a refill. Considered:
  filling from main's loop (a long panel redraw would make it late); a
  short source-11 handler that raises a software interrupt for the fill
  (HW-23), which buys nothing here, as the handler can be the lowest
  priority itself; the engine above the scan (the scan's slots would
  stretch by a whole block's work).
- **Underruns** (R-AUD-3): at each interrupt the half found free (`CON0`
  bit 15 inverted) must be the one expected (the halves alternate);
  after the engine, `CON2` bit 7 set again means the next half finished
  first, so on the chip the half just refilled began to play before it
  was full. Either counts in the audio record and writes `AUDIO UNDERRUN
  nnnn` (the count, hex) to the debug channel; the next half is refilled
  as usual. A test build late for one block in 64 gives exactly one
  report each. The firmware's longest refill: 1.8 µs at rest, 40 µs with
  every voice, the tone and the heaviest input, of 1 451 µs.
- **The audio record** follows the input record at `0x01C00550` (app.ld
  asserts it), with a marker, the start, blocks, underruns, the refill's
  time and nine words for the engine.
- **Core 1** stays parked (R-BOOT-4): one core does all of it with 97%
  to spare, and M5 decides how to split voices.

### 2026-10-23 M4: the audio API
- `firmware/src/audio.h`, beside `input.h`. An engine is one function,
  `void engine(s32 *out, u32 frames)`, called once a block to write 64
  stereo frames, left then right, straight into the half to be played:
  nothing is copied after it, so the engine costs only its own work. The
  words are the hardware's (24-bit, sign-extended), so the API is what
  HW-44 takes, not a format to convert from.
- Events: the engine reads them with `input_read_audio()`, from inside its
  callback, that is between blocks. The input layer queues each event
  twice, for main and for the engine (64 each), so neither reader can
  starve the other, and main's panel screen and LEDs work as in M3 while
  an engine plays. `input_value()` gives any control's state, and each
  event's time stamp lets a later engine place it within a block.
- Rules for an engine: finish within a block (else an underrun is
  reported), expect the tick and the scan to interrupt it, keep samples
  within ±`AUDIO_FULL`, and never call main-context functions
  (`input_read`, `input_led`, the screen).
- Considered: a block of floats (no FPU here, R-BUILD-1's freestanding
  C), 16-bit samples converted by the layer (a copy and a shift per
  word, and 8 bits lost), an engine that pulls events from main's queue
  (two readers of one queue).

### 2026-10-23 M4: the test instrument
- `firmware/src/synth.c`: an engine to prove the path, not a synth.
- **Oscillators:** a 1 025-word sine table (a full cycle in 1 024 steps,
  24-bit), each step linearly interpolated with 15 bits of a 32-bit phase
  (interpolation error about -106 dB). The table is computed at startup
  from sin's series to x^11 in 2^-29 fixed point, a quarter cycle and
  the rest by symmetry, using the core's 32 x 32 to 64-bit multiply (one
  instruction, in our own disassembly): no table copied from
  anywhere and no maths library. Phase increments: the twelve notes of
  the top octave, round(440 * 2^((n - 69) / 12) / rate * 2^32), computed
  offline in double precision; lower octaves halve them, rounded.
- **Voices:** four, from the 27 keys: KEY1 is F3, KEY8 middle C, KEY27 G5
  (the keys are chromatic from F, HW-36's layout), OCT- and OCT+ shift by
  octaves, two each way. A fifth key takes the quietest releasing voice,
  or the oldest, keeping its phase and level, so it changes pitch without
  a step.
- **Envelope:** linear, 5 ms attack (221 samples) and 20 ms release
  (882), from and to exactly 0: a voice that reaches 0 stops, and the
  output at rest is digital silence.
- **Level:** each voice a quarter of full scale, times MASTER's gain,
  the square of its position (roughly even loudness), full at 1 023,
  ramped over each block so a move doesn't click.
- **Test tone:** PLAY starts and stops 1 kHz at half of full scale
  (-6.02 dBFS), whatever MASTER says, with the same ramps.
- Found on the way: the first table overflowed (x^2 at pi/2 doesn't fit
  in 2^-30 fixed point), which the first capture's pitch showed (684 Hz
  for A4); the series is now in 2^-29. A 20-byte character array
  initialised on the stack made the compiler call `memcpy`, which the
  freestanding build doesn't have; the underrun line is a static array.

### 2026-10-23 M4: how the sound is measured
- `tools/audio_analysis.py`, our own, Python's standard library only (so
  no PROVENANCE entry): `wave` reads fwtest's capture; a four-parameter
  sine fit (amplitude, phase, offset, frequency; Gauss-Newton from a
  zero-crossing guess) gives each tone's frequency and level, and its
  residual gives THD+N. Sample times come from `ipb.csv`'s block ends.
- **Clicks:** a step shows as a second difference about the size of the
  step; a sine of amplitude A and angular step w under a linear ramp of
  R samples shows at most A((2 sin(w/2))^2 + (1 + 2w)/R), plus 4 for the
  capture's rounding. Each start and stop is checked against that bound,
  and a unit test shows an abrupt start or stop of the same notes
  exceeds it, from F1 to G7.
- Results (R-AUD-4 to R-AUD-6): the tone 1 000.000000 Hz (0.00000 cents),
  -6.021 dBFS, THD+N -92.2 dB (the 16-bit capture's own rounding is about
  -92 dB at this level); eight notes from F1 to G7 within 0.0003 cents,
  levels within 0.001 dB of MASTER's law, THD+N -74 to -86 dB; every
  sample 0 at rest.
- The golden WAV (R-AUD-7) is exact, so it moves whenever a change moves
  a note by a block; tests/fw/boot.suite says how to renew it. Records
  keep the suite's audio captures as names and SHA-256 only
  (`fwtest-audio.sha256`), not about a megabyte of WAVs a merge.
- Event to sound is timed against the time base's own start, found from
  the captures: the output began one block before its first block ended,
  `sb_audio.start` ticks after the time base began.

### 2026-10-23 M4: what audio costs, and the measure's new period
- R-PERF-2's period is now the audio block, counted by fwtest (the rows of
  `ipb.csv`), and `perf-history.csv`'s `period` says
  `audio-block-steady`. An image from before M4 has no blocks, so a
  baseline made of one is reported, not compared.
- Steady state, instructions a block (two runs, as tools/perf.py does;
  builds `SB_COST_NO_AUDIO` and `SB_COST_SILENT_ENGINE` leave parts out):
  - M3's tick, scan and LEDs, without audio: about 1 440 (992 a ms);
  - the output path alone (an engine writing silence): 1 742, so about
    300 for the interrupt, the checks and 128 stores;
  - the test instrument at rest: 1 813 (+71: reading events and MASTER);
  - four voices and the tone playing: 9 927, so about 1 640 an
    oscillator a block (25.6 a sample).
- Of core 0's 348 160 cycles a block, the platform (M3's input, the
  output path, the instrument at rest) takes 0.52%; all five oscillators
  2.85%. That leaves about 345 000 cycles a block, 99% of core 0, for
  M5's engine, less main's bursts of drawing; core 1 is untouched. In
  fwtest one instruction is one cycle; on the chip, with code run from
  flash through the cache, it will be more, which M4b's real engine and
  a probe on the chip will show.

### 2026-10-23 M4b: the loaded measure
- Facts: docs/HARNESS.md ("Input scripts", "Time"); the owner's request
  in M4b (R-PERF-1, R-PERF-2, R-PERF-4, R-PERF-5).
- Why: the steady state measures the firmware at rest (1 813 instructions
  a block), while M4's five oscillators cost about 9 900 and nothing
  gated that. For an instrument the worst case is what matters.
- **The script** (`tests/fw/scripts/perfload.txt`): from 100 ms, PLAY
  once (the tone), four keys held (every voice), then a pattern repeated
  every 250 ms until 2 500 ms: each held key in turn released for 10 ms
  and pressed again (its voice releases, then takes the key back, so all
  four keep sounding), all seven encoders turned 15 detents one way and
  15 back (they never rest), and MASTER swept 1023 to 0 and back, a step
  every 5 ms. The window between the perf runs (1 250 to 2 250 ms) holds
  four whole repeats; a test checks the repeat and the PLAY tap.
- **Measured the same way** as the steady state: the two runs again, with
  the script; instructions gained over blocks gained. Its startup isn't
  used. Under load core 0 never waits near the runs' ends, so they end
  exactly at 1 250.000 and 2 250.000 ms.
- **Result:** 114 172.717 instructions a block (689 blocks), 32.8% of
  core 0, against 1 813 at rest. The audio engine is about 9 900 of it;
  the rest is main redrawing the panel screen for every event (blocks in
  the window run from 9 900 to a whole block's 348 160 cycles while a
  redraw is in progress). No underrun: the engine preempts main.
  So under heavy input, drawing, not sound, is most of the work; M5's
  screen should redraw only what changed, at a bounded rate.
- **Gates:** its own budget (`loaded_per_period`, optional: a milestone
  without one records it as NOT GATED) and its own 3% gate against a
  baseline found by the M3 rule keyed on the loaded budget, so it may be
  another record than the steady state's (re-measured only then). The
  records before M4b have no loaded budget. M4b changes no base firmware,
  so after the budgets pull request every record still holds the
  pre-raise image, and the loaded gate stays NOT COMPARED until the
  firmware changes (M5); until then the probe below is what proves it.
- **Probe:** `SB_PROBE_SLOW`'s work per heartbeat beat adds about 87
  instructions a block, 0.08% under load, so it can't prove the loaded
  gate. `SB_PROBE_LOADED` adds a short loop for each voice sounding, each
  block: nothing at rest, about 12 000 a block under load (about 10%). It
  fails the loaded speed gate and the loaded budget and nothing else.
- **History:** `perf-history.csv` keeps its columns (it can't grow one:
  append only). Beside it, `perf-measures.csv` has one row per commit
  and measure (the owner's design): commit, record time, milestone,
  measure, value, unit, budget, change, and whether the change was gated.

### 2026-10-23 M4b: porting Plaits, what it needed
- Facts: HW-9 and HW-10 (starting core 1), HW-11 and HW-13 (240 MHz,
  the 24 MHz time base: 10 cycles a tick in fwtest), HW-25 (the debug
  console), HW-39 (ALGORITHM is fwtest's encoder 1), HW-43 to HW-46; the
  SDK's app Makefiles (P-29); our own runs (P-30).
- **Source:** Mutable Instruments' Plaits by Emilie Gillet, MIT, from the
  original upstream only (pichenettes/eurorack and the stmlib its
  submodule pins), vendored unmodified with checksums (vendor/plaits/,
  P-28). Every file's licence checked: MIT throughout.
- **Built unmodified** in upstream's own portable configuration
  (`-DTEST`: plain C++ where the STM32 build has assembly and flash
  access), at upstream's `-O2`, as its own image (`tools/build.sh build
  --demo plaits`); the firmware's sources gain only a hook under
  `SB_DEMO_PLAITS`, and the firmware's image is unchanged byte for byte.
- **What the toolchain and the chip lacked, and what it took** (all ours,
  in firmware/demos/plaits/):
  - **C++:** the toolchain's clang compiles it (`-std=c++11`, no
    exceptions or RTTI); there is no C++ library, so six small headers
    give the few standard pieces Plaits includes (`min`, `max`, `swap`,
    `fill`, `copy`, an insertion `sort`, the integer types, `size_t`).
    No global constructors: the voices are built in static storage by
    placement new at start. A handler for pure virtual calls and the
    deallocation functions a virtual destructor names, each stopping the
    firmware (never reached).
  - **Floating point:** clang turns every float operation into a call
    (`__addsf3` and the rest) and we don't link the toolchain's library
    (docs/TOOLCHAIN.md), so runtime/softfloat.c is our own IEEE 754
    binary32: correctly rounded add, subtract, multiply, divide and
    square root, comparisons and conversions, integer arithmetic only.
    It counts invalid operations, overflows and bad conversions (IEEE's
    flags) for the bench. Tested bit for bit: 4 million random and edge
    cases per operation against the host's IEEE hardware while writing it,
    and in every record 20 000 per operation in fwtest against an exact
    rational reference (tools/plaits-bench.py).
  - **Maths:** nothing more: at these flags Plaits calls only `sqrtf`.
    It uses no double precision at all.
  - **memcpy, memset, memmove** (the compiler calls them for structure
    copies), byte by byte.
  - **Sample rate:** Plaits' tables and filters are made for its own
    47 872.34 Hz; ours is 44 117.647 Hz, so the demo raises every note by
    12 log2(47 872.34 / 44 117.647) = 1.414 semitones. Its time constants
    run 7.8% slow. A block is four renders of 16 frames (Plaits takes up
    to 24).
- **Found on the way:** a Plaits source no header names (the speech
  synthesiser's phoneme table) was missed by the include walk that chose
  the files, and was added when the first link asked for it.
  ALGORITHM is fwtest's encoder 1, not 2 (HW-39), which the first live
  check got wrong. C-SEP-TERMS flagged identifiers in Plaits' MIT code
  that also occur in the emulator's source; with the owner's approval the
  vendored Plaits' terms now count as public like the SDK's (R-SEP-1).
- **Hardware float:** the toolchain has single-precision float
  instructions (its `fprev1` feature). fwtest runs them, and the SDK's
  own AC791N builds use them (`-mcpu=r3 -mfprev1`, P-29), but
  HARDWARE-SPEC.md says nothing yet: SR-5 asks. So the demo's default is
  soft-float; `PLAITS_HWFLOAT` builds Plaits with the instructions for
  the measurements. Every engine gives the same sound bit for bit either
  way (the bench's checksums): two independent float paths agree.

### 2026-10-23 M4b: what Plaits costs, engine by engine
- **Method** (firmware/demos/plaits/bench.c, check C-PLAITS-BENCH): in
  main, before interrupts, each engine renders one block after it is
  selected (its set-up, reported apart), then four blocks at each of nine
  settings (HARMONICS, TIMBRE and MORPH each at 0 and 1, and all at 0.5),
  a key struck at the first of each. Each block is timed with the time
  base, read only before and after it, and converted at 10 cycles a tick;
  in fwtest an instruction is a cycle. Cross-check: on the live
  hardware-float demo, fwtest's own count is 30 581 a block on engine 0
  against the bench's 28 832 plus the firmware's 1 813 at rest.
- **Results**, instructions a block (64 frames; core 0 has 348 160),
  heaviest of the nine settings:

  | # | Engine | Soft-float | Hardware float | Voices on core 0 (hardware float, at rest) |
  |---|---|---|---|---|
  | 0 | virtual analog VCF | 1 005 730 | 29 150 | 11 |
  | 1 | phase distortion | 1 149 230 | 40 840 | 8 |
  | 2-4 | six-op FM (3 banks) | 818 620 to 828 930 | 30 510 to 30 760 | 11 |
  | 5 | wave terrain | 1 141 280 | 29 910 | 11 |
  | 6 | string machine | 1 215 960 | 40 510 | 8 |
  | 7 | chiptune | 184 280 | 10 560 | 32 |
  | 8 | virtual analog | 864 760 | 32 490 | 10 |
  | 9 | waveshaping | 751 790 | 19 490 | 17 |
  | 10 | FM | 1 122 150 | 41 400 | 8 |
  | 11 | grain | 1 023 190 | 28 590 | 12 |
  | 12 | additive | 1 679 090 | 45 790 | 7 |
  | 13 | wavetable | 1 291 050 | 30 680 | 11 |
  | 14 | chords | 1 139 300 | 35 620 | 9 |
  | 15 | speech | 888 940 | 26 330 | 13 |
  | 16 | swarm | 1 073 190 | 28 200 | 12 |
  | 17 | noise | 1 039 740 | 48 390 | 7 |
  | 18 | particle | 1 184 630 | 47 720 | 7 |
  | 19 | string | 1 126 800 | 38 540 | 8 |
  | 20 | modal | 1 838 260 | 52 640 | 6 |
  | 21 | bass drum | 922 440 | 27 000 | 12 |
  | 22 | snare drum | 1 031 790 | 35 080 | 9 |
  | 23 | hi-hat | 627 640 | 25 210 | 13 |

  (The record's table, from tools/plaits-bench.py, has the means, the
  set-up blocks, and voices under the heaviest input too.)
- **What the bench holds fixed:** one pitch (MIDI 48, plus the rate
  offset) and decay 0.5, so an engine whose cost grows with pitch may cost
  more higher up. The voices column counts time only. Each voice is about
  29.5 KB of RAM (its 16 KiB buffer and Plaits' voice object: the demo's
  zeroed data is 59 160 bytes more than the firmware's, for two). The
  chip's 511 KiB of RAM, less the firmware's 124 KB and its stacks, holds
  about 13 voices, fewer than the column for the lightest engines.
- **Soft-float doesn't fit.** Every engine but chiptune takes two to five
  blocks' time for one block, so only chiptune plays live with soft-float.
  Any other overloads core 0: underruns, and main starves. Soft-float is
  about 30 times slower than the instructions (18 to 39 times, by engine).
- **Clean audio:** over the whole bench soft-float raised no invalid
  operation, no overflow and no bad conversion, so Plaits made no NaN and
  no infinity. Some engines reach full scale at extreme settings (chords
  33 samples, modal 23, bass drum 149, snare 3, noise 1, of 2 304 a
  setting run): Plaits' own output stage saturating on purpose (its
  `Clip16`), not an overflow. Live, with a key held: the soft-float demo
  on chiptune, and the hardware-float demo on engine 0, with no underrun.
- **Core 1** (HW-9, HW-10): started from the bench on a loop that renders
  a second voice whenever core 0 sets a word in RAM. Two voices at once
  take 0.49 to 0.50 of the time of one after the other with hardware
  float (speed-up 1.99 to 2.02), 0.51 to 0.59 with soft-float. The
  comparison is of successive blocks, so it is good to a few percent.
  fwtest models no contention between the cores; SR-6 asks what the chip
  costs, and what core 1 needs before it runs from a raw image.

### 2026-10-23 M4b: the headroom it implies for M5
- **A frequency-modulation operator:** Plaits' six-op engine plays two
  six-operator voices, 768 operator-samples a block, for 30 550
  instructions with hardware float: at most 40 an operator-sample, its
  envelopes, low-pass gate and limiter included. M4's fixed-point sine
  oscillator (interpolated table, envelope) is 25.6 a sample. With
  soft-float it is about 1 070: soft-float is out for M5's engine.
- **At 44 117.647 Hz, 64-frame blocks:** core 0 has 348 160 cycles a
  block; the firmware takes 1 813 at rest and 114 173 under the heaviest
  input (the loaded measure, M4b), most of it main redrawing the panel.
  - **One core:** about 346 000 a block at rest, 234 000 under load:
    8 600 or 5 800 operator-samples a block, that is **135 or 91
    operators** (at 40 each; 210 or 140 at M4's 25.6), for example 22 or
    15 six-operator voices.
  - **Two cores:** core 1 adds a whole 348 000 (it does no input or
    drawing): about **8 700 more operator-samples a block, 135 more
    operators**, if the chip runs both cores like fwtest (SR-6).
  - These are fwtest's numbers, an instruction a cycle. On the chip, code
    run from flash through the cache will take more; a probe on the chip
    is still to come. Leave M5 a wide margin: plan for half.
- **For M5's design:** fixed point (as M4's oscillator) costs about what
  hardware float does in fwtest, and needs no answer from SR-5; floats
  need SR-5 to say the chip has them. The screen, not the sound, is the
  heaviest user of core 0 under input: M5's screen should redraw only
  what changed, at a bounded rate.

### 2026-10-23 M4b: the loaded measure, broken down (the owner's question)
- **Method:** the M4 firmware under the loaded script (#57's
  `tests/fw/scripts/perfload.txt`), core 0's instructions between the 1 250
  and 2 250 ms runs, over the blocks that second holds (689.3), in builds
  that each leave one part out: the existing cost builds (`SB_COST_*`), and
  two measurement-only switches added to `panel.c` for these runs and not
  committed (one skipping the panel's drawing and sending, one drawing
  without sending). Taking differences:

  | Part | Instructions a block | Share |
  |---|---|---|
  | Screen: drawing into the frame buffer (main, `panel_serve`) | 102 437 | 89.8% |
  | Screen: sending the changed rows (`lcd_send_rows`, DMA started, waited for) | 1 104 | 1.0% |
  | Audio engine (the test instrument, four voices and the tone) | 8 309 | 7.3% |
  | Input scan (keys, encoders, pot, LEDs; LEDs 215 of it) | 1 861 | 1.6% |
  | Audio output path (the interrupt, its checks, the stores) | 302 | 0.3% |
  | The tick, main's wakes and the rest | 104 | 0.1% |
  | **Total** (114 173 by the record's count of blocks) | **114 117** | |

  The scan's share is the "no panel" build less the build with no scan as
  well, less the audio engine's (with no scan no note sounds).
- **The screen dominates, and it is the drawing, not the sending.** The
  panel already redraws only the region an event touches (a button, the
  keys strip, a knob's row, the event line). But it does so for every
  event, and the script makes about 1 070 a second (840 encoder detents,
  200 pot steps, 32 key changes): about 66 000 instructions an event,
  mostly pixel-by-pixel fills and scaled glyphs into the 240 x 240 frame
  buffer. A key event repaints the whole 52-row keys strip.
- **It is already off the audio's critical path** in the sense that
  matters for underruns: drawing runs in main, at the lowest level, and
  the audio interrupt preempts it, so no block was late. What it costs is
  core 0's time, which M5's voices need, and under an overloaded engine
  main starves and the screen freezes.
- **What it would take, before M5** (not done; measure first):
  - **Coalesce:** mark regions dirty per event, and redraw at most once
    per frame, at a fixed rate (30 to 60 Hz), not once per event. At 1 070
    events a second against 60 frames, that is up to 18 times less: about
    6 000 a block under this load, if a frame redraws what one event does.
  - **Cheaper drawing:** fill whole words and rows (`gfx_fill` writes
    pairs of pixels today), and draw text from pre-rendered glyph rows at
    the scale used instead of pixel by pixel; redraw a knob's value, not
    its row.
  - **A drawing budget:** let main draw for at most a set share of each
    block (from the time base), carrying on next time, so the screen can
    never take what the voices need.
  - **Moving it:** core 1 could draw (the panel's DMA and its interrupt
    would move with it, and needs SR-6's answer about core 1's
    interrupts), but core 1 is worth a whole second core of voices
    (above), so coalescing on core 0 is the better first step.
- Re-measure with the loaded measure after any of these: the loaded gate
  (#57, #58) will show the change, and its budget can then come down.

### 2026-10-23 M4b: what the API should change before M5
- **An engine context.** `audio_engine_fn` takes no pointer, so an engine
  keeps its state in globals, and two voices on two cores can't share
  one function cleanly. Add a `void *` to the engine call.
- **Knobs as parameters.** `input_value()` gives an encoder's raw detents
  since start, unbounded; the demo maps them to 0 to 1 itself. A small
  layer giving each knob a clamped parameter, and a pickup of the pot,
  would save every engine the same code.
- **A deadline the engine can see.** An engine that overruns has no way
  to know: the audio record's fill times are tests' data, not API. Give
  the engine its last fill time against the block, so it can shed voices
  before underruns start, and protect main, which starves when the
  engine overloads core 0.
- **Core 1 as an API.** The bench drives core 1 by hand (its start word,
  `C1_CON`, a RAM flag). M5 needs a small, tested way to start it, post a
  job each block and wait for it, once SR-6 says what the chip needs.
- **Floats:** if SR-5 confirms the instructions, build the firmware with
  `-mcpu=r3 -mfprev1` like the SDK, and the soft-float runtime stays a
  demo's.

### 2026-10-23 M5: built for the chip's CPU model and its float instructions
- Facts: HW-62 (the SDK builds this chip's code with `-mcpu=r3
  -mfprev1`), HW-63 (fwtest runs those instructions, one cycle each);
  Q-16 open (their cost on the chip). PROVENANCE P-32.
- Reasoning: SR-5's answer says to build as the SDK does, so the C and
  assembly flags now carry `-mcpu=r3 -mfprev1` (tools/build.sh, `CPU`;
  R-BUILD-1). Measured before and after on main at `7eb74e8`: the image
  is **byte for byte the same** (`app.bin` `543e5764...`, and the ELF):
  the firmware has no float yet, and the integer code `r3` gets is what
  the default gave. So the steady state (1 812.9 instructions a block),
  the loaded measure (114 172.7) and every size are unchanged. With the
  flag, a float operation is one instruction where it was a call into a
  float library (a test file: `a * b + a / b` became three instructions
  and a return, from two calls and their set-up).
- Fixed point stays where it is cheaper: M4's oscillator and mixing are
  32- and 64-bit integer multiplies, single instructions here (M4, P-27),
  with no conversions at the ends. Floats are for what fixed point makes
  awkward (wide-range values: rates, pitch ratios, envelope curves
  computed per block, not per sample). On the chip their cycle cost is
  still unknown (Q-16), so nothing per sample depends on a float.
- Found on the way: `-mcpu=r3` alone already makes clang use the float
  instructions (the disassembler shows them as unknown instructions). So
  the Plaits demo's own C (its soft-float runtime and that runtime's
  bit-for-bit test) keeps the flags it had, without either: built with
  them, the test ran on fwtest's float instructions instead and
  C-PLAITS-BENCH failed for add, subtract, multiply and divide. Checked
  against the test's 20 000 operand pairs a operation in Python: add,
  multiply and divide differ from the exact reference only in the NaN
  they return (fwtest gives the first NaN operand, quieted; the soft-float
  and the reference give the canonical `0x7FC00000`); subtract differs
  too, presumably in that NaN's sign (not pinned down). Every numeric
  result matched. HW-63 doesn't say which NaN comes out; nothing in the
  firmware depends on it.
- Alternatives: leaving the default CPU model (the same code today, but
  float would need a library); building only the engine with the flag
  (two ABIs to keep straight for no gain).
### 2026-10-23 M5: the screen's cost, drawn in frames within a budget
- Facts: HW-13 (the time base), HW-45 (a block is 64 frames of 544 time
  base ticks); docs/HARNESS.md "Time" (reading the time base three times
  within 64 cycles counts as waiting). M4b's breakdown of the loaded
  measure: drawing was 89.8% of it, about 66 000 instructions an event.
- Reasoning:
  - **Coalesce.** An event still sets its LED at once (R-LED-3), but now
    only marks what it changed: a button, the keys strip, a knob's value
    (and the MASTER bar), the event line. What is marked is drawn at most
    once a frame of 16 ms (about the panel's own refresh), however many
    events came in it: under the loaded script's 1 070 events a second,
    60 frames instead. A frame starts at once if the last began 16 ms or
    more ago; otherwise main asks the tick to wake it when one is due
    (`sb_wake_at`, a compare in the tick that costs nothing measurable at
    rest), so the last change always shows within one frame.
  - **A drawing budget per audio block.** Within a frame, items are drawn
    one at a time; none is started once drawing has taken 4 352 time base
    ticks (an eighth of a block, about 43 500 instructions) in the current
    block (counted by `sb_audio.blocks`). The rest waits for the next
    millisecond's tick. The time base is read once before and once after
    each item, never in a tight loop, so fwtest's waiting rule can't
    apply. Main is still the lowest level, so the audio interrupt
    preempts drawing as before; the budget bounds how much of core 0
    drawing can take, the time the voices will need in M5.
  - **Cheaper drawing.** Text at scale 1 (all of the panel's) writes two
    pixels a store, each pair's colours picked by its two bits from a
    four-entry table (an odd x has one single pixel at each end). The
    keys strip no longer fills all 52 rows black first: only the margins
    and the gaps between the lower keys, which the keys don't cover. Both
    give the same pixels: every golden image still matches.
- Results (fwtest, tools/perf.py, main at `7eb74e8` before):
  - **Loaded: 114 172.7 → 15 521.8 instructions a block, 86.4% less**
    (7.4 times less), the R-PERF-2 improvement. At rest: 1 812.9 →
    1 820.4 (+0.4%: the tick's compare and the loop's larger frame).
    Startup: 1 058 323 → 987 014 (the test screen's text is faster).
    Code +428 bytes (9 064).
  - Under the loaded script (a measurement build, not committed): the
    budget stopped a frame 107 times in 2.25 s, and the most drawing in
    any one block was 6 342 ticks, 18% of a block: the budget plus the
    longest item, the keys strip (about 20 000 instructions).
  - The chords case's picture shows the last encoder detent one frame
    later than before: its capture moved from 1 030 to 1 050 ms (the same
    golden image, renamed); the image is identical from 1 040 ms on.
- Alternatives: drawing on core 1 (it is worth a whole core of voices,
  M4b); a fixed frame timer (wakes main every frame even at rest); a
  budget in instructions (fwtest counts them, the chip can't).

### 2026-10-23 M5: the FM engine
- Facts: HW-9 and HW-10 (releasing core 1, its state), HW-62 and HW-63
  (the float instructions, used per block only), HW-64 (the cores in
  fwtest), HW-65 (`testset` and `csync`, the SDK's lock and shared
  loads), HW-43 to HW-46 (the output), HW-36 and HW-39 (the panel's
  keys and knobs). PROVENANCE P-33 (the SDK's `cpu.h`, for the lock's
  syntax), P-34 (the literature below), P-35 (our experiments).
- Sources, all public literature, none of it code: John M. Chowning,
  "The Synthesis of Complex Audio Spectra by Means of Frequency
  Modulation", J. Audio Eng. Soc. 21(7), 1973 (a sine's phase modulated
  by another sine gives sidebands at fc ± n fm with amplitudes J_n(I));
  J. R. Carson's rule for an FM signal's bandwidth, about 2 (I + 1) fm
  (Proc. IRE, 1922); M. Abramowitz and I. Stegun, Handbook of
  Mathematical Functions (1964), 9.1.10, the Bessel functions' series
  (for the tests). Everything else is from first principles. No FM-1
  firmware, no other synthesizer's firmware and no FM engine's source was
  looked at; `vendor/` was left out of every search (it holds Plaits,
  which has an FM engine, and was not opened).

#### The operators
- **Phase modulation, in fixed point.** An operator is a 32-bit phase
  accumulator (2^-32 of a cycle) stepped once a sample; its output is
  sin(phase + modulation) x gain. A modulator's output (24-bit) is added
  to its carrier's phase shifted left by 10, so full scale moves the
  phase two cycles: index 4 pi at most. The 32-bit addition wraps exactly
  as the phase does, so large indices need no care. Gains are in 2^-30
  and multiply in one 32 x 32 to 64-bit instruction (M4, P-27).
- **The sine, our own method.** A 1 024-step table (4 KiB) from the
  series of sin x to x^11 on a quarter cycle (M4's), read with linear
  interpolation on 15 bits of the phase: at most 4.7e-6 of full scale
  off, about -106 dB, below the 16-bit capture. Measured: THD+N -74 to
  -86 dB at -12 to -24 dBFS in 16 bits (the capture's floor).
- **Frequency.** The note's phase step comes from its pitch in 1/4096
  semitone: 2^(pitch / 12) by a 257-entry table of 2^(i/256) (from the
  exponential's series, interpolated) times the step of MIDI note 0;
  within 0.012 cents across F1 to G7 (measured). A ratio (x 1/256, so
  1.0 is 256 and 3.5 is 896) multiplies it, or a fixed frequency in
  quarter hertz replaces it; a detune in cents multiplies the result.
- **Feedback.** One operator per algorithm feeds the mean of its own last
  two outputs back into its phase (up to pi). The mean is a zero at half
  the rate, which damps the sample-to-sample oscillation feedback falls
  into at high amounts.
- **Aliasing, our strategy.** (1) An operator whose step reaches half the
  rate is silent (its gain ramps to 0), never folded. (2) The index
  limit: by Carson's rule a modulator fm at index I spreads its carrier
  fc over about fc ± (I + 1) fm, so each block a modulator's gain is held
  to the index that keeps fc + (I + 1) fm below half the rate
  (I <= (fs/2 - fc) / fm - 1). It works on gains, per block, with one
  float division a modulator: no per-sample cost. Low and middle notes
  never meet it (the Bessel test's index pi/2 at A4 is 43 times below
  it); high notes with bright patches do, and lose brightness instead of
  folding. (3) Feedback's mean, above. (4) The sine is interpolated, not
  stepped, so the oscillator adds no images of its own.

#### The algorithms
Our own ten, in our own order and encoding: each operator's output goes
to one lower-numbered operator or to the output (so a voice is rendered
in one pass from operator 6 down, a block at a time), with the feedback
on the operator marked `*`. Arrows point from modulator to carrier; the
bottom row is what sounds.

```
 1  6*>5>4>3>2>1        one stack
 2  6*>5>4   3>2>1      two stacks of three
 3  6*>5  4>3  2>1      three pairs
 4  6*>5>2  4>3>2  2>1  two stacks into 2, 2 into 1
 5  6*,5,4,3,2 > 1      five modulators into one carrier
 6  6*>5>4>3   2   1    a stack of four, and two carriers alone
 7  6*,5 > 4   3,2 > 1  two branches
 8  6* 5 4 3 2 1        six carriers (additive)
 9  6*>5>4   3   2>1    a stack of three, a carrier alone, a pair
10  6>5  5,4>3  3,2*>1  a tree, the feedback on 2
```

Stacks give the deep, many-sideband spectra (modulators of modulators),
pairs and parallel carriers keep several simple spectra apart, branches
(several modulators into one carrier) add their sidebands. The carriers'
sum is divided by how many sound (log2 n octaves of attenuation), so an
algorithm change keeps the level about the same. ALGORITHM changes the
algorithm for new notes only: a sounding note keeps its routing, so the
change never clicks.

#### The envelopes
- **Shape.** Each operator: attack, decay 1, decay 2 (to a held level),
  release. The attack rises linearly in gain: it reaches the ear at once
  and, being a ramp, can't click above about a millisecond. The decays
  and the release move linearly in attenuation, so they fall
  exponentially, as struck and plucked things do, and they sound even
  (loudness is close to logarithmic). Pitch has its own: P0 at note on,
  to P1, to P2 (held), and to P3 on release, linear in pitch.
- **Rates and levels.** A time code t is 2^(t/8) ms for a stage's whole
  range (1 ms to 60 s, eight steps an octave of time); a level step is
  2^(1/8) in gain (0.753 dB), 127 being 0 dB and an operator's own level
  using the same steps. Rates, not times, so a stage that moves part of
  its range takes that part of its time, and a release from any level
  falls at the same speed.
- **Per block, without steps.** Envelopes move once a block (64 samples);
  the gain an operator reaches is then interpolated a sample at a time
  across the next block, so no change is a step (no zipper). A stage that
  ends within a block hands the rest of that block to the next stage,
  so no stage loses time to the blocks: measured, every stage ends
  within 0.9 ms of its nominal time (a block is 1.45 ms) and falls
  within 0.5% of its rate.
- **Velocity.** Each operator has a sensitivity 0 to 7: at 7, velocity 0
  is 8 octaves (48.2 dB) quieter than 127, linear in velocity between, as
  attenuation. On a carrier it is loudness; on a modulator, brightness.
  The panel's keys sense no velocity and play 100 (M6's MIDI brings real
  ones); the velocity test build plays 127, 100, 64, 32 and 1 from KEY1
  to KEY5, measured within 0.03 dB of the formula.
- **Found on the way:** the first velocity test measured a patch's
  overall level (Brass) and expected phase modulation to leave the
  carrier's power alone. That holds only while no sidebands fold onto
  each other; with all ratios 1 the lower sidebands land on the upper
  ones and interfere, and the power moves with the index (0.5 to 0.75 dB
  here). The test now uses a carrier alone (test patch 8).

#### Voices
- **16 voices, 8 a core**: voice n belongs to core n mod 2. A note takes,
  in order: the voice already playing its own note (so a key struck again
  doesn't double), a free voice on the core with fewer sounding (the
  cores stay balanced), the quietest released voice, the oldest. A voice
  taken while it sounds fades out linearly over one block, and the new
  note starts the block after: one block more latency for a stolen note,
  and no click (measured: the largest second difference 7 where the bound
  for the notes sounding is 110). A note that starts on a voice still
  sounding (the same note again, or mono) keeps its phases and starts its
  attacks from where its envelopes are.
- **Mono** (a patch's flag, or SEL held with the MONO and POLY keys): one
  voice, last-note priority over a stack of the keys held. A note while
  another is held is legato: no new note, no new attack, the pitch
  glides to it; releasing it glides back to the one still held; the last
  key up releases the voice. The glide is linear in pitch over a fixed
  time (the patch's glide time code plus four steps for each detent of
  KNOB2), whatever the interval, which is easier to play than a fixed
  rate. Poly mode doesn't glide.

#### Two cores
- **Start.** fm_init (core 0, before interrupts) puts core 1's entry in
  the word at `0x01C7FFF8`, sets `C1_CON` bit 3 (HW-9), waits for core 1
  to say it runs, then gives that word (source 126's vector) its stub
  back. Core 1 sets its own stacks (HW-10, `core1.S`) and loops in
  fm_core1_main. If it never answers, core 0 plays the even voices alone
  (8 voices).
- **Each block** (core 0, in the audio interrupt): it takes the events
  and changes voices (only now: core 1 is waiting), sets every voice's
  pitch and phase steps, posts the block to core 1 if any odd voice
  sounds (a sequence number, under the lock), renders the even voices,
  waits for core 1's answer, and mixes. Core 1 renders the odd voices
  into its own buffer with its own scratch, then answers. At rest nothing
  is posted, so core 1 stays in its waiting loop and core 0's count stays
  low.
- **Synchronisation, as SR-6's answer says** (HW-65): every load of a
  shared word follows `csync`; the sequence numbers change under a
  `testset` lock (the SDK's: test-and-set the byte until it was clear,
  `csync` before and after; release with `csync` and a plain store of 0).
  Each voice has one writer at a time (core 0 between blocks, its own
  core during one), so the lock guards only the hand-over. In fwtest the
  answer comes within a turn of 1 024 cycles (HW-64): core 0 waited at
  most 10.3 µs a block under the heaviest load. Deterministic: the same
  run twice gives the same output, byte for byte (fmgold2).

#### Patches and the controls
- **The format**: docs/PATCH-FORMAT.md, 112 bytes, versioned, a check sum.
  Nine test patches of our own, defined once in tools/fm_patch.py, each
  for a test or a kind of sound (Sine, Two-op, Env test, Glide lead,
  Bell, Bass, Organ, Brass, Velocity); none is any synthesizer's preset.
- **Reaching the engine from the panel** (enough to test, until M8's
  editing): the keys play (OCT- and OCT+ as M4); MASTER is the volume
  (M4's law, ramped over a block); PRESETS selects the patch for new
  notes (and its algorithm and mode); ALGORITHM changes the algorithm for
  new notes; KNOB1 transposes by semitones (-24 to 24, sounding notes
  too, phase-continuous); KNOB2 adds to the glide time; KNOB3 adds to
  every modulator's level, a level step a detent (brightness); KNOB4 adds
  to the feedback (0 to 7). SEL held with the MONO or POLY key switches
  the mode. PLAY still starts and stops M4's test tone. KNOB3 and KNOB4
  apply to sounding notes and move smoothly (gains and the feedback
  amount are interpolated a sample at a time).

#### Figures (fwtest, main at `7eb74e8` with #65 and #66)
- **Instructions per operator-sample: about 24**, envelopes, pitch and
  index limit included: core 1 renders 8 voices of test patch 6 (six
  operators each, 3 072 operator-samples a block) in 74 200 a block.
  Plaits' six-op engine was about 40 with hardware float (M4b).
- **Voices a core**: a core has 348 160 cycles a block. At rest core 0
  uses 1 803 (0.5%), so about 37 six-operator voices would fit on it;
  under the heaviest input core 0 has about 10 300 of its own work
  (events, the screen within its budget, control), so about 36. Core 1
  has nothing else: about 37.
- **We ship 16 (8 a core)**: under the heaviest input core 0 is at
  84 918 a block (24%) and core 1 at about 75 000 (22%), a margin of four
  times. fwtest is a best case (one instruction a cycle, no caches,
  no flash or RAM wait states, no cost between the cores: HW-64, Q-16,
  Q-17); M4b's advice was to plan for half, and this leaves more for
  the chip's unknowns and for M6 to M8.
- **Sizes**: code 15.7 KB (6.6 KB more than before the engine, the test
  patches' 1 KB among it), static RAM 142.0 KB (18.0 KB more: the voices
  7.9 KB, the mixes and scratch 4.1 KB, the sine and exp2 tables 5.1 KB,
  the parsed patches 3.7 KB, core 0's notes on the voices 0.8 KB, core
  1's stack 1 KiB; M4's instrument's 4.5 KB gone), stack 388 bytes.
  Startup 1 032 624 instructions.

#### Workaround: SR-7
fwtest doesn't run the two-register load that moves its address down
first (`{r3, r0} = [-r4]`), which clang made of seven consecutive word
copies in `voice_start()` (fm_play.c), with or without `-mcpu=r3
-mfprev1`; the image faulted there. Until fwtest runs it (SR-7,
docs/SPEC-REQUESTS.md), those copies go through `copy_words()`, a word at
a time from a volatile pointer, and tools/build.sh fails any image whose
disassembly holds the form, so a new one can't reach fwtest unnoticed.
Both go once SR-7 is answered.

*Since M6a:* fwtest 0.3.0 runs all eight block-move modes (HW-66), so
`copy_words()` is gone and the copies are plain loops again. tools/build.sh
now fails an image holding the one gap left that the compiler emits, a
rotate by a register (docs/HARNESS.md, "Instructions", "Known gaps").
*Since fwtest 0.4.0* (#78) that runs too and HARNESS.md lists no known
gaps, so the build's check is gone.

### 2026-10-24 M6a: MIDI in
- Facts: HW-67 to HW-71 (SR-8's answer: the jack reaches UART1, received
  by DMA into a ring; the count latch; what fwtest counts as a receiver);
  HARNESS.md's `midi` script event (a byte every 320 us). PROVENANCE P-38
  (the request), P-43 (the MIDI 1.0 specification, as public literature),
  P-44 (SR-8's answer, read from its pull request, #81, before it merged).
- Sources: the MIDI 1.0 Detailed Specification's rules for status and
  data bytes, running status, realtime and System Exclusive messages, the
  channel mode messages (120 to 127), registered parameter 0 (pitch bend
  sensitivity) and the controller numbers' usual meanings, from the
  session's own knowledge; nothing fetched. No other synthesizer's
  firmware and no MIDI library's source was looked at.

#### The path
The receiver's interrupt only puts each byte into a 256-byte ring
(`midi_rx_byte`, midi.c). The engine's block callback, after the panel's
events, takes the bytes waiting, parses them and acts on each message
(`midi_read`, `midi_message` in fm_play.c), so MIDI and the panel change
the engine at one place and time, between blocks, and the voices never
change during one. At the wire's pace a block (1.45 ms) brings at most 5
bytes; the ring holds 256 (about 80 ms), so only a stalled engine could
fill it, and a full ring drops the newest bytes and counts them.

#### The receiver
UART1's receive DMA writes the jack's bytes into a 256-byte ring of ours
(HW-70); `midi_start()` sets the ring and turns the UART and its DMA on
(`CON0` bits 0 and 6), which is what fwtest counts as a receiver set up
(HW-71). Once a block, before the engine reads MIDI, `midi_poll()`
latches the count written since the last time (`CON0` bit 7 into
`HRXCNT`, HW-69) and hands those bytes on. No interrupt: the engine acts
on MIDI once a block in any case, so one per byte would not lower the
latency, and polling keeps every MIDI change between blocks. More than
256 bytes between two polls (82 ms of the wire) would have overwritten
the oldest (HW-71); they are counted as dropped. Not set, because fwtest
needs none and the chip's are still open (Q-12): the baud rate, the
UART's clock, its pin and the port set-up. They come with real hardware.

#### The parser
Our own, from the specification's rules (tools/midi_model.py is the same
rules written again in Python, for the tests):
- **Realtime** (0xF8 to 0xFF) is a message of its own wherever it comes,
  even between a status and its data or inside a SysEx, and changes
  nothing else. 0xF9 and 0xFD are undefined and dropped. 0xFF, a system
  reset, also ends running status and any SysEx, and the engine lets
  MIDI's notes go and its controllers back to rest.
- **Running status:** a channel status (0x80 to 0xEF) is kept for the
  data bytes that follow; every other status but realtime ends it.
- **System Exclusive** is skipped a byte at a time, so its length
  doesn't matter; past 4 096 data bytes it is counted as too long. EOX
  ends it; any other status (a note on, say) cuts it short and is taken
  as itself. Nothing in a SysEx is used yet.
- **Never wedged:** a data byte with no status, an undefined status, a
  stray EOX, and a message a status cuts short are dropped and counted.
  The parser's whole state is a status, two data bytes and a SysEx flag,
  so the next status byte always starts afresh.

#### Notes from two places
A note can be held by the panel's key, by MIDI and by the sustain pedal
at once, so each note keeps who holds it (`hold[]`, fm_play.c). A key
down from either sounds the note (again: the engine retriggers the voice
already playing it); a key up takes away only its own hold, and the
engine hears the note's off when no hold is left. So a MIDI note off
never ends a note the panel's key still holds, nor the reverse. While
the pedal is down, a released note passes to the pedal's hold, and the
pedal up ends every note it alone held. A note struck again under the
pedal starts again, and is the key's again.
- **All notes off** (CC 123, and 124 to 127) lets MIDI's keys go as
  their note offs would: notes the pedal holds go on until it is up.
- **All sound off** (CC 120) ends MIDI's and the pedal's notes and fades
  every voice out over the next block, as a stolen voice fades.
- **PRESETS, a program change and a mode change** release every voice,
  as in M5, and let the pedal's notes go; keys still down keep their
  hold, so their release later is an off the engine no longer needs.

#### The messages
- **Note on** with its velocity (1 to 127); a note on at velocity 0 is a
  note off; a note off's velocity is not used.
- **Pitch bend:** 14 bits, 8 192 the middle, +-the bend range, which is
  a setting (2 semitones by default) that registered parameter 0 (CC 101
  and 100 to 0, then CC 6) changes, up to 24. It moves every voice's
  pitch, phase-continuously, from the next block.
- **The modulation wheel** (CC 1) is vibrato: a 5.5 Hz sine on every
  voice's pitch, up to half a semitone at 127, stepped once a block.
- **Volume and expression** (CC 7, CC 11) scale the output after MASTER,
  each as its square; both start at 127, so without them nothing changes.
- **Program change** n selects test patch n (0 to 8), as PRESETS does;
  higher programs are ignored until M8's presets.
- **Mode messages:** 126 and 127 switch mono and poly, as SEL with MONO
  or POLY does; 124 and 125 (omni off and on) are only all notes off:
  the channel is the setting's.
- **Aftertouch** (channel and polyphonic) is parsed and not used.

#### The channel and the settings
`struct midi_settings` (midi.h) holds what MIDI uses: a version, the
receive channel (0: omni, the default; or 1 to 16), the bend range and
the controller map, all in bytes, so M7 can save it as it is and check
its version. Messages for another channel are counted and dropped; the
system messages are taken on every channel.

#### The controller map
A table of (controller, target) pairs in the settings, searched for each
controller change; the channel mode messages and the RPN controllers
(6, 100, 101) are fixed, as the specification has them. Default map:

| CC | Target |
|----|--------|
| 1 (modulation) | vibrato depth |
| 7 (volume), 11 (expression) | the output's level |
| 64 (damper) | the sustain pedal (down from 64) |
| 16 to 19 (general purpose 1 to 4) | KNOB1 to KNOB4 |
| 5 (portamento time) | KNOB2, the glide |
| 74 (brightness) | KNOB3, the modulators' level |

A knob's controller is an offset added to the panel's knob: 64 adds
nothing, 0 and 127 the ends of the knob's useful range (KNOB1 +-24
semitones, KNOB2 +-32 glide steps, KNOB3 -64 to +32 level steps, KNOB4
+-7 feedback steps), so the panel and MIDI can both move one. M8 adds
targets (and its macro controls) and MIDI learn by writing entries.

#### The screen
The keyboard on the panel screen shows the notes MIDI or the pedal holds
in cyan, at the keys that play them at the present octave (a key held on
the panel stays orange), and the event line shows each MIDI note as it
comes ("MIDI 1 note 60 on 100", "... off"). The engine posts each note to
a 16-entry queue main reads; a MIDI note before any panel event brings
up the panel screen, as a first event does.

#### Figures (fwtest 0.4.0, the branch at `02015ab`)
- **Latency**, from a note on's last byte to its first sample, 20 notes:
  1.718 to 2.897 ms, mean 2.308. By design at most two blocks (2.90 ms):
  up to a block until the engine's next callback takes the byte, then
  the block it renders plays after the one already playing.
- **The dense stream** (6 s of a full wire, 18 794 bytes, 3 272 note ons
  and as many offs on 16 voices): no byte dropped, no underrun, 48 571
  instructions a block on core 0 on average (the loaded measure's input
  takes 85 755). Its heaviest blocks are the panel screen's first whole
  drawing and the once-a-second heartbeat, both main's, as before M6a.
- **Cost at rest:** 1 838.6 instructions a block, 36 more than main's
  1 802.7 (+2.0%): the poll, its latch and the empty parse. Loaded:
  85 754.6, +1.0%. Code 18 408 bytes (+2 660), static RAM 143 256
  (+1 248: the two rings, the settings, the record, the hold table).
- **Every MIDI case's stream** gives the model's counters and messages
  exactly, junk and the SysEx flood included.
- **The loaded measure with MIDI** (since the pull request after the MIDI
  one): `tests/fw/scripts/perfload.txt` now ends with MIDI through the
  perf runs' window: 16 notes held, then a message every 2 ms (a note
  struck again, or the mod wheel and pitch bend moving), repeating every
  250 ms as the panel's part does, 80% of the wire. The heaviest steady
  input is the panel and MIDI together: 109 899 instructions a block,
  against 85 755 without MIDI (a wire filled to the last byte took 116 420
  in a one-off run). The M6 budgets (their own pull request) raise the
  loaded budget to 131 072 for it; the rest is M5's.

### 2026-10-24 M6b: MIDI out
- Facts: HW-72 to HW-74 (the SMK-37's MIDI OUT is a UART's transmit side;
  UART1 transmits by DMA, `TXADR` then `TXCNT`, and sets `CON0` bit 15
  when the last byte has gone, cleared by writing bit 13; the FM-1 has no
  MIDI OUT jack, so its bytes reach no socket); HARNESS.md's "MIDI
  output" (`--midi-out`, a byte every 320 us). PROVENANCE P-50, and P-43
  (the MIDI 1.0 specification) for the wire format, running status and
  local control.
- Sources: as M6a's; no other synthesizer's firmware and no MIDI
  library's source was looked at.

#### The path
One context does everything: the engine's block callback. It polls the
transmitter at the start of its events, takes the panel's events (and
queues what they send), takes MIDI in (and queues what thru passes on),
then polls again, so a message queued in a block has its first byte on
the wire in that block if the wire is free. Nothing else writes the
queue or the UART's transmit side, so there is no lock, and nothing ever
waits for the wire: a poll that finds a transfer still running returns.

#### The transmitter
A poll sends only when the last transfer has gone (`CON0` bit 15,
acknowledged with bit 13, every write keeping the UART and the receive
DMA on), never while one runs, and a running transfer's 16-byte buffer
is never touched. A transfer takes whole messages, up to 12 bytes (3.8
ms), so under a long stream a new message waits at most that plus a
block. No interrupt: the transmit interrupt's enable bit is known only
from the emulator (HW-74), the receive side is polled the same way
(M6a), and the polls a block gives are enough: the chunk lets the wire
stay busy across a block. Polling costs throughput, though: a transfer
can only start at a poll, so the wire idles from a transfer's end to
the next poll; under a stream the wire carries about 88% of its 31 250
baud (midiburst: 65 bytes in 23.6 ms). A full input wire passed on by
thru therefore builds the queue up slowly, and the policy (below)
applies. On the chip, what writing `CON0` during a transfer does beyond
the acknowledge, and whether a pin carries UART1's transmit side at all,
are open (Q-20); nothing here depends on the pin.

#### Running status
A channel message leaves out its status byte when it is the status sent
last, while messages keep coming; when a poll finds the transfer done and
nothing waiting, the wire has gone quiet and the next message carries its
status, so a receiver connected meanwhile is never left without one.
System common messages end running status, realtime messages don't. The
panel's note offs are note ons at velocity 0 (the receiver treats both
the same, M6a), so a run of notes keeps one status.

#### The policy when the wire can't keep up
The queue holds 32 messages (at most 96 bytes, 31 ms of the wire):
- **Merging:** a control change, pitch bend, pressure or program change
  replaces a waiting one of the same kind, channel (and controller or
  note), looking back from the newest over such messages only, so no
  value moves past a note, a mode message or a parameter-number sequence.
  Data entry (6, 38), the parameter numbers (96 to 101) and the mode
  messages (120 to 127) never merge: their order is their meaning.
- **The reserve:** 8 places are kept for note offs (and all notes off,
  all sound off). Any other message that finds the other 24 full is
  dropped and counted.
- **Never a stuck note:** a note on dropped marks its note, and its note
  off is dropped too. A note off that finds all 32 full drops the newest
  waiting message that ends no notes (a note on so dropped marks its
  note). Only a queue of 32 note offs alone could lose one; it is counted.

#### What the panel sends
On the out channel (1 by default):
- **Keys:** a note on at velocity 100 (the keys have no velocity) and a
  note on at velocity 0 when let go, for the note the key started, so an
  octave change while it is held can't leave it on. OCT- and OCT+ only
  move the notes sent.
- **KNOB1 to KNOB4:** as the first controllers M6a's map routes to them
  (16 to 19 by default; a changed map changes them), each value the
  inverse of how MIDI in reads it: the value nearest 64 whose offset is
  the panel knob's position, held to the knob's span. So a far end with
  its own knob at rest takes the position the panel's knob has; a value
  is sent only when it changes. tools/midi_model.py checks every
  position.
- **PRESETS:** a program change, the test patch's number.
- **SEL with MONO or POLY:** the mode messages 126 (value 1) and 127,
  which MIDI in takes as mono and poly.
- **Pitch:** the panel has no bend or pitch wheel; KNOB1 transposes and
  goes as its controller (a bend could not carry ±24 semitones at the
  default range of 2). Not sent: MASTER (the device's own output level,
  not in the map), ALGORITHM (no controller in the map yet; M8), PLAY's
  test tone, SELECT.

#### Thru and local control
- **Thru** (off by default) passes on every message MIDI in parsed, on
  every channel, before the receive channel's filter, realtime and system
  common included, as messages merged with the panel's at message
  boundaries (never bytes, which would break running status). A SysEx is
  not passed on: the parser keeps none of its bytes (M6a); it is counted.
  Only bytes received at MIDI in go through thru, never the firmware's
  own messages. A cable from out to in with thru on would repeat
  messages without end, as on any instrument with soft thru.
- **Local control** (on by default; CC 122 sets it from MIDI, as the
  specification has it): off, the panel's keys, knobs and PRESETS go to
  MIDI out only. The engine keeps the knob positions it last took and
  its patch, and a key let go still ends its note if it had started one
  before. MIDI in still plays, so a sequencer can play the engine from
  the panel's own notes. On again, the engine takes the panel's knobs
  where they are.

#### The settings and the screen
`struct midi_settings` (version 2) adds the out channel (1 to 16), thru
and local control after M6a's fields, all bytes, for M7 to save. The
thru test build sets thru on and the out channel to 2. The panel
screen's bottom line shows them ("MIDI out ch 1  thru off  local on"),
redrawn when they change.

#### Figures (fwtest 0.5.0, through `FWTEST_IMAGE` before its pin)
- **Latency** from a key going down to its note on's first start bit, 20
  keys: 3.260 to 5.286 ms, mean 4.196: the key's debounce (2.5 to 4.5 ms,
  M3), then up to a block until the engine takes the event; the byte
  starts in that block.
- **The burst** (94 messages in one block): 28 merged, 18 dropped (the 10
  note ons past the room, 6 more and the controller and bend to make room
  for note offs), 16 note offs dropped with their note ons, none lost; 16
  notes sent and each ended, 77 bytes in 10 transfers, 31 status bytes
  left out.
- **Cost at rest:** 1 863.9 instructions a block, 25 more than M6a's (the
  two polls of an empty queue); loaded 110 207.6, +0.3% (the perf input's
  keys and knobs now also go out). Code 20 144 bytes (+1 736), static RAM
  143 776 (+520: the queue, the transfer buffer, the dropped-note bits,
  the record).
- **Never disturbs audio:** no underrun in any case, audiogold and fmgold
  byte for byte as before.

### 2026-10-24 M7: flash storage
- Facts: HW-5 (the code window shows the chip from offset `0x4000` in
  fwtest), HW-47 (SPI0, the chip select, the commands); and SR-9's answer,
  HW-76 to HW-82 (#97, read from its branch before it merged): the part
  (the P25Q80H, if the FM-1 carries it: Q-21), its times and endurance,
  its command rules, nothing from the window while the flash is busy,
  the FM-1's flash layout, the window encrypted and cached on the chip,
  fwtest 0.5.0's chip; HARNESS.md's `--flash`, `--flash-out` and its
  known gap around an unused volatile read. PROVENANCE P-55.
- Sources: our own design. No other firmware's store, no file system's
  or EEPROM-emulation library's source, was looked at for it.

#### Nothing runs from the window
On the chip the code window is the flash itself, and while an erase or a
program is in progress nothing may be read through it, on either core
(HW-79); a 4 KiB erase takes up to 12 ms, longer than a half of the audio
buffer lasts. So the firmware no longer reads the window once main runs
(the first of HW-79's ways to keep the audio going): the
linker places every instruction and constant in RAM (`.data`, from
`__ram_code_start` to `__ram_code_end`), and the start-up copy that
already copied the initial data copies them too (24 KiB, about 63 us more
at the start). Only `_start`, the stack fill and `sb_start` run from the
window (`.boot.text`, 120 bytes). Core 1, the interrupt handlers and the
vector table's addresses are all RAM addresses. The store reads the chip
through SPI0's read command, never through the window, as HW-81 asks
(the window is encrypted and cached on the chip). The wipe test build
proves the rest:
it erases its own image once main runs, and the heaviest load with saves
then plays on with no underrun and no fault. `tools/build.sh` still
counts all of it as code, and `ram_code` says how much runs from RAM;
since it takes RAM, `tools/perf.py` counts it in static RAM too.

#### The store
A ring of 18 sectors of 4 KiB, chip offsets `0xEA000` to `0xFBFFF`
(docs/STORE-FORMAT.md has the bytes). The region is the stock layout's
user patch region (HW-80): out of the boot area, the Bluetooth sector
and the per-unit last sector. A first draft used the chip's last 64 KiB,
which HW-80 showed includes that last sector; the move was one define.
Where our own image sits on the chip is M9's to settle (Q-24), so the
region stays one definition. The choices:
- **Append only, CRC on everything.** A record is never changed once
  written, so a power cut can only leave the newest record incomplete;
  its CRC-32 fails and the copy before it is read. No commit bit, no
  second write to the same bytes: that keeps the store right whatever a
  program cut short leaves in the bits, and whatever the chip does when a
  program meets bits that are not erased.
- **Read whole sectors, in 16-byte steps.** A torn record can leave erased
  blocks inside it, so an erased block is no sign that a sector's records
  have ended; the reader goes on to the sector's end, and the head takes
  new records only after its last byte that is not erased. A torn record
  therefore never closes the head. (An earlier draft closed it, and the
  sweep's design showed the trap: a cut during a compaction would leave a
  closed head with live records still in the sector after it, and every
  save after it refused.)
- **The ring and its compaction.** The sector after the head holds nothing
  live, always: when the head is full, that sector is erased and becomes
  the head, and the live records of the sector after it are copied in.
  All the live records together (16 patches, the selection, the
  settings, a reset) take 2 160 bytes, so they always fit one sector with
  room to spare; `tests/test_store.py` checks it. A cut during a
  compaction leaves the originals where they were; the next save finishes
  the copying first.
- **Reset is a record.** The factory reset writes one record that voids
  every older one, so it is as safe against a cut as any save, and wears
  nothing. A reset is always copied forward.
- **The part's rules** (HW-78; since SR-15, HW-121 and HW-124 for both
  parts): a write enable before every erase and program, a page program
  never past its page, the end of each waited for on the status
  register's WIP bit, never by a delay, allowing 3 s (`BUSY_LIMIT_TICKS`),
  far past either part's longest maximum (12 ms). Start-up reads the
  JEDEC ID, then status 1 (`0x05`) and status 2 (`0x35`) into the
  record's `status`. The store writes to the two parts `STORE_PARTS`
  lists (store.h: the P25Q80H, `0x856014`, and since SR-15 the UC25HQ80,
  `0xB36014`, HW-120). For the commands it sends they differ only in the
  ID (HW-122). Any other ID is read but never written (`STORE_ERR_PART`).
  If any of BP0 to BP4 (status 1, `0x7C`) or CMP (status 2, `0x40`) is
  set, nothing is written (`STORE_ERR_PROTECT`). The store never writes
  the status register (no `0x01`, `0x31` or `0x15`). Refusing whenever
  any protection bit is set is coarser than the protection table both
  parts share (HW-122), and it is meant to be: it can't misread the
  table. A region the bits leave unprotected is still refused, which
  costs nothing on a unit m-bootloader has written (HW-123: nothing is
  protected after it). Since SR-15 each erase is read back after its
  wait: the sector must read all `0xFF` through `0x03`, or the erase
  counts as failed (HW-124 item 4), as a program that reads back wrong
  does. Until then an erase was checked only through the header
  programmed after it, and a protected erase does nothing without the
  busy bit showing it (HW-121). The read-back is 4 100 bytes on SPI0
  after each erase: in fwtest, where a byte takes no time of its own
  (HW-83), some 80 000 instructions, about 0.35 ms at 240 MHz, beside the
  erase's 12 ms; on the chip SPI0's clock sets it (HW-124 item 6, not in
  this change), about 1.4 ms at 24 MHz. Main runs it with the interrupts
  on, as it waits for the erase, so the audio, the tick and the scan go
  on (R-STORE-7: the busy and wipe cases still pass).
  SPI0's sending side never reads `BUF`, which also keeps clear of fwtest
  0.5.0's gap around an unused volatile read (HARNESS.md).
- **Start-up** reads the ID, 18 headers and every valid sector: 20 us
  for an empty store, 5.8 ms for a full one (72 KiB
  through SPI0 in fwtest, where a byte takes no time of its own, HW-82;
  on the chip SPI0's clock sets it).
- **Main does it all.** The engine never waits: it takes the panel's save
  in its block callback, stores the patch in RAM at once, and adds one to
  that slot's save count; main's loop writes every slot whose count moved
  (and none a later reset voided), then the reset. The selection and the
  settings are compared once a second. While main waits for the flash the
  interrupts stay on, so the audio, the tick, the scan and core 1 go on;
  the screen waits.

#### Wear
- **Limits by kind** (`STORE_SETTLE_S`, R-STORE-8): the selection and the
  settings are written only when they changed, at most once every 2 s; a
  patch only when the player saves it; a reset only when asked. Under
  PRESETS turned four times a second for 6 s, the selection was written 4
  times (wear).
- **Spread:** every sector is erased in turn (the ring), so each takes one
  erase in 18. The model writes 6 000 random saves with erase counts
  within one of each other (`tests/test_store.py`).
- **Lifetime:** the P25Q80H takes 100 000 erase cycles a sector (HW-77).
  A sector has 1 920 bytes for new records after the largest compaction,
  so the region takes 18 x 1 920 x 100 000 bytes of records: the
  selection and the settings both changing every 2 s without a break
  (96 bytes in 2 s) last about 2.3 years; a patch saved every 10 s
  without a break, about 8.6 years. Real use is a small part of either.

#### The panel (minimal; the full UI is M8)
- **Save:** hold SAVE and press one of the 16 leftmost keys (KEY1 to
  KEY16, lower and raised keys counted left to right, HW-37): the patch
  playing now is
  saved to that user slot, with the algorithm ALGORITHM chose and the
  mode SEL with MONO or POLY chose; no note plays while SAVE is held. The
  screen's event line says "saved to slot n" (or "SAVE FAILED, slot n").
  KNOB1 to KNOB4 stay offsets over the patch, as they are over every
  patch, and are not saved, so a saved patch never takes them twice.
  The program stays as it was.
- **Programs:** PRESETS and program changes reach the test patches (0 to
  8), then the user slots that hold a patch (9 to 24), and since M8b the
  presets (25 to 88, P01 to P64 on the screen). PRESETS stops at
  the first program and the last one that holds a patch: it never wraps
  from one end to the other (the owner's answer on #126, 2026-10-25;
  until then it went round the ends). A program change selects its
  program directly, so the ends don't concern it.
- **Factory defaults:** hold SAVE and HOME together for 2 s: every user
  slot empty, the settings' defaults, the first program; the event line
  says "factory defaults". Held less, nothing happens.
- **Kept without asking:** the selection and the settings, once they have
  stayed changed for 2 s (above).

#### How it is tested (R-STORE-1 to R-STORE-9)
`tools/store_suite.py`, run by `tools/fw-suite.py` after the suite, since
its runs need the flash another run left. `tools/store.py` reads every
image the way the firmware does, and where a case starts from an image it
made, its model also predicts the image the firmware leaves, command for
command; the two are compared byte for byte. The sweep's save takes a new
head, erases it and copies 17 live records (28 commands); the cut test
build stops after each command and part way through each page program
(109 cuts), and the model adds programs with half their bits cleared and
erases half done (29 images). Every image holds the old patch or the new
and nothing else changed, and the shipping image starts from each one,
finds what `tools/store.py` finds, and saves again. The busy test build
makes each erase take 12 ms and each page program 3 ms, the part's
longest (HW-77; an earlier run at 400 ms an erase passed too). Under
audioload's input (test patch 6 on all 16 voices, core 0 at 82 000
instructions a block on average), SAVE held three times makes the keys it
strikes meanwhile save to their slots: 24 saves, one of them erasing a
sector (18 ms), and still no underrun, the longest fill 419 us of a
1 451 us block, and every tick within 2 time base ticks. The screen's
event line after a save, a refused save and a reset is checked against
golden images.

#### Open (SR-9's open questions)
- **Q-21, the part:** read on a unit; the ID check above refuses to write
  to any other until its datasheet is read.
- **Q-22, SPI0 on the chip:** how the window's controller hands the flash
  to SPI0 and back, SPI0's clock and mode, and the chip select (fwtest
  takes PD0; on the chip it may be another pin). The driver writes only
  HW-47's bits; what the chip needs goes in `store_init` and the select
  functions. Core 1 already runs from RAM, so it needn't be stopped.
- **Q-23, write protection:** if a unit's protect bits are set, a write
  reads back wrong and the save is reported failed (never silently lost).
- **Q-24, updates:** whether an update rewrites the user region decides
  whether saved patches survive one (M9).

### 2026-10-25 M8a: the store moves to the unused region

The owner prefers that our firmware never erases the stock firmware's
saved patches. M7's store took the stock user patch region (HW-80,
`0xEA000` to `0xFBFFF`, 18 sectors), so it erased them. HW-80 names one
other region a store may take without touching anything of the stock
firmware's: `0xFC000` to `0xFEFFF`, 12 KiB, three sectors, ending before
the per-unit last 4 KiB. The store now lives there (`STORE_BASE`,
`STORE_SIZE`; the format is unchanged), and the image is still linked to
end before `0xEA000`, so neither touches the user patch region. No unit
runs a build with M7's store yet, so nothing is migrated.

**Does it fit?** Everything the store keeps live at once is 16 patches
(a record of 128 bytes each), the selection (32), the settings (64) and
a reset (16): 2 160 bytes. A sector holds 4 080 bytes of records after
its header. The ring moves the live records of the sector after the new
head into it, so a sector is never erased with anything live in it; even
when every live record has to move, the new head keeps 1 920 bytes for
new records, more than the largest record (128). So no save is ever
refused for want of room, with any mix of slots in use; the model and
the store suite's `full` and `wear` cases run on three sectors.

**Wear life,** counted as M7 counts it (its "Wear", a bound): each
sector takes 100 000 erases (HW-77), and each erase gives at least the
1 920 bytes left after the largest compaction, so the region takes
3 x 1 920 x 100 000 bytes of records, a sixth of M7's 18 sectors:

| Use, without a break | Life, 3 sectors | (M7's 18 sectors, same bound) |
|---|---:|---:|
| the selection and the settings both changed every 2 s (the most `STORE_SETTLE_S` allows; 96 bytes in 2 s) | 0.38 years (3 300 hours) | 2.3 years |
| a patch saved every 10 s | 1.4 years | 8.6 years |
| a heavy day: 300 program changes, 20 settings changes, 20 saves (about 13 KiB of records) | about 117 years | |
| two hours a day of the most the limits allow | about 4.6 years | |

The bound is pessimistic: `tools/store.py`'s model, with all 16 slots,
the selection and the settings live, takes about 3 000 to 4 000 bytes of
new records an erase, not 1 920, so real lives are about 1.6 to 2 times
these. So the smaller region meets the 16 slots, the selection and the
settings with a long life in real use; the cost is the margin for abuse.
If that ever matters, `STORE_SETTLE_S` is the lever: at 10 s the
selection's and settings' worst case lasts five times longer.

**What is not known** (HW-80): FM-1-RE says the stock layout's free
regions have not been validated as safe for writes from outside the
stock firmware, and whether an update rewrites any region past the app
area is open (Q-24). The unused region is no worse known than the user
patch region on either count.

**Tests.** The constants test checks the store lies past the user patch
region and before the last 4 KiB, and the image's window ends where the
user patch region begins. The store suite's `persist` and `wear` cases
start with the user patch region full of a pseudo-random pattern standing
for the stock firmware's saved patches, and every run checks the chip
outside the store is unchanged, so an erase or a write there would fail.

### 2026-10-25 M8a: the screens' framework

The instrument's interface (docs/M8-PROPOSAL.md, with the owner's
answers in docs/prompts/M8a.md), first its frame. `firmware/src/ui.h`
and `views.c`; M3's panel screen (`panel.c`) is gone.

- **Who owns what.** The engine owns the interface's state (`struct
  fm_ui`: the screen, the selected operator, the page, the settings
  row). It already takes the panel's events in order in its block
  callback, from its own queue; so a screen button and a knob turned just
  after it reach it in that order, and what a knob does always matches
  the screen it was turned on. Had main decided the screen, an EDIT
  press and a KNOB1 turn in one block could reach the engine as a macro
  turn. The engine adds one to `fm_ui.seq` on every block that took an
  event or a MIDI message, and wakes main. Main only draws: it copies the
  state when `seq` holds still, works out what each part of the screen
  should show, and redraws only the parts that changed.
- **The frame.** Every screen has a header (rows 0-25: the program's
  number, `001` to `009` for the test patches and `U01` to `U16` for the
  user slots, its name at double size, the mode and the octave), a body
  (rows 26-189, the screen's own), an event line (rows 190-201) and the
  bottom strip (rows 202-239), which names what KNOB1 to KNOB4 do on this
  screen, with their values at double size, in four columns of 60
  pixels. Until M8a's patch view lands, KNOB1 to KNOB4 keep M5's meanings
  on every screen, and the strip says so.
- **Parts, frames and the budget.** M5's rule stays: what is marked is
  drawn at most once a 16 ms frame, part by part, and no part starts in
  an audio block once drawing has taken 4 352 time base ticks of it. A
  whole new screen is many parts: the header; the body cleared in four
  bands; the body drawn into the frame buffer; the body sent in four
  bands; the event line; the strip. A knob turn redraws only the strip's
  values and sends their 16 rows. The first build drew a body as one part
  of 11 300 ticks; split so, the longest part is 3 800 ticks (the strip's
  names and values after a change of screen), within the budget, and a
  block's drawing is under two budgets. Two things made that: a fast path
  for double-size text (a glyph pixel is one 32-bit store of two
  pixels) and not padding the body's text, whose bands are cleared
  anyway. A body is marked once a change, since its parts may take
  several blocks: marking it again while they were under way restarted
  its clearing and never finished (found in the first run).
- **LEDs.** A held button or key is fully lit, the shown screen's button
  lit, and on EDIT and ENV the selected operator's key at half. Main
  sets them (`input_led` is main's only) as it takes each event, from
  the same events the engine takes, so they change within R-LED-3's
  1 ms, not a block later when the engine's state arrives.
- **The heartbeat** stays the test screen's: main no longer draws it
  once the instrument's screens show (it drew over their rows 200-215
  every second).
- **The record.** `sb_ui` at `0x01C00870`, after the store's: the screen
  drawn, the parts, rows sent, the longest part and which, the most
  drawing in one block, the LED changes and messages.
- **Costs.** Code 26 700 bytes (+2 560). The steady state (the test
  screen, no input) 1 872 instructions a block, as before; the loaded
  measure 98 265, down from 107 590, as the screens redraw less than the
  M3 panel did under the same input.

### 2026-10-25 M8a: the macros

KNOB1 to KNOB4 on the patch view are four macros (docs/M8-PROPOSAL.md),
unless the settings say "Knobs: direct" (M5's pitch, glide, depth,
feedback). The owner's answer: they stay offsets, never written into the
patch on SAVE. `fm_play.c`, "The macros".

- **What each moves.** BRIGHT is M5's KNOB3 renamed: every modulator's
  level, -64 to +32 steps of 0.75 dB. COLOR, -32 to +32: above 0 every
  modulator's ratio is multiplied by 2^(c/64), up to the square root of 2
  at +32, an irrational factor, so the sidebands leave the harmonics the
  same way on every patch; feedback rises by up to 3 steps. Below 0 each
  ratio moves toward its nearest whole number (or a half), so a patch
  with fractional ratios grows purer and a harmonic one is unchanged.
  SHAPE, -64 to +64, moves the carriers' time codes and levels toward a
  pluck (attack 0, decay 1 to 56, decay 2 to 72 with the held level to
  0, release 40, the level after decay 1 toward 96) or a pad (attack 80,
  about a second; the levels after decay 1 and held toward 127; release
  96, about four seconds), in proportion. MOTION, 0 to 64: vibrato at
  M6a's 5.5 Hz, up to half a semitone more than the wheel's, and the
  carriers but the first detuned up to 12 cents, above and below in
  turn, so a held note moves and, with several carriers, beats and
  widens.
- **Exact at 0.** The operators with COLOR and SHAPE applied are worked
  out once a change (`shape_ops`: the patch, the algorithm or a macro),
  copying the parsed patch's values and changing only what a macro moves.
  At 0 nothing moves, so the notes are the stored patch's bit for bit:
  audiogold and fmgold are unchanged, and the macros case plays a note,
  turns BRIGHT and COLOR and back, and gets the first note again, sample
  for sample. COLOR also reaches the notes already sounding (their
  ratios); SHAPE the notes started after it.
- **MIDI.** Controllers 16 to 19, as M6a mapped them to the four knobs,
  over each macro's own range by M6b's rule (64 is 0). SHAPE and MOTION
  have more positions than a controller has values, so one position
  (+63) goes out as the next (+64). With the macros, the default map's
  74 (brightness) moves BRIGHT, and 5 (the glide time) nothing.
- **The setting** is `struct midi_settings`' last byte, always 0 in
  version 2, so a version 2 record reads as version 3 with the macros
  (R-STORE-6). M5's and M6's cases written for the direct controls start
  from a flash chip holding settings that say "Knobs: direct", made by
  `tools/store.py` (the store's own record): the shipping image, as a
  player who chose it.
- **Measured** (the macros case, test patch 1, MIDI note 70): the share
  of power above 7.5 f0 0.067 at 0, 0.373 at BRIGHT +20; partials 0.005
  f0 off the harmonics at 0, 0.29 at COLOR +32; test patch 0: attack to
  -3 dB 2.9 / 0.0 / 637 ms and release to -60 dB 41 / 17 / 2 520 ms at
  SHAPE 0 / -64 / +64; the pitch swings 50 cents at MOTION +64.

### 2026-10-25 M8a: the operator view (EDIT)

- **What it shows.** The algorithm as boxes and lines, laid out from
  `fm_algorithms` alone (a carrier's row is 0; a modulator sits a row
  above what it modulates, in its column or the next free one), centred
  in the body; the selected operator outlined twice in yellow; the
  feedback operator's hook in cyan; a line with the selected operator's
  values; the strip with the page's four values.
- **Live levels.** While EDIT shows (only then), the engine writes each
  operator's loudest gain over the voices sounding, after a block is
  rendered (`fm_op_level`; about 100 compares a block). Main reads them
  every 50 ms and redraws only the meters that moved, each one a
  rectangle of a box's width and 3 rows. `lcd_send_rect` sends a
  rectangle: HW-31's column and row address set bound the memory write,
  and the rectangle is copied first into a staging buffer (7 680 bytes,
  a chunk), since the frame buffer's rows are apart. A meter costs about
  90 ticks; whole rows would have meant 16 to 120 rows for six meters.
  The proposal's figure assumed rectangles; this is how it gets them.
- **Editing.** The edits go to a copy of the program playing now
  (`edit_raw`), which is what the screens show and SAVE writes; each one
  parses the copy again (about 5 000 instructions, once a detent). Another
  program discards them: the patch is parsed again from its stored bytes.
  So editing never changes a test patch or a user slot until SAVE.
  Ratios step through the whole numbers 1 to 16 and a half (COARSE and
  FINE reach the rest); a fixed frequency steps a semitone a detent.
- **Knob positions.** Since this part, KNOB1 to KNOB4's positions as the
  patch view's controls move only with turns on the patch view, held to
  their span: turning a knob on EDIT edits the operator and leaves the
  macros where they were, and turning back from past an end answers at
  once (M5 counted every detent since start). MIDI out sends the same
  values as before for the same turns.
- **Measured** (edit, test patch 0): ratio 2 932.32 Hz (466.16 x 2);
  level 103 -18.06 dB; detune +50 49.98 cents; fixed 440.00 Hz; held
  103 -18.06 dB; velocity 7 -10.24 dB at the panel's velocity 100.

### 2026-10-25 M8a: the envelope view (ENV), and a line that never ended

- **The drawing.** An envelope's stages are drawn as wide as their time
  codes (plus 8, so a code of 0 still shows), the held stage a fixed 36
  pixels, the height the level code. Since a code is 2^(t/8) ms, the
  time axis is logarithmic, as the proposal said it would be. The pitch
  envelope is drawn about its middle (P0 to P3, signed), the glide as a
  ramp over its code.
- **The dot.** While ENV shows, the engine writes the newest sounding
  note's stage and level for the envelope shown (the operator's gain in
  the attack, its attenuation after; the pitch envelope's level). Main,
  every 50 ms, places the dot along the stage's segment by how far the
  level has come between the stage's ends, keeps the 25 pixels under it,
  and on a move puts them back and sends two 5 x 5 rectangles, so the
  graph is never redrawn for it (about 500 ticks, the stage's name
  included). The graph, when an edit changes it, is cleared in two
  halves, drawn and sent as parts of their own (each within the budget;
  as one part it took 4 800 ticks).
- **Editing** works as the operator view's, on the program's copy: the
  four rates or three levels of the selected operator; the pitch
  envelope's three rates and depth, or its four levels; the glide time.
- **The line.** M2's `gfx_line` tested its second step against the
  error its first step had just changed, so on some lines it stepped
  past the end and never stopped: about one random line in five. M2's
  test screen and M8a's algorithm diagrams happen to draw only lines it
  finishes (all ten algorithms checked, on both screens), so the first
  envelope drawn after an edit was the first to hang main, in the env
  case. Now both tests use the error from the step's start, the usual
  form. The test screen's two diagonals change by a few pixels (their
  golden images with them), and so do the diagrams' lines.
- **Measured** (env, test patch 2): ATTACK 40 -> 56 makes the attack x
  4.13 (21.8 -> 89.9 ms to -3 dB); RELEASE 64 -> 48 x 0.27; HOLD 87 -> 71
  -12.04 dB; DEPTH 12, P0 -127, RATE1 56: -9.6 semitones 10 ms in, 0.00
  by 390 ms.
- **Also:** main now serves the panel's events from before its loop
  began (a key pressed during the boot screens shows the instrument's
  screens at once, rather than at the next event).

### 2026-10-25 M8a: the live spectrum

- **The transform.** `spectrum.c`: a Hann window and a 256-point
  radix-2 FFT in fixed point. Samples are the output's top 16 bits;
  every stage halves its results, so values stay within 16 bits, their
  products within 32, and no float is needed (the proposal assumed the
  float unit; this is simpler and exact from run to run). A full-scale
  sine's peak bin comes out near 2^26 of power; the bars show 60 dB
  below that over 40 rows.
- **The bars.** 56 bars, 4 pixels apart, from 200 Hz to 20 kHz on a
  logarithmic axis (the owner's answer). Bins are 172 Hz apart, so the
  bars below about 700 Hz are narrower than a bin: each takes the power
  between its two nearest bins, in proportion; above, the strongest bin
  in its band. A pure tone therefore shows as a hump on the log axis,
  narrow at the top: its tallest bar is its own (the spectrum case
  checks the test tone's 1 kHz lands there), and the Hann window's
  leakage falls 31 dB within 3 bins.
- **Cost.** Before each transform main asks the engine for a capture:
  the next 4 blocks' output (256 samples), or silence at rest; between
  captures the engine copies nothing. Main runs at most a transform each
  33 ms, as three parts, each within the drawing budget: the window and
  the first four of seven stages; three more; the split into 128 bins
  and the bars. The transform is of 256 real samples as 128 complex ones
  (the even samples real, the odd imaginary) and a split, half the
  butterflies of a 256-point complex transform; a butterfly is 25
  instructions. Only the bars that moved are redrawn, each as the column
  between its old height and its new, and only the spectrum's 40 rows
  are sent (19 200 bytes; on the chip's bus about a third of the time at
  30 a second, as the proposal said). At rest, with the bars down, it
  makes one capture after each piece of new work (a note starting is
  one) and nothing else.
- **Against the proposal's figures.** RAM: 2 048 bytes (the capture 512,
  the transform 1 024, the twiddles 512; the window and the bins' power
  are computed as needed), the proposal's "about 2 KiB". CPU, with the
  test tone alone (the spectrum case, core 0's instructions a block over
  its steady tone, with and without the spectrum): 1 489 a block, about
  2.3 times the proposal's 650; the proposal counted the transform
  alone, at about 15 000 instructions, where this one, with the window,
  the bars and their drawing, is about 32 000.
- **Under the heaviest input** (the loaded measure) it costs more than
  that: part 4 measured 105 721 instructions a block; this part 110 268
  (+4.3%). Built without the spectrum, 104 648 (main's bookkeeping is
  lighter now: it skips everything when the engine's state hasn't
  moved); transforming without drawing, 109 757; the transform as one
  part instead of three, 110 157; capturing only what a transform needs
  rather than every block, 110 268. So under that input the spectrum
  adds about 5 600 a block where the same work adds 1 489 with the tone
  alone. Not explained yet: one candidate is core 0's wait for core 1 in
  the audio interrupt, which may lengthen when main is busy (fwtest takes
  the cores in turns). The loaded budget moves in its own pull request,
  and the owner is asked.
- **Waking.** The frames used to set the tick's wake directly, so a
  frame's own wake could replace the live parts' and main then slept
  until the next event: 9 transforms where 40 were due. Now every wake
  keeps the sooner of two, and the live parts ask again after each frame
  (the operator view's meters and the envelope's dot update more often
  for it too).

### 2026-10-25 M8a: the settings screen

- **Rows:** every setting of `struct midi_settings` the panel had no way
  to reach (in and out channels, thru, local control, bend range), the
  knobs' mode, the store's use and the factory reset. SELECT picks a row,
  KNOB1 changes it one step (the on/off rows by the turn's direction);
  the engine changes the settings, as MIDI's controllers already did, so
  M7's saving keeps them 2 s after the last change.
- **Factory reset:** the owner moved it here with a confirmation. KNOB1
  on the last row asks, the screen says what SAVE will clear, SAVE does
  it, and HOME, SELECT or another screen cancels it. M7's hold of SAVE
  and HOME is gone; the store suite's reset case now asks, confirms and
  cancels this way.
- **Drawing:** the eight rows are two parts (the body draws the title and
  the first four, the info line's part the rest), each within the budget;
  as one part they took 5 700 ticks.

### 2026-10-25 ARP: the arpeggiator

Our own design, from docs/ARP-PROPOSAL.md and the owner's answers there
(`firmware/src/arp.c`, `arp.h`; hooks in `fm_play.c`, `fm.c`, `views.c`).

- **What it plays:** while it is on, a note held by a key, by MIDI in or
  by the pedal is the arpeggiator's input, not a note for the engine. It
  plays them one at a time (CHORD: all together) on a clock, each as an
  ordinary note on and off to the engine, so every patch, macro and voice
  rule applies. Its own notes reach the engine past `hold[]`, so a held
  key and the arpeggiator's note of the same pitch never end each other.
- **Modes:** UP and DOWN by pitch; UP/DOWN up then down, the ends not
  repeated; ORDER as the notes came; RANDOM a fixed linear congruential
  generator (x = 1664525 x + 1013904223, the note at (x >> 8) mod the
  count), seeded with 1 each time the arpeggiator starts, so a test can
  predict it; CHORD every note held each step. With 2 to 4 octaves the
  pattern runs through the notes, then again an octave up, and so on
  (CHORD moves the whole chord up an octave a step). A note above 127
  plays octaves lower.
- **Rates:** 1/2, dotted 1/4, 1/4, dotted 1/8, 1/8, 1/8 triplet, dotted
  1/16, 1/16, 1/16 triplet, 1/32: 48, 36, 24, 18, 12, 8, 9, 6, 4 and 3
  MIDI clock pulses (24 a beat), in the owner's order. The grid is whole
  multiples of the step from the clock's zero, so a rate change takes
  effect at the next multiple of the new step, and on MIDI clock the
  steps fall on the sender's beats.
- **Gate and swing:** each note sounds GATE% of its step (10 to 100%),
  ending at the next step at the latest; SWING (0 to 75% in 5% steps)
  delays every odd step of the grid by that share of a step.
- **Latch:** with LATCH on, letting go of the keys keeps the notes
  playing; the first key down after none starts a new chord. Turning
  LATCH off lets go of every note no key holds.
- **Starting and stopping:** a short press of ARP (released within
  500 ms) turns it on or off; held 500 ms, ARP shows its screen instead
  and leaves it as it was. Turned on, the notes held leave the engine
  for the arpeggiator; turned off, every note it played ends and the
  notes held sound again (the panel's only with local control on). On
  the internal clock, the first note held after none starts the pattern
  and the clock at once, so the first note plays at the next block, not
  at the next step; on MIDI clock it waits for the next step.
- **The clock, in exact units:** the clock's position is pulses and
  units of a pulse, 3 750 000 units a pulse. At t beats a minute a frame
  (24 MHz / 544) is 34 t units, exactly (t x 24 / 60 x 544 / 24 000 000
  = 34 t / 3 750 000), so the internal clock never drifts: step k of a
  1/16 at 120 beats a minute is at 5 514.705... frames x k, rounded up to
  the frame, for ever. Only 32-bit divisions are needed (the firmware has
  no 64-bit one).
- **Sample-accurate steps:** each block, before the voices are
  rendered, the clock moves on 64 frames and every step and gate end in
  that span plays at its frame. A start or release at frame f > 0 is
  pending on the voice (`struct fm_voice`'s `pending`, `at`, and for a
  voice still sounding each operator's level with the velocity and a
  pointer to the shaped operators, unchanged until the block is
  rendered, so a voice keeps 40 bytes for it, not its operators): the
  renderer renders frames 0 to f - 1 as the voice was, takes the start
  or release, then renders f to 63 (`fm.c`, `render_pending`, its own
  copy of the operator loop, so the whole-block path is unchanged). A
  fresh voice is silent before f; a voice taken again (the same note,
  or mono) keeps its phases and starts its attacks from its envelopes'
  levels, as at a block's start. What is not to the frame: a stolen
  voice still fades for a block first (R-FM-4); a release before a start
  on the same voice in one block is dropped (the start wins); and for
  the frames before a start on a voice still sounding, the pitch is
  already the new note's (the pitch is worked out once a block). MIDI
  out sends once a block, so the arpeggiator's notes there are within a
  block and a byte of their frame.
- **MIDI clock (the owner's answer: followed whenever it arrives):**
  - a 0xF8 while on the internal clock starts following it, the position
    taken to the next whole pulse; then each 0xF8 is a pulse, and the
    position never runs more than a pulse past the last clock (so a
    late clock delays the steps, never skips them), and jumps to it if
    it was behind;
  - between clocks the position moves at the rate of the last 24 clocks
    (frames between their arrivals, at the block they were taken), so
    steps between clocks still fall on their frames;
  - Start (0xFA): the next 0xF8 is pulse 0: the pattern and the grid
    start again there. Continue (0xFB): the next 0xF8 carries on from
    where the position is;
  - **when the clock has stopped** (the firmware side's choice, open in
    the proposal): a Stop (0xFC), or 250 ms (172 blocks) without a 0xF8
    while following it. Then the internal clock takes over at once, at
    the settings' TEMPO (not the MIDI clock's last tempo, so what plays
    is what the screen shows), from where the position is: the step
    playing ends at its gate and the next falls where the internal
    tempo puts it. After a Stop, clocks are ignored until a Start or
    Continue (a sender that keeps its clock running while stopped would
    otherwise take it over again). Notes still sounding end at their
    gate.
- **Per patch, per instrument (open in the proposal):** a patch keeps
  on or off, LATCH, MODE, RATE, OCTAVES, GATE and SWING (the patch
  format's version 2, docs/PATCH-FORMAT.md: version 1's three reserved
  bytes, so patches keep their 112 bytes and the store its records'
  sizes). TEMPO and what MIDI out sends belong to the instrument (the
  settings, version 4): changing patch while playing doesn't change the
  tempo, and MIDI out's choice is about what is plugged in. A patch saved
  before ARP (version 1), a preset and every test patch take the
  defaults: off, no latch, UP, one octave, 1/16, no swing, gate 50%. The
  ARP screen's changes are edits of the program, as the operator view's
  are: SAVE keeps them, another program discards them.
- **MIDI out (the owner's answer):** the arpeggiator's notes go out on
  the out channel by default, and the keys held don't; the setting
  (MIDI OUT: keys) sends the keys held instead, and the arpeggiator's
  notes don't. A key's note off goes out only if its note on did, so
  turning the arpeggiator on or off while a key is held leaves no note
  hanging at the far end. With local control off the arpeggiator still
  takes the panel's keys and MIDI in's notes, and its notes go only to
  MIDI out.
- **MIDI clock out (the proposal's):** while the arpeggiator runs on the
  internal clock, a 0xF8 each pulse its position passes (sent in that
  block, like every MIDI out message); a Start (0xFA) with pulse 0's
  clock each time its pattern and grid start again (turned on, or the
  first note after none); a Stop (0xFC) when it stops or MIDI clock takes
  over; a Continue (0xFB) when the internal clock takes over again. While
  it follows MIDI clock it sends none (thru passes the sender's on, if on).
  Since overnight-1025 (the owner's answer to ARP's question 4): none
  either while a clock comes in that it doesn't follow (after a Stop, a
  sender's clocks may go on, and with thru on a follower saw both). Any
  0xF8 coming in stops ours (with a Stop, if it was running); ours
  starts or continues only once 250 ms (ARP_LOST_BLOCKS) pass without
  one, so after a Stop the arpeggiator plays on at once on the internal
  tempo and its clock out continues 250 ms after the sender's last
  clock (clock-quiet). So a follower downstream sees a gap of 250 ms in
  the clock even when the sender stopped cleanly: ours can't tell a
  sender that stopped its clock from one that keeps it running after a
  Stop until 250 ms pass without a clock. The owner accepted the gap
  (2026-10-26, overnight-1025's question 5).
- **The screen (ARP held):** the strip shows RATE, MODE, OCTAVES and GATE;
  SELECT pages to SWING, LATCH, TEMPO and MIDI OUT. The body shows the
  settings in words; the info line is its live part (every 50 ms when
  it changes): the clock, internal or MIDI, with its tempo, and the last
  step's note. ARP's LED is lit while the arpeggiator is on, and the
  event line says "ARP on" or "ARP off".
- **Stuck notes:** every note it starts is kept until its gate ends, and
  ends with it, with the pattern stopping, a program or mode change
  (`all_off`), all sound off, or the arpeggiator turned off; each end
  goes to the engine and to MIDI out as its start did.
- **Costs (measured, fwtest 0.6.0, against #131's image):** code 45 060
  bytes (+8 668), static RAM 214 332 (+10 192, the code run from RAM
  with it), stack 576 (+40); steady state 1 879.7 instructions a block
  (+0.75%: off, a block costs it one test of `arp_busy` and the ARP
  button's hold check), loaded 109 459 (+0.7%: each voice's test for a
  pending start). The rare paths (the ARP screen's edits, turning it on
  or off, a block in two parts) are kept out of line, as inlined they
  took the stack to 724 of its 768 bytes. On, a step is a few hundred
  instructions, at most 32 a second at 1/32 and 240 beats a minute. The
  heaviest input with CHORD at 1/32 and 240 beats a minute: no underrun,
  the longest fill 479 us (load). RAM: about 200 bytes, the
  record 224 bytes, and the voices' pending starts 16 x 40 bytes: 1.4
  KiB of static RAM in all. That matters beyond the budget: the start-up
  clears it before the time base starts, so more of it moves every
  event's time stamp later against fwtest's clock (about 2 us a KiB).

### 2026-10-26 overnight-1025: timing goldens

The owner's answer to ARP's question 6 ("timing goldens keep moving"):
a policy, built in `tools/goldtime.py` and `tools/regolden.py`, and
applied to the firmware suite's and the arpeggiator's cases
(R-GOLD-1 to R-GOLD-3).

- **Why they moved.** A bigger image starts a few microseconds later
  (start-up clears more RAM before the time base starts, about 2 us a
  KiB), and anything of ours that waits for an audio block (1.451 ms)
  then sometimes waits one more: a MIDI byte taken a block later, a
  note a block later, a MIDI out byte queued behind another (320 us).
  And a run's end comes late while core 0 waits (docs/HARNESS.md,
  "Time"), by an amount that moves with core 0's instructions, so a run
  that ended near a block's end sometimes took that block and sometimes
  didn't: a WAV a block longer or shorter. fmgold at `--ms 4200` ended
  2 us from one.
- **1. A run's end clears the blocks.** Every case that keeps its
  blocks' times (`--ipb`) and is compared with a golden ends at least
  `END_BEFORE_MS` (1 ms) before the next block's end, so a late end
  takes no extra block, and `END_AFTER_MS` (0.2 ms, about 100 KiB of
  start-up) after the last, so start-up moving the blocks later loses
  none. A block is 1.451 ms, so the window is 0.25 ms wide; "1 ms clear"
  on both sides cannot be had. `check_end` works it out from the run's
  own `ipb.csv` and suggests the nearest tenth of a millisecond that
  keeps it; tools/fw-suite.py and tools/arp_suite.py fail a case that
  doesn't; the ends are put in the middle of their window (about 0.1 ms
  of room each way) and in the same block as before where they can be,
  so the runs take the blocks they took. 30 of the suite's cases and 24
  of the arpeggiator's moved, each by about a millisecond or less (the
  arpeggiator's in its `END_MS`: each run starts from its own
  flash chip, so its blocks fall at their own times). The store's cases are left as they are: their goldens are
  screens taken mid-run, which no end moves, and only one keeps
  `ipb.csv` (a load test with no golden).
- **2. MIDI out's captures, with a tolerance.** fwtest compares golden
  files byte for byte, and `rel-percent` would let a byte written as
  hex digits differ too, so midiout's, midithru's, midilocal's and
  midiburst's captures moved to `tests/fw/golden-midi/`, which
  tools/fw-suite.py compares itself: the same bytes in the same order
  (and the same messages, decoded), each within `MIDI_TOL_MS`, 2.091
  ms (a block and two bytes), of its golden time. The arpeggiator's
  goldens were already without times.
- **3. Written again only when proven a time shift.**
  `tools/regolden.py --out <the suite's --out>` compares each golden
  with the run's output of the same name and prints `same`, `shift` or
  `REFUSED`; `--write` writes the shifts, and nothing at all if any is
  refused. A shift is proven:
  - for MIDI captures, by the same bytes (or messages) in the same
    order, only their times moved;
  - for a WAV, by the same sounds (runs of frames over +-1, parted by
    128 quiet frames), in the same order, each sample for sample the
    golden's, each moved by a whole number of frames (at most 1 024);
    a sound cut by either run's end need only match as far as both go;
  - for the arpeggiator's sound hashes (`--arp-out`, `--arp-old`, the
    suite's outputs on the new and on the base image), by the base
    run's WAV giving the golden hash and the two WAVs being a shift;
  - for anything else (screens, consoles, RAM captures), only by being
    identical.
  A golden whose content changes is a change of behaviour: made in the
  commit that changes the behaviour, which says so.
  `tools/arp_suite.py --write-golden` now writes only goldens a run
  doesn't have yet; `--replace` overwrites one that differs (a change
  of behaviour).
- **Live screens.** The patch view's live spectrum (views.c, `SPEC_X`,
  `SPEC_Y`, 56 bars of 4 pixels, `SPEC_H`) shows the last few blocks of
  sound, so a shift moves its bars: macros', midipanel's and spectrum's
  screens moved to `tests/fw/golden-live/`, compared exactly outside that
  rectangle (`compare_screen`); the spectrum case checks the bars through
  the interface's record.
- **The arpeggiator's inputs, off its grid.** Its runs let their keys go
  exactly on a step (2 000 ms is 96 clock pulses, and every rate's hold a
  whole number of steps), and one by one, 30 ms apart, so a step could
  fall among them; the stuck run had panel events on 1/16 steps and two
  keys pressed at the same instant. Which came first moved with a few
  microseconds. The keys now go together, 10 ms (`OFF_GRID_MS`) after
  the grid; stuck's later events 7 ms off it, its two keys 10 ms apart;
  its golden messages were written again for that (a change of its
  input), and it keeps no sound hash (its last notes are panel keys
  whose starts and ends come by the key scan and the block, so their
  lengths move by a scan).
- **Proven on real outputs.** The clock-out change (this session) moved
  the four MIDI captures by 1 us: `regolden` called each a shift; under
  the tolerance they pass as they are. A test build, `SB_TEST_LATE_START`
  (firmware/src/main.c), starts late, as a bigger image would:
  - **About 0.4 ms late** (twice the 0.2 ms margin): every end check
    fires, and `regolden` refused what is not a shift: fmgold (a note 98
    frames longer: its start and end came by different paths), midiout
    (the same messages, but two more status bytes: running status
    follows the gaps between messages), the live screens (before they
    were masked), and the arpeggiator's runs whose inputs sat on its
    grid. That is the size of shift the policy does not absorb.
  - **About 0.14 ms late** (the build as committed): every golden of the
    firmware suite passes as it is (the MIDI captures moved by up to 1.3
    ms, within the tolerance; the live screens the same outside the
    spectrum; fmgold identical), and `regolden` proves all eight changed
    files shifts. The arpeggiator's runs all pass. Only the end check
    fires (0.18 to 0.2 ms after a block, under its 0.2): the early
    warning, answered by moving `--ms` within its block, which changes no
    golden.
- **The owner's answers (2026-10-26, overnight-1025's questions 3 and
  4; recorded by clean-pin-answers).**
  - **The end check keeps failing CI**, since its fix is mechanical. Its
    message gives the fix in one step: the exact replacement and where
    it goes, `in tests/fw/boot.suite, line N: change --ms A to --ms B`
    for the firmware suite's cases, `in tools/arp_suite.py, END_MS: set
    "name": B` for the arpeggiator's (`goldtime.check_end`'s `where`).
    The replacement is `suggest_end`'s, so it takes the same blocks
    where it can and changes no golden; a rule 1 failure is never fixed
    by writing a golden again.
  - **The four exceptions** to "written again only by tools/regolden.py",
    accepted, each a change of what a case compares or of its input,
    never of a golden's content to match new behaviour:
    1. *The live screens.* The five screens of macros, midipanel and
       spectrum that show the patch view's live spectrum are compared
       exactly outside its rectangle (`LIVE`), not byte for byte. Why:
       the bars show the last few blocks of sound, so any shift of a
       sound moves them, and no shift can be proven of an image. The
       bars themselves are still checked, through the interface's record
       (the spectrum case).
    2. *stuck's sound hash, dropped.* Why: its last notes are panel keys
       whose starts and ends come by the key scan and the audio block,
       so their lengths move by a scan with the code's timing; its MIDI
       messages and no-stuck-notes checks stay.
    3. *The arpeggiator's inputs, moved off its grid* (its keys let go
       together, 10 ms after a step; stuck's later events 7 ms off the
       grid and its two keys 10 ms apart), and their golden messages
       written again by hand, as a change of the test's input. Why: on
       the grid, which came first, a step or a key, moved with a few
       microseconds.
    4. *env's screen at 1 400 ms, moved to 1 600 ms* (draft #126's,
       landing with it), its golden written from that image's run. Why:
       at 1 400 the envelope's dot was moving (the release), drawn where
       the code's timing put it; at 1 600 the note has ended and the
       screen holds still. The dot stays checked at 1 000 ms, where it
       rests at the hold.

### 2026-10-27 A1: the firmware as a `.fwsc`
- Facts: HW-87 to HW-93; docs/HARNESS.md, "Packages" (PROVENANCE P-61);
  our own runs in fwtest 0.8.0 (P-62). docs/A1-PLAN.md, Note A1-1.
- Reasoning:
  - **One linker script, two links.** `firmware/app.ld`'s image origin is
    a symbol, `0x02000000` unless `tools/build.sh` passes
    `--defsym=IMAGE_ORIGIN=0x02000120` for the package link (HW-91), and
    the image's length shrinks by the difference, so both end before the
    stock user patch region. Since M7 only the boot code runs from the
    window and everything else runs from RAM, so the two links differ
    only in the boot code's own addresses: the build fails unless what
    goes to RAM is byte for byte the same in both (the firmware's build;
    a `--define` test build may differ, as the store's wipe test reads a
    link symbol), the boot code is as long, and the package's `_start`
    is at `0x02000120`. The raw image is
    unchanged (the same `app.bin` as before A1; the ELF gains the origin
    symbol). The window shows flash `0x4000 + n` at `0x02000000 + n` in
    both paths, so the store's wipe test, the one place that turns a link
    address into a chip offset, holds for either.
  - **The packager writes only what the facts give.** One entry, the
    flash image; in it the flash header, two directory heads, our own
    key block and the app area at `0x4000`, ending at the app's last
    byte, so a package writes nothing past it (not the stock patches at
    `0xEA000`, not our store at `0xFC000`). Every field the facts leave
    open is 0 and listed in `tools/fwsc.py`'s docstring; the flash size
    is the chip's 1 MiB. The flash image starts at file offset 1024, so
    the byte at 1007 (a 21st block's marker's place, HW-88) is 0. The
    identity is `small-beeps-<version>`, checked to be at most 19
    printable characters, not another board's, and with no character
    whose marker would be `0x7D`.
  - **The reader is fwtest's order, in fwtest's words.** HW-93 gives the
    emulator's five steps; fwtest adds four (HARNESS.md). The reader
    follows fwtest's nine and, where HARNESS.md names a check without
    its message, uses the words fwtest printed (P-62), so C-PACKAGE can
    ask that fwtest's refusal and the reader's are the same text.
  - **The test compares, not re-goldens.** C-PACKAGE runs eight of the
    suite's cases on `app.bin` twice, raw and from the package, and asks
    for the same outputs byte for byte, with two stated exceptions (the
    r0 block, which must be HARNESS.md's boot block; the flash chip below
    `0xEA000`, which holds each path's own image). The goldens stay
    C-FW-SUITE's. Cases on test builds and on generated flash files are
    left out: they test the firmware, not the load path.
- Alternatives: a second linker script (two files to keep in step); a
  position-independent image (the toolchain's support unknown, and every
  absolute address in the boot code would need care); running the whole
  suite twice (as long again, for the same evidence).

### 2026-10-26 M8b: presets 65 to 70

The owner asked for presets covering the classic FM sounds, from known
recipes, never copied: six new ones, P65 to P70 (programs 89 to 94),
added after the 64 as candidates, for the owner to choose which of the
64 they would replace. **2026-10-27 (clean-1027), the owner's
decision:** this is a sample firmware, so no preset notes are needed and
all 70 stay, as they are; the bank is ready for review. Each
is built in `tools/fm_patch.py` from the recipe the owner named, with
numbers chosen here and checked by measuring renders with
`tools/preset_measure.py` (our own: one note at velocity 40 and 120);
no voice bank, SysEx or published patch was opened, and the names are
our own, none a factory name.

- **What the measures showed first.** An operator's envelope levels
  multiply its own level: a modulator at level 112 whose envelope holds
  104 acts at 89 (index about 0.5), not 112. The first drafts, written
  as if the envelope's levels were absolute, measured as near-sines;
  the bank's existing presets are mellow by the same measure (Saw Lead's
  second harmonic -11 dB at 500 ms). Second: two detuned carriers at the
  same level cancel when they beat (12 to 25 dB swings), and the bank's
  loudness trim, which raises every carrier, clips the main one at 127
  and evens them out; so each candidate keeps its main carrier at 127
  and its detuned partner 8 to 12 steps (6 to 9 dB) below, gets its
  loudness from lower carrier velocity sensitivity rather than a trim,
  and the trim is left at 0 (or -1, -2 where it lowers).
- **The figures** (C4 at velocity 120, the basses an octave down;
  brightness the power's spectral centroid in harmonics, 1 a sine; the
  suite's loudness at velocity 100, target -25 +- 3 dBFS):

| # | Name | Category | Recipe, as built | Measured |
|---|---|---|---|---|
| 65 | Tutti Swell | pads | three pairs: two near-unison carriers 7 cents apart (+4, -3) rising over about 0.5 s, and a brass-like pair (feedback 5) that barks in 2 ms and fades within a few hundred ms | -25.6 dBFS; within 3 dB of its peak after 357 ms (the pad rule's 50 ms); the stab alone at 10 ms, -15 dB under the full swell; brightness 1.9 at 5 ms (the stab), 1.0 at 50, 2.0 at 1.5 s; the unison's beating 5.9 dB |
| 66 | Round Seq | bass | a 1:1 pair, its modulator at feedback 5 closing in about 40 ms like a filter envelope, over a sine an octave down | -27.8 dBFS; brightness 2.25 at 5 ms, 1.06 at 50 ms; velocity 40: 0.95 at 5 ms |
| 67 | Neon Riff | leads | two bright 1:1 stacks of three 6 cents apart, the second 9 dB down, feedback 6, a fast attack that settles a little | -27.8 dBFS; attack under 1.5 ms; brightness 3.0 at 5 ms, 2.6 at 1.5 s; velocity 40: 1.0; beating 1.9 dB |
| 68 | Steam Pipes | brass and winds | an almost pure carrier with a 0.15 s attack and a vibrato from a 5.5 Hz fixed-frequency modulator (the engine has no LFO); beside it a quiet breath: a low carrier noised by a ratio 3 modulator at feedback 7 | -24.7 dBFS; attack 147 ms; vibrato 5.5 Hz, 6.4 cents; breath 0.3% of the power off the harmonics (-25 dB) at 600 ms, and a breathy onset (brightness 10.7 at 5 ms, 1.2 from 300 ms) |
| 69 | Hammer Keys | keys | three pairs, the second 3 cents up and 6 dB down, velocity 6 and 7 on the modulators (none on the carriers), each index decaying with the note, the upper pair's carrier at 2.01 (-2 cents: about 6.6 cents sharp, a stretched partial) | -27.1 dBFS; down 21 dB at 500 ms, 43 dB at 1.9 s; brightness 2.1 at 5 ms, 1.7 at 50, 1.0 by 300; velocity 40: 1.02 at 5 ms; the stretched partial 6.1 dB under the 2nd harmonic (the other candidates' leakage at that frequency: -12 to -30 dB) |
| 70 | Wire Bass | bass | one pair, the modulator at feedback 7 closing within about 5 ms from a bright bite to a still-wiry level | -24.7 dBFS; brightness 1.63 at 5 ms, 1.60 held (Round Seq's settles at 1.06); velocity 40: 1.0 |

- **Their tests:** the preset suite's (R-PRESET-2 to R-PRESET-4): no
  clipping, DC or click, the loudness, the category's shape (a bass's
  power below 300 Hz, the pad's attack), all 16 voices without an
  underrun, and the golden SHA-256 of each run. The WAVs are in
  `~/<top>/drop/presets/` (65 to 70, INDEX.md).

### 2026-10-27 clean-1027: seams for firmwares built on small-beeps

small-beeps is meant to be a base other people build their own firmwares
on. A firmware built on it asked, in general terms, for seams: places
where it can add its own engine and use the platform's parts without
changing the base's files. Each seam here is general, for any such
firmware; docs/BUILDING-ON-SMALL-BEEPS.md says how to use them. Each
pull request adds one, with its tests in `tools/seams_suite.py` (check
C-SEAMS) and its part below.

#### The write-back store check (R-BUILD-3)

- **What.** A store with write-back, `[++rN=k] = rN` or `[rN++=k] = rN`
  (also byte and half-word stores, k a number or a register), stores its
  own base register. Whether the chip stores the base's value from
  before the increment or after it is open (SR-10, the spec side's).
  Until it is answered no image of ours may hold one, so the build
  refuses it.
- **How.** `tools/build.sh` disassembles every object (`objdump -d`,
  which shows code sections only) before linking, and
  `tools/ownbase.pl` flags each such store with the object, the
  function, the offset and the instruction. Not the linked image: its
  RAM part holds the constants after the code, which would decode as
  instructions. The matcher is unit-tested on the disassembler's own
  text (`tests/test_ownbase.py`), and C-SEAMS builds a test image
  holding one (`SB_TEST_OWNBASE`, an inline store in `probe.c`) and
  checks the build is refused.
- **Today's firmware holds none**, at #126's head and at every seam's:
  the shipping image and its package link pass the check, and so does
  every test build CI makes. The image is unchanged by the check (the
  same `app.bin`).
- **The one exception** (until BR-13, below: it rested on a misreading).
  The Plaits demo's measurement builds with the hardware float
  instructions (`PLAITS_HWFLOAT`, M4b) were read as holding 68 such
  stores, all in the vendored Plaits (17 objects), and the check let
  those builds go on. Read as compiled, they hold none: each was the
  second half of a float conditional block. Since BR-13 there is no
  exception.

#### Building with outside sources (BR-5, R-BUILD-4)

- **What.** `tools/build.sh build` takes `--src DIR` (repeatable): every
  `.c`, `.S` and `.cc` under a folder outside `firmware/` is built into
  the image; and `--leave-out FILE` (repeatable): a base source, named
  by its path from the repository's root, is left out, so a firmware can
  replace a base file or do without it. With `--define` (already there
  for test builds) that is all a firmware built on the base needs to be
  built with the base's own build image, its files kept in its own
  repository and the base's used unmodified.
- **The same flags.** C with the firmware's flags; assembly with the
  firmware's (and, new, the `--define`s, which a firmware's `.S` may
  test); C++ as C++14 with the same CPU, warnings-as-errors and
  freestanding flags, without exceptions, RTTI or guarded statics (the
  toolchain's clang 4.0.1 knows no C++17). Each source gets `-I` for its
  own folder; the base's headers are on the path as for the firmware.
- **Names.** Base objects are named by their file name, as before (the
  default image is unchanged: the same `app.bin`). An outside object is
  named by its path, `src<N>_<path>.o`, so a file named as a base file
  is (`probe.c`, say) is built beside the base's, never over it; two
  definitions of one function then fail the link, as they should.
- **Deterministic.** Each folder is mounted read-only beside the source
  mount, as `sb-src-N`, and built by its path from the source mount
  (`../sb-src-1/...`), as the base's files are built by theirs. Clang
  4.0.1 keeps an absolute source path in the objects even with
  `-fdebug-prefix-map`; a relative one it keeps as given. So where the
  folder sits on the host, and where the source is mounted (C-BUILD-B),
  never reaches an output: C-SEAMS builds the same folder from three
  places, once with the source mounted elsewhere, and gets the same
  bytes; the build's own check that no output holds the source path now
  covers each outside mount too.
- **Refused:** a folder holding the base (its sources would be built
  twice), one inside `firmware/` (built already), a path with a space,
  and a `--leave-out` that names no base source (a typo would otherwise
  build the base file silently).
- **From another repository.** The firmware built on the base keeps the
  base as a folder (a git submodule or a clone) and runs the base's
  script from there: `sh base/tools/build.sh build --out out --src src
  --define ...`. The script builds the base's pinned build image the
  first time (`tools/build.sh image`) and runs everything inside it, so
  the firmware gets the same toolchain and the same deterministic build
  (docs/BUILDING-ON-SMALL-BEEPS.md).

#### The engine seam (BR-1, R-ENG-1)

- **What.** Built with `SB_ENGINE_EXTERNAL`, `main()` leaves out the
  base's FM engine and its store start-up (`fm_init()`, `store_boot()`)
  and the instrument's loop work (the screens, the store's writes), and
  calls three functions the firmware built on the base defines
  (`firmware/src/engine.h`):
  - `sb_engine_init()`, once, where `fm_init()` is called: after the time
    base, the tick's and SPI1's handlers and the panel's scan, before
    interrupts are on and before the audio starts;
  - `sb_engine_block()`, the block callback `audio_start()` gets: core 0,
    the audio interrupt, every block;
  - `sb_engine_serve()`, from main's loop: once before it begins, then
    on every wake that found work (a change of `sb_work`: the whole
    seconds, the panel's events, anything the engine adds itself).
  Everything else main does stays the platform's: the tick, the screen's
  start (pattern, then the test screen with its heartbeat), the loop and
  its counts in the beacon.
- **Without the switch nothing changes:** the default path's code is the
  same text, and the image is the same bytes (`da13d093…`).
- **Why three functions and not a table of pointers:** a build switch and
  link-time names cost nothing at run time, keep the default image as it
  was, and make a missing function a link error rather than a jump to
  nowhere. The block callback is the engine's own function, so the audio
  interrupt calls it as directly as it calls `fm_block` today.
- **The Plaits demo is a user** (M4b's load test): it defines the three
  in `firmware/demos/plaits/plaits_demo.c` (its bench, which never
  returns, runs from its init, where `main()` called it before) and the
  demo build defines `SB_ENGINE_EXTERNAL`. Its screen no longer shows the
  instrument's views after a touch (they never belonged to it); it keeps
  the test screen and its heartbeat. Nothing C-PLAITS-BENCH measures
  depends on that.
- **Tested** (C-SEAMS, case engine) with a test engine kept outside
  `firmware/` (`tests/seams/engine/`) and built through BR-5's `--src`:
  in fwtest its init runs once with no tick taken and no block played
  yet, its block callback gets every block, its serve runs before the
  loop and on each wake, seeing the key presses its block callback
  took, its square wave is in the audio, and the FM engine's record
  stays zero (the instrument never started). The instrument's files are
  still linked here; leaving them out is the platform link's (BR-2).

#### The platform without the instrument (BR-2, R-PLAT-1)

- **The platform's files:** boot (`crt0.S`, `start.c`), interrupts
  (`irq.c`), the tick, the loop and the beacon (`main.c`), input
  (`input.c`), audio (`audio.c`), the LCD and screen (`lcd.c`, `gfx.c`,
  `font.c`, `screen.c`), MIDI in and out (`midi.c`, `midi_out.c`), the
  store (`store.c`), and the test builds' `probe.c`. **The instrument's:**
  `fm.c`, `fm_play.c`, `patches.c`, `arp.c`, `views.c`, `saving.c`,
  `spectrum.c`, and for now `core1.S`, whose entry calls the FM engine's
  core-1 loop (BR-3 makes core 1's start the platform's). `tools/build.sh`
  lists them once (`INSTRUMENT`). Only `main.c` called the instrument,
  and since BR-1 it doesn't when built with `SB_ENGINE_EXTERNAL`; the
  test builds' references are inside their own defines.
- **`tools/build.sh build --platform`** leaves the instrument's files
  out, defines `SB_ENGINE_EXTERNAL` and links with
  `firmware/platform.ld`; the engine comes from `--src` (BR-5). With
  `--ld SCRIPT` an engine links with a script of its own (in the base or
  in a `--src` folder) that includes the platform's (`INCLUDE
  platform.ld`; the build passes `-L firmware`) and asserts its own
  records; the package link uses the same script.
- **The linker scripts.** `firmware/platform.ld` is what `app.ld` was,
  less the instrument: the memory, the sections, the stacks and the
  assertions about the platform's records. `firmware/app.ld` includes it
  and asserts the instrument's records. The image is unchanged
  (`da13d093…`); only the ELF's section names differ.
- **Where an engine's records go.** The records sit at fixed addresses
  that the tests (and the app) read, and the FM engine's record sits
  between the audio record and MIDI's. A platform-only link would slide
  MIDI's, MIDI out's and the store's records down by its size. So the
  64 bytes there are now the **engine's slot** (`.beacon.engine0`,
  `0x01C00590`): kept whether anything fills them or not (the script
  moves the location counter past them), at most 64 bytes (more and the
  link fails, as the counter would have to move back), the FM engine's
  record in the base. After the store's record come the **engine's
  records** (`.beacon.engine1` to `.beacon.engine4` in that order, then
  `.beacon.engine`, from `0x01C00870`), as large as they need: the
  base's interface record and arpeggiator's take the first two, so they
  stay at `0x01C00870` and `0x01C008D0`; a firmware on the platform alone
  gets `0x01C00870` for its first.
- **Tested** (C-SEAMS, case platform): the test engine linked with the
  platform alone and its own script (which asserts its record at
  `0x01C00870`). The ELF holds none of the instrument's functions or
  records, the platform's records are where the base has them, the
  package link is built too, and the engine case's whole run passes on
  it. The platform alone is 11 180 bytes of code (the firmware: 52 960).

#### Core 1's start, the platform's (BR-3, R-CORE-1)

- **What.** Starting core 1 and handing it work were the FM engine's
  (M5, "Two cores"): `core1.S`'s entry called the engine's loop on a
  stack of its own, `fm_init()` pointed source 126's vector word at it
  and set C1_CON bit 3 (HW-9), and `fm_play.c` kept the lock and the
  shared loads (HW-65). The Plaits bench had its own copy of the entry
  and the start. Now the platform has one of each (`core1.h`):
  - `sb_core1_start(entry, stack_top)`: core 0 leaves the entry and the
    stack's top where the entry (`core1_entry.S`) finds them, points the
    vector word at it, sets the bit, and waits (`SB_CORE1_WAIT` polls,
    about 1 ms in fwtest) for core 1 to say it runs; then puts the word
    back and returns 1, or 0 if core 1 never said so. On core 1, the
    entry sets both stack pointers from the given top and calls
    `sb_core1_main` (`core1.c`), which says it runs, under the lock, and
    calls the engine's entry; if that returns, core 1 stops with
    interrupts off.
  - `sb_lock`, `sb_unlock`, `sb_shared`, `sb_publish`: the lock byte
    taken by test-and-set with csync around, a shared word read after
    csync, a shared word written under a lock. `static inline`, as they
    are short and sit in core 0's per-block path (the FM engine posts a
    block and waits for its answer with them).
- **The FM engine** keeps its own stack (1 KiB, as before, now a
  `static` array in `fm_play.c`), its job's lock and sequence numbers,
  and its loop; it starts core 1 with `sb_core1_start(fm_core1_main,
  ...)` and keeps its two-core fallback (the result). Core 1's flag that
  it runs is the platform's now, so `fm_core1_main` only sets
  `sb_fm.core1`. **The Plaits bench** starts its core 1 the same way, on
  its own 8 KiB stack, and its copy of the entry is gone.
- **A name clash on the way.** The base names its objects by file name,
  so `core1.c` and `core1.S` both made `core1.o` and the link failed
  ("multiple definition"); the entry is `core1_entry.S`.
- **The image changes** (code 53 028 bytes, from 52 960), and start-up
  ends 2 to 3 µs later. One golden changed by hand, as the timing
  goldens' policy says a change that is not a pure time shift must be:
  midiout's MIDI capture, where the chord's three keys, pressed in the
  same instant, now reach the engine in the order 60, 64, 67 (was 64, 67,
  60); which key the panel's scan sees first depends on its phase
  against the script, which the later start moved. Every other message
  is the same, 2 to 3 µs later; the case's own checks take the chord in
  any order and pass, and midiround's script is written from the new
  capture (`tools/midi_scripts.py`). The order is the same on every
  later seam's image.
- **Tested** (C-SEAMS, cases engine and platform): the test engine
  starts core 1 and hands it a job every block, a sequence number to
  triple: core 1 starts, does exactly one job a block, every answer
  right and in time, and the vector word holds its stub again, with the
  instrument linked and with the platform alone.

#### The C++ runtime and `mem*`, the platform's (BR-4, R-RT-1)

- **What moved.** M4b wrote a small runtime for the Plaits demo:
  `memcpy`, `memmove` and `memset` (byte by byte), what C++ needs
  (`__cxa_pure_virtual`, `operator delete`, each a halt if reached), the
  soft-float routines, and freestanding headers (`<algorithm>`,
  `<cmath>`, `<math.h>`, `<stddef.h>`, `<inttypes.h>`). They are now the
  platform's, in `firmware/runtime/` (the headers in
  `firmware/runtime/include/`), with a `<string.h>` declaring the three
  `mem*` functions. Only `plaits_pre.h`, which is Plaits' own, stays
  with the demo.
- **An archive, so the firmware gets nothing it doesn't call.** The
  build links every object it is given (no `--gc-sections`), so
  `mem.c` as a plain object would add code to the firmware, which needs
  none. The runtime is built into `libsb_runtime.a` (`ar` in its
  deterministic mode) and the link takes it last: a member comes in only
  when something calls it. The firmware calls none, so its image is the
  same bytes; C-SEAMS checks build A has none of them. Its C is built
  without the float instructions, as soft-float's must be (and as the
  demo's C always was).
- **Two things C++ needed that the demo never did.** A static object
  with a destructor registers it with `__cxa_atexit` (the link failed
  without it): the runtime now has it, keeping nothing, as the firmware
  never exits. And the toolchain puts static objects' constructors in
  `.ctors`, which the platform never ran (with `--orphan-handling=error`
  such an object failed the link): `platform.ld` now gathers them, and
  `main()`, built with `SB_ENGINE_EXTERNAL`, runs them (last first, as
  `.ctors` is run) before the engine's init. The base has none, so its
  layout and its image are unchanged.
- **Include path.** Outside sources (BR-5), C and C++, and the demo's
  C++ get `-Ifirmware/runtime/include`; the base's own C does not need
  it.
- **Tested** (C-SEAMS, cases engine and platform): the test engine's
  init calls C++ (`tests/seams/engine/sb_test_runtime.cc`) with a
  virtual class, `std::sort`, `memcpy`, `memmove` and `memset` with
  lengths known only at run time, a static object built by its
  constructor and one with a destructor; its result is the expected
  1301, the runtime's members are in its ELF, with the instrument linked
  and with the platform alone. The Plaits demo builds and runs on the
  platform's runtime (C-PLAITS-BENCH).

#### SysEx bytes from MIDI in (BR-7, R-MIDI-8)

- **What.** MIDI in's parser skipped System Exclusive, counting it (M6a).
  A firmware built on the base may need its bytes (a dump of its own
  data, for one, of a few kilobytes). `midi_sysex_tap(fn)` sets a
  function the parser calls with each SysEx byte and what it is:
  `MIDI_SYSEX_BEGIN` (the F0), `MIDI_SYSEX_DATA` (each data byte),
  `MIDI_SYSEX_END` (the F7) or `MIDI_SYSEX_CUT` (any other status byte
  that ends it: a new F0, a channel or system common status, or a
  reset; the byte then also does what it always does). Realtime bytes
  inside a SysEx (a clock, say) never reach the tap: they are messages
  of their own, handed on by `midi_read()`, and the SysEx goes on after
  them, as MIDI 1.0 has it. The parser is otherwise unchanged: its
  counts, and `MIDI_SYSEX_LIMIT`, which only counts a message long, so a
  message of any length reaches the tap whole.
- **A tap, not pieces through `midi_read()`.** `midi_read()` hands on
  whole messages of at most two data bytes, and the instrument and the
  arpeggiator read it once a block; giving it SysEx in pieces would
  change what every reader sees. A tap changes nothing for a firmware
  that sets none (the base sets none), and costs one test of a pointer
  per SysEx byte.
- **Where it runs, and where the work goes.** The tap runs where the
  parser runs: in `midi_read()`, from the engine's block callback, core
  0's audio interrupt. So it should only keep the bytes (into a buffer
  of the firmware's) and, at the end, add one to `sb_work` to wake
  main; the work on them (checking, decoding, storing) goes in main's
  loop, `sb_engine_serve()` (BR-1). At the wire's pace a block brings at
  most five bytes, so the tap's share of a block is small whatever the
  message's length; a 4 104-byte message takes 1.3 s to arrive.
- **The image changes** (code 53 068 bytes, from 53 028): the pointer
  tests in the parser.
- **Tested** (C-SEAMS, case sysex) on the test engine linked with the
  platform alone, which starts MIDI in and keeps each message's bytes
  through the tap and sums them in its serve: a message of 4 104 data
  bytes, with a clock byte in its middle, arrives whole and in order
  (length, a sum weighted by place, first and last byte), the work done
  in the serve; the clock is handed on as a message; a second message
  cut short by a note on is reported cut by 0x90, and the note handed
  on; MIDI's record counts the first long and drops nothing. The
  firmware's own MIDI cases (C-FW-SUITE) check MIDI in is as before.

#### Raw bytes to MIDI out (BR-8, R-MIDIOUT-9)

- **What.** MIDI out sent queued messages of at most two data bytes
  (M6b). `midi_out_raw(buf, len)` streams any bytes as they are (a
  System Exclusive message, say): the poll hands the transmitter the
  next transfer of up to `MIDI_OUT_CHUNK` (12) bytes whenever the last
  has gone, as it does for messages. `midi_out_raw_busy()` says when the
  last byte has been handed on and the buffer may change; a second call
  meanwhile is refused (0).
- **The queue waits, but for realtime.** A channel message inside a
  System Exclusive message would end it, so the queue's messages wait
  until the stream's last byte has been handed on. Realtime messages
  (a clock, say) are the exception MIDI 1.0 makes: they may go anywhere,
  even inside System Exclusive. So each transfer of a stream starts with
  the realtime messages waiting, taken out of the queue (the others keep
  their order), and a clock keeps its time through a long stream. The
  stream may hold any status bytes, so the message after it carries its
  status (running status starts again).
- **The policy holds meanwhile.** Messages queued during a stream wait
  under the same rules (merging, the reserve for note offs, dropping):
  a stream of 4 096 bytes takes 1.3 s of the wire, longer than the
  queue lasts at a busy rate, so a firmware that sends long streams
  sends little else meanwhile, or accepts what the policy drops.
- **Who calls it.** The queue is the block callback's alone (no lock).
  The stream is handed over through three words the caller writes, the
  last a sequence number the poll answers, so `midi_out_raw` may be
  called from main's loop (`sb_engine_serve`, where the work on a SysEx
  goes, BR-7) or from the block callback, as long as from one of them
  only.
- **Its counts** are in a record of their own (`sb_midi_out_raw`, found
  by its symbol): MIDI out's record ends where the store's begins
  (`0x01C00780`), so it can't grow.
- **The image changes** (code 53 340 bytes, from 53 068).
- **Tested** (C-SEAMS, case rawout) on the test engine linked with the
  platform alone: at the first whole second its serve hands MIDI out a
  600-byte System Exclusive message while its block callback queues a
  clock every block and a note every 16th. On the wire: the 600 bytes in
  order, nothing inside them but clocks (about 200), every note after
  the F7, the first with its status, and every clock and note sent. The
  firmware's own MIDI out cases (C-FW-SUITE) check MIDI out is as before.

#### Storage for large records (BR-9, R-STORE-10)

- **What.** The store kept the base's own records: a patch (112 bytes)
  in each of 16 slots, the selection, the settings, a reset. A firmware
  built on the base needs its own, some large (a payload of 4 096 bytes,
  say). Kinds 0x80 to 0xFE are now kept for firmwares built on the base,
  with any id, and `store_put`/`store_get` take a payload of up to 5 904
  bytes for them (docs/STORE-FORMAT.md, "Kinds for firmwares built on
  the base"). A reset voids them with everything else.
- **Why parts.** A sector is 4 KiB with a 16-byte header, and a record
  can't leave its sector, so a 4 096-byte payload can't be one record. It
  is written as parts, records of up to 492 bytes of it (512 with their
  header, tag and CRC), each carrying its index and the part count in
  the header's two bytes that were always 0, and a tag (the write's own
  number) as its payload's first word. Of each part the newest record
  counts, as for any key; the payload is read only when every part is
  there with part 0's tag and count. A write never mixes with the one
  before it: cut short, the old payload still reads until the new
  write's first part is whole, and then nothing until its last part is
  (the model checks every cut point: old, then none, then new; fwtest's
  power cut checks one on the firmware). A firmware that can't do without
  its payload writes it again; the store never hands it half of each.
- **Why not keep the old one through the whole write.** (Since
  clean-1028 it does: BR-12, "Saves that survive a power cut", below.)
  That needs room for two copies of the payload at once, and the three
  sectors don't have it: the ring needs a sector's worth free to move on, so about two
  sectors (8 160 bytes) hold everything live, and two copies of 4 096
  bytes are 8 192 before any header. Writing part by part needs room for
  one new part beside everything live.
- **What today's region holds** (`tools/store.py`'s model, which the
  firmware's images match after every run of the seams suite): one
  payload of up to 5 396 bytes, rewritten as often as asked, with
  nothing else stored (a firmware on the platform alone, its own small
  records aside); a 4 096-byte payload so has 1.3 KB to spare. Beside the
  base's full store (all 16 user slots, the selection and the settings,
  saved between rewrites) how much fits depends on how the records fall
  in the sectors: 2 952 bytes held in every one of 40 histories of 300
  rewrites the model tried; up to about 3.5 KB in some histories but not
  all; 4 096 not reliably. Past what fits a write is refused
  (`STORE_ERR_FULL`), and what was there stays. Where a larger region
  goes is the owner's later decision; the part size was chosen for
  today's: of the sizes tried, from 236 to 2 012 bytes, 492 let the most
  be rewritten beside the base's full store (428 a little more alone).
- **Keys.** The base's keys are fixed (16 slots and three more). The
  firmware kinds' parts take places in a table of their own, 32 of them,
  after the base's: the ring's compaction, a sector's live count and the
  reset treat both alike, in that order, and the model keeps the same
  order, so an image it writes is one the firmware could have written.
  A write checks first that every part has a place, so it never stops
  for want of one; a payload rewritten with fewer parts frees the rest.
- **Format.** Version 1's records, as before: a reader that doesn't know
  these kinds (the base before this) counts them unknown and never
  copies them forward. The base's own records and their limits are
  unchanged, and its tests pass as they are.
- **The image changes** (code 54 416 bytes, from 53 340; RAM 1 312 bytes
  more: the table, and the record buffers sized for a part).
- **Tested:** the model in C-UNIT (a payload in parts read whole, every
  cut point of a rewrite, fewer parts, the reset, what the region holds,
  the constants the firmware's); and the firmware in C-SEAMS (case
  store): nine runs chained through the flash file, the model writing a
  control record before each that tells the test engine what to do: a
  4 096-byte payload and a small one written and read back, then read at
  the next start-up; rewritten; rewritten again with the power cut at
  the middle of its page programs, after which the large payload is gone
  and the small one stays; rewritten after the cut; a reset voids both;
  then alone, 5 000 bytes written and read back and 5 904 refused as
  full. The model reads what the firmware does after every run.

### 2026-10-28 clean-1028: saves that survive a power cut (BR-12, R-STORE-11)

- **What.** A firmware built on the base asked that a save survive a
  power cut: whenever the power goes during a save, the next start finds
  the complete old payload or the complete new one, never neither and
  never a mix, large records (BR-9) included.
- **What was already so.** The store appends and never rewrites a byte
  (M7): a record counts only once its CRC holds, and of a key's records
  the newest valid one is read, so a record cut short leaves the one
  before it. The base's records and a firmware kind's one-part payload
  (up to 492 bytes) are one record each, so their saves were atomic
  already; the ring's moves (a sector erased, its header, the live
  records copied forward) never touch the only copy of a live record
  (M7, "Append only, CRC on everything" and "The ring and its
  compaction"; the sweep case cut them at every command with a halting
  test build). This session tests that with fwtest's power cut at
  every command (below). A payload in parts was not: once the new
  write's first part was whole the old payload was gone, and nothing
  read until the last part was (clean-1027's choice, for room).
- **How: the last part commits the write.** Of the choices the request
  named (a second copy, a log, alternating slots), this is the second
  copy, kept in the ring itself: the old write's parts stay live (copied
  forward by the ring like any live record) until the new write is
  committed, and the commit is the new write's last part, which the
  store writes only once every other part of the write reads back as the
  payload it holds (each part is also read back as it is written). At
  start-up the store finds, of each payload, the write with the highest
  tag whose last part is valid and newer than the newest reset (its
  committed write), and takes that write's parts and no other. A write
  cut before its last part is whole leaves the old one committed; one
  cut after leaves the new one. No new record type and no byte of the
  format changes (docs/STORE-FORMAT.md): a write's last part already
  carried its tag, index and count, and clean-1027 wrote it last too.
- **Why not a log or alternating slots.** Both need the same room (the
  old payload stays whole until the new one is) and more machinery: a
  log needs its own record type and replay; alternating slots fixed
  places in a store whose records have none. The ring's copy-forward
  already keeps whatever is live.
- **Start-up reads the sectors holding a firmware kind's record three
  times** (store.c, `scan`): first the base's keys as before, and which
  sectors hold firmware kinds; then the committed writes (one place per
  payload, 32 of them, `STORE_FW_PAYLOADS`); then their parts (32
  places, `STORE_FW_KEYS`, as before). Taking each part's newest record
  in one pass, as before, can't tell the committed write from a newer one
  cut short; tables of every write seen would grow with each cut. A
  firmware with none of these kinds reads each sector once, as before.
- **The space it costs.** A rewrite needs room for the whole new payload
  beside everything live, the old payload included, where clean-1027
  needed room for one new part. The ring keeps a sector free to move on,
  so the live records fit in the other sectors (each less its 16-byte
  header), and a part can't leave its sector: a 4 096-byte payload (9
  parts, 4 608 bytes as records) needs 9 216 bytes during a rewrite,
  more than today's two working sectors (8 160). From `tools/store.py`'s
  model, which the firmware's images match:

  | Region | Alone, rewritten 40 times | Beside the base's full store and a small payload (100 random histories) | 4 096 bytes beside the base's full store (300 histories) |
  |-------:|------:|------:|------:|
  | 3 sectors (today's) | 3 920 bytes | 1 664 bytes | never |
  | 4 sectors | 4 904 | 3 300 | never |
  | 5 sectors (`SB_TEST_STORE_WIDE`) | 5 904 (the most a payload takes) | 4 948 | every one |

  ("Beside the base's full store": all 16 user slots, the selection and
  the settings, then 60 rewrites with up to five of the base's saves and
  sometimes a payload of up to 400 bytes between them.) So for a
  4 096-byte payload the store region must grow from 3 sectors to 4 (4
  KiB more) for a firmware that keeps nothing else, and to 5 (8 KiB
  more) beside the base's full store. Where those sectors go is the
  owner's decision (BR-9 left it open): the unused region is 3 sectors
  (HW-80), so a larger one takes the end of the stock firmware's user
  patch region below it, or another place. Today's region stays as it
  is; the wide region test build takes its 5 sectors from 0xFA000, which
  only a test may do.
- **Refused before writing.** A rewrite that can't fit (everything live
  and the new records together more than the sectors but one hold) is
  refused at once, `STORE_ERR_FULL`, and nothing is written: in today's
  region a 4 096-byte rewrite is (C-SEAMS, case store). A write refused
  part way (the ring's layout left no room after all; the model never
  found one) drops its new parts and keeps the old payload
  (`sb_store_fw.abandoned` counts them).
- **Tested.** The model in C-UNIT: every state a cut can leave, every
  byte of every flash command (`tools/store.py`'s `cut_states`, which
  leaves the chip as fwtest's cut does), of a 3 000-byte rewrite in
  today's region, a 4 096-byte one beside the base's full store in the
  wide region (every fourth byte), and a patch and a one-part payload
  saved when the head is full: always old or new, whole, the old until
  a moment and then the new; and what each region holds (the table's
  first two columns); the 3 000-byte case is a 3 400-byte one since
  #170's review, rewritten after four writes so the ring copies the old
  write's parts forward during the rewrite (checked). The firmware in
  C-SEAMS (case powercut): four saves on the test engine (4 096 bytes
  from the base's full store on the wide region test build; on today's,
  that 3 400-byte rewrite, whose old parts the case checks were copied
  forward, and from the base's full store with the head full 300 bytes
  and a patch), each
  cut by fwtest's `--power-cut` just after each flash command starts,
  halfway, just before it ends, and between commands; the firmware
  started again from each cut's flash reads the old payload or the new
  one, whole, never another, and the others unchanged.
  In this session's run: the 4 096-byte rewrite 27 commands (one
  erase), 108 cuts, the old payload after 106 and the new after the
  last 2; the 3 400-byte rewrite 47 commands (two erases, all 7 of the
  old write's parts copied forward), 188 cuts, old 186, new 2; the
  300-byte payload 41 commands (one erase, the compaction's
  copies), 164 cuts, old 162, new 2; the patch 41 commands, 164 cuts,
  old 161, new 3; tools/store.py read each cut's flash as the firmware
  did. Case store's rewrite in today's region is refused with nothing
  written. Without this change the model's cut test finds no payload
  part way, as clean-1027 said it would.
- **The image changes** (code 55 108 bytes, from 54 416; RAM 272 bytes
  more: the payload table and the start-up's bookkeeping). The base's own
  start-up reads each sector once, as before (no firmware kind's
  record): the store read 275.2 us at the next start in the persist
  case (276.7 before). Start-up 2 854 instructions more (1 070 789);
  steady state and loaded per period no slower (1 884.6 and 108 944,
  from 1 886.0 and 109 125); stack 572 bytes at most (544). Every budget
  holds; the firmware suite and the ARP suite pass as before.
- **A probe made stronger** (C-PERF-PROBES): the big probe build
  (`SB_PROBE_BIG`, `firmware/src/probe.c`) must also fail the start-up
  budget, and its one extra round of work (about 750 instructions) no
  longer did: the start-up count moves by a few thousand instructions
  from one image to the next, and with this change the probe's image fell
  the other way. It now does the round 64 times (about 34 000
  instructions), and fails it by 31 000.

### 2026-10-28 clean-1028: per-folder compiler flags (BR-11, R-BUILD-5)

- **What.** A firmware built on the base asked for its own compiler
  flags, folder by folder (a vendored library at `-O2` with its warnings
  off, its own code with a define or a newer C++), while the base's
  files keep the base's. `tools/build.sh build` takes `--cflags DIR
  FLAGS`, `--cxxflags DIR FLAGS` and `--asflags DIR FLAGS`, beside
  `--src` and `--leave-out`, for the C, C++ or assembly files under DIR,
  a `--src` folder or a folder inside one (docs/BUILDING-ON-SMALL-BEEPS.md,
  section 5).
- **After the base's, in the order given.** A folder's flags come after
  the firmware's on each compile line, so they can override them (`-O2`
  over `-Os`, `-w` or `-Wno-...` over `-Werror`'s stops), and a file
  under several such folders gets each one's, in the order given: a
  folder inside another, given after it, overrides it. Why not "the
  deepest folder's only": a library's subfolder usually wants its
  parent's defines too; giving each folder's flags and letting the order
  decide keeps both possible and the rule one line.
- **One option a language.** C, C++ and assembly take different flags
  (`-std=c11` is an error for C++), so each has its own option, as the
  build already keeps `CFLAGS`, `CXXFLAGS` and `ASFLAGS`.
- **The base's files never get them.** The flags apply only under a
  `--src` folder, which can't hold the base or be inside `firmware/`
  (BR-5); `--define` stays the switch for every file. The base's
  runtime archive is built as before.
- **Paths.** The container builds an outside folder as `../sb-src-N/...`
  (BR-5), so a relative `-I`, `-isystem` or `-iquote` path is taken from
  DIR and rewritten to that (joined to its option; a bare `-I` is
  refused, as the word after it would not be rewritten).
- **What a folder may set, and why a list.** The flags reach the
  compiler's command line, so a flag that names a file could read or
  write the host's (`@file`, `-Wp,-MD,...`, `-fplugin=`, `-B`), change
  the outputs with where things are (`-fdebug-prefix-map`, an absolute
  `-I`), or undo the build (`-o`, `-c`, `-x`, `-target`). A list of what
  is refused would always miss one, so the build takes only the families
  firmware code needs (`-D`, `-U`, `-O`, `-W`, `-w`, `-f`, `-m`, `-std=`,
  `-I`, `-isystem`, `-iquote`, `-g`, `-pedantic`, `-ansi`), refuses within
  them the prefix maps, `-fprofile...`, `-fplugin...`, `-fpass-plugin...`,
  `-fsave-optimization-record` and `-Wa,`/`-Wp,`/`-Wl,`, refuses any
  absolute path or `..`, and takes words of letters, digits and
  `_ = + . , / : -` only (no quoting, no shell characters). The outside
  folders are mounted read-only, as before; the write-back store check
  (R-BUILD-3) still checks every object, whatever its flags.
- **Carried into the container** as one variable, `SB_FOLDER_FLAGS`,
  entries `option|folder|flags` (the option `cflags`, `cxxflags` or
  `asflags`) after a `;` each: the allowed
  characters hold neither, so no flag can break the format.
- **Tested** (C-SEAMS, case flags): `tests/seams/flags`, whose files
  `#error` without their flags (C, C++, assembly, and a C file in a folder
  inside it that needs both folders' flags and its own `-Iinclude`; the
  outer C file also errors if the base's `-Os` came after its `-O2`):
  built with them, each file's compile line ends with its folders'
  flags in order, its symbol is in the ELF; the base's compile lines
  carry none of them, and those of `firmware/src/` are the same as in
  the build without the flags (which the folder's files stop: the first
  on its include); built from two copies of the folder
  elsewhere on the host, one with the source mounted elsewhere, the same
  bytes; and eleven refusals.
- **The image doesn't change** for a build without these options: the
  base's compile lines are as they were (the case's check), and C-BUILD-A
  and C-BUILD-B give build A as before.

### 2026-10-28 clean-store-region: the write-back check reads code as compiled (BR-13, R-BUILD-3)

- **What.** A firmware built on the base reported that the write-back
  store check (R-BUILD-3) misreads float instructions unless it
  disassembles with the float feature (`-mattr=+fprev1`). It did: the
  check ran `objdump -d` with no CPU options, so the disassembler (the
  toolchain's, LLVM 4.0.1) knew no float instructions. Each one, 4 bytes,
  read as an unknown 2-byte one and then its second half as another
  instruction; the float feature's conditional block, `iff (r2 > r5) {`
  (bytes `12 ee 80 05`), reads as an unknown half and `[r0++=4] = r0`,
  a store the check refuses. The check could so refuse code that holds
  no such store, and, as the bytes after an unknown half are read out of
  step, could miss one that is there.
- **The fix: each object read as it was compiled.** `tools/build.sh`
  notes, as it compiles each object, the CPU and features its flags give
  (`note_cpu`): clang's own reading of the compile line (its `-###`
  output's `-target-cpu` and `-target-feature`), so `-mcpu=r3
  -mfprev1`, `-mno-fprev1`, a folder's own `-m` flags (BR-11) and the
  Plaits demo's `-Xclang -target-feature -Xclang +fprev1` all count, and
  the base's own files, the runtime's C (built without them, as
  soft-float must be), the demo's C and C++ and every outside folder's
  each get their own. The check disassembles each object with those
  (`objdump -d -mcpu=r3 -mattr=+fprev1` for the base's files) and prints
  how many objects it read with which.
- **Code it can't read fails the build.** `tools/ownbase.pl` now also
  refuses an instruction the disassembler shows as unknown (it prints
  `unreadable`, with its place, and exits 2; `tools/build.sh` fails
  with its own message): a check that misreads code can't vouch for it,
  and should the flags ever not reach the disassembler again, the build
  stops instead of reading out of step. With the right options no build
  CI makes (build A, the Plaits demo, its hardware-float build, every
  seams build) holds such an instruction, but one: the bad instruction
  test build (`SB_TEST_BADINSN`, C-FW-SUITE's case badinsn), whose
  `sb_test_badinsn` in `probe.o` is bytes no CPU decodes, on purpose, to
  test fwtest's fault outcome. There, and only there, they are listed
  and allowed; anything else unreadable, or any write-back store, still
  fails that build. (The first full run of the firmware suite on this
  change found it: the test build was refused.)
- **What it changes.** The firmware's own images and the base's code
  read as before (they hold none; the outputs are byte for byte the
  same, the check only reads). The 68 stores the check counted in the
  Plaits demo's hardware-float build (17 vendored objects) were all this
  misreading; read as compiled the build holds none, so the build's one
  exception for it is gone (above).
- **Tested** (C-UNIT, `tests/test_ownbase.py`: the conditional block's
  bytes as the disassembler shows them without the feature, refused as
  unreadable, and with it, passed; C-SEAMS, case ownbase):
  `tests/seams/float/float_heavy.c`, a float-heavy outside source (the
  compiler's float code at the firmware's flags, and the conditional
  block), passes, disassembled with the firmware's CPU and features as
  the base's own C is (one more object read so than without it, the
  runtime's two as before, with none), nothing unreadable; built with
  `SB_TEST_FLOAT_OWNBASE`, a real store placed after its float code, it
  is refused for that store alone, named at its place. The same object
  under the check as it was (no CPU options) is refused for the
  conditional block's misread store: what the downstream firmware saw.

### 2026-10-28 clean-store-region: each firmware chooses its own store region (R-STORE-12)

- **What.** The owner's answer to where a larger store goes (BR-9 and
  BR-12 left it open): small-beeps keeps today's three sectors at
  `0xFC000` as its default, the stock firmware's user patch region below
  them untouched (M8a's promise), and a firmware built on the base sets
  its own region's start and size in its linker settings, for example a
  larger region in the flash its own image's app area spans.
- **One definition, at link time.** `firmware/platform.ld` sets
  `STORE_BASE` and `STORE_SIZE` (chip offsets, bytes) with `DEFINED()`
  defaults, so a firmware's own script sets them first and includes the
  platform's (BUILDING-ON-SMALL-BEEPS.md, "Where the store goes"; ld
  2.26 takes a symbol its including script assigned before the
  `INCLUDE`, and `--defsym` too). The store reads them as link symbols,
  `sb_store_base` and `sb_store_size`, so one compiled `store.c` runs in
  any region: no define, no rebuild of the base's objects per firmware.
  `store.h`'s `STORE_BASE` and `STORE_SIZE` were constants (and
  `SB_TEST_STORE_WIDE` a second pair for a test build); they are the
  symbols' addresses now. The tables sized by sectors take
  `STORE_SECTORS_MAX` (128, 512 KiB, more than the app area can hold
  after any image; 768 bytes of RAM), and a sector's "holds a firmware
  kind" flag, a 32-bit mask until now (32 sectors at most), is a byte a
  sector. The ring's next sector is a compare, not a modulo (no divide at
  run time). The test engine's linker scripts `store5.ld` and
  `store16.ld` are the documented way, used.
- **The build refuses what doesn't fit** (`tools/store-region.pl`, run by
  `tools/build.sh` on both links, `app.elf` and `app-pkg.elf`, whose
  image is the longer by the app area's 0x120-byte directory): a start
  off a 4 KiB sector boundary or a size not whole sectors; fewer than 3
  sectors (the store's minimum: a head, a sector to move on to, and one
  to compact) or more than `STORE_SECTORS_MAX`; a region over the image
  (window address `0x02000000 + n` is chip offset `0x4000 + n`, HW-5,
  HW-91) or the boot area; a region across the app area's end, or in the
  stock layout past it (the VM region, the Bluetooth sector, the stock
  user patch region, the per-unit last sector: HW-80). Each message says
  what is wrong, with the numbers, and where a region of that size would
  fit (from the first sector after the image to the last start that ends
  by the app area's end, and the unused region's 3 sectors). The checks
  are in a script, not ld `ASSERT`s, because an `ASSERT`'s message can't
  carry numbers, and an `ASSERT` would stop the link before the script
  could say more; platform.ld's two store asserts are gone.
- **Stricter than asked, where HW-80 says so.** The owner named five
  refusals (over the image, across the app area's end, the stock user
  patch region, off a sector boundary, below the store's minimum). The
  build also refuses: more than the store keeps track of (an array
  bound, so a must), the boot area, and the stock layout's regions past
  the app area that aren't the unused one, the VM region (the stock
  firmware's settings, and where an update stages its loader), the
  Bluetooth sector and the last sector (never to be erased). HW-80 says a
  store "must stay out of" or "should stay out of" each.
- **Where the app area ends: a reading, SR-11.** HW-87 to HW-93 give the
  app area's start (`0x4000`) and its length as its area head says (our
  packager's: our app's), not a fixed end; HW-80 gives the stock
  layout's, `0x93FFF`. The build takes `0x94000` as the end, the most
  conservative reading that leaves the owner's example (a region in the
  space a stock image would take, after our smaller one) possible.
  SR-11 asks the spec side where the area may end, whether the chip's
  loader or an update touches flash past our package's image, and
  whether the window's decryption reaches there.
- **The store's room-making moves on more than once.** With the region
  free, the worked example (16 sectors for several 4 096-byte records)
  showed what bigger regions need. The ring made room by moving the head
  on once: open the next sector, copy the live records of the one after
  it into it (compaction), and, if what was left was still too small,
  refuse. With large payloads most sectors are mostly live, so one move
  often frees nothing: in the model, 16 sectors kept only one rewritable
  4 096-byte payload beside the base's full store in every history (two
  alone), though they have room for twelve. `make_room` (and the model's
  `_room`) now moves on while the new head has no room, once round the
  ring at most, each move an erase of a sector holding nothing live and
  a copy of the next's live records, as before; still `STORE_ERR_FULL`
  when the sector to move to holds something live. A save that one move
  served makes exactly the commands it made before (the loop only goes
  on where the old code refused), so every history the store took before
  is unchanged. The cost: in a nearly full region one save can erase
  several sectors (in the power-cut case's save, 2 for one part; up to 7
  seen in the model's searches), still spread over the ring.
- **More parts kept track of.** `STORE_FW_KEYS`, the places for parts,
  was 32: three 4 096-byte payloads (9 parts each) left no room for a
  rewrite of one, in any region. It is 128 (1.5 KiB more RAM): 14 such
  payloads, 13 beside a rewrite. Past it a write is refused as full, as
  before. `STORE_FW_PAYLOADS` (32 payloads) stays.
- **Start-up grows with what the region holds.** `store_init` reads
  every sector's header, every valid sector whole, and those holding a
  firmware kind's record twice more (BR-12). Measured in fwtest (the
  store record's `init_ticks`): the default region holding the base's
  full store, a 10-byte and a 1 500-byte payload, 1.13 ms (the base's own
  records alone: 0.28 ms, clean-1028); 5 sectors holding the base's full
  store and a 4 096-byte payload, 2.17 ms; 16 sectors holding the base's
  full store and eleven 4 096-byte payloads after 27 rewrites, 18.1 ms.
  The larger key table is about 1 % of it (2.14 ms in 5 sectors with 32
  places). A firmware calls `store_init` once, in its init.
- **The sizing rule, plainly.** A rewrite is atomic (BR-12), so it needs
  room for the old payload and the new one at once: everything live plus
  the new payload's records must fit in the region's sectors but one, at
  4 080 bytes of records a sector (`(STORE_SECTORS - 1) * 4 080`, the
  check `put_fw` makes before writing anything), with no record across
  two sectors, and its parts within the places for parts. A payload of
  n bytes is `ceil(n / 492)` parts of 512 bytes as records (the last
  smaller); 4 096 bytes take 4 288. The ring's layout takes some of that
  room back, so what fits in every history is less; from the model
  (`tools/store.py`), histories as clean-1028's table describes them;
  this session's script, run on main's model, gives that table's figures
  for 3 and 5 sectors (3 920, 1 664 and never; 5 904, 4 948 and every
  one) and for 4 gives 4 904, 3 268 (the table: 3 300) and never, so the
  "before" figures below are its own:

  | Region | One payload alone, rewritten 40 times | One payload beside the base's full store and a small payload (100 histories) | A 4 096-byte payload beside the base's full store (300 histories) | 4 096-byte payloads, each rewritable: alone (beside the base's full store; 100 histories in 16 sectors, 300 in 5) |
  |-------:|------:|------:|------:|------:|
  | 3 sectors (the default) | 3 920 bytes | 2 444 bytes (1 664 before) | never | none |
  | 4 sectors | 5 396 (4 904 before) | 4 284 (3 268) | every one (never) | 1 (1) |
  | 5 sectors | 5 904 | 5 904 (4 948) | every one | 2 (2) (1 (1) before) |
  | 16 sectors | 5 904 | 5 904 | every one | 12 (11) (2 (1) before) |

  So a 4 096-byte payload now needs 4 sectors beside the base's full
  store, where clean-1028 found 5. The store's format is unchanged
  (docs/STORE-FORMAT.md): a region of any size from 3 sectors up is the
  same ring of the same sectors.
- **Tested.** C-UNIT: `tests/test_store_region.py`, each refusal on the
  check's own input (the symbols `nm` prints), with its message and the
  place it offers, the default and both test regions taken, every
  problem of a region listed; `tests/test_store.py`, the model in 5 and
  16 sectors from `0x20000`: a 4 096-byte rewrite beside the base's full
  store cut at every fourth byte of every command, one of four 4 096-byte
  payloads rewritten in 16 sectors cut at every eighth, eleven 4 096-byte
  payloads rewritten in turn beside the base's full store, and the
  figures above that the tests pin (2 808 bytes beside the full store in
  3 sectors by the deterministic history, 2 316 before; 4 096 bytes in
  4). C-SEAMS: case region (the test engine linked with `store5.ld` and
  `store16.ld`, both links' regions as set; five regions refused through
  real builds, each saying why and where one would fit), and case
  powercut, whose 4 096-byte rewrite now runs in the 5-sector region and
  which gains a fifth save: in the 16-sector region, one of eleven
  4 096-byte payloads rewritten after 27 rewrites, the ring so full that
  the save moves the head on twice for one part's room, the firmware's
  flash commands the model's one for one, every command in the region,
  cut at every command, the other ten payloads unchanged.

### 2026-10-29 clean-pin-flags: the owner's answers on the store region (R-STORE-12)

clean-store-region asked the owner six questions about the store region
(its session report). The answers, as decisions:

- **Moving on until there is room, and 128 parts: accepted.** The store
  moves the ring on until the head has room, once round at most, and
  keeps track of 128 record parts. Every save the earlier store accepted
  writes the same bytes, and the power-cut runs (R-STORE-11) cover the
  new path; only saves it refused behave differently. STORE-FORMAT says
  so ("Writing").
- **Every extra refusal stays.** The build keeps refusing, beyond the
  five the owner named, regions over 128 sectors, in the boot area, in
  the VM region, the Bluetooth sector and the last sector. The VM region
  in particular: it holds the stock firmware's settings and is where an
  update stages its loader, so a store there could be lost or break an
  update. `tools/store-region.pl`'s refusal now says that.
- **SR-11 waits for the spec side.** Until it is answered the guide's
  wording stands: a store in the app area survives fwtest and the app,
  not yet a real unit's update.
- **The PLAITS_HWFLOAT exception's removal (BR-13): accepted.**
- **fmgold's moved key release: accepted.** The golden is unchanged; the
  cause was an event within microseconds of an audio block's edge. The
  script's header now says to keep key events well clear of block edges,
  and why.
- **18 ms once at init for a full 16-sector region: acceptable.** Not to
  be optimised. The guide's sizing section gives the figures as a table
  ("Where the store goes").

### 2026-10-29 clean-pin-flags: a folder's code for the SDK's CPU and float (amends BR-11, R-BUILD-5)

BR-11 let a `--src` folder set its own `-m` flags, so a folder could
build for another CPU or with instructions the SDK's flags leave out
(double-precision float, SIMD): code fwtest doesn't run (it runs the
forms `-mcpu=r3 -mfprev1` give, R-HARN-14).
The owner's rule: a folder may still set other `-m` flags, but its
objects are built for CPU `r3`, with the features `+fprev1` or none.

- **By clang's reading, not by spelling.** BR-13 already reads each
  compile line's CPU and features from clang's own `-###` line
  (`note_cpu`, now `read_cpu` and `note_cpu`). The check takes the same
  reading of every folder file's flags (the base's for its kind, then
  its folders'), so `-mcpu=r4`, `-mfprev2`, `-msimd`, a
  `-target-feature` and a flag the toolchain gains later are caught
  alike. The toolchain's target knows CPUs `generic` and `r1` to `r5`
  with variants (`r3s`, `r3v1`, ...), and nine features, among them
  `fprev1` (float), `fprev2` (float and double) and `simd` (its
  `-mcpu=help`).
- **What passes.** CPU exactly `r3` (not `r3s` or another variant), and
  of the features, each taken at its last `+` or `-`, none enabled but
  `fprev1`. So the base's own set, `-mfprev1` again, and
  `-mno-fprev1` (no float instructions: soft-float, which the base's
  runtime provides) all pass; the face-value reading of "+fprev1 or
  none". A reading with no CPU (clang read none) is refused too.
- **Where.** Only `--src` folders' files that have folder flags: the
  base's own files keep the base's flags, and two of the base's builds
  read without a CPU on purpose (the runtime's C and the Plaits demo,
  which are soft-float; the demo's `PLAITS_HWFLOAT` build adds `+fprev1`
  through `-Xclang -target-feature`, the SDK's set, and stays as it is).
- **When.** Every folder file is checked before any is compiled, so the
  refusal comes before a compiler error and once per option, folder and
  effect ("and N more" files), on stderr only. The message names the
  option and the folder whose own flags give the effect, as the user
  gave them (carried into the container beside the mount path; only
  messages see it, so the outputs stay the same from any place; every
  folder of the file, if only their flags together give it), the first
  file, what the flag does, which of the folder's flags alone give it
  and the fix.
- **`-Xclang`.** The owner named `-Xclang -target-feature` among the
  spellings to catch. A folder can't give it: `check_flags` takes only
  the listed families, and `-Xclang` is not one (refused at exit 2
  since clean-1028). The reading would catch it if it ever got through;
  its reading (`+fprev2`, the same as `-mfprev2`'s) is in the unit test.
  Through `-m`, `-mllvm` passes options to the code generator, past
  the driver's reading; `-mllvm -mattr=...` and `-mllvm -mcpu=...` are
  not options this toolchain knows (it stops on them), so it is no
  route today, but it is the one the reading doesn't see.
- **Tested.** C-UNIT (`tests/test_build_flags.py`): the verdict on the
  readings of the SDK's set, `-mcpu=r3` alone, `-mno-fprev1`, another
  CPU, no CPU, double precision, SIMD and an unlisted feature. C-SEAMS
  (case flags): the flags folder built with `-mcpu=r3 -mfprev1`,
  `-mno-fprev1` (inner/, read as without float instructions), C++
  `-mfprev1` and assembly `-mcpu=r3`; and refused, each before any of
  its files is compiled, with its message: inner/ `-mcpu=r4`, the C++
  `-O2 -mfprev2` (only `-mfprev2` named) and the assembly `-msimd`.

### 2026-10-29 clean-mllvm: the owner's answers on `-Xclang`, `-mllvm` and fwtest 0.10.0's counts (BR-11, R-BUILD-5)

clean-pin-flags left two questions on the flags a folder may set, and an
unexplained change in fwtest 0.10.0's instruction counts.

- **`-Xclang` stays refused.** As since clean-1028: it is not one of the
  families `check_flags` takes (exit 2).
- **`-mllvm` is refused outright.** It came in under `-m`, and passes
  options to the code generator past the driver, so the `-###` reading
  that keeps a folder's code to the SDK's CPU and float can't see what it
  does. `check_flags` now refuses `-mllvm` and its joined spelling
  `-mllvm=...` (exit 2) with a message saying why, before anything is
  built. Tested in C-UNIT (`FolderFlagsTest`: `-mllvm -fast-isel` and
  `-mllvm=-fast-isel` refused with the message, `-Xclang` still refused,
  plain `-m` flags taken) and among the flags case's refusals (C-SEAMS).
  The guide's section 5 says so.
- **fwtest 0.9.0 to 0.10.0: why three cases' counts moved.** The pin
  (#176) found audioload, store-busy and store-wipe's instruction counts
  per block differing in 28, 7 and 2 blocks (totals under 0.01 %), with
  every golden, outcome and check the same. The cause, from the spec
  side: 0.10.0 runs `*p &= ~m` on the same path as the other memory
  operations, which moves instruction counts slightly with the same
  results. These three cases are the ones that save while the audio
  runs.

### 2026-10-30 clean-br16: starting without the base's bring-up screens (BR-16, R-ENG-2)

A firmware built on the base asked (BR-16) to start without the base's
bring-up screens: today main shows the address pattern, waits until
500 ms and draws the test screen at every power-on, before the engine's
first serve can draw its own.

- **The option.** `SB_NO_START_SCREENS`, given with `--define` (so main.c
  sees it; a folder's `--cflags` never reach the base's files). Under
  it main, after `lcd_init()`, fills the frame buffer black (the
  engine's init may already have drawn into it), sends it and turns the
  display on, as the pattern is sent today: the panel's memory is
  written before the display shows it. It does not wait for the test
  screen's time and never draws the test screen.
- **A state of its own.** `sb_beacon.screen` is `SB_SCREEN_BLANK` (4,
  after the existing values, which keep their numbers) until the engine
  sets its own. The heartbeat is drawn only while the state is
  `SB_SCREEN_TEST`, so it stays off; `render_ticks` stays 0. The
  firmware suite's checks read the default build only, which is
  unchanged: build A's image is the same bytes as before
  (`5bc12a34…`), so every golden is too.
- **Only with an external engine.** Without `SB_ENGINE_EXTERNAL` the
  base's instrument would show black until the first touch (its screens
  start then), a configuration nothing tests; main.c stops the build
  with an `#error` instead.
- **How much sooner.** The first serve moves from 500 ms to 127 ms in
  fwtest: 373 ms, not the whole 500, because `lcd_init()`'s own waits
  (120 ms after the reset, 5 ms after sleep out) stay. The case's bound
  is 300 ms.
- **Tested.** C-SEAMS, case nostart: the test engine (which since this
  change records, at its first serve, the heartbeat's time, the screen
  state and the whole frames sent, and with the option draws a square
  of its own there) built with and without the option, and the option
  alone refused. Without the change in main.c the case fails on every
  check (the first serve at 500 ms both ways, the test screen on the
  panel).

### 2026-11-17 clean-br17: a package for a unit's installer (BR-17, R-PKG-1, R-PKG-3, R-REL-4)

The FM-1 unit arrived, and its third-party USB installer refused our
`.fwsc` (made at `ab16ee2b`) before writing anything: "damaged firmware
package (file list CRC)". Our packager wrote 0 where the spec had not yet
placed a field. The spec side has since answered what JieLi's own
packaging tools write (HARDWARE-SPEC section 24, HW-103 to HW-108, #180;
PROVENANCE P-66 for this side's use). The owner's two answers
(docs/prompts/clean-br17-answers.md): the first app-area-only package
leaves out `blimit.bin`, `info.log`, `ota.bin`, `script.ver` and
`tail.bin`, the unit settling which an installer needs (Q-26), with
R-REPRO held; and the candidate is a `.fwsc` holding only the app area,
the form the owner's installer takes, not HW-106's OTA form.

- **Section 24's fields, written (part a).** `tools/fwsc.py` writes the
  header's list CRC (the CRC-16 of the entry list as stored, masked, from
  logical offset 64, the block markers taken out), its image size (the
  logical image's length, the file's less 20) and the chip's name
  `AC791N`; the entry's index, data CRC (of the flash image as written to
  flash), rounded length and name `flash.bin`, its data moved to logical
  `0x400` (a multiple of 32, as the tools put it; the file offset 1007
  stays 0); the flash header's FM-1 values (HW-105), its VID `0.01` and
  PID `AC791N_STORY` plain on flash, its CRC over the head unmasked whole;
  every head's name ended by one zero byte and padded with `0xFF`; the
  key block's head attribute 2 and reserved `0x80`; `app_dir_head`'s
  length `0xFFFFFFFF`, data CRC `0xFFFF`, reserved `0xFF`; a `key_mac`
  head (`0xFF000`, 4 KiB, attribute `0x12`, reserved 1, last), a region
  the package writes nothing to; the area head named `app_area_head` at
  `0x02000120`, attribute `0x83`, reserved `0xFF`. The reader matches
  names up to their first zero byte (HW-105), which is what made it
  refuse JieLi's own packages. `fields()` checks all of these; fwtest's
  nine checks (`check()`) are unchanged, since they mirror fwtest's own
  in its order.
- **Left as they were (Q-25), and said so.** The header's bytes 10-15
  stayed 0 at first; since the owner's answer below they carry the tools'
  4 and `0x200`, their meaning still open; the 64 bytes
  the tools write after the area are not written; the key block's head's
  data stays our key block and its CRC (the tools write a 765-byte
  configuration that starts with them); the 48-byte blocks stay HW-88's,
  though which program adds them is not known (HW-107). Every pack prints
  these, with the Q-26 items, as `fwsc: open (Q-..): what: what we
  write`.
- **"Today's full-image mode, unchanged"** is read as its layout and its
  use: the flash image from 0, for fwtest, the emulators and the app. Its
  bytes change with the fields above. C-PACKAGE passes on it as before
  (the same outcomes, instructions and outputs as the raw image in eight
  cases; each broken package refused at its check with fwtest's words),
  and C-RELEASE (built twice, the same bytes).
- **The app area alone (part b).** `fwsc.py pack --app-area --key KEY`
  writes one `flash.bin` entry holding the flash image's bytes from
  `0x4000`: the area head, the area's directory (app.bin alone) and the
  app, scrambled with KEY. No flash header, directory or key block, so
  the key travels with nothing and must be given: `0xFFFF` (the tools'
  without a key file, HW-105, HW-108) or `0x980F` (the stock package's,
  HW-90); which a unit runs is Q-26. `isd_config.ini`'s entry is left out
  too: its data is not given and it lives below `0x4000` (HW-105,
  `0x3628`). So the package holds `flash.bin` alone, which is the owner's
  answer 1 with that one more; the owner confirmed it on merging #181
  (docs/prompts/clean-br17-answers-2.md): `isd_config.ini` lives below
  `0x4000`, and an app-area-only package leaves that region alone.
- **Where an installer writes it: open (SR-12).** No fact places a
  `.fwsc` entry's data anywhere but flash 0: HW-89 says the type-0 entry
  is written from offset 0, and HW-104's entry fields are file offsets.
  HW-106's OTA file states no flash offset either; its target is
  implied. So `--app-area` takes the entry to go at `0x4000`, our
  reading, and an installer that follows HW-89 would write the area's
  bytes from 0, over the unit's loader and its recovery. The candidate
  is made because the owner asked for this form for their installer;
  the risk is put to the owner before they try it, and SR-12 asks for
  the field.
- **Nothing below `0x4000`, tested** as the reader reads the package
  (`below_area()`): its entries only `flash.bin`; that entry not a flash
  image from 0 (one that passes fwtest's checks is refused); an area
  head first under the key; no head in the area's directory naming a
  region below `0x4000` (app.bin's offset counted from `0x4000`, a
  region's as a flash offset, HW-90). The test also lists every entry
  and region from the file's bytes itself and checks each start, and
  shows the check failing on the full image and on an area with a region
  head at `0x3000`. Under our reading of SR-12 the entry's own placement
  is our assumption; what the test proves is that the package carries no
  boot-area structure and names nothing below `0x4000`.
- **The hardware mode.** `--hardware` refuses (exit 2, nothing written)
  while any field a unit needs is open, naming each with its Q-number or
  SR (today seven: three Q-25, three Q-26, SR-12), and refuses the full
  image outright (it writes the boot area). It always refuses today; it
  is the mode a release for a unit will use once the unit and the spec
  have settled these.
- **A hardware target (part c).** `release.json`'s `targets` may name
  `fm1-unit` beside `f-emulator-app`, only for a tag listed in
  `config/releases.json`'s `unit_checks`, which names the unit check and
  how much was checked; the release notes say it, and say "not checked on
  a unit" otherwise. No tag is listed (R-REL-4; docs/RELEASING.md).
- **The owner's answers to the report** (docs/prompts/clean-br17-answers-3.md,
  after #181 merged): (1) the owner tries both candidates on the unit and
  sends the installer's exact words; nothing to do on them until then.
  (2) The header's bytes 10-15 carry the values JieLi's tools write, 4 and
  `0x200`: fixed, so the same inputs still give the same bytes; taken
  from the tools, their meaning open (Q-25), and every pack says so. The
  candidates were packed again with them. (3) The key: `0xFFFF` first,
  then `0x980F`. (4) The disk measurement that walked other roles'
  folders was acceptable (sizes only, no file opened); a clean session
  measures only its own folders from now on. And `flash.bin` alone is
  right: `isd_config.ini` lives below `0x4000`, and an app-area-only
  package leaves that region alone.
- **Round 1 on the unit, and round 2** (docs/prompts/clean-br17-unit-1.md,
  2026-11-18). The owner tried both app-area `.fwsc` candidates, `0xFFFF`
  first. The installer refused both before writing anything: "unexpected
  flash image size 55608", which is our `flash.bin` entry's length; the
  unit is unchanged. A unit's behaviour is not among the firmware side's
  sources (CONTRIBUTING.md: our experiments run in the emulator), so the
  observation goes to the spec side in SR-12's evidence and SR-13's
  question, and no fact is drawn from it here. What follows for the
  candidates: the installer reads the type-0 entry as a flash image with
  an expected size, so a `flash.bin` sized to pass (a guess this side
  won't make: a multiple of 32 or 4 KiB, or HW-105's `0xFF000`) is the one
  most likely written from flash 0 (HW-89), over the loader. The refusal
  protected the boot area. No more app-area `.fwsc` candidates until
  SR-13 is answered; the mode stays as it is.
- **The OTA form** (`--ota`, R-PKG-4) is round 2, as the owner's answer 2
  foresaw ("if the unit refuses the .fwsc candidate, we'll ask for it
  then"), read as asked by "make the next candidates from this". It is
  JieLi's own app-area-only form (HW-106): two heads, `update_data` over
  the file and `app_core` over the data, then the flash image's bytes
  from `0x4000`; no `.fwsc` blocks, no entry list, no type-0 entry. Here,
  unlike the `.fwsc`, the placement is HW-106's ("the flash image from
  `0x4000` only"), not our reading. Open and printed: the 64 bytes after
  the area, part of `app_core`'s data and CRC (Q-25; `0xFF`, our choice),
  the heads' name padding (HW-106 doesn't say; HW-105's rule, our
  choice), whether the installer takes the file at all (Q-26; HW-106
  notes the stock updater takes `.fwsc` files), the key and the checks
  (Q-26). Its files are named `.ufw`, as the SDK's `update-ota.ufw`. If
  an installer wrote this file's data from flash 0 it would still
  overwrite the loader; trying it is the owner's call.
- **Held** (docs/prompts/clean-br17-hold.md, 2026-11-18): the owner holds
  the OTA candidates this round. The spec side is settling SR-12, SR-13,
  Q-25 and Q-26 from new sources under an owner ruling; the next
  candidate is made from that update, and this pull request stays open
  until then.

### 2026-11-18 clean-br17-round2: a hardware package from what the unit checks (BR-17, R-PKG-3)

HARDWARE-SPEC section 25 (#184; PROVENANCE P-68) says what the unit's
installer (m-flasher) checks, in order, what it writes and where, how it
gets the chip key, and what the bootloader (m-bootloader) checks before
it starts an app; HW-114 answers SR-13. Round 1's refusal ("unexpected
flash image size") is HW-109's step 8.

- **The installer writes from `0x4000` up and keeps the boot area**
  (HW-110), and takes `flash.bin` from flash 0, its offsets as flash
  offsets. So BR-17's app-area-only package is a `flash.bin` from flash
  0, sized as HW-114 says: SR-12's and SR-13's concern (an image written
  from 0 over the loader) doesn't arise with this installer. The area-only
  `.fwsc` of clean-br17 (`--app-area`, its reader and its tests) is
  removed: its shape is the one the installer refused.
- **`fwsc.py pack --hardware --key K --store-base ADDR`** writes it: the
  emulator package's boot area as it is (flash header, directory, key
  block, every field and CRC by HW-104 and HW-105; never written to a
  unit), the app area scrambled with K, the unused head slots up to
  `0x120` `0xFF` before scrambling (HW-114: so their CRC fails and the
  bootloader's walk ends there; zero slots would read as records), and
  the image padded with `0xFF` to the first 4 KiB boundary at or after
  the area's end and its 64 trailing bytes (HW-114), never further. K
  has no default (HW-111): the owner reads the unit's key with
  `m-flasher info`. The identity is `FM-1_<version>`, the version without
  `_` (HW-109 step 9). One entry, `flash.bin`.
- **What it must not reach.** Everything from `0x4000` to the image's
  end replaces the unit's flash, `0xFF` filler included (HW-110), so
  `pack` refuses an image that would end past the stock VM region's
  start (`0x94000`, HW-80) or past the store region's start, given as
  `--store-base` (required: a firmware's own region may lie in the app
  area after its image, R-STORE-12; the base's is `0xFC000`).
- **`fwsc.py check FILE --key K`** (`unit_check()`) runs HW-109's checks
  1 to 11 and then HW-112's 1 to 3, stopping at the first that fails,
  with the installer's own words for checks 3, 5, 8 and 11; on success
  it prints the range the installer writes. Readings taken where the
  facts leave the checker a choice: check 2 fails on a `0x7D` at file byte
  1007 (the prompt's rule: the installer would take a 21st block); check
  11's "valid file table" is the area head's own CRC passing, then the
  records HW-112 reads (at most eight, to the first whose CRC fails);
  HW-112 step 2 fails on an all-zero slot read as a record (HW-114); step
  3's bounds are inside the 1 MiB flash, and the entry inside the area
  (the area head's length from `0x02000000`). `pack --hardware` runs it
  before it writes.
- **Tests**: a hardware package passes, each field recomputed from the
  file's bytes (the header and list CRCs, the entry's CRC over the
  stored bytes, the length rule, the `0xFF` filler and slots, the area
  head, `app.bin`'s CRC, the boot area's heads), for both keys;
  `broken_hardware()` makes one package per check (16, covering HW-109 1
  to 11 and HW-112 1 to 3: short, byte 1007, header CRC, list past the
  image, list CRC, an entry past the image, `flash.bin`'s CRC, the size,
  the model, a `_` in the version, longer than the flash, a file's CRC,
  no `app_dir_head`, zero-filled slots, the area head's attribute, the
  entry outside the area), each failing exactly that check; a `0xFFFF`
  package fails check 11 under `0x980F`; the emulator package fails
  check 8. The emulator package is byte for byte main's, and so are its
  broken packages (compared with main's packager), so C-PACKAGE is
  unchanged.
- **No more OTA candidates for this installer**: HW-106's OTA file has
  no type-0 `flash.bin`, so the installer refuses it at HW-109's step 7.
  `--ota` (R-PKG-4) stays for other updaters.
- **The key for the first candidate.** The prompt gives K as the unit's
  key, read with `m-flasher info`, which this side cannot read. HW-111:
  every unit known to the bootloader's author uses `0x980F`, but neither
  tool assumes it. The candidate is made with `0x980F`, named for it, and
  the owner is asked to confirm `m-flasher info` shows `0x980F` before
  trying it; for another key, the same command with that key makes the
  right one.
- **Round 2 on the unit** (the owner's report, 2026-11-18, relayed; a
  unit isn't among the firmware side's sources, so it goes to the spec
  side as SR-14's evidence): the installer accepted the hardware package
  (`847f3c5a…`), wrote `0x4000`-`0x11FFF`, verified it and kept the boot
  area; it reports "firmware check OK" and chip key `0x980F`;
  m-bootloader's menu shows "app OK". Then nothing shows: a black
  screen, no LEDs, no key lights, from power-on and from Boot app. **The
  hardware package is done**; what is left is start-up on real hardware.
  Our firmware sets up no port pin (fwtest needs none), and the pins the
  panel, its backlight and the LEDs need on the board are Q-6 and Q-7, so
  no candidate can light anything until SR-14 is answered. Guessing a pin
  is the mistake round 1 avoided by not guessing a length. No
  `unit_checks` entry: the firmware doesn't run.
- **The entry-return probe** (R-PROBE-1, `SB_PROBE_RETURN`) is the one
  probe possible now: its first instruction is `rts`, the return our own
  code uses (crt0.S), before any register or RAM is written. HW-112:
  m-bootloader calls the entry, and opens its recovery menu when the app
  returns. The menu appearing would say the entry is reached and the
  call is a call; nothing appearing, that the bootloader doesn't enter
  our code as we think. It can't go deeper yet: a later stage writes RAM
  that may be m-bootloader's own (`uboot.boot` loads at `0x01C02000`,
  inside our RAM), so a return after it means nothing until SR-14's item
  3 says what RAM the bootloader keeps. In fwtest, where every register
  but r0 starts at zero, the return jumps to 0 and faults at once.


### 2026-11-18 clean-br17-light: the backlight and PLAY's LED from the entry (BR-17, R-PROBE-2)
The owner's prompt: docs/prompts/clean-br17-light.md. The facts are
HARDWARE-SPEC section 26 (HW-115 to HW-119, the spec side's answer to
SR-14, merged in #186), with HW-56, HW-91 and HW-112 (PROVENANCE P-70).
The round-3 entry-return probe (`1b61609e…`) is still waiting on the
unit; this probe doesn't depend on its result, because it ends with the
same return.
- **The light probe** (R-PROBE-2, `SB_PROBE_LIGHT`, `firmware/src/crt0.S`)
  does the prompt's four steps at `_start`, before anything else:
  1. PA2 an output driven low (HW-116);
  2. PA1, PA3, PA4, PA9, PA10, PH6 and PH9 outputs driven low, `0xFBFF`
     shifted in and latched, PA10 high (HW-117, HW-118);
  3. a hold;
  4. PA10 low, `0xFFFF` shifted in and latched, PA2 an input, and `rts`.
  Each pin's `OUT` bit is cleared before its `DIR` bit, so no pin is
  ever briefly an output driven high. Each data, clock and latch edge is
  its own read-modify-write of `OUT` (the core's one-instruction
  `[rN+0] |= bit` / `&= ~bit`), with `csync` after it, as HW-117 asks.
  The assembler takes one bit per such instruction, so each pin has its
  own.
- **Why assembly at `_start`, not C.** Nothing outside `.text.entry`
  and `.boot.text` is in place before `sb_start` has copied the code and
  constants to RAM. A C function could also spill to the stack or call
  a helper. The probe uses r0 to r3 alone, no stack, no RAM. It never
  calls, so `rets` still holds m-bootloader's return address at the
  `rts`, and `sp` and `ssp` are never written. r0 to r3 are registers a
  called function may change. That is a toolchain fact, not a hardware
  one: the pinned compiler (P-1), compiling a leaf function of our own,
  saves r4 and up and never r0 to r3 (P-70). Nothing is written in the
  bootloader's RAM or the retained area: the probe writes only port A's
  and port H's `OUT` and `DIR`. This is what HW-119 says a return needs.
- **The hold** is 900 000 000 passes of a two-instruction loop. That is
  5 s at HW-119's 360 MHz if the core runs one instruction a cycle from
  the cached window, and longer if a taken branch costs more. A busy-wait,
  not a timer: HW-119 leaves TIMER0 stopped, and its prescaler on the
  chip is Q-3. In fwtest, at 240 MHz, the hold is 7.5 s of emulated time
  and about 17 s of wall time, so the seams suite runs the very image
  the candidate holds, with no shorter test hold.
- **In fwtest** the port registers are modelled, so none of the probe's
  accesses is in `unmodelled_accesses`. The LED at row 2, column 10
  (fwtest's LED 12, HW-35, HW-42) is lit the whole of every sample until
  the return, and no other LED ever is. fwtest has no backlight, and
  `--ram` saves only RAM, not the port registers, so neither PA2 nor the
  switching off (PA10 low, `0xFFFF` latched, PA2 an input) can be seen
  there. They were checked in the probe's disassembly, instruction by
  instruction against the four steps, and nowhere else. Build A without
  the define was rebuilt from this change's tree and compared by hand
  (`5bc12a34…`): no CI check records its hash. The return jumps to 0, where every register
  but r0 starts in fwtest (HW-1), and faults as R-PROBE-1's does, after
  the hold.
- **On the unit**, three outcomes:
  - the backlight on (the panel isn't set up, HW-115 is the next round,
    so a lit black or blank screen) and PLAY's LED lit, for about 5 s,
    then both out and m-bootloader's menu with "APP EXITED": the entry
    runs, the pins are right, and the return keeps what HW-119 needs;
  - nothing lit, but "APP EXITED": the entry ran, and the pins or their
    set-up are the question;
  - neither: the entry wasn't reached (round 3's result should agree).
- `SB_PROBE_RETURN` and `SB_PROBE_LIGHT` together are refused by an
  `#error`. Without either, build A is `5bc12a34…`, byte for byte as on
  main.

### 2026-11-18 clean-br17-panel: the panel from the entry (BR-17, R-PROBE-3)
The owner's prompt: docs/prompts/clean-br17-panel.md.
- **Light1's result on the unit** (`74e19144…`, the owner's report): the
  backlight came on and PLAY's LED lit for about 5 s, both went out,
  and the menu said "APP EXITED". So the entry is reached, HW-116 to
  HW-118's pins work as written, and the return keeps what HW-119 says
  it must. The round-3 entry-return probe is no longer needed. The owner
  has confirmed the key `0x980F` on the unit with `m-flasher info`.
- **The panel probe** (R-PROBE-3, `SB_PROBE_PANEL`) brings the panel up
  as HW-115 gives it and draws red, green, blue and white bars 60 pixels
  wide, left to right, with a yellow 40 × 40 square at (0, 0). The bars
  show whether the colours come out right with inversion on, and the
  square shows which corner is (0, 0), so the picture answers Q-6's
  orientation question too. Then the backlight is on for about 5 s; the
  backlight goes out, SPI1 is switched off (`CON` 0, as HW-119 says the
  bootloader leaves it after its menu), and the probe returns as light1
  does. PC7 to PC10 stay outputs and `JL_IOMAP->CON1` bit 4 stays set,
  which HW-119 also gives as the state after the bootloader's own menu.
- **In C, on a stack of its own.** The bring-up is too long to write
  well in assembly, so `_start` switches to a stack at `__stack_top`
  (`0x01C7FC00`) and calls `sb_probe_panel` (probe.c). That address is
  above m-bootloader's RAM (below `0x01C0A800`) and below the retained
  area (from `0x01C7FD80`), so nothing HW-119 asks a return to keep is
  written. The deepest the probe goes is a few dozen bytes. The loader's
  `sp` is kept in r4, with r4's own value and `rets` saved on the new
  stack. The compiler saves r4 and up in each function (P-70), so r4
  comes back unchanged. `ssp` is never written, and interrupts stay off.
  Every function is in `.boot.text`, because `sb_start` hasn't copied the
  rest of the code to RAM. There are no tables, so nothing is read from
  `.rodata` either. The disassembly shows every call and load staying in
  the window and the registers.
- **Every byte through `BUF`**, pixels included, as HW-115 says for the
  command and data bytes. A frame by DMA would need `ADR` and `CNT` set
  up as well, and buys nothing for a probe: 230 400 bytes at about
  12 MHz take a fraction of a second either way.
- **The waits** (150 ms after the reset, 120 ms after sleep out, the 5 s
  hold) are passes of a two-instruction loop counted for HW-119's 360 MHz
  at one instruction a cycle. A slower loop only makes them longer,
  which the panel's minimum waits (HW-32) allow.
- **In fwtest** the screen at 3 s and at the end is the picture, every
  pixel, from the raw image and the emulator package. The return comes
  at 7.9 s: the waits at fwtest's 240 MHz, plus the bytes. fwtest needs
  no pin set-up or waits and has no backlight (HW-29, HW-32), so those
  parts are checked in the disassembly only.
- **On the unit**, the outcomes:
  - the bars and the square on a lit screen for about 5 s, then the
    backlight out and "APP EXITED": the panel works as HW-115 says.
    Which corner the square is in, and whether the colours are right,
    settle Q-6's orientation and colour questions;
  - a lit screen that stays black or blank, then "APP EXITED": the
    bring-up didn't take. Something in HW-115 is missing or different,
    for example `CON`'s other mode bits (Q-6);
  - a picture in the wrong colours, or noise: the panel is reached, and
    the mode or byte order is the question;
  - no "APP EXITED" (a hang or a reset): the return or the stack is
    wrong. Light1 returned, so the new part is the stack.
- **Panel1's result on the unit** (`5ffe64fc…`, the owner's report and
  correction): colour bars with the yellow square in the top-left
  corner, the backlight on, then "APP EXITED". So HW-115's bring-up
  works, and the picture's (0, 0) is the top-left corner as the FM-1 is
  held, as fwtest shows it, with `MADCTL` `00`. The owner's first report
  said top right and was corrected at once; no record here takes that.
  The owner treats the orientation as right, and the start-up build's
  screen will confirm it.

### 2026-11-18 clean-br17-start: small-beeps' own start-up on a unit (BR-17, R-HW-1)
The owner's prompt: docs/prompts/clean-br17-start.md, with the
answers in clean-br17-start-answers.md. Panel1 worked on the unit, with
the square in the top-left corner; the owner takes the orientation as
right.
- **The reading taken.** "Its screen, keys, LEDs and timer from section
  26, as one hardware build": `SB_HW_FM1`, small-beeps' own start-up
  (the address pattern, then the test screen with its heartbeat) on a
  unit, staying in the firmware. Only what HARDWARE-SPEC gives on the
  chip is set up. Left out, for want of a chip fact (SR-16 items 4 to
  6): the FM engine and core 1, the audio output, MIDI, the store, the
  pot and the encoders. Without the store, the build writes no flash at
  all. The instrument's own screens need the engine and the store, so
  the build keeps the test screen. On it, each button or key pressed
  or released is named (its control number and label), and its LED
  follows it, so a unit shows which contact is which (Q-7). No release
  gets the build, and no `fm1-unit` entry.
- **A black screen must say where it stopped.** Each step that rests on
  an assumption about the chip is bracketed by a band, drawn polled
  through SPI1's `BUF` as panel1 drew, with code in the window
  (`hw_fm1.c`):
  1. band 1 (blue), from `sb_start` before the copy: the panel brought
     up as HW-115 gives it, then the backlight on;
  2. band 2 (green), at `main`'s start: the code copied to RAM, over RAM
     m-bootloader used, runs (SR-16 item 3);
  3. band 3 (white), after interrupts are on and TIMER0's tick has
     counted two beats in a spin: the vector table, interrupt entry, its
     stack and TIMER0 (items 1 and 2);
  4. then the address pattern and the test screen, by DMA chained on
     SPI1's interrupt, as in build A. Between the two, `sb_wait_ms` uses
     `idle`, whose chip behaviour is item 2's;
  5. the heartbeat counting seconds, in the main loop's `idle`.
  A halt (a fault, a stray interrupt, a stack guard) draws the whole
  screen red, polled, in place of the console line no unit shows (Q-5).
- **One timer.** HW-119 gives TIMER0's clock at the app's entry (the
  60 MHz low-speed bus); nothing gives TIMER1's (the scan's) or TIMER4's
  (the time base and the clock measure). So TIMER0 interrupts every
  5000 counts at prescaler setting 0 (HW-48's ÷1): 83.3 µs, one scan
  slot. Every twelfth slot runs the tick, `sb_tick` and `input_scan`
  become ordinary functions of that one handler (`hw_slot`), and
  `sb_now()` returns the slots and the count in the same 24 MHz units as
  before, so every caller is unchanged. `CON` `0x1` to run it is
  fwtest's reading of bits 0 and 1, taken for the chip (SR-16 item 1).
  If it's wrong, the screen stops at band 2.
- **The scan's pins and edges** are HW-117's and HW-118's: latch, clock,
  data and the four LED lines outputs driven low; the rows PA5 to PA8
  inputs with `DIE` and the pull-up on and the pull-down off. Each bit
  goes in with each edge its own read-modify-write of `OUT`, `csync`
  after it, and the LED lines low. PA2 stays low from `hw_early` on, so
  the backlight is lit and the matrix enabled. Rows 0 and 5 (the
  encoders') are ignored. The column walk is build A's, one 0 bit from
  bit 0 to bit 10. That reaches PLAY's and REC's columns (`0xFBFF` and
  `0xFF7F` select bits 10 and 7), but OCT−'s and OCT+'s words clear two
  bits each, one of them past 10. Whether they read is an outcome to
  report, and SR-16 item 4.
- **The LEDs are multiplexed** as in build A: a key's LED is lit only
  while its column is selected, one slot in twelve. At "full" it is
  about as bright as m-bootloader's, which lights its three menu LEDs at
  a third each.
- **`SPI_CON`** is `0x21` in this build: lcd.c's writes set every bit,
  and build A's `0` would switch SPI1 off on the chip (HW-55).
- **The vector table at `0x01C7FE00`** (HW-18) is inside HW-119's
  retained area. A return would need that area kept, but this build
  never returns, and the table has to be there. Whether the area
  matters at the next power-on is SR-16 item 2.
- **In fwtest** TIMER0 counts 24 MHz (HW-48), not 60, so this build's
  slots, beats and seconds all run 2.5 times slow there, and the test
  allows for that. The bands, the pattern, the test screen, PLAY's name
  and LED, and the red halt screen are all checked (seams case hw).
  The waits, the pins' set-up and the backlight are not visible in
  fwtest; the disassembly shows `hw_early` and everything it calls
  running from the window.
- Build A without the define is still `5bc12a34…`, byte for byte.

### 2026-11-18 clean-br17-start2: start1 on the unit, and the chip select (BR-17, R-HW-1)
The owner's prompt: docs/prompts/clean-br17-start2.md.
- **Start1's result** (`c02427d9…`, the owner's report): the backlight
  and bands 1, 2 and 3 in order, then nothing more drawn, and no red
  screen. Every button tried (PLAY, OCT− and OCT+ included) lit its own
  LED while held and put it out on release.
- **What that says.** The owner read it as the drawing stopping at the
  first DMA transfer. The LEDs say otherwise. In this build only
  `hw_serve`, in the main loop, lights an LED (main.c; `views.c`'s
  caller isn't built in, and `probe.c`'s is a test build's). The main
  loop only begins after the pattern and the test screen have been sent
  and `lcd_wait` has seen their transfers end. So on the chip SPI1's DMA
  ran, its interrupt came for every chunk, `idle` woke, and the keys
  were scanned, debounced and queued. It also suggests that OCT− and
  OCT+ each give an event the walk reads, since each lit its own LED and
  only an event lights one. The test screen will show whether each is
  named as itself. The panel just didn't take what lcd.c sent.
- **The cause: the chip select.** HW-115 sends every command with PC7,
  the panel's chip select, low, and raises it after. `hw_early`'s
  polled path does so (`hw_cmd`, `hw_end`), but lcd.c was written for
  fwtest, which doesn't model PC7 (HW-30), and never drives it. After
  band 3, PC7 was high, so the panel ignored every byte. Nothing in
  fwtest could show this.
- **The fix**: in the hardware build, `lcd_command` raises PC7 and lowers
  it again as each command starts, once the transfer before has ended,
  with `csync` after each edge. So PC7 is low through each command, its
  data and a frame's DMA, and high for a moment between commands. After
  the last command it stays low until the next. HW-115 raises it after
  each command; whether staying low between frames matters to the panel
  isn't stated, and nothing else is on SPI1.
- **The bands asked for**, so the next result reads either way:
  - band 4 (yellow), drawn over the pattern once its DMA chain has ended
    by SPI1's interrupts;
  - band 5 (magenta), if a chain is still going 500 beats after it began
    and `CON` bit 15 says its transfer is done: the interrupt never came;
  - every LED lit, if the transfer never finished: then SPI1 can't draw a
    band either.
  In fwtest a transfer finishes at once, so only band 4's path and band
  5's (with SPI1's interrupt left off, `SB_TEST_SPI_NO_IRQ`) are tested.
  The all-LEDs path isn't.
- No spec request: HW-115 already gives the chip select, and start1
  showed the DMA and SPI1's interrupt working as HW-29 and HW-55 give
  them. SR-16 stands as filed.

### 2026-11-18 clean-sr15-flash: the store on both flash parts (SR-15, R-STORE-13)
The owner's prompt: docs/prompts/clean-sr15-flash.md. The facts:
HARDWARE-SPEC section 27 (HW-120 to HW-124), with HW-76 to HW-79 and
HW-83, docs/SPEC-REQUESTS.md's SR-15 and HARNESS.md's "The flash chip"
(PROVENANCE P-74).
- **Start2's result first** (the owner's report on #190's last
  candidate, `128ea17b…`): bands 1 to 3, the address pattern with band 4
  over it, then the test screen, its seconds counting at a watch's rate,
  so TIMER0's reading in SR-16 item 1 holds. PLAY shows "12 PLAY down"
  and "12 PLAY up" with its LED following it; OCT− shows "00 OCT-" and
  OCT+ "01 OCT+", and every other button and key its own number and
  name. The chip select was the whole story, and the column walk reads
  the board's matrix as fwtest's (SR-16 item 4, relayed for the spec
  side to take).
- **The store, as "The part's rules" (above) now says:**
  - it writes to both parts' IDs and refuses every other one;
  - it reads both status bytes at start-up and refuses to write if any
    protection bit is set;
  - it reads each erase back after the wait on the busy bit.
  HW-124 items 2 and 3 were already met (SR-15 says where), and still
  are: the only new command is `0x35`, which item 2 allows, and the
  read-back comes after the wait, never in place of it.
- **The record** gains `status` (status 1 | status 2 << 8) beside
  `part`. The engine's records follow the store's at `0x01C00870`,
  where firmwares built on the base assert theirs (BUILDING-ON), so the
  record can't grow: the command trace gives up its oldest entry (31,
  not 32), which no test reads. store.c asserts the record's size.
- **The tests.** fwtest's chip answers only `85 60 14` and, before
  0.12.0, never showed protection (since 0.12.0 it does when the flash
  file sets it: clean-br17-protect), so a test build, `SB_TEST_STORE_PART`, takes the ID and the
  two status bytes from the test's flash file (16 bytes past the cut
  build's parameters at chip offset `0xE8000`, below the store) in place of what it
  read; everything else runs as on the chip. The store suite's case
  part saves slot 1 and finds it at the next start with either ID, and
  refuses every save, writing nothing, with an unknown ID and with each
  of BP0 to BP4 and CMP. The seams suite's case parts writes and reads
  back a firmware kind's 4 096-byte payload with the test engine's region
  at `0x80000`, as RevoiceDX keeps its saves, with either ID, and refuses
  it with an unknown one.
- **The images that change:** every image that links the store, since
  its code changed: the firmware's own (build A, `5bc12a34…` before), the
  test builds, and the test engine's. The store's format and every
  record on a chip are as before (docs/STORE-FORMAT.md unchanged). In
  fwtest, whose chip reads status 0, the shipping image behaves as
  before but for the start-up's two status reads and each erase's
  read-back.
- **What a real second part in fwtest would test that these cases
  can't** (for the owner to raise as a harness request, if wanted): the
  erase read-back failing. fwtest never ignores an erase, so a protected
  erase that does nothing, the path HW-124 item 4 guards, isn't run.
  Block protection modelled by fwtest's chip (an erase or program in a
  protected area ignored, with the bits set from the flash file) would
  run it. The part test build checks the refusal before any write, not a
  write the chip ignores. (Since fwtest 0.12.0 the chip does model it,
  and the store suite's case protect runs that path: clean-br17-protect.) The UC25HQ80's shorter times need nothing: the
  store waits on the busy bit either way.
- **Not in this change**, as the prompt says: handing the flash from the
  code window to SPI0 and back on a unit (Q-22) and SPI0's clock (HW-124
  item 6). The store doesn't work on a unit until Q-22 is settled, on
  either part, so the hardware build (R-HW-1) still leaves it out.

### 2026-11-19 fwtest 0.11.0: the panel's chip select in fwtest (clean-br17-start3, item 0)
`config/fwtest-image` moves to fwtest 0.11.0
(`sha256:34ec6720…`, published from main at `5f56a5f7`, #192), whose
panel ignores SPI1's bytes while PC7 is an output driven high
(HARNESS.md, "The LCD").
- **Main's hardware build** (start2's, with PC7 driven by lcd.c) passes
  the seams suite's hw case on 0.11.0 as on 0.10.0.
- **Start1's build** (`58c87df3`; its package link `46bbb942…`, the bytes
  the owner installed), rebuilt from that commit's files, now shows on
  0.11.0 what it showed on the unit: black, then bands 1, 2 and 3, and
  nothing more to the end of the run. Start1's own hw case fails there,
  on three counts: the screens were black then bands 1 to 3 and no
  pattern; no test screen; PLAY not named. So the chip select that only
  the unit caught (clean-br17-start2) is now caught in fwtest.

### 2026-11-19 clean-br17-start3: the matrix, the ADC, the flash and core 1 on a unit (BR-17, R-HW-1)
The owner's prompt: docs/prompts/clean-br17-start3.md. The facts:
HARDWARE-SPEC sections 27 and 28 (HW-120 to HW-130), with HW-9, HW-18,
HW-40, HW-56, HW-85 and HW-115 to HW-119 (PROVENANCE P-75).
- **What start3 asked that #193 already did.** Part (c) step 2 asks for
  the store's changes from clean-sr15-flash.md. #193 (merged) made them:
  both IDs, the refusals of an unknown ID and of any protection bit with
  results of their own, each erase read back, the busy wait kept, the
  test build `SB_TEST_STORE_PART`, and the cases with each part, an
  unknown ID and each protection bit, at the default region and at
  `0x80000`. Start3 adds only what is new: the read-only round trip with
  its two LEDs, and the start-up counter at `0xFC000`.
- **The reading taken for the screen.** "Each reports on the test screen
  in rows of its own": the test screen keeps its border, its corner
  squares, its title, start2's event line and the beat, and gives the
  ramps', box's and font's rows to start3's. Start2's bands and its key
  and LED test are as they were.
- **Before the vector table** (HW-126): crt0 keeps r0 in r4 through the
  stack fill, and `sb_start` reads the chip key at +12 of the block r0
  pointed at before its copy. The vector table is written later, by
  `sb_irq_init`, as before. A `csync` follows the copy (HW-127). Both
  `ssp` and `sp` were already set before interrupts go on.
- **(a) The matrix.** Our scan (input.c) walks one 0 bit through the
  shift registers, one place a slot, twelve slots a cycle. With 16 bits,
  the 0 from the cycle before is still at bits 12 to 15 while the new one
  is at bits 0 to 3, so columns 0 to 3 are selected together with 12 to
  15. That is our firmware's walk, not a fact about the board. The unit
  confirmed every key under it, so start3 leaves the scan as it is.
  About ten times a second, main sweeps instead: the scan skips its
  slots, the LED lines go low, and each of the 16 single-zero words is
  shifted in light1's way, rows PA5 to PA8 read at least 10 µs later.
  Then `0xFFFF` is latched and the scan starts again from slot 0. Ports
  A, B, C and H's inputs follow in hex, the pins this build drives itself
  masked: PA1 to PA4, PA9, PA10, PB1, PB6, PC7 to PC10, PH6, PH9. Pull-ups
  this build sets: PA5 to PA8 only. By default (HW-85): PD0, and PB1,
  whose pull-up this build clears for the ADC. Every other pin is as the
  ROM left it. In fwtest a detent of an encoder is four contact changes
  2 ms apart that end where they began, so a sweep ten times a second
  can't catch one there: hw3 tests the grid with a key, and the encoders
  are the unit's to show.
- **(b) The ADC**: channels 0 to 11 in turn, as HW-40 gives the bits, each
  wait bounded. PB1 and PB6 are made analogue inputs as the prompt asks,
  which is this build's choice, not section 28's.
- **(c) The flash round trip** (HW-128), at start-up, after band 2, with
  interrupts off, all from RAM:
  - The window's `CON`, base and key, and the boot block's key, are shown
    first, before anything changes, so they can be read even if
    everything after hangs.
  - If `CON` reads 0, nothing is tried. HW-128's quad mode word might not
    be the width m-bootloader chose for this unit, and guessing wrong
    would stop the window the round trip is testing (SR-17).
  - Otherwise the build takes SPI0 as HW-128 lists, reads the ID and both
    status bytes, and lights PLAY's LED from RAM. Then it gives the flash
    back as HW-128 lists, except the window's `BAUD`, which has no
    address there and which the take never wrote. It writes back the
    `CON` it read, the base `0x4000` and the boot block's key, and bounds
    the cache's idle wait, counting a timeout.
  - The first thing it runs back in the window lights PLAY's and REC's
    LEDs together (their words `0xFBFF` and `0xFF7F` ANDed).
  If the round trip came back, the store's step follows band 3, with
  interrupts on (every handler is in RAM): one take, `store_init`, the
  counter's `store_get` and `store_put` (kind `0xF0`, id 0, a 4-byte
  count), one give-back. Its row shows the count, both results, the
  programs' and the erases' read-back failures (the latter a plain count
  of its own, since the store's record can't grow) and the ID. A halt
  while the flash is taken can't draw the red screen, which runs from the
  window.
- **(d) Core 1**: released after `sb_irq_init` (HW-9: slot 126 holds its
  start, and nothing writes that slot afterwards), a `csync` before.
  It runs a loop in RAM whose first instruction turns its interrupts
  off, counting in a RAM word that main shows once a second, with
  `C1_CON` read back.
- **In fwtest** the window's controller isn't modelled and its `CON`
  reads 0, so the shipping build tries no round trip there. The test
  build `SB_TEST_HW_WINDOW` takes HW-128's quad mode word in its place,
  and hw3 runs everything after it. Only the window's and the ciphers'
  registers are unmodelled (`0x01F0xxxx`, the cache's ranges, is RAM in
  fwtest, HW-7).
- Build A is unchanged (`aae50b29…`, #193's).

### 2026-11-19 clean-br17-start3b: where start3 stops on the unit (BR-17, R-HW-1)
The owner's messages: docs/prompts/clean-br17-start3b.md, then
docs/prompts/clean-br17-start3b-correction.md. On the unit, start3 drew
bands 1 to 3, the window's row (`CON` non-zero, about `0098038?`, base
`04000`, key `980F/980F`) and "flash 856014 s1 00 s2 02 back"; then the
address pattern, which stayed. No test screen; no LED lit and no button
lit one.

- **What that rules out.** The round trip came back (its row). The
  pattern is sent after band 3 and after the store's counter step, so
  that step returned too; the hang is after the pattern goes out: band 4's
  wait for the pattern's chain, the display-on command, the idle wait for
  the test screen, or the test screen's drawing. Buttons lighting nothing
  fits: only the main loop lights them, and it comes after the test screen.
  The round trip's LEDs couldn't be seen in start3: the scan, started a
  few milliseconds later, drives the same shift register and lines.
- **The flash at `0xFC000`.** Because the store's step returned, its
  `store_put` most likely ran: on a blank region it erases and writes in
  the store's region, `0xFC000` to `0xFEFFF`, and nowhere else. start3b's
  store row shows what it found: a count of 2 or more at its first start
  means start3's write landed.
- **The suspects, and how start3b tells them apart.** Core 1 is released
  after the store's step now, and the unit's build watches the tick for
  300 beats after each (a spin, its row red if the beats stand still).
  The wait for the test screen is a watched spin; idle follows alone for
  20 beats. Each step names itself in the step row as it begins. Every row
  is one transfer whose end is polled, so a row is drawn even with
  interrupts stopped.
- **The window's `CON`.** It reads back on the unit, as about the quad
  mode word HW-128 gives (bits 23 to 20 at 9): part of SR-17's question,
  relayed from a photo with one digit uncertain. start3b shows it again.

### 2026-11-19 clean-br17-finder: the knob finder, and core 1 (BR-17, R-HW-1)
The owner's message: docs/prompts/clean-br17-finder.md. On the unit,
start3b ran to its test screen and its main loop: every key registers; the
store counted 14, then 15 after a power cycle, so the earlier starts
had written 13 counts at `0xFC000`; the pot (MASTER) is channel 4.
Which of start3b's changes cleared start3's hang isn't known: core 1's
release moved after the store's step, and the wait for the test screen
became a spin. Core 1 still doesn't run.

- **Why start3's grid missed encoders.** It swept ten times a second. An
  encoder rests with its contacts open and closes them only between
  detents, so a slow sweep catches a contact only now and then, as KNOB1
  showed "only when spun fast". The finder sweeps without a pause, a few
  thousand times a second.
- **Pins and cells kept apart.** Reading every port at every column word
  finds a contact wherever it is wired. That includes a column against a
  pin that isn't one of PA5 to PA8, which start3's "in" row (read with no
  column) could never show. A pin wired outside the matrix changes at
  every word alike, so it counts as a change of its level with no column,
  not as 17 cells.
- **Noise.** Floating or busy pins would fill the lines, so the first
  3 s are hands-off: whatever changes then is left out, and each
  channel's threshold is twice its spread plus `0x18`.
- **No pin set-up changed.** The finder reads what start3b's set-up and
  m-bootloader left. It shows the pull-up and direction registers, so a
  control still unseen can be matched against the pins without
  pull-ups. Turning pull-ups on would be the next step's choice.
- **Core 1** (SR-18): HW-9's release left `C1_CON` at `01000002`, bit 3
  clear. The finder shows `C1_CON` before and just after the write, and
  the start word read back.

### 2026-11-19 fwtest 0.12.0: block protection in fwtest (clean-br17-protect, item 1)
`config/fwtest-image` moves to fwtest 0.12.0
(`sha256:70f2c788…`, published from main at `6aa273a9`, #196's merge),
whose chip takes status registers 1 and 2 from a flash file of 1 MiB and
two bytes, and ignores an erase or program that HW-131's table protects
(HARNESS.md, "The flash chip"). Every other flash file behaves as before,
so no existing case changes: none gives a file of that length.

### 2026-11-19 clean-br17-protect: the store against a protected chip, and the give-back's BAUD (R-STORE-13, R-HW-1)
The owner's prompt: docs/prompts/clean-br17-protect.md. The facts:
HARDWARE-SPEC HW-131, HW-133, HW-134 (with HW-9, HW-121, HW-124,
HW-128), SR-17's answer, and HARNESS.md "The flash chip".

- **The read-back, run at last.** The store suite's case protect gives the
  part test build ID `0x856014` and status 0, so the store's own check
  passes, and fills the store's region with old bytes, so the save has to
  erase. The flash file's status bytes set the chip's protection. With
  BP0 or BP2 the store's record shows one erase, no program, the save
  failed with `STORE_ERR_VERIFY` (`last_result` -3, `refused` 1, which
  counts every failed `store_put`), `verify_fail` 0 (it counts records
  read back wrong, not erases), no valid sector, and no head. The store
  doesn't retry the erase: `put_record` tries twice only when a record
  reads back wrong, and gives up at once when making room fails, as an
  erase that doesn't read back makes it fail. The control, CMP with BP2,
  protects the bottom half: one erase, two programs (the sector's header,
  then the record), the save done. The part test build keeps its own
  status bytes so a case can show the store's refusal before any write
  (case part) apart from the chip ignoring a write (case protect).
- **flash.bin's two status bytes.** `tools/store.py` gains `chip_of` (a
  flash.bin's first 1 MiB) and `status_of` (its two last bytes, or 0 and
  0), and `Image` takes either length. Changed to take the chip:
  `store_suite.py`'s `region()` and `outside_writes()`, and the three
  seams cases that read a run's `flash.bin` as the chip (`store`,
  `parts`, `powercut`). Nothing else needed a change. `store_suite.py`'s
  `Run` keeps the whole file, so a protected run's `flash.bin` stays
  protected as the next run's `--flash`. That is also why seams case
  hw3's first run, which hands its `flash.bin` on, and arp_suite's save
  case are left as they are. fw-suite's edit and settings cases read
  through `Image`.
- **The one give-back** is `flash_give` in hw_start3.c. It is used by the
  round trip and by the store's counter (`hw_store_counter`), the only
  path from the hardware build to the store; store.c itself never takes
  or gives back the window. It now writes HW-134's order: `CON` =
  `0x00F00000`, `CON` = 0, `BAUD` = 1, `CON` = the value read before the
  take, then HW-128's base, key, cache and cipher. After the cipher it
  sets the cache's bits 8 and 9 again, as m-bootloader does (HW-134 item
  6).
- **The store on the unit** (HW-133 items 2 and 3): nothing to change. The
  counter across starts is covered: seams case hw3 counts 1, then 2 at a
  second start from the first run's `flash.bin`, and the store suite's
  persist case finds a save at the next start.
- **Core 1** (HW-133 item 4): the hardware build doesn't depend on it.
  start3 releases it and shows its counter, and nothing waits on it. The
  firmware's engine (`fm_play.c`) already runs without it:
  `sb_core1_start` waits a bounded time for core 1 to say it runs, and
  if it doesn't, core 0 renders every voice it gives a note, the even
  ones, at half the polyphony. A probe for what core 1 needs is SR-18's
  business. The proposal: read `C1_CON` before and after setting bit 3
  (the finder already shows both), and try the release before
  m-bootloader's state is changed (at the entry) as well as after.
- **The panel** (HW-133 items 5 and 6): the scan reads MASTER from
  channel 4, from PB6 set up as an analogue input before `input_start`,
  and the test screen names it as it moves. Main's 10-a-second sweep of
  all twelve channels pauses the scan, then starts channel 4's conversion
  again. The finder labels channel 4's line MASTER and the cells at
  columns 8 and 9 KNOB1. HW-133 doesn't give KNOB1's row, so the scan
  doesn't decode it as an encoder yet. PRESETS (Q-7, Q-8, a note) is left
  to the finder's ADC lines: each shows its channel, its value and up to
  three other levels it took, with no name.

### 2026-11-19 clean-br17-core1: a probe of core 1's release, and PA0 as a row (BR-17, R-HW-1)
The owner's prompt: docs/prompts/clean-br17-core1.md, and finder1's
result: docs/prompts/clean-br17-core1-finder1.md. The facts: HARDWARE-SPEC
HW-135 (SR-18's answer), with HW-9, HW-10, HW-53, HW-133, Q-17 and Q-18.

- **The release, in HW-135's order** (`hw_core1_start`, after the store's
  step):
  1. the loop's address in the start word, read back;
  2. `SYS_DIV` read, then written as that value with bit 3 set, then read
     back;
  3. `C1_CON` bit 3 set and read back, then bit 1 cleared and read back;
  4. a wait of at most 100 ms for core 1's own flag (`hw_core1_flag`, the
     first store of its loop), then `SYS_DIV` written back as read, never
     a constant, so m-bootloader's dividers are kept.
  The step row names each stage, so a hang shows where.
- **The variant** (`SB_HW_CORE1_NO_SYSDIV`) does steps 1 and 3 only:
  `SYS_DIV` is read and never written. The default build, and the
  candidate named A, is the full release. If A starts core 1 and B
  doesn't, step 2 is what the chip needs. If both start it, clearing
  bit 1 is enough. If neither does, something else is missing.
- **A sign that doesn't rest on Q-18.** Before the release, and a second
  after, the `corex2` words 0x80 to 0x8F (Q-17's per-core counters, whose
  meaning the SDK doesn't state) are read. Core 1's screen shows both
  readings, yellow where a word changed. A word that changes only when
  core 1's flag is seen, or only in A, is evidence of core 1 running
  that doesn't depend on core 0 seeing core 1's stores. Q-17 doesn't say
  which words belong to core 1, so all sixteen are shown.
- **Core 1's screen** (`hw_core1_screen`, `SB_HW_HOLD`): drawn a second or
  more after the release, at scale 2 but for the sixteen words, and held
  10 s before the test screen. It shows which build it is, the sign and
  the wait, the counter, `SYS_DIV` at each stage, `C1_CON` at each stage,
  and the start word against the loop's address. The finder's two small
  rows keep the same values afterwards.
- **In fwtest** core 1 starts at whichever comes first of `SYS_DIV` bit 3
  and `C1_CON` bit 3 (HW-10), so both builds see the sign there: hw3's
  held run (A) and the seams case core1 (B). fwtest doesn't model the
  `corex2` words, which read 0 there (unmodelled reads, allowed in the
  cases).
- **Without core 1** (until a unit run settles it): nothing in the
  hardware build depends on it. If the wait times out, the build goes on
  and says so. The firmware's engine runs without core 1:
  `sb_core1_start` waits a bounded time for core 1's word, and without it
  core 0 renders the even voices alone, half the polyphony (`fm_play.c`).
  **Once the probe shows core 1 running,** `core1.c`'s `sb_core1_start`
  (HW-9's release alone today) would take the steps the unit needed, from
  the value read for `SYS_DIV`. The engine would then play all its voices
  on a unit, and core 1's share of the work would need timing on the chip
  (Q-17).
- **PA0, a fifth row** (the owner's reading of finder1: PA0's lines changed
  at small counts all along, and ALGORITHM showed on columns 0 and 1 of
  PA0). HW-117 gives only PA5 to PA8 as rows, so this is the build's
  choice at the owner's request. The scan sets PA0 up as it does PA5 to
  PA8 (input, digital input on, pull-up on, pull-down off) and reads it
  as row 0. The finder reads port A whole, so it now sees PA0 pulled up.
- **AD8 and AD9** are PC9 and PC10 (HW-129): on the FM-1 they are SPI1's
  clock and data out to the panel (HW-56, group B). They aren't floating:
  they follow each screen transfer, which is why they wandered on every
  screen. The finder leaves both channels out. Channel 2 is PA10, an LED
  line, driven low during the sweeps, and channels 0 and 1 are PA7 and
  PA8, rows with pull-ups: that is why they read 0 and `3FF`.

### 2026-11-19 clean-br17-encoders: the encoders, core 1 by B's release, PRESETS (BR-17, R-HW-1)
The owner's message: docs/prompts/clean-br17-encoders.md. On the unit,
start3c's A and B both started core 1: its sign at once, its counter
rising. `C1_CON` read `01000002`, then `01000002` after bit 3 was set,
then `01000000` after bit 1 was cleared. `SYS_DIV` bit 3 isn't needed.
The finder, with PA0 pulled up, showed SELECT, ALGORITHM, KNOB4, KNOB3
and KNOB2 on PA0 at columns 0-1, 2-3, 4-5, 6-7 and 8-9, and KNOB1 at 8-9
on PA5. PRESETS showed nothing.

- **Core 1, B's release by default.** The start word, then `C1_CON` bit 3
  set and bit 1 cleared, then the wait for core 1's flag. `SYS_DIV` is
  read, never written. start3c's A stays behind `SB_HW_CORE1_SYSDIV`,
  with its screen, for the record (seams case core1). Core 1 runs its
  counting loop for good. Nothing depends on it yet. `core1.c`, the
  firmware's own release (HW-9's bit 3 alone), is unchanged until
  HARDWARE-SPEC records the unit's release (SR-19).
- **The encoders.** The unit's cells are exactly where the scan's
  encoder table (HW-38's layout, emulator-only) has SELECT, ALGORITHM,
  KNOB4, KNOB3, KNOB2 and KNOB1. So the hardware build decodes them with
  that table and its quadrature rule (+1 when the B contact, the higher
  column, closes first), now that PA0 is row 0. The test screen names
  each detent at scale 2: its name, +1 or -1, and the column that closed
  first as the encoder left rest. A slow clockwise turn shows which
  column leads, and so each encoder's phase order, and +1 or -1 shows
  whether HW-38's clockwise is the unit's.
- **PRESETS.** The table puts PRESETS at columns 0 and 1 on row 5, PB7.
  On the unit PB7 read with no pull-up (port B's `PU` was `0000`), as PA0
  had, so the finder couldn't see a contact close there. This build sets
  PB7 up as PA5 to PA8 are and reads it as row 5, in the scan and in the
  finder, which tags its cells "P?". That is the build's choice, a lead
  rather than a fact. If PRESETS still doesn't show, SR-19 asks for port
  E's to G's registers and any source for PRESETS' pins. Port D's masked
  bits are the flash's pins (HW-85: PD0 to PD5, and PD6 its power gate),
  which change with the flash's traffic, not with a control. The pins
  this build drives are masked for the same reason.
- **The finder** now opens when HOME is pressed on the test screen, so
  the encoders can be tried there first. HOME's own release falls in the
  finder's hands-off time, so its cell may be marked noisy. The finder
  tags each cell with its encoder (K1 to K4, SEL, ALG), by column and row
  rather than by column alone, so KNOB2 is no longer called KNOB1.
- **SELECT on A** (only column 2 once): the owner's later runs show SELECT
  at columns 0 and 1 every time, so that was the turning. Nothing in A's
  finder differs from B's.
- **Neighbouring columns** pick up a few counts (c4 with ALGORITHM, c8 with
  KNOB3, c10 with KNOB1 and KNOB2). The scan's decoder looks at each
  encoder's own two cells only, so this doesn't reach its detents. HW-117
  says edges that are too short select the neighbouring column, which
  fits.

### 2026-11-19 clean-br17-presets: PRESETS at PB7, columns 11 and 12 (BR-17, R-HW-1)
The owner's message: docs/prompts/clean-br17-presets.md. On the unit, each
of the six encoders gave +1 for a slow clockwise detent and -1 for an
anticlockwise one, the higher column leading clockwise, as the scan's
table orders them. The finder, with PB7 pulled up, showed PRESETS on PB7
at columns 11 and 12 (a brisk turn: 22 counts each).

- **Why the test screen couldn't see it.** The scan walks one 0 through the
  shift registers, one slot a column, and reads the rows at the start of
  the next slot. With 12 slots it read columns 0 to 10. Column 11 was
  selected only during slot 0, which reads nothing. The 0 then moved on to
  column 12 while slot 0's new 0 entered column 0, so column 12 shared
  column 0's read (and 13 to 15 shared 1 to 3). PRESETS' B contact was
  read as if in column 0, and its A contact never.
- **The hardware build now reads 13 columns** in 14 slots. Slot 0 first
  shifts three 1s, so the last cycle's 0 leaves the 16 bits before column
  0's goes in, and no read sees two columns. PRESETS is decoded at
  columns 11 (A) and 12 (B) on row 5, like the others: +1 when column 12
  closes first. A scan cycle is now 14 slots, 1.17 ms, and each LED is
  lit one slot in 14. Debouncing counts cycles, so it takes a sixth longer.
  Build A keeps 11 columns in 12 slots.
- **fwtest** has PRESETS (its encoder 6) at columns 0 and 1, so it can't
  turn the unit's. hw3 checks a detent of encoder 4 (KNOB3, PA0) on the
  event line instead. The unit's run gives PRESETS' phase order.


### 2026-11-19 clean-br17-audio1: a first audio probe for the unit (BR-17, R-HW-1)
The spec side's prompt: docs/prompts/clean-br17-audio1.md. On the unit
presets1 showed PRESETS +1 at c12 clockwise and -1 at c11 anticlockwise,
so all seven encoders decode (relayed by the owner). audio1 is a probe,
`SB_HW_AUDIO1` in hw_audio.c. It asks three things: does ALNK0 run on the
chip, at what rate, and does any sound come out.

- **What it writes.** Only what `audio.c` writes in fwtest: ALNK0's `ADR3`,
  `LEN`, `CON2`'s clear and `CON0`'s run bit, and source 11's `ICFG`
  bits. It writes nothing to the analogue block, PLL2, the clock registers
  or `JL_AUDIO`, since no source gives their values.
- **The pins.** HW-141 names group A's pins (PC0, PC1, PC2, PC6) but not
  the register that selects the group, nor the port set-up the link
  needs. The `JL_IOMAP` bits the spec gives are SPI1's (HW-56) and
  SPI0's (HW-85). So no pin-map
  register is written and the four pins are left as the call left them
  (SR-20). Setting their `DIR` alone would drive them from `OUT` as
  plain pins, not through the link. Sound on path 2 comes only if the
  chip's reset routing happens to be group A and the part outside needs
  nothing more. The probe mainly settles whether ALNK0 runs. PC0 and PC1
  are ADC channels 6 and 7 (HW-129), so the sweep skips them.
- **The rate.** The halves are timed against TIMER0 (`sb_now`, HW-119's
  60 MHz) from the first half to the latest, over at least a second: a
  count per second moves in steps of 64 frames and couldn't tell 44 100
  from 44 118. The time base is TIMER0's slots plus its count. In fwtest
  the acknowledge restarts the count (HW-48), so each slot runs a little
  over its 5000 counts and the measure reads about 80 ppm high (44 121.2
  for 44 117.6, after the 2.5 for fwtest's 24 MHz TIMER0). Whether the
  chip does the same is Q-13. Either way the error is well under the
  400 ppm between 44 100 and 44 118.
- **A storm guard.** That `CON2` bit 3 clears the half's flag is
  FM-1-RE's, at medium to high confidence. If it doesn't clear on the
  chip, source 11 would fire again at once and main, below it, would never
  run: a frozen screen, which the owner couldn't tell from "doesn't run".
  More than 40 interrupts in one beat (a half is 1.45 ms) stops the
  output, disables the source and shows STORM.
- **Without the interrupt.** On the page, main polls `CON0` bit 15 (its
  flips) and `CON2` bit 7 (seen set) itself. So "runs but never
  interrupts" shows as flips with no interrupts counted.
- **The level.** The tone's peak is at most -20 dB of 24-bit full scale
  even with MASTER at the top, in HW-44's word format. No other format is
  tried: if the chip took the low 24 bits as the top of a word, a shifted
  variant could reach full scale in headphones.
- **Images.** `sb_irq_disable` (irq.c) exists only with `SB_HW_AUDIO1`, so
  build A stays byte for byte. In the hardware build `audio.c`'s
  underrun line, written to fwtest's `DBG_MSG` (HW-25), is left out; the
  page shows the count instead.

### 2026-11-19 clean-br17-audio1-result: the page's MASTER (BR-17, R-HW-1)
The owner's message: docs/prompts/clean-br17-audio1-result.md. On the
unit ALNK0 did not run: `CON0` read back with its run bit set, but no
half finished (no interrupt, `CON0` bit 15 never flipped, `CON2` bit 7
never seen). The page showed "vol 0" with MASTER well up. The cause:
`hw_aud.master` was read only in the engine, which runs from source 11's
interrupt, so with no interrupt it stayed 0. The ADC and the scan were
not at fault. The page now reads MASTER itself each time it draws its
top lines. The rest waits on the spec side (the audio clock's set-up,
SR-20).

### 2026-11-19 clean-br17-audio2: audio1 plus CLK_CON2 bit 9, by hand (BR-17, R-HW-1)
The spec side's prompt: docs/prompts/clean-br17-audio2.md, with the
owner's ruling allowing the step exactly as it describes. audio1 showed
ALNK0 doesn't run after m-bootloader's call (HW-144). The only clock
write any source gives is `CLK_CON2` bit 9 (HW-145), so audio2 adds that
step behind a key, and reads more back.

- **The key is REC.** PLAY already toggles the tone and HOME shows the
  page. REC is pressed only on the test screen, so audio1's state is seen
  before the step.
- **The step.** `CLK_CON2` is read, written with bit 9 alone added, and
  read back. The next press writes back the value read before the first
  (not "bit 9 cleared"), so anything the write changed besides bit 9 is
  put back too. A third press takes the step again from a fresh read.
  Before each write the step row (start3b's, row 216) names it with the
  value. If the unit hangs on the write, that row is left showing.
- **What stays as read.** `CLK_CON2`'s low byte (m-bootloader's system
  clock select), bit 8 (0: 192 MHz / 17, the 44.1 kHz family), bits 10
  and 11 (ALNK1's); `PLL_CON0`, `PLL_CON1`, `PLL2_CON0` and `PLL2_CON1`,
  since PLL2 clocks the processor (HW-144); `CLK_CON0` (PC0's clock
  output, HW-145); every routing, mode and port C register (HW-146 gives
  no value for any).
- **The page.** audio1's 22 registers and audio2's 13 don't fit on one
  screen, so the page shows audio1's for the first half of its hold and
  audio2's for the second, each with three columns: at the call, tone
  on, and after the last step. The CLK_CON2 sequence (read, with bit 9,
  put back) is under audio2's half. REC shows the page after each step;
  HOME shows it any time.
- **The rate after a step.** If ALNK0 starts only after the step, its
  first half becomes the measure's base, so the frames a second read
  from that point on, over at least a second.
- **fwtest** stores `CLK_CON2` but nothing depends on it (HW-53), so the
  tone plays on through both presses (case audio2).

### 2026-11-20 clean-br17-audio3: why core 1 stops in the audio builds (BR-17, R-HW-1)
The owner's unit report on audio2 (docs/prompts/clean-br17-audio2-result.md)
and approval (docs/prompts/clean-br17-core1-probe.md). On the unit, core 1
counted from its release (6 742 150 at the step after it, about
36 586 082 at the test screen), then froze at 419 825 784 about 21 s
after power-on and stayed there while the beats ran on. It ran again
only while `CLK_CON2` bit 9 was set. Nothing in this repository's code
links core 1 to the audio: its release comes before any audio code, and
its loop touches only RAM. The two readings: (A) ALNK0, told to run
with no clock, stalls core 1's access to memory, and bit 9 releases it;
(B) core 0 doesn't see core 1's stores because the count shares a cache
line with core 0's writes (in audio2 it shared 32 bytes with `hw3`,
`step_n` and `hw_scan_paused`). The frozen non-zero count favours A.
But the freeze did not come at `audio_start`: core 1 counted about 383
million more after the first test screen, which `audio_start` follows,
so it stopped some seconds later, during the page's 1.5 s settle or its
10 s hold (the core 1 row isn't drawn on the page, so "21 s" is only
when the test screen came back). What core 0 does first in that span,
with core 1 running and ALNK0's clock off, is read the analogue, audio,
ALNK0 and pin-map registers again (`hw_audio_boot`'s same reads ran
before core 1's release), then poll ALNK0's `CON0` and `CON2` in a
tight loop. Either could be what stops core 1, as could ALNK0 itself
some time after it was told to run. audio3 tells these apart without
guessing:

- **The count at fixed points:** just after the release, just before
  and after `audio_start`, 10 ms and 100 ms later, at the end of the
  page's first settle (before its register reads) and just after them,
  after the page loop's first `CON0` and `CON2` reads, the same three
  after each REC or SEQ write, at the page's start and at each redraw.
  Each mark keeps its beat, and the beat the count was last seen to
  change is kept too (polled in the settle, on the page, by the test
  screen's line and in the waits). Core 1's rate (counts a beat, from
  the release to `audio_start`) is shown with them, so a frozen count
  converts back to a time.
- **SEQ stops ALNK0** by clearing `CON0` bit 11 alone (HW-43), the
  write `audio_start` makes the other way; the next press writes back
  the `CON0` read before, exactly, like REC's step. No clock step and no
  other register. If core 1 counts again after the stop, A is shown
  without touching `CLK_CON2`. SEQ was free (PLAY, REC and HOME are
  taken), and is pressed on the test screen only.
- **Core 1's own block:** the flag and the count in a 64-byte struct on
  a 64-byte boundary (`hw_core1_blk`), wider than any likely line, so no
  store of core 0's shares it. If core 1 still stops, B is ruled out.
  Only `SB_HW_AUDIO1` moves them; the other hardware builds keep their
  layout.
- **The corex2 words 0x80 to 0x8F** (Q-17's per-core counters) read
  at the page's start and again when its third view shows, some seconds
  later in the same state; a changing word is shown yellow. That is a
  sign of core 1 that doesn't rest on what core 0 sees of RAM.
- **The page** now has four views, 5 s each on a unit: audio1's
  registers, audio2's, core 1's (the marks, the last-moved beat and
  rate, `CON0`'s stop sequence and the corex2 words) and the steps' (see
  below), the last two redrawn each quarter second. HOME and the first
  page show all four (20 s); a step's key shows the steps view, then core
  1's (10 s). The test screen's line keeps the interrupts and frames a
  second at scale 2, with the steps' states at its right at scale 1
  (R and S above, A and B below: T taken, U undone, S stopped, R put
  back, - never pressed). With the short hold the whole page stays 1 s,
  so the older cases' timings hold.
- **fwtest** stops ALNK0 on bit 11 clear, so no half is taken while it
  is stopped, and the tone plays again after (case audio3); core 1 runs
  there throughout, so its count rises through every mark (two marks in
  one beat may read the same count: core 1 takes turns with core 0).

### 2026-11-20 clean-br17-audio3: steps A and B, in the same build (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio3.md, after #213:
HW-147 to HW-149), relayed by the owner (docs/prompts/clean-br17-audio3-owner.md)
to go into the core 1 probe's build and branch, so the owner flashes one
file. The owner allowed A and B and nothing else.

- **Keys.** ARP takes step A and SAVE step B; a second press of the same
  key undoes it, and a third takes it again. PLAY, REC, HOME and SEQ
  were taken; ARP and SAVE sit together and are free in this build. Each
  is pressed on the test screen only.
- **Step A** (HW-45's start, fwtest's; HW-148: no source says a restart
  is needed): `CON0` read, bit 11 cleared (written, read back), then set
  again (written, read back), at once, with no wait between: no source
  gives one. The undo writes back the `CON0` read before.
- **Step B** (HW-145; the SDK's switched-off definitions only):
  `CLK_CON2` read and written with bit 8 alone added, read back; the
  undo writes back the value read before. Its low byte and bits 9 to 11
  stay as read.
- **Bit 9 first.** A and B are refused unless `CLK_CON2` bit 9 reads
  set, as the prompt gives both "with bit 9 set". REC's undo is refused
  while B is taken: it would put back the `CLK_CON2` read before REC,
  clearing bit 8 behind B's back, so B's undo comes first and each undo
  stays "the value read before its own press". A refusal is said on the
  step row and counted; nothing is written.
- **What each press shows.** As REC's step does, the step row names each
  write before it is made, with the value, so a hang leaves it showing.
  Each step keeps a snapshot before and 100 ms after its last press:
  `CON0` (bit 15 in it), `CLK_CON2`, source 11's interrupts and core 1's
  count, with core 1's marks after the write (key, +10 ms, +100 ms). The
  steps view shows every step's state, presses and snapshots, the same
  four values now, A's readbacks and B's, and the refusals; the page's
  top lines keep the interrupts, bit 15's flips and frames a second.
- **The frames a second after a step** are measured from a fresh base
  (the next half the handler sees) after A, B, REC and SEQ's restart, so
  a link that starts, restarts or changes clock is measured on its own,
  over at least a second. With B taken, 48 077 frames a second would fit
  12.31 MHz and a 256-clock frame (the prompt; no source gives the
  frame); the tone's pitch then rises with it.
- **fwtest** (case audio2, extended): bit 9, A, A's undo, B, B's undo,
  then bit 9's undo; each undo puts back the value read before (A's
  `CON0` with bit 15 aside, the half playing), the tone plays on at
  440 Hz and 44 117.6 frames a second (`CLK_CON2` has no effect there,
  HW-53, and A restarts the link as HW-45 says). Case audio3 checks that
  ARP is refused without bit 9.

### 2026-11-21 clean-br17-report1: a report log in the flash (BR-17, R-HW-1)
The owner's request (docs/prompts/clean-br17-report1.md): photos are too
slow and error-prone, so after a run the owner reads the whole 1 MiB flash
back in download mode and it is decoded. With the owner's unit
observation (docs/prompts/clean-br17-report1-unit.md): the store's record
at 0xFC000 reads back as plain bytes, and the sectors outside the image and
the store hold older data.

- **Where.** A ring of the 32 sectors ending at 0x93FFF, the end of the
  app area (HW-80). The repo's rule for a region of the firmware's own
  (tools/store-region.pl, R-STORE-12, from HW-80 and HW-110) allows the
  app area after the image; an install writes only its image's range
  (HW-110) and a start writes nothing (HW-112), so installing a new build
  never touches it, and it is out of the store, the boot area, the stock
  layout's regions past the app area and the last sector. The request
  says "a flash sector"; one 4 KiB sector holds four of these records and
  a wrap would erase them all, while one audio3-style run makes some 40,
  so the log takes 32 sectors (128 records), as the reading taken. Before
  each write the image's end is checked to be at least a sector below
  the ring. hw_fm1.h's HW_LOG_* is the one definition.
- **Never blank.** Each sector is erased, and read back as erased (the
  store's erase), before its first record unless all of it already reads
  erased; a record whose slot isn't erased moves to the next sector's
  start. So the first run on the unit erases the ring's sectors one at a
  time as it reaches them, and the older data past them stays.
- **A record** is 1024 bytes, little-endian words: the magic "SBRL", the
  layout (1) and the field count, a sequence number, the beat, the
  build's identity (16 bytes: the package's version, "0.10.0-hw3k"), a
  label (16 bytes), the fields, zeros, and the CRC-32 (the store's) of
  everything before. Layout 1's 155 fields (layout 2 since audio4): core 1's count, `C1_CON`, the
  store's counter and result, the window's `CON`, the flash's ID and
  status; then, in the audio build, audio1's 22 registers and audio2's 13
  read at the record, the counts and frames a second, each step's state,
  presses and readbacks, the refusals, core 1's marks, the corex2 words
  and each step's snapshots. A new field goes at the end with a new
  layout number; the decoder names fields by layout.
- **The ring.** At a run's first record every slot is read; the next
  record follows the newest valid one by sequence, or starts at slot 0
  with sequence 1. A slot written to, even if its read-back failed, is
  never reused before the ring comes round, and its number isn't either.
- **When.** At the end of boot (the test screen up), at each page's
  start (after its settle, the first time), after each step key's write
  or refusal (REC, SEQ, ARP, SAVE, labelled with what happened), and on
  EDIT ("save key"), which was free. Each write takes the flash from the
  code window and gives it back as the store's counter does, names itself
  on the step row first ("report: writing #n"), then says "saved #n" or
  what failed (no flash, image too long, erase, program, verify). Without
  the round trip there is no flash access, and the record is refused.
  The take and give-back has run only at boot on a unit before; now it
  runs with core 1 running and the tone on.
- **The decoder** (tools/report_decode.py, Python 3, standard library):
  searches every 4-byte boundary of the image for the magic, so a record
  outside the ring still turns up, checks each CRC, and prints the records
  by sequence with their fields named (states in words, counts in
  decimal, registers in hex; fields 0 in every record left out unless
  --all; --json for tools). With no valid record it says so, and whether
  the ring is erased, holds other bytes, or holds the magic with failing
  CRCs. A failing CRC outside the ring isn't counted: the magic is also a
  constant in the firmware's own image.
- **fwtest** (case report1): from a chip whose ring holds older data, the
  nine records of boot, the pages, REC, ARP, ARP's undo and EDIT, numbered
  1 to 9 in the first slots, the third sector's rest erased and the
  sectors past it untouched; the last record's fields match the probe's
  RAM; a second run numbers on (10, 11); a full ring of valid records
  loses its oldest sector to the next record and keeps the rest.
- **The candidate** is audio3's build with the log (`SB_HW_REPORT`), so
  its run repeats audio3's and compares with the photos. Every hardware
  candidate from now on is built with it.

### 2026-11-21 clean-br17-audio4: steps H and I, in report1's build (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio4.md; HW-150 to
HW-152, SR-21), with the owner's rulings allowing H and I and nothing
else new, into report1's build and branch so the owner flashes one file.

- **Keys.** ENV takes step H and FX measures again while it is taken; LFO
  takes step I and SEL adds `CLK_CON2` bit 10 while it is taken; a second
  ENV or LFO undoes. All four were free; the page's H and I view names
  them.
- **Step H** (HW-151): `CLK_CON1` bits 4-6 set by read-modify-write of
  those bits alone, first to 3 (the high-speed bus, a check: 180 MHz
  over the 24 MHz crystal is 7.5 times the gate, HW-119 and HW-54), then
  to 5 (the audio clock), in whatever state REC, B and I left `CLK_CON2`.
  `JL_GPCNT->CON`: counted clock 4 (the clock system's input), gate clock
  1 (the crystal), gate 32 x 2^10 = 32 768 cycles (1.37 ms), enabled with
  the pending flag cleared. Since when `NUM` holds a gate's count isn't
  given, each measurement takes two readings, each after the pending flag
  (bit 7) or a 20 ms timeout, the flag cleared with bit 6 after each, and
  logs both and the timeouts. The undo writes back `CLK_CON1` and
  `JL_GPCNT->CON` as read before the first press. The prompt's expected
  audio clocks, about 11.29 MHz (bit 8 clear) and 12.31 MHz (bit 8 set),
  would read about 15 410 and 16 810 a gate.
- **Step I** (HW-140, HW-145): ALNK1 at 0x00015100, set up as ALNK0 is
  in fwtest (`ADR3` its own silent buffer, `LEN`, `CON2` bit 3, `CON0`
  bit 11 added to the value read), and `CLK_CON2` bit 11 alone; source
  12 is never enabled. ALNK1 is polled for 1 s: `CON0` bit 15's changes
  and `CON2` bit 7 seen (cleared with bit 3), giving halves a second. The
  undo writes back `CON0` and `CLK_CON2` as read before the first press.
- **Undo order.** REC, B and I all write `CLK_CON2` back as read before
  their own press, so undoing one taken earlier would clear a later
  one's bit behind its back. Of the three, only the one taken last can be
  undone; the others are refused, the step row naming the step to undo
  first (this replaces audio3's "REC's undo refused while B is taken").
- **The page** gets a fifth view, H and I: H's `CLK_CON1` and `CON`
  sequences, its counts (the bus count per 1000 gate cycles, 7500
  expected; the audio clock in kHz) and `CLK_CON2` at each; I's ALNK1
  registers before, after and put back, `CLK_CON2`'s sequence, the poll
  and ALNK1 now. H's and I's keys show it, then core 1's view; HOME shows
  all five; the first page keeps its four. The steps view lists all six
  steps; the test screen's state box adds H and I.
- **The log**: layout 2, 219 fields: layout 1 with six steps' snapshots,
  then H's and I's readbacks and counts, `CLK_CON1`, `JL_GPCNT` and
  ALNK1's registers as read at the record, and the `CLK_CON2` steps
  taken. A record after every H, FX, I and SEL press and each refusal,
  and at each page; the decoder prints H's counts as a multiple of the
  gate and in MHz.
- **A bug found on the way:** the step row's `draw_step` built "step n: "
  and the text in a 48-byte stack buffer with no bound, so a 40-character
  text after a two-digit step number overran it (in fwtest, a jump into
  RAM after I's first step text). It now stops at the row's 40
  characters, and the probe's text buffers are larger. The earlier
  builds' texts stayed just inside it.
- **fwtest** models neither `JL_GPCNT` nor ALNK1: their registers read 0,
  so H's gates time out and ALNK1 doesn't play; case audio4 checks every
  write, read-back, undo and refusal, and the log's records, and prints
  that.

### 2026-11-21 clean-br17-leds1: the keys' LEDs show what is held and taken (BR-17, R-HW-1)
The owner's request (docs/prompts/clean-br17-leds1.md), after report1 ran
on the unit (23 records read back from a full flash image, all CRCs
valid): light each key's LED while it is held, and keep the step keys'
lit while their step is taken. Nothing else changes.

- **Held.** Every key's LED is set at its press and release before any
  key's own work, so the keys main handles itself (HOME, EDIT and the
  step keys, which never lit before) light while held, as the others
  always did.
- **Taken.** With the audio probe, a step key's LED stays lit after its
  release while its step is taken: REC (bit 9), ARP (A), SAVE (B), ENV
  (H), LFO (I); SEQ while ALNK0 is stopped; FX while H is taken (it
  measures H again); SEL while I is taken with bit 10 set. EDIT saves a
  report and has no state, so it lights only while held. After each step
  key's work every step key's LED is set again from its state, since a
  step can change another key's (I's undo clears SEL's bit 10).
- **While a page shows.** A step key's page holds main for 10 s, and its
  release is read after it, so the key's LED stays lit through its page
  even if released sooner.
- The build's identity is 0.10.0-hw3l. Case audio4 samples the LEDs:
  each step key's lit (one slot in 14, as PLAY's) while its step is
  taken, and every other dark, at moments with no key held.

### 2026-11-21 clean-br17-audio5: steps K and J, in leds1's build (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio5.md; HW-153,
HW-154), with the owner's rulings allowing K and J and the owner's change
to J (docs/prompts/clean-br17-audio5-owner.md): one press runs J's whole
sweep. Built on leds1 (merged with #220), one file.

- **Keys.** GLO takes step K, OCT+ runs step J; both were free. A second
  GLO undoes K. An OCT+ while J's sweep runs aborts it; an OCT+ with a bit
  left set puts it back; any other OCT+ sweeps again, in whatever
  `CLK_CON2` state the other keys left. Each lights its LED while taken
  (K; J with a bit left set).
- **Step K** (HW-151, HW-153, HW-154), all from one press: H's method
  and gate (the crystal, 32 768 cycles, two readings), each reading after
  the pending flag or 5 ms (report1 never saw the flag set, and the two
  readings agreed, HW-153). In turn: the clock system's inputs 3, 1, 5, 6
  and 7 (`CLK_CON1` bits 4-6, those bits alone); the counter's own 480 MHz
  input (its counted-clock choice 6); then input 5 with the DAC's clock
  choice, `CLK_CON1` bits 2-3 alone, at 1, 2 and 3 and then as read. Each
  measurement keeps `CLK_CON1` and the counter's `CON` as read back, both
  counts, the timeouts and `CLK_CON2`. K is refused while H is taken, and
  H while K is (both write `CLK_CON1` back as read before their own
  press). The undo writes back `CLK_CON1` and `CON` as read before K.
- **Step J**, the owner's form: one press sweeps ALNK0's `CON1` bits 0-15
  and then `CON3` bits 0-7. Each try reads the register, writes it with
  the one bit added, reads it back, watches the link for 100 ms (`CON0`
  bit 15's changes, `CON2` bit 7 seen, source 11's interrupts), and, if
  nothing moved, writes back the value read and reads it back; a record
  for each try. If a try moves the link the sweep stops there with that
  bit left set until the next OCT+; a press during the sweep aborts it
  after the try in progress has been put back (keys other than OCT+ only
  light their LEDs while it runs). J writes nothing but `CON1` and `CON3`.
  Each try's read-back is kept, and the tries whose bit didn't read back
  set. After a try that moves the link, and after J's undo, the frames a
  second are measured from a fresh base.
- **The page** gets a sixth view, K and J: each of K's measurements
  (`CLK_CON1`, both counts, the second in kHz), J's state, its last try,
  the tries whose bit didn't hold, and `CLK_CON2` when the sweep began.
  K's and J's keys show it, then core 1's; HOME shows all six. The steps
  view keeps the first six steps; the state box adds K and J (J: D done,
  M moved, X aborted, U undone).
- **The log**: layout 3, 344 fields: layout 2 with eight steps'
  snapshots, then K's ten measurements and J's last try, read-backs and
  state, and ALNK0's `CON1` and `CON3` now. That doesn't fit a 1024-byte
  record, so layout 3's are 2048 bytes, in a ring of the 64 sectors ending
  at the app area's end (128 records, as before). Layouts 1 and 2 stay
  1024 bytes; the decoder takes a record's size from its layout, so older
  records still read, and the firmware treats them as not blank and
  erases their sectors when the ring reaches them. A J sweep writes some
  26 records.
- The build's identity is 0.10.0-hw3n: fwsc refuses "hw3m", whose "m"
  would make a marker byte the format's end.

### 2026-11-21 after audio5: three log records with a failing CRC, and the next key (BR-17, R-HW-1)
The owner's report (docs/prompts/clean-br17-audio5-result.md): audio5's
run left 65 valid records and three with the magic but a failing CRC, at
sequence gaps #34, #36 and #45 (about 0x64800, 0x65800 and 0x6A000: the
ring's slots 33, 35 and 44). And a request: light the key to press next.
Both go into the next build (with step D, when its prompt comes); audio5
isn't rebuilt for them.

- **What the run says.** This code skips a sequence number only when a
  write's page program timed out or its read-back didn't match (errors 4
  and 5); every other failure keeps the number. The owner's look at the
  raw bytes (the same prompt file, its second part): each of the three is
  cut off, its first pages right and its last 256-byte pages still erased
  (#34 page 7, #36 pages 3-7, #45 pages 6-7), all in fast bursts of
  records. That is `program` returning at a page whose busy wait said
  "timed out": the remaining pages are never programmed. Records don't
  overlap: main writes them one after another.
- **The cause: time going back.** The busy wait (store.c, `wait_ready`)
  measures with `sb_now()`, `d = sb_now() - t`, unsigned, against a 3 s
  limit. The hardware build's `sb_now()` read the slots counted and
  TIMER0's count in a loop that repeats if a slot's interrupt comes
  between them, but read the count's wrap flag (`CON` bit 15) after the
  loop. A slot's interrupt there counts the slot and clears the flag, so a
  count read after the wrap was paired with the slots before it: one slot
  (83 us) back in time. A wait that started just after reads a "time" of
  about 4 000 million units, past the limit at once, and stops while the
  chip is still programming a page. Many records in a burst give the race
  more chances. Nothing else ruled in: no page program crosses a page
  (records start on 2048-byte boundaries, `program` splits at every
  256-byte page), the limit is 3 s against a page's 3 ms (HW-77), and no
  interrupt handler or core 1 touches SPI0 or the flash's pins.
- **The fix.** `sb_now()` reads the wrap flag inside its loop, with the
  slots and the count, so it never goes back. The log programs a record a
  page at a time, each finished before the next: a page whose wait says
  busy is waited on again (up to eight times, counted), and only a chip
  that stays busy stops the write. Each write also first waits until the
  chip isn't busy (counting the times it was), reads a mismatch back a
  second time (a right second read is a read glitch, counted, and the
  record stands), and on a real failure writes the record again in the
  next slot under the same number, so no record is lost or number
  skipped. Each failure is kept, the last four, in every later record
  (layout 4): its number and slot, the error, which 256-byte pages
  differ, the first differing byte, how many differing bytes read 0xFF,
  and the word written and the word read there; with the counts of busy
  takes, glitches, retries and repeated page waits. The decoder prints
  each record whose CRC fails with its offset, slot, header, page map (F
  all 0xFF, 0 all zero, d other bytes) and its blank pages, and the
  firmware's own counts. A test build (`SB_TEST_LOG_VERIFY_FAIL`)
  programs the first record with one bit wrong, and case report1 checks
  it is found, logged, and written again.
- **Every other difference of two readings** (the owner's follow-up, the
  same prompt file's third part), in the hardware build, where the race
  was; build A's `sb_now()` is TIMER4's free-running count, one register,
  and never had it. The race needs the slot interrupt to come between
  `sb_now()`'s loop and its flag read, so it could hit main and the audio
  interrupt (priority 0, which the slot's, priority 2, preempts), never
  code inside the slot interrupt itself. A step back made one difference
  about 4 000 million units:
  - *Could act wrongly:* the flash's busy wait (store.c, `wait_ready`,
    3 s limit), the log's cut-off records, and the same for the store's
    start-up counter (its write or erase could have failed at boot; it
    never did on the unit); and the 12.5 us settle in the matrix sweep and
    the knob finder (hw_start3.c, `while (sb_now() - t < 300)`), cut to
    nothing, so one sweep could read a column before it settled: a
    momentary wrong grid cell on the test screen, or a spurious cell
    change in the finder (the keys and knobs themselves come from the
    scan in the slot interrupt, which never had it).
  - *A wrong number, nothing acting on it:* audio.c's fill time
    (`fill_last`, `fill_max`) and the audio probe's rate base (hw_audio.c:
    a `t1` before `t0` just after a fresh base gives one wrong frames a
    second until the next half, and a needless re-base); ALNK0 never ran
    on the unit, so neither showed. The store's `init_ticks` and
    `put_max`, lcd.c's `frame_ticks`, screen.c's `beat_ticks`, main's
    `render_ticks` and input.c's `led_lag_max`: durations kept for the
    beacon and the records only.
  - *Never affected:* everything timed in beats (the slot interrupt counts
    them): the panel's 500-beat wait, the pages, the settles, K's and J's
    waits, H's gates, core 1's wait; `sb_tick` and the scan's event times,
    taken inside the slot interrupt; the engine, MIDI and views, which the
    hardware build doesn't run.
- **The race kept out by a test.** In fwtest an interrupt is taken at
  the first instruction after the wrap, so the race doesn't happen there
  by itself. A test build (`SB_TEST_NOW_RACE`) makes the slot interrupt's
  time-keeping (its acknowledge and its count) happen at each of four
  points between `sb_now()`'s reads, just after TIMER0 has wrapped with
  interrupts off, 50 times at each; case nowrace checks that no reading
  is earlier than the one before it. Built with the old order (the flag
  read after the loop) it fails, every one of the 50 runs at the fourth
  point going back.
- **The next key.** One table in hw_audio.c (`guide`) holds the build's
  suggested order, each entry a key and what it does; now audio5's: GLO
  (K), GLO (K's undo), REC (bit 9), OCT+ (J), REC (bit 9's undo), OCT+
  (J), EDIT (a save). The next key's LED blinks, half a second on and
  half off, refreshed every tenth of a second and through the pages and
  J's sweep; the step row says "next: KEY (what)" after each key's page
  (and "next: none" at the end). A press of that key moves on; any other
  key leaves it. A key lit for its step blinks too while it is next.
  Step D's build replaces the table with its own order; its case
  (audio6) checks the guide.
- **fwtest**: the counter isn't modelled (K's gates time out, its counts
  0); ALNK0's `CON1` and `CON3` are stored (every try read back as
  written); and with ALNK0 running, `CON1` bit 0 sets off a burst of
  source 11 there, the guard stops the output (a storm), and the try
  counts as moving the link. Case audio5: K's ten `CLK_CON1` values and its
  undo; with ALNK0 stopped (SEQ) a full sweep of 24 tries, each put back,
  then a second sweep aborted; with ALNK0 running again the third stops at
  `CON1` bit 0 and is put back; the tone at 440 Hz and 44 117.6 frames a
  second after the sweeps, before that try.

### 2026-11-21 clean-br17-audio6: step D, JL_IOMAP->CON5 a bit at a time (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio6.md; HW-155,
HW-156), allowed by the owner, built on the build after audio5 (the
sb_now() fix, the log's retries, the next key) as one file
(docs/prompts/clean-br17-audio6-owner.md).

- **The key.** OCT-, the last free key. A press runs the sweep: `CON5` as
  read with bit 0 alone set, then bit 1, up to bit 31, each with every
  other bit as read. A press while it runs stops it after the try in
  progress (which the firmware undoes as always); a press with a bit kept
  puts `CON5` back as read. OCT-'s LED is lit while a bit is kept. If J has
  a bit left set, its register goes back as read before the sweep, logged
  ("J back for D"). Before its first try the sweep waits (at most 5 s,
  "release OCT- to start" on the step row) until OCT- is released: held,
  its cell would differ between a try's baseline and its check (fwtest
  showed it). A press of OCT- to stop a sweep that lands during a check
  shows as that try's failed check: undone and stopped all the same.
- **Each try**, in the prompt's order: (1) a record "D bN before" with
  `CON5`, `JL_IOMAP` `CON0` to `CON8`, port A's eight registers, `CLK_CON2`,
  ALNK0's `CON0` to `CON3`, source 11's and core 1's counts, written and
  verified before anything else; (2) the scan paused, the matrix's
  baseline taken, `CON5` written with the one bit added and read back;
  (3) the watch, 100 ms: `CON0` bit 15's changes, `CON2` bit 7 seen,
  source 11's interrupts, port A's `IN` at its start and end; (4) the
  matrix check with the bit set; (5) the undo, the firmware's own,
  unless the link moved with the check right: then the bit stays and the
  sweep stops; (6) after the undo, port A and `JL_IOMAP` read again and
  the check repeated, `CON5` read back against the value read before; (7)
  the scan resumed and the try's record ("D bN", or with "moved", "check
  BAD", "after BAD", or "kept"). No undo waits on a key.
- **The matrix check.** 0xFFFF latched (no column): rows PA0, PA5 to PA8
  and PB7 (HW-117, HW-138, HW-139) must all read high; then each of the 16
  single-zero column words: the closed cells must be those of the
  baseline taken just before the write, with the scan paused (so a knob
  resting with a contact closed doesn't count as a key; a key held during
  the sweep makes its check fail and stops it); then port A's `DIR`, `DIE`,
  `PU` and `PD` against step 1's. Its port A writes are the test screen's
  matrix sweep's own (the LED lines low, the shift register's data, clock
  and latch). The check fails on any of these, and the try's record says
  which (rows, cells, port A, `CON5` not back, another `JL_IOMAP` word
  changed).
- **Where it stops.** At the first try whose check fails (undone), whose
  link moves (kept if the check passed, else undone), or whose check after
  the undo fails; else it runs to bit 31 ("D done"). It takes no further
  try after a stop.
- **What D writes.** `JL_IOMAP->CON5` alone. Port A only as the matrix
  sweep always has; no other `JL_IOMAP` word, no port C, no PLL, no
  `CLK_CON2` low byte; ALNK0's `CON1`/`CON3` only by putting back what J
  left.
- **The log.** Two records a try, about 67 a sweep; two sweeps would
  overrun the 128-record ring of audio5, so the ring is now 96 sectors
  (192 records) ending at the app area's end, its base still far above
  the image (checked before each write). Layout 5 adds D's 81 fields (the
  last try's every reading) before layout 4's log fields; the decoder
  prints a D line for each record.
- **The page and the guide.** A seventh view, D: the state and stop, the
  try's bit and `CON5` values, the watch's counts, the idle rows and
  cells before, with the bit set and after, the checks, port A's eight
  registers before, with the bit set and after (`DIR`, `DIE`, `PU`, `PD`
  red if they changed), `IN` over the watch, core 1's count. HOME shows all
  seven; OCT- shows D's and core 1's. The guide's table is now D's order:
  REC (bit 9), OCT- (D), REC (bit 9's undo), OCT- (D), EDIT; while a bit
  is kept, OCT- (D's undo) comes first. The identity is 0.10.0-hw3p.
- **fwtest** stores `CON5` (case audio6 prints whether every try read
  back as written) and does nothing else with it that the sweep sees: with
  ALNK0 stopped both sweeps run through all 32 bits, every try put back
  and both checks passing; with ALNK0 running its link moves at bit 0, so
  the sweep keeps that bit, and a press puts it back. A test build
  (`SB_TEST_D_CHECK_FAIL`) makes the check at bit 2 fail: the sweep
  undoes that try itself and stops.

### 2026-11-21 clean-br17-audio7: set-ups L1 and L2, D held (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio7.md; HW-157, HW-158),
allowed by the owner, into the same build as audio6 and the fixes after
audio5, one file (docs/prompts/clean-br17-audio7-owner.md).

- **D held.** D's code stays (OCT- still runs it), but it is out of the
  guide's order; its view's title says it is held, and the state box
  shows it as `h` until it is run. A D result in this run counts for
  nothing.
- **Keys.** KEY1 (the keyboard's lowest key) takes L1, KEY2 L2: every
  panel button was taken. A set-up kept running is put back by a press
  of either key; its own key does only that, the other then runs its
  own set-up. Each key's LED is lit while its set-up is kept.
- **A set-up**, HW-157's driver's order on ALNK0's own registers alone:
  `CON0` as read with bit 11 clear, then `CON3` (L1 `0xC2`: the
  oscillator, divided by 1, 512 master clocks a frame; L2 `0x83`: the
  PLL's audio clock, by 1, 256), then `CON1` = `0x1000` (data 3 an I2S
  output, 16-bit), then `CON0` as read with bit 11 set and bits 7 and 8
  clear; each read back. `ADR3`, `LEN` and the buffer stay as audio1 set
  them; `CON2` is written only as audio1's handler does; `CLK_CON2` bit 9
  only by REC. As D does, a set-up first waits (at most 5 s, "release
  KEYn to start") for its key to be released, so the matrix check sees no
  key held. With D's safety machinery: (1) a record before, with
  `CON0` to `CON3`, `LEN` and `ADR3` as they read back (both are
  write-only in the SDK's header; the expectations use `LEN` as read if
  not 0, else the 128 audio_start wrote), `CLK_CON1`, `CLK_CON2`, port A,
  source 11's and core 1's counts, and the expected frames a second
  (46 875 for L1, 44 117.6 for L2) with the halves a second that gives
  by each reading of `LEN` (HW-157's: a half `LEN` frames; fwtest's,
  HW-44: `LEN` / 2); (2) the scan paused, the matrix's baseline, the
  writes; (3) a 1 s watch: bit 15's changes, `CON2` bit 7, source 11's
  interrupts, and the halves timed against `sb_now()` from the first
  change to the last, as halves a second and frames a second by each
  `LEN` reading; (4) D's matrix check with the set-up in place; (5) kept
  if the link moved with the check right, else `CON0`, `CON1` and `CON3`
  put back as read, in that order, each read back; (6) the check again
  and the three against step 1's; (7) the record ("L1 kept", "put back",
  "check BAD", ...). Any failure stops: no further set-up is taken.
- **The guide**: L1, REC (bit 9), L2, REC (bit 9's undo), L2, EDIT (a
  save); while a set-up is kept its own key ("L1 undo", "L2 undo") comes
  first, which is the prompt's "undo if it was kept".
- **The log**: L's 78 fields don't fit a 2048-byte record beside the
  rest, so layout 6's records are 4096 bytes, a sector each, 96 in the
  ring; the ring's first read now finds records of every size (looking
  at every 1024 bytes), so the numbers go on from the last build's. With
  96 records the ring holds one of D's sweeps (about 67 records) and
  part of another: if D is run twice, the first sweep's oldest records
  give way (D is held in this build). This run's L1 and L2, with their
  undos, pages and the rest, take about 30. The
  decoder prints an L line for each record, with both `LEN` readings
  beside the expected rates.
- **The page**: an eighth view, L: the set-up's state, `CON0` to `CON3`
  and `LEN` before, each write and read-back, the counts, the halves and
  frames a second by each reading beside the expected, the checks, what
  was put back, port A before, set up and after. KEY1 and KEY2 show it,
  then core 1's; HOME shows all eight.
- **fwtest** stores `CON1` and `CON3` and plays the link whatever they
  hold (HW-44, HW-45), so in case audio7 each set-up is kept, its halves
  read fwtest's 44 117.6 by fwtest's `LEN` reading, and its key puts the
  three back as read. A test build (`SB_TEST_L_CHECK_FAIL`) fails L1's
  check: the firmware puts it back and refuses the next set-up. The
  identity is 0.10.0-hw3q.


### 2026-11-21 clean-br17-audio8: L2 at start-up, port C's routing, the sense scan (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio8.md; HW-159, HW-160
and the entries it names), with the owner's rulings: R0, R2, R3 step 1 and
R5 allowed; step 2 only if step 1 leaves port C still; R4 drives no pin.
Everything new is behind `SB_HW_AUDIO8` (refused without `SB_HW_AUDIO1`;
`SB_HW_PCM16` is refused without `SB_HW_AUDIO8`), so audio1 to audio7's builds and cases are as they were;
the unit's candidate adds it and `SB_HW_PCM16`.

- **L2 at start-up (R0).** Once the test screen is up and audio1's output
  has started, `hw_audio_boot_l2` runs audio7's KEY2 set-up with no key
  to wait for: the same writes, order, records ("L2 before", "L2 kept")
  and matrix check. If `CLK_CON2` bit 9 reads set, L2 isn't tried (the
  link wouldn't run, HW-160). audio8's keys run only while an L set-up is
  kept and no check after an undo has failed. With L2 kept, the guide no
  longer puts its undo first; KEY1 and KEY2 still work as in audio7, but
  are refused while R2 is in place (a route needs R2), and D and J are
  refused while an L set-up runs (their watches would see the link move
  at once). SEQ's stop and A are refused while R2 is in place.
- **The tone's format, by target.** `SB_HW_PCM16`, in the unit's
  candidate only, fills a half as the unit plays it (HW-160): `LEN` (128)
  frames, a 32-bit word each, the 16-bit sample (the tone's value >> 8,
  so the same -20 dB at MASTER's top) in both halves of the word, since
  which half is left isn't given. The block's frames are twice audio.c's
  `AUDIO_FRAMES`; the probe's frames a second count the same. Without it
  (every fwtest case but one) the tone keeps fwtest's layout (HW-44).
  audio.c is unchanged.
- **REC's watch.** After REC's write the link is watched for 200 ms (bit
  15's changes, source 11's interrupts) and the step row says whether it
  runs; with bit 9 set it should stop (HW-160). Step 1 and the sweep are
  refused while bit 9 is taken.
- **Pin sampling.** Port C's and port A's `IN` read in a tight loop for
  10 ms; each pin's changes counted for PC0, PC1, PC2, PC6 and PA4 to
  PA10, with the loop's passes and its `sb_now()` span logged, so a rate
  can be read and aliasing judged. Interrupts stay on (a pass they delay
  may miss changes, so a fast pin is undercounted, never invented). Every
  sample is taken with the scan held: paused, the LED lines low and
  `0xFFFF` latched (`hw_scan_hold`), so nothing of the scan's moves PA4,
  PA9 or PA10. "Port C moved" means any of its four pins counted a
  change; "port A moved", any of PA4 to PA10.
- **R2 (KEY3).** First a control sample, nothing routed and R2 not yet
  in place. Then port C read, and PC0, PC1, PC2 and PC6 set as the
  AW30N's driver sets a master's pins: `OUT` high, then `DIR` 0, then
  `DIE` on, each a read-modify-write of those four bits alone, the pulls
  and drive as read; checked against the read (pulls and drive, other
  pins' bits; PC7 and PC8 in `OUT` excepted, which the panel's driver
  moves). Again: the routes first, then `DIE`, `DIR` and `OUT`'s four
  bits back as read, each by read-modify-write of those bits alone
  (writing whole words back could undo the panel's chip select and
  data/command lines), and every port C register checked against the
  read.
- **Step 1 (KEY4).** (a) a sample with R2 in place and `CON0` bits 7 and
  8 clear; (b) a routed try. **A routed try**, D's machinery: a record
  before; "TOUCH NO KEY" on the step row; the scan held, the matrix's
  baseline, and the rows with no column checked idle (else nothing is
  written); the writes, each read back; a sample at once; for (b) the
  rest of the 100 ms watch and a second sample. If port A moved, the
  write is undone at once, before the matrix check, since the check
  drives columns low against rows the link may be driving (this
  build's reading of "its own undo if port A moved"); else D's check,
  kept if port C moved with the check passing, else undone; the check
  after an undo (cells, idle rows, port A's registers, `CON0` and `CON5`
  back, the other `JL_IOMAP` words unchanged); a record. A failed check
  after an undo turns audio8's keys off.
- **The sweep (KEY5),** refused unless step 1 ran and port C didn't move
  (a step 1 stopped by port A's movement alone counts as still). One
  press: CON5's bits 0 to 31, each a routed try that sets the bit and
  then `CON0` bits 7 and 8, and undoes them in the other order, so
  between tries nothing is routed (this build's reading of "bits 7 and 8
  set for each try"). It stops at the first try that keeps, moves port A
  (that bit undone and logged), finds a key held, or fails a check.
- **The sense scan (KEY6),** read-only: each port's `DIR`, `DIE` and `IN`
  (A to H) read once, the scan held once (its single latch, then no
  write for 20 s), then every port's `IN` each millisecond. Each bit's
  changes are counted, and its first 12 kept with their times (ms,
  port, bit, level) in a list of 120, so a busy pin (the flash's on port
  D, the panel's on port C, which the countdown's drawing moves once a
  second) can't fill it. The step row counts down and the page shows the
  bits that changed beside each port's `DIE`.
- **Keys and guide.** KEY3 R2, KEY4 step 1, KEY5 the sweep, KEY6 the sense
  scan; a second KEY3, KEY4 or KEY5 undoes its own (KEY3 also any route).
  Their LEDs are lit while R2, step 1's route or a sweep's bit are kept.
  The guide: KEY3, KEY4, KEY5 (skipped unless the sweep may run), KEY6,
  EDIT. D, J, K and L1 are out of it.
- **The log.** Layout 7 adds audio8's fields (933 of a record's 1011);
  audio8's key pages write no "page" record, so a run (boot, L2, R2, step
  1, a full sweep of 66 records, the sense scan, a save) is about 82 of
  the ring's 96. A ninth page view shows audio8; HOME shows it first.
- **fwtest** (case audio8): port C's `OUT`, `DIR` and `DIE` are stored,
  but its `IN` reads 0 whatever they hold, so no pin's `IN` follows the
  link and every sample counts 0: step 1 leaves port C still and the
  sweep runs all 32 bits. `JL_IOMAP->CON5` is stored and read back as
  written, with no other effect. Bit 9 doesn't stop fwtest's link. The
  test seams: `SB_TEST_A8_CHECK_FAIL` (the sweep's bit 1 fails its
  check), `SB_TEST_A8_PA_MOVE` (its bit 3 moves port A) and
  `SB_TEST_A8_PC_MOVE` (step 1 moves port C: kept, the sweep refused,
  both put back by KEY3). The identity is 0.10.0-hw3r.

### 2026-11-21 clean-br17-audio9: the route at start-up, the synth on it, S2 (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio9.md; HW-161, HW-162), with the
owner's rulings: S0 and S2 allowed; S1 allowed, off at start-up and
switched by a key; each half's fill sized per target. Behind
`SB_HW_AUDIO9` (refused without `SB_HW_AUDIO8`); the unit's candidate adds
it to audio8's defines.

- **Start-up (S0):** `DAA_CON7` read (never written); L2 as audio8 sets it
  up; only if it is kept, R2 as audio8 sets it (its control sample
  included); then **the route**, a routed try of a new kind: a record
  before, the scan held with `0xFFFF` latched, the idle rows checked,
  `CON0` bits 7 and 8 set and read back, port A sampled over the whole
  100 ms watch, then (if port A stayed still) D's matrix check. It is
  kept when port A stayed still and the check passed: there is no port C
  test, since port C's `IN` can't show the link's pins. Otherwise the try
  undoes bits 7 and 8 itself and checks again, and then R2 is put back
  as read. `CON5` is never written. If R2's own check flags anything, R2
  is put back and no route is tried.
- **SEQ** takes the route down (bits 7 and 8 clear, then port C's four
  pins back as read, checked) and up again. Up redoes R2 first, since
  the way down put port C back: "steps 3 and 4" read as R2, then the
  route.
- **FX** switches the halves between the tone and the synth; the synth is
  off at start-up. **LFO** steps S2: both halves, the upper alone (the
  lower 0), the lower alone (the upper 0). It applies to whatever plays,
  the tone or the synth. **REC** (bit 9), **PLAY** (the probe's tone on
  and off), **EDIT** (a save) and **HOME** (audio8's and audio9's view,
  5 s) stay. The other old steps' buttons and keys (ARP, SAVE, ENV, SEL,
  GLO, OCT+, OCT-, KEY1 to KEY6) start no step: they are the engine's.
  The CON5 sweep, step 1's two-part sampling, the sense scan and the L
  keys are no longer on any key in this build; their code stays for the
  audio8 build.
- **The synth (S1):** `fm_init` runs once at start-up, before audio1's
  output starts. On a unit it releases no core (core 1 runs the hardware
  build's own loop, and fm_play's shared words aren't yet in cache lines
  of their own), so core 0 renders the even voices alone: 8 voices, half
  the polyphony. MIDI is off on a unit: `midi_start` and `midi_poll` do
  nothing and `midi_out_poll` drops what waits, so UART1 is never
  touched. PLAY doesn't reach the engine's M4 test tone, whose level is
  past MASTER. The engine assumes 24 MHz / 544 = 44 117.6 frames a second
  (audio.h), which is L2's rate (HW-160), so pitch is exact. Its
  arpeggiator times itself by audio interrupts, which on the unit come a
  half (two engine blocks) apart: ARP runs at half speed this round.
- **The fill, per target.** fm_block renders 64-frame blocks. On the unit
  (`SB_HW_PCM16`) a half is `LEN` (128) frames of one word: two engine
  blocks, each frame's left sample >> 10 (the engine's 24-bit full scale
  to 16 bits, then -12 dB until levels are set), packed as S2 says. In
  fwtest a half is `LEN` words of its own layout (HW-44): one engine
  block of 64 frames, as build A plays. fwtest's `LEN` change is a later
  spec PR's.
- **Late halves:** audio.c's own test (the half filled was already
  playing, or the next half finished before the fill did) counted from
  the moment FX turns the synth on, with the longest fill (`sb_now()`'s
  24 MHz units, the timer audio1 uses), on the screen and in the log.
  After 50 late halves the interrupt goes back to the tone, so main, the
  screen and the keys keep running, and main logs it. While the tone
  plays, the engine's queue of the panel's events is emptied each block,
  so the synth starts with none stale.
- **PB5:** read from the scan's slot, read only (`JL_PORTB->IN` bit 5),
  each change counted with its beat (the last 16 kept); main writes a
  record when the level has stood 50 ms, so a bouncing contact takes one
  slot. The test screen shows the raw bit and the count; which level
  means plugged is the owner's to say. The existing port B set-up (PB1
  and PB6 analogue, PB7 the scan's row) is unchanged and never touches
  bit 5.
- **`DAA_CON7`** is read at start-up, after the route and each minute,
  carried in every record with its change count; a record is written
  only when it changes.
- **Screen and log.** The test screen's audio line shows TONE or SYN with
  the late halves, PB5 and its changes, the route's state, S2 and the
  frames a second. audio8's view gains three rows. Layout 8 (985 of a
  record's 1011 words) adds audio9's fields, the first words of a half
  in each S2 state, and MIDI out's byte count.
- **fwtest** (case audio9): the synth plays KEY1, KEY3 and KEY5 into
  `audio.wav` at fwtest's 44 117.6 with no late half and no MIDI byte; the
  old steps' buttons write no step and leave `CLK_CON1` and `CON5` as
  read; SEQ takes the route down and up with port C back as read; PB5
  changes with `SB_TEST_A9_PB5`; `SB_TEST_A9_PA_MOVE` and
  `SB_TEST_A9_CHECK_FAIL` make the route undo itself and R2; the 16-bit
  build's words match each S2 state. The identity is 0.10.0-hw3s.

### 2026-11-21 clean-br17-audio10: the sample format, the mix, MASTER, the clicks (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio10.md; HW-163,
HW-164), with the owner's rulings: F with U at start-up; the mix M2 with M3 under it, no M1;
V and C as written. Behind `SB_HW_AUDIO10` (refused without
`SB_HW_AUDIO9`). Only the samples change; no register is written beyond
audio9's.

- **F (LFO)** cycles the format of everything the link plays, the tone and
  the synth: P (the sample in both halves, audio9's), U (the upper half,
  the lower 0), L (the lower half, the upper 0), N (the sample upper, its
  negative lower) and N' (the negative upper, the sample lower); the most
  negative sample's negative is clamped to the most positive. U at
  start-up. Each change is logged with its beat (the last 8 in every
  record) and named on the step row and the audio line. It replaces
  audio9's S2, whose three states are P, U and L.
- **The packing, before audio10:** a cast to 16 bits, which would wrap,
  but nothing reached full scale: the tone peaks at 3 276 and the synth
  at 8 191 (the engine clamps its own sum at its full scale, 24-bit, and
  the >> 10 puts that 12 dB below 16-bit full scale). So four voices at
  full level reached the engine's clamp, a hard clip, not a wrap.
- **M2 and M3.** In audio10's build the engine leaves its sum unclamped
  (fm_play.c), and hw_audio.c takes it at 16-bit scale (>> 10, so the
  engine's full scale stays 12 dB below): straight up to half full scale,
  then a soft clip, K + R t / (t + R) with K 16 384, R 16 383 and t the
  excess, whose slope is 1 where it starts and which never reaches full
  scale; then M3, saturation at full scale (a hard clip, never a wrap) in
  the packing. Under N the output's swing is twice a half's; the headroom
  is per half. In fwtest's layout the same 16-bit sample goes out << 8,
  so the WAV shows the unit's sample. Samples bent and saturated are
  counted.
- **The fill:** the synth's own fill time (`sb_now()`'s 24 MHz units),
  longest overall and longest with 8 voices sounding (all of core 0's),
  and the most voices, in the log (the audio line shows the late halves).
- **V, MASTER.** input.c reads SARADC channel 4 once a scan cycle (the raw
  reading), reports the mean of the last 4 when it moves more than 3 from
  the last reported, or reaches an end (MASTER's value, 0 to 1023). The
  tone's gain is linear in it (value / 1023 of its top); the synth's level
  is its square (value² × 16 of 2^24), so near the bottom one step of 4 is
  several dB: at 12 to 16 about 5 dB for the synth, 2.5 dB for the tone.
  The audio line shows the value and the raw reading. Each reported change
  is kept with its beat (the last 40), the raw readings' steps are watched
  from the scan's slot (steps over 32 counted as jumps, the largest kept),
  and a record is written once MASTER has stood still for 1 s, so a turn in
  eight steps leaves a record at each pause.
- **C, before the build: what happens about twice a second.** The LED
  guide's blink: the next key's LED changes every 500 ms (the only thing
  at exactly that period). Also: the test screen's refresh every 100 ms
  (main's matrix sweep of 16 columns, the SARADC's 12 channels, three rows
  redrawn over SPI1), and once a second the core 1 row and the audio line;
  the PB5, `DAA_CON7` and late-half checks every 100 ms, which write a
  record only on a change; log writes only on events. In fwtest's
  `audio.wav` the tone shows no step at any period (case audio10: its
  largest second difference stays near a clean sine's).
- **C, the holds,** each on and back by its own key, logged with its beat
  (the last 8) and as a record: PLAY plays zeros (the tone and the synth
  set aside, the engine's queue still emptied); HOME holds the LED guide's
  blink (the LEDs left as they stand; the scan still runs and multiplexes
  them, so this holds the blink alone); ENV holds the screen (no drawing:
  the step row, the refresh's rows, the audio line and the event line keep
  what they show; main's sweeps still run); GLO holds the log (records
  dropped and counted, the count written when it is let go); REC holds
  the scan: the scan paused with `0xFFFF` latched and the LED lines low,
  and main's matrix and SARADC sweeps skipped, for 5 s, ending by itself
  with a countdown on the step row.
- **Keys:** SEQ (the route), FX (the synth), LFO (F), PLAY, HOME, ENV,
  GLO and REC (C's holds), EDIT (a save). REC's bit 9 and HOME's page are
  off in this build. The guide: F through all five and back to U, the
  synth, each hold on and off, the scan hold, a save.
- **The log:** layout 9: the sense scan's event list cut from 120 to 32
  (audio10's fields needed the room), the first words kept for each of
  F's five formats, and audio10's fields (980 of 1011 words).
- **fwtest** (case audio10): the formats logged; an 8-key chord with 8
  voices, the sum never wrapping; with `SB_TEST_A10_GAIN` (18 dB more)
  the soft clip bending it and nothing saturating; the pot moved by the
  script and each move logged; the holds on and back, the scan hold
  ending by itself; zeros in `audio.wav` while held; in the 16-bit build
  each format's words, with `SB_TEST_A10_CLAMP` forcing each half's first
  sample to the most negative. The identity is 0.10.0-hw3t.

### 2026-11-22 clean-br17-audio11: N fixed, the SARADC's set-up, the clicks in N, the key status (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio11.md), with the
owner's rulings: A, N the only format from start-up; B2, `CON` bit 3 set as
the SDK does; B3, MASTER by a curve with ramped changes; C as written; D
items 1 to 4; E, the key status in large text. Behind `SB_HW_AUDIO11`
(refused without `SB_HW_AUDIO10`). No register is written beyond audio10's
but the SARADC's `CON`.

- **A.** Everything the link plays, the tone and the synth, goes out as N
  (the sample upper, its negative lower, the most negative's negative
  clamped) from start-up. LFO, the format key, is the engine's again: main
  gives it nothing (the engine sees every key, as before).
- **B, one service for the converter.** Every conversion the build starts
  goes through `hw_a11_adc_poll`, run from TIMER0's slot (every 83 us). It
  never waits: a slot finds the conversion in flight done (bit 7) or not;
  done, it keeps the reading and starts the next; not done, it returns,
  until 5 ms (counted as a time-out). Conversions alternate MASTER (channel
  4) and one channel of the sweep, so main's 10 Hz sweep of 12 blocking
  conversions is gone, and no conversion can delay a half's fill (the fill
  is the audio interrupt's; the service's own time in a slot is logged).
  input.c's pot() takes MASTER's newest reading from it, once a scan, and
  never writes `CON`. The sweep leaves out channel 2 (PA10, an LED line), 8
  and 9 (PC9, PC10, the panel) always, and 6 and 7 (PC0, PC1, the link's
  clocks) unless the route is down (HW-129).
- **B, the set-ups.** The SDK's (at start-up): three writes, the channel in
  bits 8-11, bits 0-2 `0b110` (the divide by 96), bits 12-15 `0xF` (the
  start delay), bit 3, bit 6 with bit 4 clear; then the same with bit 4; then
  the same again (bit 6, the start, set again). For channel 4: `F44E`,
  `F45E`, `F45E`. The old: one write, the channel with bits 4 and 6 (`0450`).
  Bit 5, the interrupt enable, is set in neither: the build polls bit 7 (the
  SDK sets it). SEL cycles them, named on the step row and in the large
  area, logged with the beat.
- **B, timing.** Each conversion's time from its start to bit 7 seen by a
  slot (83 us steps), least and greatest per set-up; one conversion of
  channel 4 timed by a tight poll in main once the start is over and at
  each change of set-up. MASTER's first reading, in input_start, comes
  before TIMER0 runs, when `sb_now()` stands still: its wait is counted in
  passes (2 000 000 at most), not timed. Every wait is also bounded by
  passes, so none can hang whatever the clock does. In fwtest a conversion
  finishes at once (HW-40); `CON` reads back as written with bit 7 set
  (`F4DE`, `04D0`): bits 0-3 and 12-15 are stored, and change nothing in the
  conversion's time. The test build `SB_TEST_A11_SLOW` holds bit 7 back
  300 us: no wait ends early and none times out.
- **B, the log.** For each set-up and each kept channel: the least and
  greatest reading, the count, and the values with counts (exact while a
  channel has shown 4 distinct values or fewer; past that, the slot with
  the fewest goes to the newer value and its count to "other"); the log
  keeps the two with most and the rest. MASTER's raw reading is kept beside
  each of its value changes (audio10's ring), and its raw jumps (over 32)
  with their beats.
- **B3, MASTER's curve.** The tone's level is MASTER's square, value² /
  1023² of its top, 0 silent; a change ramps evenly over the half (the
  level steps once a sample from the last half's to the new). The synth's
  level was already the square (pot² × 16 of 2^24) ramped over each of the
  engine's 64-frame blocks (half the unit's half, all of fwtest's).
  input.c's mean of 4 with its dead band of 3 is kept: the value moves in
  steps of 4 or more as the knob turns slowly.
- **C.** audio10's holds kept (PLAY zeros, HOME the LED blink, ENV the
  screen, GLO the log, REC the scan for 5 s). What now comes about twice a
  second: the LED guide's blink alone, as before; the old 100 ms SARADC
  sweep is replaced by the continuous service; the large area redraws only
  when its text changes. MASTER's raw reading and level are logged over
  each hold (the ring with raw readings, the jumps, the holds' beats).
- **D item 4.** The synth's longest fill per algorithm (`sb_fm`'s), any and
  with 8 voices, logged in 0.1 us.
- **E.** The key status in its own area, y 40 to 112, in place of the
  matrix grid, the ports and the event box: three lines of up to 12
  characters at three times the font, each glyph 15 x 21 pixels on an
  18 x 24 cell: "N TONE SDK" (the format, the tone or the synth, the
  set-up; green with the route up, red without), "M300 r300" (MASTER's
  value and raw reading), "L8% -" (the level applied, in whole per cent of
  full, and the hold: ZERO, LED, SCRN, LOG, or SCAN with its seconds left;
  yellow while one is on). The rest of the screen is as it was; the lines
  are in each record too.
- **The log:** layout 10, audio11's builds only: layout 9 without the sense
  scan's fields and F's change list, with audio11's (1011 of 1011 words).
  Every other build still writes layout 9.
- **fwtest** (case audio11): N's words from start-up in the 16-bit build,
  the clamp included; each set-up's writes, read-back and conversion times
  with the slow seam; channels 6 and 7 never read with the route up;
  MASTER turned in each set-up, a record at each pause; the tone's largest
  second difference with MASTER moving (no step); the holds; zeros in
  `audio.wav`; an 8-key chord and the fill per algorithm; the large area
  read off the screen in each state. The identity is 0.11.0-hw3u.
### 2026-11-22 clean-br17-audio12: the sweep, ALGORITHM, the instrument's start, frames (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio12.md), with the
owner's rulings (docs/prompts/spec-audio12-rulings.md): S yes; G yes; G2 only
if G finds the start-up patch the cause; D5 now; D6 now; D8 later. Behind
`SB_HW_AUDIO12` (refused without `SB_HW_AUDIO11`), but D6, which is the
shared engine's. No register or pin beyond audio11's, no port B write, no
USB register, no store write.

- **G, found before the build.** The unit started in test patch 0, Sine:
  operator 1 at level 127, operators 2 to 6 at 0 (so `off`), and operator 1
  is a carrier (`FM_TO_OUT`) in all ten algorithms, so every algorithm gives
  one carrier and the same sine, bit for bit. fwtest, build A, one note per
  algorithm with ALGORITHM turned between: Sine's ten notes identical, Bell's
  (patch 4, all six operators sounding) ten different. A change of
  algorithm reaches only notes started after it: `voice_start` copies
  `algorithm_now` into the voice, and the renderer reads the voice's. The
  turn is also taken only with local control on. So G2: the unit starts in
  Bell (`FM_A12_PATCH`; Brass was quieter at the low key and sustains less
  differently); a test flag (`SB_TEST_A12_SINE`) keeps Sine for the check.
  On the unit the engine logs each note on (the note, its voice, ALGORITHM
  as read, the voice's algorithm, local control; the last 16) and each turn
  (taken or dropped, the algorithm after).
- **S, the sweep.** On the test screen LFO (which the engine ignores)
  starts it; it runs in the engine's context, from `synth_fill` before the
  engine's blocks, timed in the frames filled (128 a half on the unit, 64 in
  fwtest's layout): for algorithm 1 to 10, ALGORITHM set, eight notes (MIDI
  48, 55, 60, 64, 67, 72, 79, 84) on, 1.5 s, off, then every voice idle
  waited for (at most 3 s, logged if reached). Per algorithm: the longest
  fill with the voices then, soft-clipped and saturated samples, late halves
  (the audio layer's underruns, which count both a half missed and one
  refilled late). LFO during it stops it after the chord in progress, its
  release waited for. The large area's first two lines show "SWEEP A<n>" and
  "F<us>US <v>V" (the algorithm's longest so far), and for 10 s after,
  "DONE A<n>" (or "STOPD") with the slowest. Records: Sweep start, stop
  asked, done or stopped. The synth goes on first if it is off.
- **D5, the instrument's start.** At the point the test screen was drawn,
  HOME held gives the test screen (PLAY and REC are m-bootloader's at
  power-on, HW-117): HOME must be let go first (the route's check stops on
  a key held; at most 10 s), and its events are dropped so the test screen
  doesn't take the press. Otherwise: the engine, the synth on (so the first
  half is the synth's, not the tone), ALNK0 in N, L2, port C's four pins and
  the route with the matrix check and its self-undo (audio9's start, as
  is), then the panel (`view_message`, views.c's own screens) with "audio12:
  sound on", or "NO SOUND: " and the step row's reason; main serves the
  panel instead of the test screen's keys, so they do nothing; the start's
  rows are held off the panel. The line also goes in the boot record (in the
  large area's words). The store isn't started or served on the unit
  (`store_boot`, `serve_store` would write its flash): a save from the panel
  isn't kept.
- **D6, frames.** Measured first: ARP's position already moved by each of
  the engine's blocks, so its steps came at the right frames on the unit
  (5 514 or 5 515 frames apart at 120 beats a minute, 1/16, on both layouts
  in fwtest). What counted audio interrupts (`sb_audio.blocks`) were its
  times: each step's logged frame, the MIDI clock's arrival times (so a
  followed clock's rate), the clock's loss after `ARP_LOST_BLOCKS`, and the
  record's first note on and last off. On the unit a half is one interrupt
  but two blocks, so those were half the frames (the log's steps 2 762
  frames apart; a followed MIDI clock would have run ARP at twice its tempo,
  and the loss taken twice as late; MIDI is off on a unit). Now the engine
  counts its own frames, a block's at its start, and passes the block
  number (frames / 64) where the interrupt count went; in fwtest's layout
  that number is the interrupt count, so build A's outputs are unchanged
  (the ARP suite passes as before). Nothing else in the engine counted
  interrupts: envelopes, glide, LFO and the arpeggiator's position count
  blocks already. The views' redraw watches `sb_audio.blocks` only for a
  change.
- **fwtest's `--audio-chip` (0.13.0) not adopted:** the fill stays sized
  per target, and fwtest's own layout runs the unit's 16-bit build at twice
  its rate; adopting it belongs with D7's harness change.
- **Layout 11** (audio12's builds only): layout 10 without audio11's
  settled fields (the set-up's change list, the old set-up's channels,
  MASTER's raw ring and jump list, the fill per algorithm), with the start,
  the sweep's fields and G's after the large area: 996 words.

### 2026-11-22 clean-br17-audio12b: audio12's file stopped at the first bands; the instrument's start behind SEL (BR-17, R-HW-1)
The owner's report (docs/prompts/clean-br17-audio12b.md): audio12's file
stopped on the unit at the blue and green bands, with or without HOME, no
record written. The owner's rulings: power-on to the test screen; the
instrument's start behind a test-screen key, with a record before each
stage; the hang found; a seams case that would have caught it; S, G, G2 and
D6 kept.

- **The hang was the file, not the code.** audio12's `.fwsc` was packed
  from `app.bin`, the raw image linked at `0x02000000` (fwtest's raw
  path), instead of `app-pkg.bin`, the package link at `0x02000120`, where
  a package's app runs (HW-91). Every earlier candidate was packed from
  `app-pkg.bin`: re-packing audio11's gives its file's SHA-256 exactly,
  and re-packing it from `app.bin` doesn't. With the raw link the start
  code (in the window, position-independent enough) draws bands 1 and 2,
  then copies the RAM image from the wrong place (`__data_load` is 0x120
  short), so main runs garbage: in fwtest's package path that package stops
  at the two bands with garbled rows, and the same build packed from
  `app-pkg.bin` runs to the panel. The report's own reading (a hang after
  core 1's screen) doesn't fit the screen: with HOME held the step row
  would have asked for HOME to be let go, and before that come band 3, the
  pattern and the rows.
- **How fwtest passed it:** every seams case runs `app.bin`, the raw link,
  through fwtest's raw path, which is right for that link; none ran the
  file that went to the unit. The pack was a manual step, and `fwsc check`
  checks the package's structure and key, not the app's link.
- **What catches it now:** `tools/fwsc.py pack` reads the ELF beside the
  app and refuses one not linked at `0x02000120` (or with no ELF beside
  it). Case audio12 builds the unit's own defines (the 16-bit layout, no
  test seams, the full hold), packs both links and runs them through
  fwtest's package path for 40 s: the package link must get past the
  start's blue and green bands (to the audio page, at fwtest's slower
  slots), and the raw link must still show them (the negative control).
- **The instrument's start behind SEL** (SEL pressed alone is nothing to
  the engine, and audio11's set-up comparison is settled, HW-170): a
  record ("Inst synth", "Inst ALNK0", "Inst L2", "Inst R2", "Inst route",
  "Inst panel") and a step row before each stage. ALNK0, L2, R2 and the
  route are up already from the test screen's start, so those stages
  record it and leave them as they are; the route is tried again only if
  it is down (SEL let go first: the check stops on a key held). Then the
  panel, as audio12's. Identity hw3w.


### 2026-11-22 clean-br17-audio13: power-on to the instrument; the USB block read; ARP's steps timed (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio13.md), with the
owner's rulings: D5 (power-on straight to the instrument, HOME held for the
test screen), U2 (the USB block read, never written: U2-A, U2-B, and U2-C
on its own key; docs/prompts/spec-usb-u2-rulings.md and -rulings2.md), and
ARP checked on the unit with each step's timing logged. Facts from
HARDWARE-SPEC HW-171 to HW-175, HW-86, HW-91, HW-117 and HW-129.

- **D5 from cold** (`SB_HW_AUDIO13`, on audio12): after core 1's screen,
  HOME is read; not held, the boot's record, then the instrument's start
  as #240 ran it (the engine, the synth, ALNK0, L2, R2, the route with its
  matrix check and self-undo), keeping audio12b's record and step row
  before each stage and adding "Inst engine" first; then the panel, no
  test screen. Held, the test screen once HOME is let go (#240's wait and
  drop of its events); SEL there runs the start as audio12b (the engine
  already up). `main` jumps past the test screen's drawing and start to
  the loop. The cold stages are audio12b's, so a stage already up is
  never started twice (`a9_route_up` skips R2 when it is set).
- **U2-A** reads the five words (`JL_USB->CON0`, `CON1`, `JL_USB_IO->CON0`
  to `CON2`, by the SDK header's names, HW-171) in `sb_start` right after
  the panel's band 1, before the copy to RAM: band 1 alone on the screen
  would mean a read hung. They stay in registers until the copy and the
  zeroing, then go to RAM. A second reading comes at beat 1000, before
  either start's audio path (the audio block count then is logged, 0), and
  OCT- reads them again in the test screen. Each start's boot record
  carries both readings, and so does every record after it, so each
  start's reading reaches the flash with no save key, the last 96 records
  kept. Nothing is ever written to the block, and nothing goes through
  `CON1`'s port (an access there starts with a write, HW-86).
- **U2-B** polls the words every 100 ms from the test screen's tick, logs
  each word's change with its beat (the last 24), and keeps, for each run
  and cable state, each word's bits ever set and always set. SAVE marks
  the next state (a to e, then a again); state a takes the words then as
  the ones the others are compared with. OCT+ turning U2-C on marks state
  a too: the second run. The large area says the state letter and "SAME AS
  A", or "CHANGED" with the word (C0, C1, P0 to P2); its second line shows
  the start's words one every 2 s, its third U2-C.
- **U2-C** adds channels 12 and 13 to audio11's sweep only while OCT+ has
  it on (off at start-up). They are converted as the others (the SARADC's
  `CON` as audio11 writes it, the only write) and kept apart: the count
  and least and greatest by state, each turn-on's first readings, and a
  log of readings that move by more than 8 or every 2 s, with the state.
- **ARP** in the panel: the build starts ARP's settings as the ARP
  suite's (UP, 1/16, 2 octaves, gate 50 %, 120 beats a minute; Bell gives
  all but the octaves), off; ARP's short press turns it on and off. After
  the engine's blocks each fill takes the steps it played from `sb_arp`'s
  log, their frame counts, timed by the fill's start by `sb_now()`
  (TIMER0, the fill times' timer; the audio interrupts don't drive it). A
  chain runs while ARP is on and holds a note; its gaps give the shortest
  and longest in frames and in units, and the longest chain's ends give
  the rate. While ARP runs the panel's message line shows the last gap
  ("ARP gap 5514 fr 125.0 ms"). REC in the panel (a later milestone's
  button) saves the log, not the store.
- **Layout 12** leaves out the old steps' snapshots and steps H, I, K, J,
  D, L1 and L2 (audio2 to audio7, 380 words) for audio13's 371. Identity
  hw3x.
- **What fwtest shows of it:** without `--usb` fwtest reads the five words
  as 0 but `CON1`, which reads `0x8000` (bit 15, `MACK`, set: HW-86's
  "every access is done at once"). ARP's gaps are 5514 or 5515 frames on
  both layouts; by `sb_now()` they are 50 ms in fwtest's layout (its
  TIMER0 2.5 times slow) and 25 ms in the 16-bit layout, where fwtest takes
  the unit's 128-frame half in the time of one of its own 64-frame halves.
  On the unit both should be 125 ms. The unit's build writes no log in
  fwtest (its window `CON` reads 0 there); its package reaches the panel.

### 2026-11-23 clean-br17-audio14: the panel's ARP save; the block at 0x16A00 read; U3-F, the USB MIDI device in fwtest (BR-17, R-HW-1)
The spec side's prompt (docs/prompts/clean-br17-audio14.md), with the
owner's rulings: R (the panel's save writes ARP's record), P (the block at
`0x16A00` read only, with U2-A's), U3-F (the USB MIDI device, built and
tested in fwtest only; no serial-number string). Facts from HARDWARE-SPEC
HW-171 to HW-173, HW-176, HW-177, HW-86 and Q-36, REQUIREMENTS R-USB-1, and
docs/HARNESS.md's "USB".

- **R: why audio13's save wrote none.** Not found. fwtest writes the
  record in every order tried: REC with ARP on (case audio13), and the
  owner's order, the chord released, ARP off, then REC, and ARP off with
  the chord still held. All code and constants run from RAM (since M7),
  so the flash take stops nothing; ARP's step counter only counts up; and
  by count of what the run's later starts and keys write (about 45
  records), the ring's 96 slots wouldn't have come round to it. What is left is the
  unit itself: whether REC reached the panel there, and whether the write
  failed (a failed write is counted only in RAM, and the next record,
  which would have carried the count, came after a power-off). audio14
  makes each of those visible. REC's record is labelled "ARP save", counts
  itself (`arp_saves`), and the panel's message line says "ARP saved #n"
  or "ARP NOT saved, error e", with the steps; the next record keeps that
  result (`arp_save_err`, `arp_save_seq`). ARP turning off with steps not
  yet in a record writes "ARP off" by itself, so the steps reach the flash
  with or without REC. Every record already holds ARP's step log
  (audio13's fields: the gaps' extremes in frames and `sb_now()` units,
  the steps, the last 48 steps' frame counts and times).
- **P** reads the four words at `0x16A00` and the three words after it in
  `sb_start` just after U2-A's, before the copy (kept in registers until the zeroing), at
  beat 1000 with U2-A's second reading (before either start's audio
  path), and on OCT- with U2-A's key. Every record holds all three, so
  each start's reading reaches the flash with no save key, as U2-A's
  does. The large area's second line shows them after U2-A's five, by
  their addresses' last three digits ("A00 xxxxxxxx", the line's twelve
  cells), one every 2 s. The decoder says whether bit
  1 of `0x16A00` reads set at each reading. Nothing is written to the
  block or to any clock register.
- **ARP's gaps in fwtest:** 5514 or 5515 frames, but over a long chain a
  step can come one frame early: a step due in a block's last
  frame-fraction rounds to frame 64, which `arp.c` clamps to 63, giving one
  gap of 5513 and the next of 5516. The unit's layout in fwtest (320 steps)
  showed one such pair; fwtest's own layout (160) none. It is the base's
  ARP as it has been since ARP, not changed here (its goldens would move).
  On the unit a 5513 followed by a 5516 means the same, not a wrong
  frame count.
- **Layout 13** is layout 12 with P's twelve words and R's four counts
  before the log's own health: 1003 fields of the record's 1011.
  Identity hw3y; `hw_fm1.h`'s last `HW_BUILD_ID` stays the identity of a
  build without audio13, which seams case report1 builds.
- **U3-F** (`firmware/src/usb_midi.c`, built only with `SB_USB_MIDI`):
  - **Kept out of the unit's builds:** no build script, candidate or
    release sets `SB_USB_MIDI`; only seams case usbmidi's test build does.
    With `SB_HW_FM1` the build stops (`#error`). Without the flag the file
    holds nothing, and the three hooks (main, midi.c, midi_out.c) are
    under it too. Case usbmidi checks this from the builds: a unit build
    with the flag fails with that message, and the candidate's ELF has
    none of the device's symbols.
  - **The device:** a MIDI-only device, vendor `0x1209` and product
    `0x0001` (pid.codes' test PID, with R-USB-1's comment that it is for
    in-house testing only), the manufacturer and product strings
    "small-beeps", no serial-number string. Endpoint 0 answers the
    standard requests (device, configuration and string descriptors, set
    address, set and get configuration, get status, get and set
    interface, clear and set feature); any other is stalled. USB MIDI 1.0's
    audio control interface comes first, then the MIDI streaming
    interface with a bulk OUT endpoint (1) and a bulk IN endpoint (2), one
    embedded and one external jack each way. The descriptors' layout and
    the standard requests are from general knowledge of the published USB
    specifications, not from HARDWARE-SPEC (PROVENANCE P-99).
  - **One context:** all the device's work is done in the first core's
    start-of-frame interrupt (source 8, HW-171), once a frame: the flags
    (read once, they clear), a bus reset, endpoint 0, then the bulk
    endpoints by their `CSR` bits. Only that interrupt uses `CON1`'s port
    and `INDEX`. The host's MIDI goes into a ring of its own that the
    engine empties into MIDI in's ring once a block (`midi_poll`), so the
    ring keeps one writer, and plays the engine as the jack's bytes do.
    The firmware's own channel messages (`midi_out_channel`: the panel's
    keys, ARP) go to the host through a ring the interrupt empties. MIDI
    thru calls `midi_out_send` and doesn't go to the host, so the host's
    notes never come back to it.
  - **The port:** every access waits until 2 µs (48 units of the 24 MHz
    time base) have passed since the last one ends (HW-172 gives no
    figure; it is this side's choice, kept in `USB_PORT_GAP` alone), and
    every wait for `MACK` is bounded (HW-86), counting time-outs.
  - **The core's set-up** is `usb_core_setup()` alone: `CON0` bit 0 and
    `POWER` at `0x60`, the SDK's value with `FUSB_MODE` 0 (HW-172). That
    is all fwtest's host waits for (HARNESS.md "USB"). U3-U replaces this
    function once Q-36's writes and the owner's ruling are there.
  - **The lines before connecting:** `CON0` read 32 times 50 µs apart, the
    first value, bits 16 and 17 ever set, and the reads with either set
    logged (`sb_usb`). fwtest doesn't model those bits, so they read 0
    there: "steadily 0", which on the unit means a computer that is on
    (HW-177). In fwtest that comes from the model, not from a host.
  - **`FADDR`** is written as soon as SET_ADDRESS's setup is taken, which
    is when fwtest's host checks it; when the chip takes it is U3-U's to
    find.
  - **Without a host** nothing happens after the start: no frame, so no
    interrupt. The start's 1.6 ms of line reads put the audio's first
    interrupt about one block later, so a run without `--usb` gives build
    A's samples and MIDI bytes, microseconds later.
- **fwtest 0.14.0** is pinned (`config/fwtest-image`; HARNESS.md
  "Versions"). It is the one pin for every case: without `--usb` or
  `--audio-chip`, 0.14.0's outputs are 0.12.0's.

### 2026-11-23 clean-br17-u3u: U3-U, the USB MIDI device on the unit, for the owner's flash only (BR-17, R-HW-1, R-USB-1)
The spec side's prompt (docs/prompts/clean-br17-u3u.md), with the owner's
rulings of 2026-11-23, and the owner's answers to audio14's questions
(docs/prompts/clean-br17-audio14-answers.md). Facts from HARDWARE-SPEC
HW-171 to HW-173, HW-176 to HW-180, HW-86 and HW-117, and REQUIREMENTS
R-USB-1. Q-36 isn't in the clean folder; HW-178 and HW-180 say what it
leaves open.

- **R is closed** (the owner, 2026-11-23): audio13's log had no "Panel
  save" record because REC wasn't pressed; on audio14, REC showed "ARP
  saved", and the log has the "ARP save" and "ARP off" records (HW-179).
  The panel's save works; its cause above needed no fix.
- **The owner's file:** `SB_HW_U3U` (with `SB_HW_AUDIO14` and
  `SB_USB_MIDI`), identity `0.15.0-hw3z`, log layout 14. It differs from
  the published build (audio14's, hw3y) only by the USB device: its
  descriptors carry pid.codes' test product ID, so the file goes to the
  owner's flash alone and its name says so. A unit build with
  `SB_USB_MIDI` but not `SB_HW_U3U` stops, and the published build's ELF
  has none of the device's symbols (seams case usbmidi).
- **When USB starts** (the owner's ruling): nothing is written to the USB
  blocks until the cable reading, `CON0` bits 16 and 17, reads steadily 0
  (32 reads 50 us apart, HW-177) in three checks in a row: the first at
  the app's start (main's loop, after the instrument's start or the test
  screen), then one each second. So the set-up begins about two seconds
  after an awake computer is plugged in; on the battery, with a charger or
  a sleeping computer it never begins. Each change of the reading is a
  record ("USB cable", the first 16; the rest counted). Once the device is
  set up the lines carry the bus, so what they read then isn't given:
  it's counted (`lines_after`), never acted on. USB runs in the test
  screen too (HOME held at power-on): the poll is main's loop's, not the
  panel's.
- **The set-up** (`u3_core_setup`) replaces U3-F's one function, in
  HW-178's order: IO `CON0` bit 10 then bit 9; `IO_MODE` cleared then `SR`
  set; `CON0` bits 2, 4, 5 and 14 cleared; `CON1` 0; `PHY_ON`; both
  pull-downs cleared, both pull-ups cleared, then `DPPU`; `CON0` bits 2 to
  5 set. Then, in HW-172's order by the owner's ruling: the device's
  interrupt enables cleared (HW-178: `INTRUSBE` 0, every transmit and
  receive enable 0) straight after; `POWER` `0x60` with interrupts off;
  endpoint 0's 64-byte buffer, set as the receive address of endpoints 0
  to 4; `INTRUSBE` reset and suspend; endpoint 0's enable; the controller's
  interrupt (source 9) registered; `SIEIE` last. Each write names its HW
  entry in the code. Every change to `CON0` and IO `CON0` reads the word
  and changes only its step's bits, so either start state (HW-177) gets
  every step. Nothing goes to `0x16A00` or to any clock register.
- **U3-F's `CON0` writes are gone.** U3-F wrote whole words to `CON0`
  (each frame, and at its start), which on the unit would clear `USB_NRST`
  and the bits step 7 sets, and `SIEIE`; fwtest doesn't model those bits,
  so it never showed. The device no longer uses the start-of-frame
  interrupt (`SOFIE` isn't in HW-178 or HW-172): its work is the
  controller's interrupt's, at priority 1 (below the tick's 2, above the
  engine's 0), and main's loop starts packets out with interrupts off
  (`usb_midi_send` wakes it), so the port and `INDEX` have one user at a
  time.
- **The port** (`port()`): only while `USB_NRST` reads set; each access
  10 us after the last (`USB_PORT_GAP`, 240 units of `sb_now()`, the
  spacing's one place, logged as `gap_units`); a `csync` after the write;
  bit 15 polled up to 20 000 times (HW-178). A give-up there (NRST clear,
  or bit 15 never came), or the interrupt taken 1000 times in a row with
  no flag up, logs the stage, the index and the word read, turns source 9
  off at the CPU (HW-20; not a USB write), and nothing more is written to
  USB until the next power-on; the instrument runs on. There is no stop
  sequence: none has a source.
- **The log** (records from main's loop only, never the interrupt): a
  record before each of HW-178's steps 1 to 6 ("USB step 1" to "USB step
  6"), so a hang in one of them shows which; from step 6 (D+'s pull-up:
  the host sees the device) to `SIEIE` nothing waits for the flash, and
  the step row names each write; "USB set up" after `SIEIE`, with `CON0`,
  `CON1` and IO `CON0` read back (the cable reading is `CON0`'s bits 16
  and 17 there). Then one record for each first: the host's reset, the
  address, the configuration, the first MIDI packet in, the first packet
  out (when the host took it), a give-up. Every record carries the whole
  device record (`struct sb_usb_record`): each stage's beat, the cable
  checks, the counts. Babble isn't visible to a device (HW-172:
  `INTRUSB` bit 2 is babble only as a host); the endpoints' `UnderRun`,
  `OverRun` and `DataError` are counted if they ever show, with the
  rings' drops.
- **Layout 14** is layout 13 without ARP's step log (96 words; R is
  done), with the device's words (71 in try 1, 98 since try 2) before the log's own health.
- **`FADDR`** (general USB knowledge, PROVENANCE P-99): a MUSB-style core
  takes the address at once, and the status stage of SET_ADDRESS must
  still be answered at address 0, so on the owner's file the address is
  written at endpoint 0's next interrupt (the status stage's end), or by
  main's loop 3 ms later if none comes (`addr_late` counts those).
  fwtest's host checks `FADDR` straight after the request (its own model,
  HARNESS.md "USB") and lists "FADDR is 0" for that, though it goes on
  and the file enumerates; so fwtest's test builds write it at once, as
  U3-F did, and seams case usbmidi expects that one problem on the
  owner's file alone. If the unit shows the host's reset but no address,
  this is the first thing to look at.
- **fwtest:** with `--usb` the test build and the owner's file enumerate
  as `1209:0001`, "small-beeps" twice, no problems. fwtest doesn't model
  `CON0` bits 16 and 17: they read 0 with and without `--usb`. So without
  `--usb` the reading shows "a computer" there too and the set-up runs,
  with no host and no bus event after it; the outputs are still build
  A's. On the unit the reading tells the two apart (HW-176, HW-177).
- **Tries, by the owner's ruling of 2026-11-23:** USB goes on one branch
  (#249, a draft) with no PR per try; each try runs the USB seams cases
  (report1 on an identity change), the terms check and packs the owner's
  file. A value that is a guess is offered several ways behind a
  test-screen key, logged; a write HW-172 or HW-178 doesn't give stops the
  work and goes to the owner.
- **Try 2** (after #249's first commit):
  - C-SEP-TERMS named two of the first try's identifiers; they are now
    `usb_halt_writes` and `u3_sie_isr`, and the decoder's stage
    "stopped".
  - After a give-up nothing more reaches the USB blocks: the endpoints'
    DMA words go through `put()`, which writes nothing once the device has
    given up; the set-up returns after any stage whose port access gave
    up, and no later stage is marked. Before, a give-up in the set-up's
    first port access still let it write `EP0_ADR` and the receive
    addresses, and mark POWER's stage and the rest. The test build
    `SB_TEST_USB_STOP` makes the first access's bit 15 never come: the log
    names the stage (the interrupt enables) and the index (11), no stage
    after it, fwtest's host never sees a device (`POWER` not written), and
    the instrument plays on (seams case usbmidi).
  - The port's spacing is the first guess offered: KEY7 on the test
    screen (HOME held at power-on) takes the next of 2, 10, 50 and 200 us
    (10 us at power-on), named on the step row and in a record ("USB
    spacing"). Each bus reset starts an attempt, and the last 8 attempts
    are logged with the spacing then in use, what they reached (address,
    configuration, a packet in, a packet out), the reset's beat and their
    last step's; every attempt's reset and configuration is a record (the
    first 16 of each). So one flash tries every spacing: unplug, KEY7,
    plug in again. Layout 14 holds the device's 98 words.
  - The log end to end in fwtest: audio14's log-writing test build with
    the owner's device, with `--usb`: "USB cable", "USB step 1" to "6",
    "USB set up", "USB reset", "USB address", "USB configured", in that
    order, every record of layout 14's length, no give-up.
- **Try 3** (the owner's unit report of try 2,
  docs/prompts/clean-br17-u3u-try2-unit.md): "small-beeps" enumerated at
  10 us and notes went both ways, with two bugs.
  - **The counts in that log were a snapshot.** Records were written only
    at stages, so the last one was "USB first out", with the counts as
    they were then ("out 1 packet, 1 event"). Each suspend (unplugging,
    or the host asleep) is now a record too, the first 16, so a run's
    counts reach the log when the cable comes out; REC in the panel
    ("ARP save") writes them as well.
  - **Bug 2, notes in twice:** 749 events in 54 packets, where the host
    sent one event a packet, means the count read about 64 bytes. The
    count was `RXCOUNT1 | RXCOUNT2 << 8`; a bulk packet at full speed is at
    most 64 bytes, so it is now `RXCOUNT1` alone, and both are logged as
    read (the last 8 packets: both counts, the events taken, `RXCSR1`).
    After a packet its bytes and the 4 past them are cleared, so nothing
    of one packet can be taken again with the next. Which of the two
    counts read wrong on the unit is the log's to show.
  - **Bug 1, the releases out as the first packet again:** every second
    packet the host got was a copy of the very first one. That fits the
    transmit DMA reading memory the CPU's latest writes hadn't reached
    (a data cache, HW-152, open for DMA), or a second hardware buffer;
    no source says which, and a cache flush has no register-level source
    (HW-152). So the ways a packet goes out are offered behind KEY8 on the
    test screen, logged: 0 as before, one buffer whose address is set at
    the configuration; 1 the address (`EP2_TADR`) written again before
    each packet; 2 two buffers, the address switched each packet. Each
    packet out logs `TXCSR1` as read before it, its bytes and the way,
    and the host's taking it is counted (`tx_done`). If none of the three
    fixes it, the fix needs something HW-172 and HW-178 don't give (a
    cache flush, or the SDK's own packet write): that goes to the owner.
  - **Layout 14** leaves U2-C's log out as well (HW-177 settled U2), for
    the device's 118 words.
  - **Seams usbmidi:** a packet of two events and two of one each give
    exactly their own (2, 1, 1); three keys each send one note on and,
    released, one note off of the same note, and nothing else.
  - **Try 3, finished from the owner's fuller analysis of try 2**
    (docs/prompts/clean-br17-u3u-try2-owner.md; `a70ad95a` was never
    flashed):
    - **Old layouts stay decodable:** layout 14 is try 2's again (98
      device words, U2-C's log kept), so the owner's backups decode with
      names; try 3 writes layout 15. Try 1's own layout 14 was never
      flashed.
    - **Separate buffers:** they already were: `ep0_buf`, `rx_buf`,
      `tx_buf` and `tx_buf2` each 128 bytes apart on 64-byte boundaries
      (the owner's file's ELF). So the bytes that mixed on the unit (a
      packet out with the key's note and the host's velocity) didn't share
      memory in our layout; they meet in the chip's DMA or cache, which no
      source gives. KEY8's ways stay offered for it.
    - **Both endpoints re-armed after every packet:** the IN endpoint is
      filled whenever its `TxPktRdy` reads clear, at every interrupt and
      from main's loop (woken each beat while something waits), no longer
      only on its interrupt, which on the unit never came after the first
      packet ("out 1 packet" in every session). After each packet in, the
      OUT endpoint's buffer address and size (`EP1_RADR`, `EP1_CNT`,
      HW-171's words, already written at the configuration) are written
      again before `RxPktRdy` is cleared.
    - **Unplugging:** the suspend interrupt never came on the unit (0 in
      every session). Main's loop now reads the frame number (HW-86's
      indexes 12 and 13) once a second: stopped while configured is
      "USB gone" (a record, and nothing sent while gone), counting again
      "USB back".
    - **The instrument first:** the controller's interrupt is at the
      engine's priority (0), so it never pre-empts the audio's fill; more
      than 64 of them in one ms is a give-up (a storm), so a runaway
      interrupt can't hold the instrument. Once on the unit the keys went
      silent after unplugging until a power-off; the log will show the
      most interrupts in one ms (`irq_peak`).
    - **Seams usbmidi:** one packet of two events and six of one, four of
      them in a row 50 ms apart and two while the keys play: each gives
      exactly its own (fwtest's counts agree); three keys each send their
      note on at 100 and their note off at 0, of their own note, and
      nothing else. fwtest has no unplugging, so "USB gone" is the unit's
      to show.
  - **The owner's answers to try 3's questions**
    (docs/prompts/clean-br17-u3u-answers.md):
    - USB's interrupt stays at priority 0: the owner's ruling, which the
      spec side records. The source comment will say so with try 4.
    - fwtest's host should drive `CON0` bits 16 and 17, and check `FADDR`
      after the status stage. Both are harness changes, so they went to the
      spec side as a request; this side doesn't change fwtest.
    - Each try gets its own identity, so the backups name the try. Tries 2
      and 3 were both `0.15.0-hw3z`; their records still tell them apart by
      layout (14 for try 2, 15 for try 3). Try 3's file (`ace98173…`) was
      checked and flashed as it is. From try 4, the identity is
      `0.15.0-u3u-t<N>`: 13 characters, so `FM-1_` and it fit fwsc's 19
      and the record's 16. It is set in `hw_fm1.h` and seams' `U3U_ID`.
  - **Try 4, from the owner's run of try 3, way 0**
    (docs/prompts/clean-br17-u3u-try3-unit.md, backup fm1-20261123-194712):
    nothing from the Mac sounded, because `RXCOUNT1` isn't the length. For
    4-byte packets it read 56, 12, 60, 16, 64, 20, 68, 48.
    - **In:** `RXCOUNT1` is logged only. Because the buffer is cleared after
      each packet, the events are read from its start up to the first
      all-zero one, at most 16.
      - An event whose code index doesn't match its status byte is dropped
        and counted (`rx_bad`). For 8 to E the status's high nibble must be
        the code index; system and SysEx code indexes need their own status
        bytes; data bytes must be below 0x80.
      - The whole buffer and the 4 bytes past it are now cleared, not a
        count's worth.
      - For each packet, which of the 17 four-byte slots read non-zero is
        logged beside `rx_log` (`rx_mask`). If the DMA puts the bytes
        somewhere other than the start, try 5 can see where. This reads our
        own memory only; there is no new register.
    - **Out:** every message the Mac took was the first one again, in
      packets of 64 and 28 bytes. That question is with the spec side, and
      KEY8's ways stay.
      - A fit with the facts, not a finding: HW-152 leaves open whether
        main RAM sits behind a data cache that the DMA doesn't see. A cache
        not kept in step with the DMA would give both a send that repeats
        its first packet and a receive that reads the buffer as cleared. No
        allowed source gives a register-level flush, so nothing here tries
        one.
    - **The way out at each power-on:** the owner can't use the test screen.
      - `usb_midi_power_on`, in `hw_a13_power_on` after U2-A's second
        reading, runs whether HOME is held or not.
      - It reads the log ring and takes the flash just as a save does,
        writing nothing (`hw_report_newest`). It finds the newest valid
        record of this build whose label starts "USB way ".
      - The way is the next one after that record's (0, 1, 2, then 0), or
        0 if there is none. Try 3's and audio14's records are other builds.
      - It is shown in large text for 2 s, with the build's identity, and
        logged as a "USB way N" record. That record is the one the next
        power-on reads, so no store write is needed.
      - A KEY8 press still changes the way for the rest of the run, under
        its own label ("USB out way"). The next power-on goes on from the
        power-on's way, not KEY8's.
    - **Layout 16** (1006 fields of 1011): the device's record gains
      `rx_bad`, `rx_mask[8]` and `way_prev`. Layout 15 is try 3's again
      (`USB_REC_TRY3`), and the decoder now checks that no layout passes
      `HW_LOG_FIELDS`.
    - **Identity** `0.15.0-u3u-t4`; USB stays at priority 0, and the source
      comment now says that is the owner's ruling.
    - **Seams usbmidi:**
      - one packet with code index 8 and status 90 is dropped and counted;
      - the packets' events and non-zero slots are checked;
      - "USB way 0" is first among the USB records;
      - three more power-ons from the flash each run before left give the
        ways 1, 2 and 0. Each is an 8 s run, because starting from a used
        flash took more than 4 s of fwtest's time;
      - KEY7's run lets HOME go at 8 s and presses KEY7 at 12 s, after the
        way's 2 s of large text.
    - The ring scan's label check is built only with SB_HW_U3U. The
      published audio14 file packs byte-identical to
      `small-beeps-audio14-key-980f.fwsc`.
  - **Try 5, the SDK's steps** (docs/prompts/clean-br17-u3u-try5.md).
    The owner ruled that the spec side's report P-519 is a source, as
    HW-172 and HW-178 are. Try 4 wasn't flashed; try 5 is built on it.
    - **Interrupts off around each endpoint group:** from each `INDEX`
      write to the last access that goes with it, in main's loop and in
      the controller's interrupt (`ep_lock`/`ep_unlock`, which nest). The
      interrupt's reads of `INTRUSB`, `INTRTX1` and `INTRRX1` are a group
      too, because they share `CON1`'s port.
    - **In:** `INDEX`, then `RXCSR1`; only with `RxPktRdy` set,
      `RXCOUNT1`/`RXCOUNT2` give the length. `EP1_RADR` is written again
      before the copy. The copy takes the smaller of the length and 64,
      in whole events, with try 4's guards (at most 16, none past an
      all-zero one, the code index matching the status) and the buffer
      cleared after. The packet is let go with `RXCSR = (as read & 0xFE9B)
      | 0x10`. `EP1_CNT` is no longer written per packet, since P-519's
      receive steps don't write it. The length is logged in `rx_log` as
      before.
    - **Out, way 0:**
      - `TxPktRdy` must read clear;
      - the events are copied into the endpoint's own buffer, then `csync`;
      - `EP2_TADR` is written again, then `EP2_CNT` with the byte count;
      - `TXCSR` (17 and 18) is read and written back with 0x01 set.

      Ways 1 and 2 are try 4's: the address each packet, and two buffers
      in turn. They now share the `csync` and the `TADR` write; their
      `TXCSR1` write stays `TxPktRdy` alone. Try 4's way 0, one buffer
      with no `TADR` write, is gone.
    - **Set-up:** `TXCSR1` 0x48, `RXCSR1` 0x90, and `TXMAXP`/`RXMAXP`
      written 1023, which the port carries as 0xFF.
    - **Gaps, where P-519 can't be followed as written, and what try 5
      does:**
      1. Whether the release write comes before or after the copy turns on
         a flag P-519 doesn't decode. Try 5 writes it after, so the next
         packet can't land in the buffer while it's read.
      2. The release is a 16-bit value, but its byte order isn't given.
         Try 5 writes `RXCSR2` (HW-172's index 21, which carries
         `IncompRx`) first and `RXCSR1` last.
      3. The order of `TXCSR`'s two bytes on write-back isn't given either.
         Try 5 writes 18 first and 17 (`TxPktRdy`) last.
      4. P-519 doesn't say whether the set-up writes the CSRs' high bytes.
         `TXCSR2`'s direction stays as tries 1 to 4 wrote it, and `RXCSR2`
         isn't written.
      5. The SDK polls until `TxPktRdy` reads clear. Try 5 doesn't wait:
         while the bit is set nothing is written, and the packet goes at
         the next interrupt or beat, so the instrument never waits on USB.
      6. The SDK's branch for `TXCSR`'s `IncompTx` isn't decoded. The bit is
         only logged (`tx_log`).
      7. In the handler, whether the chip closes the `sti` gate on entry
         isn't given (Q-10). If it doesn't, `sti` at a group's end restores
         the gate as it was. If it does, sources of higher priority can
         nest sooner, and none of them touch USB.
    - **Layout 17** (1007 fields) adds `try_n` (5), so the decoder names
      the ways by try. The identity is `0.15.0-u3u-t5`.
    - **The owner's run:** a plain power-on, with no keys and no test
      screen. Way 0 shows in large text. Plug into the Mac, play notes both
      ways, unplug. Only if way 0 fails, power on again for ways 1 and 2.
    - **The owner's answer** (docs/prompts/clean-br17-u3u-try5-answer.md):
      the seven gaps' choices are accepted as they are, to be tested first.
      If way 0 fails on the unit, the spec side decodes gaps 1 and 2 first.
      Try 5's file (`e58082c2…`) was checked and flashed.
    - **Try 5 on the unit** (the owner, 2026-11-24, backup
      fm1-20261124-065615; docs/prompts/clean-br17-u3u-final.md): way 0,
      the SDK's steps, works. The Mac's notes play once each at the right
      pitch, the unit's keys send one note-on and one note-off each, and
      the instrument plays on after unplugging. The log shows 8 packets in
      with 18 events (`RXCOUNT1` 4 each, and one of 44 at connect with 11
      events), and 7 packets out of 4 bytes each. There were no stalls,
      drops or give-ups, and "USB gone" was logged at unplug. The loop is
      done.
- **U3-U's final build** (the owner's direction, same prompt).
    - Only way 0 is kept. Ways 1 and 2 are gone, with their second buffer.
      So are the power-on choice of way, its large text, and its log
      lookup (`hw_report_newest`), which puts hw_report.c back as on main.
      The tries' test keys are gone too: KEY7 (the port's spacing) and
      KEY8 (the way out). Nothing else used them, so on the test screen
      they now do what they did before U3-U.
    - The port's spacing is fixed at 10 µs (`USB_PORT_GAP`, 240 units),
      and the list of spacings is gone. Every log record stays.
    - Layout 17 is unchanged, so the decoder reads the final build as it
      read try 5. The fields only the tries used stay in the record:
      `tx_variant` reads 0, `gap_presses` 0, `way_prev` none, and
      `try_n` 5 (the try whose way the build keeps).
    - The identity is `0.15.0-u3u`.
    - The published build is still USB-off (R-USB-1). audio14's packed
      file is byte-identical to the published one, and seams checks that
      a unit build with `SB_USB_MIDI` but without `SB_HW_U3U` stops. The
      owner-only file is still named and marked so.
    - In seams, the `usbmidi` case no longer runs the three chained
      power-ons. The log run now checks that there are no way, spacing or
      out-way records, and that the record reads way 0, spacing 240 and
      try 5. The key run taps KEY7 and KEY8 on the test screen and checks
      that USB is unchanged and still configured.

### 2026-11-25 clean-r2-cleanup: round 2, two builds, a start in milliseconds, a quiet log (R-HW-1, R-USB-1)

Round 2 of the owner's plan to finish small-beeps (docs/prompts/clean-r2-cleanup.md): clean-up and speed. Nothing
new is written on the unit: no new register, no clock or `0x16A00` write, no store format change.

- **Two builds** (section 1). The bring-up flags are gone; `hw_fm1.h` says which build is which.
  - **The release**, `SB_HW_FM1`: the instrument and the log. Published with USB off (R-USB-1: the device isn't
    compiled in and no product ID is in the image), identity `0.16.0-r2`. With `SB_USB_MIDI` it is the owner-only
    release, identity `0.16.0-r2u`.
  - **The test build**, `SB_HW_FM1`, `SB_USB_MIDI` and `SB_HW_TEST`: the release with the bring-up code, identity
    `0.16.0-r2t`. It is owner-only and never published. `SB_HW_TEST` without `SB_USB_MIDI` is refused.
  - **Where each flag's code went:**

    | Flag | Now |
    |---|---|
    | `SB_HW_AUDIO1`, `SB_HW_AUDIO8` to `SB_HW_AUDIO14`, `SB_HW_REPORT`, `SB_HW_PCM16` | folded into `SB_HW_FM1` (every unit build set them). Code only the test build runs is in `hw_test_audio.c` and `hw_test_start3.c`, or under `SB_HW_TEST` where it sits inside a release function |
    | `SB_HW_U3U` | `SB_HW_FM1` with `SB_USB_MIDI` |
    | `SB_HW_HOLD` | `SB_HW_TEST` |
    | `SB_HW_FINDER`, `SB_HW_CORE1_SYSDIV` | deleted with their code (HW-136, HW-138, HW-139; HW-137: the `SYS_DIV` step isn't needed) |

    The mechanical part (cf40f1f5) changed no image: the published audio14 build, U3-U's owner-only build and build
    A came out byte for byte as before. fwtest's `SB_TEST_*` hooks stay.
  - **USB alone between the published and owner-only files**, checked from the build (seams case release):
    - every symbol only the owner-only image has is `usb_midi.c`'s, and none is only in the published one;
    - the published image has neither 1209:0001's bytes nor "small-beeps" in UTF-16.
- **The release's start** (section 2), from TIMER0's start to ready, timed by the app with `sb_now()` (24 MHz
  units). The span before TIMER0 (`sb_start`'s copy and `hw_early`'s panel bring-up) isn't counted, since no counter
  runs that early without a new register.
  - **In fwtest:** ready 2.7 ms on fwtest's clock. Its TIMER0 counts 24 MHz where the chip counts 60, so that is
    about 6.8 ms of fwtest's time. Only the unit's number counts: fill times differed by about 7 times (HW-175).
  - **What the release does:** bands 1 to 3, the window's registers read for the log, interrupts and TIMER0, a
    black frame and the display on. Then the engine; the synth on and ALNK0 started; L2's writes; R2's; the route's;
    the panel's message. The test build's cold-start writes are kept in their order.
  - **Removed from the release** (kept in the test build), with the wait each took in the code:

    | Check | Settled by | Wait it took |
    |---|---|---|
    | The round trip and its LED marks | HW-133 (item 2) | a flash take and give-back, interrupts off |
    | The 5 s hold of the start-up rows | HW-133 | 5 000 ms |
    | The store's power-on counter | HW-133 (item 3) | a flash take, a store write and a give-back |
    | Two watched spins of the tick | HW-133 | 2 × 300 ms |
    | Core 1's release, its marks and its screen | HW-137, HW-175 (the engine fits on core 0) | ≤ 100 ms, then to 1 s after the release |
    | The pattern and the wait for the test screen | HW-176, HW-177 (the start from cold works) | to beat 500, then 20 ms |
    | U2's readings, and the wait for the second | HW-177 | to beat 1 000 |
    | The `0x16A00` read | HW-180, HW-183 | reads only |
    | HOME's test-screen start | HW-176, HW-177 | none (a read) |
    | L2's link watch, with the matrix check before and after | HW-160 | 1 000 ms |
    | ALNK0's and each key stage's core 1 marks | HW-175 (as a check) | 100 ms each, at ALNK0, L2 and R2 |
    | R2's control sample | HW-162 | 10 ms |
    | The route's sample and its matrix checks | HW-162, HW-164 | 100 ms; refused with a key held |
    | 15 records on every power-on | HW-176, HW-177 | a flash erase and program each |
    | ARP's step record | HW-179, HW-180 | the panel's REC (the release's REC does nothing) |
    | The tone fallback after late halves | HW-175 | none (the release keeps the synth and logs each underrun) |

    The route's check refused the route while a key was held. That would leave the owner's run (keys tapped from
    power-on) silent, and HW-162 and HW-164 settle the route itself. The one check kept is a read: `CLK_CON2` bit 9
    set stops the link (HW-160), so the release then writes a problem record ("L2 bit 9") and says NO SOUND.
  - **Kept:** the USB cable check, as U3-U has it.
  - **What no entry settles:** every start on the unit so far had at least 100 ms between ALNK0's start and L2's
    writes (core 1's marks), and the release has microseconds there. HW-175 settles the marks as a check, not that
    gap. No delay is added. If the release is silent on the unit, this gap is the first suspect.
  - **The problem records follow counts taken again after every record,** so a record's own flash write (which
    may hold the audio off on the unit) never reports itself. The out ring's drops count only while the host's
    frames run: after an unplug the device stays configured (HW-183) and the ring fills.
- **The release's log** (section 3), layout 18: one summary record a power-on, "Summary", written once the start is
  done, and a record for each problem, at most 16 a power-on.
  - **The summary's fields:** each stage's time in µs (interrupts on, engine, ALNK0, L2, R2, the route, the panel,
    ready), the problems written and not written, the beat, the audio's blocks, underruns and longest fill, the
    storm guard, the route, both stacks' unused bytes, and in the owner-only release the USB device's record whole.
    The log's own health comes last.
  - **Problem records:** "Underrun" when the count rises; "USB give-up"; "USB stall"; "USB drop" (MIDI in's ring
    full, or the out ring); "Stack low main" or "Stack low irq" under 256 bytes; "L2 bit 9".
  - **Not written:** a fault or trap halts with the screen red and no record, because writing the flash from a trap
    isn't safe. A store error can't happen: the release, like U3-U, doesn't boot the store on the unit (a question
    for the owner).
  - **The test build** keeps today's records (layout 17).
  - **The decoder** reads layout 18 in both forms (the field count tells them apart) and prints the start's stages.
    tests/test_report_decode.py makes a record of every layout from 6 on, and checks that each reads back named and
    whole, since no seams case writes the older layouts any more.
- **hw_audio.c** (section 4). It was 5 985 lines; it is now 711.
  - **What the release keeps there:** the output path (`tone_block`, `synth_fill`, `pack16`, the soft clip, MASTER's
    gain ramp, the storm guard), the SARADC service for MASTER (converting channel 4 alone in the release, as the test
    build does while the scan is held: HW-169, HW-170), `report`, `usb_midi_note`, and the release's start, summary
    and problems.
  - **`hw_test_audio.c`** (4 775 lines, built only with `SB_HW_TEST`) has the rest: the steps and pages, L, D, H, I,
    K, J, the sweeps, R2's and the route's checked forms, U2, ARP's step log, the guide and the test screen's keys.
  - **hw_start3.c** is split the same way: the release keeps the step row, the bands' helpers, the flash take and
    give-back, the window read and the ADC pins (219 lines). `hw_test_start3.c` has the round trip, the store
    counter, core 1, the holds and the test screen's rows and sweeps. Core 1's loop (`hw_core1.S`) and start.c's U2
    and P reads are test-only too.
  - **How the split was made:** by reachability from the release's entry points, reading each item as the release
    sees it (`unifdef -USB_HW_TEST`). `hw_audio_int.h` and `hw_start3_int.h` hold each pair's shared macros and names.
  - **Kept as it was:** the Bell start and ARP's preset (UP, 1/16, 2 octaves) stay in the release. They are
    starting state, not checks, and the owner's ARP step needs them.
  - **Images:** the published release is 59 392 bytes (audio14's was 112 744), the owner-only 64 996, the test
    118 372.
  - The audit's matched code and targets weren't opened. The audit is re-run after this round.
- **fwtest 0.15.0** (section 5): pinned here, not in #254, whose first run failed seams case audio13 on it (U2's
  readings expect the lines to hold still). This PR removes that case. usbmidi expects no problem, and expects USB
  not to start without `--usb`.
- **Seams** (section 6, with #254's four parts):
  - **Cases removed:** finder, hw3, core1, audio1 to audio14. Their builds are gone, and the test build covers what
    is left of their code in case test.
  - **hw** is the release's start.
  - **report1** is the release's log: one Summary a power-on, the next numbered on, the ring's wrap, a failed write
    retried.
  - **release** and **test** are new; nowrace and usbmidi use round 2's builds.
