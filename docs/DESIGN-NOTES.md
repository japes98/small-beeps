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
