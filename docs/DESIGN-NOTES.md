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
- **The part's rules** (HW-78): a write enable before every erase and
  program, a page program never past its page, the end of each waited for
  on the status register's WIP bit, never by a delay. Start-up reads the
  JEDEC ID, and a part other than the P25Q80H (HW-76) is read but never
  written (`STORE_ERR_PART`), since its rules and times are not known.
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
