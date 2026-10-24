<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# fwtest: the harness, as a black box

`fwtest` runs a raw image on an emulated board for a given number of
emulated milliseconds, feeds it timed inputs, and saves what it did:
memory, the screen, the LEDs, the flash chip, the audio, instruction counts.
It is the firmware side's only window into the emulator, and this page is
its whole manual. It says what fwtest does, not how the emulator does it.
Facts about the chip itself (registers, pins, timings, the panel's layout)
belong in `HARDWARE-SPEC.md`; ask for one through docs/SPEC-REQUESTS.md.

fwtest is a model. Where it and `HARDWARE-SPEC.md` disagree, the spec is the
authority on the hardware; report the difference as a spec request.

## Running it

The firmware side runs fwtest only through `tools/fwtest`, which runs the
published container image pinned by digest in `config/fwtest-image`
(R-SEP-3). It needs Docker; the image runs as linux/amd64 on any host.

```sh
tools/fwtest run out/build/app.bin --ms 100 --out out/t1 --ram 0x01c00000:64@end
tools/fwtest suite tests/fw/boot.suite --out out/suite
tools/fwtest version
tools/fwtest --image        # the pinned image reference
```

- Run it from the repository root. The current folder is mounted read-only,
  so every input path (image, script, flash file, golden folder, suite) must
  be inside it. `--out` is created and mounted writable on its own, and must
  be empty or not exist yet.
- The container has no network and runs as your user.
- After a run, `tools/fwtest` adds `runner.txt` to the output folder, naming
  the image it ran and whether it was the pinned one. A test record that
  used fwtest names that image; every record also notes the pinned image in
  its environment.

## The raw image

| Rule | Value |
|------|-------|
| Format | A flat binary: the bytes of the code window, from its first byte. No header, no ELF. |
| Load address | The image's first byte is at `0x02000000`, the start of the code window. Link it there. |
| Entry | Core 0 starts at `0x02000000`: the image's first instruction. |
| Size | 1 byte to 1 032 192 bytes (1 MiB less 16 KiB). |
| The flash chip | 1 MiB. Erased (all `0xFF`) unless `--flash FILE` gives its first bytes. The image is then written into it at offset `0x4000`, as an installed image sits. |
| Past the image | Reads in the code window after the image's last byte show the flash chip: window address `0x02000000 + n` shows chip offset `0x4000 + n`. Changes the image makes to the chip (erase, program) show through the window, also over the image's own bytes. |
| Writes to the window | Ignored (and listed as unmodelled accesses). |
| RAM | 1 MiB at `0x01C00000`, all zero at the start. Other memories, and what the real chip has: `HARDWARE-SPEC.md`. |
| Core 0 at the start | User mode. Every register is 0, both stack pointers included (set your own stacks first), except `r0` = `0x01C7FC00`: a 64-byte block of zeros whose first word holds `0x01C7FC40`. |
| Core 1 | Does not run until the image releases it (`HARDWARE-SPEC.md` says how). Then it runs alongside core 0 (below, "Time"). |

## Time

- Emulated time starts at 0 when the image starts. One instruction of core 0
  takes one cycle; there are 240 000 cycles in an emulated millisecond.
- Every instruction counts the same: the hardware float instructions
  (`-mfprev1`) too, divide included. fwtest computes them as IEEE 754
  single precision, rounding to nearest even and keeping subnormals; no
  float condition raises an exception or sets a flag (`HARDWARE-SPEC.md`,
  HW-63, gives the edge cases).
- Once released, core 1 also runs one instruction a cycle. The cores take
  turns: core 0 runs 1024 instructions, then core 1 as many cycles as
  passed. They share memory with no caches and no contention, so neither
  slows the other, but a store by one core reaches the other core's loads
  up to one turn (1024 cycles) later. Core 1 takes the interrupts its own
  enable words enable (HW-64).
- Everything happens at exact emulated times, and the outputs are
  deterministic (below), but **while core 0 waits, fwtest moves time ahead**,
  so that waiting costs (almost) no instructions and instruction counts
  measure work. The rules for that, and what they do to captures, are
  exact; they follow.

### When fwtest treats core 0 as waiting

Two things, and nothing else, count as waiting:

1. **The wait-for-interrupt instruction**, executed by core 0 while no
   interrupt is pending. Time jumps to one cycle before the next scheduled
   event (below). With nothing scheduled, time doesn't jump.
2. **Polling the free-running timer**: reading its count (HW-13 in
   `HARDWARE-SPEC.md`, the 24 MHz time base), outside an interrupt handler
   of core 0, for the third time or more in a row with each read coming
   within 64 cycles (64 instructions of core 0) of the one before. On each
   such read, time jumps ahead by up to 20 µs, and never past one cycle
   before the next scheduled event. The read then returns the count for
   the new time.
   - **Only the spacing of the reads matters.** What the loop does between
     them doesn't: stores to RAM, arithmetic, reads of other registers, a
     call. A loop that reads the count every few instructions *and* writes
     a heartbeat to RAM on every pass is waiting, by this rule.
   - A read more than 64 cycles after the previous one starts the count
     again, so a loop whose reads are at least 64 instructions apart is
     never treated as waiting.
   - Reads made while core 0 is in an interrupt handler are ignored: they
     neither count, nor jump, nor break a sequence.
   - Reads by core 1 count in the same sequence as core 0's: the rule
     looks at reads of the count, not at which core made them.
   - Other timers' counters, their pending flags, and RAM flags are not
     part of this rule. Polling them never moves time ahead.

**Scheduled events** are what the emulated chip and the script have coming
next:
- the end of a timer period;
- an audio half-buffer finishing;
- a transfer completing;
- a MIDI byte arriving;
- an encoder contact changing;
- a script event.

They count whether or not their interrupt is enabled. **Captures, the end
of the run and the watchdog are not scheduled events:** a jump never stops
for them.

### What that does to captures

- fwtest looks at the board between runs of core 0 instructions. Each run
  is at most 1024 instructions, and no longer than the instructions that
  would reach the next capture (or the end of the run) at one cycle each.
  Captures, the watchdog, halts and the end of the run are checked only
  between runs. A capture is taken at the first such stop at or after its
  time.
- **While core 0 is busy (not waiting), captures are exact:** taken at the
  first instruction boundary at or after the time asked.
- **While core 0 waits, a capture can come late**, because every jump
  inside a run moves time without using up the run's instructions:
  - Polling the timer: each read can add up to 20 µs. A loop that reads the
    count every *k* instructions can move up to about 1024 / *k* × 20 µs in
    one run, for example 2 ms when *k* is 10. A capture asked for at *t*
    can be taken that much after *t*.
  - Wait-for-interrupt: each wait jumps to the next scheduled event. A run
    that wakes on every event can cross many of them, for example several
    milliseconds of 100 µs interrupts.
- What is late is the moment the capture is taken, not its label. RAM and
  screen captures show the state at the moment fwtest took them, but are
  named for the time asked (`ram-…-10ms.bin`). `leds.csv`'s `ms` column is
  the time asked, while each duty value covers the real time since the
  previous sample. The end of the run, and so every `end` capture, can come
  late in the same way. `result.json`'s `emulated_ms` says when the run
  really ended.
- The watchdog compares its word between runs, so a hang is noticed up to
  one run late.
- None of this varies between runs: the same image, script and options give
  the same late times, byte for byte, everywhere.

### Getting exact timing

- **Don't wait around the times you capture.** Keep core 0 busy then, for
  example by spacing reads of the timer's count at least 64 instructions
  apart, or by waiting on something else: another timer's pending flag, or
  a RAM flag that an interrupt handler sets. Captures are then exact.
- **Or let the image record the time itself.** Store the timer's count (or
  your own tick count) next to what you capture, and check the capture
  against that stored time instead of the time asked. The M0d firmware's
  beacon does this (docs/DESIGN-NOTES.md).
- **For the end of a run**, read `emulated_ms` in `result.json`.
- Instruction counts (`instructions` in `result.json`, `ipb.csv`) do not
  include the time jumped over: a waiting image's counts stay small and
  stable.

### Timers and their acknowledge

The write to a TIMER0 to TIMER3 control register that acknowledges its
interrupt also restarts that timer's count and its period from the moment
of the write. So the time between two of its interrupts is the
period programmed plus the time from the interrupt to the acknowledging
write: about one tick of the 24 MHz time base when the handler acknowledges
first, more when it acknowledges later (`HARDWARE-SPEC.md`, HW-48). To
measure a period exactly, acknowledge first, or subtract the time the
handler took to reach its acknowledge. Whether the chip does the same is an
open question in `HARDWARE-SPEC.md`.

## The LCD

The panel's transfers finish at once: SPI1's done bit always reads 1, and
a DMA transfer of any length up to a whole screen in one `CNT` write
(115 200 bytes) draws (`HARDWARE-SPEC.md`, HW-29, HW-58). SPI1's `CON`
reads back as last written. A transfer, by DMA or a single byte, that
finishes while `CON` bit 13 is set raises interrupt source 16; with bit 13
clear it raises nothing. A write with bit 14 set acknowledges it, and like
every write it sets the other bits as written: a write of bit 14 alone also
clears bit 13. A transfer that finished with bit 13 set stays pending until
acknowledged, even if bit 13 is cleared afterwards (HW-59).

From fwtest 0.2.0. Before it, a write to `CON` could set bits but never
clear them: once any write had set bit 13, every later transfer raised
source 16, whatever `CON` was written to afterwards (SR-3).

## The command line

```
fwtest run IMAGE --ms MS --out DIR [options]
fwtest suite FILE --out DIR
fwtest version
```

`run` options:

| Option | What it does |
|--------|--------------|
| `--ms MS` | Run for MS emulated milliseconds (up to three decimals). Required. |
| `--out DIR` | Write the outputs here. Required; must be empty or new. |
| `--script FILE` | Timed inputs (below). |
| `--flash FILE` | The flash chip's first bytes (at most 1 MiB); the rest is erased. |
| `--ram ADDR:LEN@WHEN` | Save LEN bytes of memory at ADDR at WHEN. Numbers in decimal, or hex with `0x`. Only RAM (main RAM and the other RAM banks `HARDWARE-SPEC.md` lists) can be saved; anything else is a usage error. Repeatable. |
| `--lcd WHEN` | Save the screen as a PNG at WHEN. Repeatable. |
| `--leds-every MS` | Sample the LEDs every MS into `leds.csv`. |
| `--flash-out` | Save the whole flash chip at the end (`flash.bin`). |
| `--wav` | Save the audio output (`audio.wav`). |
| `--ipb` | Save instructions per audio block (`ipb.csv`). |
| `--console` | Save the bytes written to the chip's debug message register (`console.txt`; `HARDWARE-SPEC.md` names it). |
| `--watchdog ADDR:MS` | A hang if the 32-bit word at RAM address ADDR stays the same for more than MS ms. |
| `--halt-ok` | A halt counts as success (exit 0). |
| `--golden DIR` | Compare the outputs with the golden files in DIR (below). |

WHEN is a time in ms (`10`, `2.5`) or `end`. The run ends at `--ms`, or
earlier on a fault, halt or hang; `end` captures are taken then.

## Input scripts

A text file, one event per line; `#` starts a comment. Times are emulated
milliseconds with up to three decimals. Events at the same time happen in
the order written.

```
# time   event
2        key 12 down
4        key 12 up
6        key 5 tap 3          # down at 6 ms, up at 9 ms (default hold: 50 ms)
10       enc 0 +2             # encoder 0, two detents clockwise
12       enc 3 -1             # one detent anticlockwise
15       pot 300              # the pot now reads 300
20       midi 90 3c 64        # bytes into the MIDI input, in this order
```

| Event | Meaning |
|-------|---------|
| `key N down`, `key N up` | Key N (0 to 40) pressed or released. |
| `key N tap [HOLD]` | Pressed, then released HOLD ms later (default 50). |
| `enc N +C`, `enc N -C` | Encoder N (0 to 6) turned C detents (1 to 1000); `+` is clockwise. Each detent is four contact changes, 2 ms apart, the first at the event's time. |
| `pot V` | The pot's reading becomes V (0 to 1023). It reads 900 until a script sets it. |
| `midi HH ...` | Bytes (two hex digits each) arrive at the MIDI input one after another, at the wire's pace: one byte every 320 µs, the first 320 µs after the event's time. |

Key, LED and encoder numbers are fwtest's own. `HARDWARE-SPEC.md` maps them
to the panel and to the key matrix.

## Outputs

All in `--out`. A run writes only what it was asked for, plus
`result.json` and `junit.xml`.

| File | Contents |
|------|----------|
| `ram-AAAAAAAA-L-WHEN.bin` | The bytes saved by `--ram` (address as 8 hex digits, length in hex, WHEN as `10ms`, `2.500ms` or `end`). |
| `lcd-WHEN.png` | The screen, 240 x 240, 8-bit RGB, whatever the display's on/off state. Each pixel is the panel's 16-bit colour (5-6-5 bits) with each channel scaled to 8 bits (`c * 255 / 31`, or `/ 63` for green). |
| `leds.csv` | Header `ms,led0,...,led40`, then one row per sample: the sample's time, and for each LED the share of the time since the previous sample (or since the start) that it was lit, in thousandths (0 to 1000, rounded). LED N belongs to key N. |
| `flash.bin` | The flash chip (1 MiB) at the end of the run. |
| `audio.wav` | The audio output: 16-bit PCM, stereo, the header says 44 100 Hz. Every sample the output played, in order. How the firmware feeds the output, and its exact rate: `HARDWARE-SPEC.md`. |
| `ipb.csv` | Header `block,end_ms,core0,core1`, then one row per audio block (each time the output finished one half of its buffer): its number, the time it finished, and the instructions core 0 and core 1 executed since the previous block (the first row: since the start). Core 0's count is exact; core 1's is counted at a granularity of 1024 core-0 instructions. |
| `console.txt` | The debug console bytes, as written. |
| `result.json` | What happened (below). |
| `junit.xml` | JUnit XML: a test case `run` (fails on a fault or hang, and on a halt without `--halt-ok`), and one `golden NAME` per golden file. |

`result.json` holds: `fwtest` (version and the emulator build it carries),
`image` (file name, size, SHA-256), `script_sha256`, `run` (`outcome`,
`detail`, `emulated_ms`, `instructions` per core, `midi_bytes_dropped`,
`unmodelled_accesses`, and every output's name, size and SHA-256), `golden`
(each file's `match` or `mismatch` and why), and `exit_code`.

- `midi_bytes_dropped`: bytes that arrived while the image had no MIDI
  receiver set up, or more than about a second's worth waiting.
- `unmodelled_accesses`: addresses the image read or wrote that fwtest does
  not model (reads give 0, writes are dropped), with counts, up to 256.
  Usually a sign the image touched something unexpected; if the hardware
  has something there, ask for it in a spec request.

## Outcomes and exit codes

| Exit | Outcome | When |
|------|---------|------|
| 0 | completed | Ran for `--ms`, and every golden file matched. (Also a halt with `--halt-ok`.) |
| 1 | golden mismatch | A golden file differs (beyond its tolerance), or an output it names is missing. |
| 2 | usage error | Bad arguments, an unreadable or oversized image, a bad script, `--out` not empty, a capture outside RAM. Nothing ran. |
| 3 | fault | A core met an instruction it cannot decode or the emulator does not implement, or its program counter left every memory that can hold code (the image, RAM, the other RAM banks). |
| 4 | halt | Core 0 executed a jump to itself with interrupts disabled: a deliberate stop. The run ends there. |
| 5 | hang | The `--watchdog` word did not change for longer than its time. |

When several apply, the first in this order wins: 2, 3, 5, 1, 4, 0. Captures
and `result.json` are written for 1, 3, 4 and 5 too. Any other exit code
means fwtest itself failed.

### Faults and CPU exceptions

fwtest raises no CPU exception: no condition makes interrupt source 0, 1
or 2 pending, so an image's exception handler is never entered by a fault.
What happens instead (`HARDWARE-SPEC.md`, HW-52, says it with the measured
values):

- Misaligned loads and stores complete. A word load or store uses the 4
  bytes at the address given; a halfword load from an odd RAM address
  ignores the lowest address bit.
- Reads outside every memory and register fwtest models give 0, writes
  there are dropped, and both are listed in `unmodelled_accesses`; so are
  writes to the code window, which are dropped too.
- An integer division by zero gives 0 (a float one gives an infinity or a
  NaN, HW-63).
- An instruction fwtest cannot decode ends the run as a fault (exit 3).
  fwtest may stop at the start of the straight-line code that holds it,
  before any of that code has run, and `result.json` then gives that
  address as the fault's `pc`; to have code run up to it, put the
  instruction behind a call or a branch.
- A jump outside every memory runs what fwtest reads there (zeros) for up to
  1024 instructions, until fwtest next checks the program counter, and then
  ends the run as a fault.

## Instructions

fwtest runs the code the pinned toolchain's compiler emits for the
firmware's flags (`-target pi32v2 -mcpu=r3 -mfprev1`, tools/build.sh);
the two gaps the checks below found run since 0.4.0. That was checked on a corpus, not proven for
every instruction (SR-7). The corpus: the firmware at `18d9459`, the
vendored Plaits and the demo's C++ built with the firmware's CPU flags,
and several hundred small C functions written to vary types, operations
and pointer patterns, each at `-Os` and `-O2`. Two checks ran in fwtest
0.3.0, each unit on its own:

- every distinct disassembled unit of the corpus's objects (13 981; a
  dual-issue pair is one unit; some are constants in the code, decoded
  as if they were instructions);
- every form in the compiler's assembly output (660, registers and numbers
  abstracted), with each register slot set in turn to r0 to r15 (register
  pairs to each even-odd pair) and each number to values from 0 and ±1 up
  to the 32-bit limits, as far as the assembler accepts them: 34 437
  distinct encodings.

They show only that fwtest decodes and runs each one, not that it
computes what the chip does. An instruction neither check held can still
end a run as a fault ("Outcomes and exit codes"): report it as SR-7 was,
with its bytes and the smallest image that shows it.

No known gaps since fwtest 0.4.0. Until 0.3.0 two forms ended the run as
a fault, "an instruction the emulated CPU cannot decode"; 0.4.0 runs them,
and one more change makes dual-issue pairs behave as the compiler expects:

- **Rotate by a register.** `rD = rS <> rT` (bytes `cc e1`, then two
  bytes naming the registers; `cc f1` as a pair's head), for every
  register. It rotates right by rT: the compiler emits
  `(x << s) | (x >> (32 - s))` as `rT = 32 - rT` then this, and
  `(x >> 7) | (x << 25)` as the rotate by a constant `rD = rS <> 7`. By
  0 it leaves the value (the compiler's masked rotate relies on that). An
  amount of 32 or more is taken mod 32, which the compiler's code doesn't
  show (it masks such amounts itself): don't rely on it.
- **A 4-byte push or pop of any register list.** `[--sp] = {list}` (bytes
  `d8 e8`, then the 16-bit mask, bit k for rk) and `{list} = [sp++]`
  (`d4 e8`, then the mask), without `rets` or `pc`: every list, for
  example `[--sp] = {r5-r1}`, `{r11-r6} = [sp++]` or `{r15} = [sp++]`, as
  the lists from r0 already ran. A push moves sp down by 4 a register and
  the lowest register takes the lowest address; a pop reads them back the
  same way. The compiler emits only lists from r0 (in interrupt
  handlers); lists above r0 behave the same by analogy, not checked
  against the chip.
- **Dual-issue pairs** (`A #` then `B`, as the toolchain's disassembler
  prints them): the pair's second half sees the registers as they were
  before the head, and the head's result is there after the pair. The
  compiler relies on this (in our firmware, a pair whose second half
  stores a byte back through the base register the head changes). Until
  0.3.0 some 4-byte ALU forms as a pair's head wrote their result at
  once, so the second half saw the new value: which ones depended on the
  operation and the registers (of one of each family with the same
  registers, two: `r6 = r5 ^ (1 << r3) #` and `r6 = r5 >>> r3 #`; also,
  for example, `r0 = r8 | (1 << r12) #`).

None of the three changed any output of the firmware's suite at `cdfd067`.

### Block moves with a register base

Since 0.3.0 fwtest runs all eight modes of this 4-byte instruction (bytes
`xm eb`, then a 16-bit register mask; HARDWARE-SPEC.md HW-66). As the
toolchain's disassembler writes them, with n registers in the list:

| First byte | Form | Words moved | The base after |
|------------|------|-------------|----------------|
| `0x0N` | `{list} = [rN+]` | rN to rN + 4n - 4 | unchanged |
| `0x1N` | `{list} = [rN++]` | rN to rN + 4n - 4 | rN + 4n |
| `0x2N` | `[rN+] = {list}` | rN to rN + 4n - 4 | unchanged |
| `0x3N` | `[rN++] = {list}` | rN to rN + 4n - 4 | rN + 4n |
| `0x4N` | `{list} = [-rN]` | rN - 4n to rN - 4 | unchanged |
| `0x5N` | `{list} = [--rN]` | rN - 4n to rN - 4 | rN - 4n |
| `0x6N` | `[-rN] = {list}` | rN - 4n to rN - 4 | unchanged |
| `0x7N` | `[--rN] = {list}` | rN - 4n to rN - 4 | rN - 4n |

- The lowest-numbered register in the list takes the lowest address.
- Every address comes from the base as it was before the instruction. A
  base that is also in a loaded list, in a mode without `++` / `--`, ends
  with its loaded word (the compiler relies on this); in a write-back mode
  it ends with the written-back address. A store writes the base's
  value from before the instruction.
- An empty list moves nothing (and a write-back mode leaves the base as
  it was).
- The compiler emits the modes without `++` / `--` (`0x0`, `0x2`, `0x4`,
  `0x6`). The write-back modes, a write-back mode whose base is in its
  list, and an empty list are not established for the chip (Q-19): avoid
  relying on them.

Before 0.3.0 the four modes below the base (`0x4` to `0x7`) ended the run
as a fault, "an instruction the emulator does not implement".

## Golden files

`--golden DIR`: every file in DIR is a golden file, compared with the output
of the same name. A golden file without such an output is a mismatch. Outputs
without a golden file are not compared.

- **Exact by default:** byte for byte. Every fwtest output is deterministic,
  so exact is right unless the firmware's own behaviour is meant to vary.
- **Tolerances**, where an output is meant to be approximate: a text file
  `NAME.tolerance` beside the golden file, one line:
  - `pixel-diff N` (a `.png`): same size; each colour channel of each pixel
    within N.
  - `sample-diff N` (a `.wav`): same format and length; each sample within N.
  - `rel-percent P` (a `.csv`): same lines and fields; text fields equal;
    each integer within P percent of the golden value (at least 1). For
    example `ipb.csv` with `rel-percent 3` is the performance gate R-PERF-2
    will use.
- Golden PNG and WAV files compared with a tolerance must be ones fwtest
  wrote. To make a golden file, run once, check the output by hand, and copy
  it into the golden folder in the same commit as the test.

## Suites

`fwtest suite FILE --out DIR` runs several cases. Each line of FILE:

```
# NAME  EXPECT     IMAGE                 run options (paths relative to FILE)
boot    completed  ../out/build/app.bin  --ms 50 --ram 0x01c00000:16@end --golden golden/boot
stop    halt       images/stop.bin       --ms 10
```

NAME (letters, digits, `-`, `_`) is the case's output folder under DIR.
EXPECT is the outcome expected: `completed`, `halt`, `fault` or `hang`. A
case passes when its outcome is EXPECT and every golden file matches. DIR
also gets `result.json` (every case's result) and `junit.xml` (one test case
per suite case). The exit code is 0 when every case passes, 1 otherwise, 2
on a usage error.

## Determinism

The same image, script, options and fwtest build give byte-identical outputs
on every run and every machine: no host time, no randomness that isn't
seeded the same way every run, nothing from the environment, no host paths
in the results. CI runs the harness's own suite twice in fresh containers
and compares every output byte (C-HARNESS-DET). If two runs of yours ever
differ, that is a bug in fwtest: report it.

## Versions

`fwtest version` prints fwtest's version and the emulator build it carries;
`result.json` has both. The image is identified by its digest. When the
harness changes, a pull request moves `config/fwtest-image` to the new
digest, so a firmware test always names the exact runner it used.

- 0.4.0: the rotate by a register and the 4-byte push and pop of any
  register list run; a dual-issue pair's head among the 4-byte ALU forms
  holds its result until after the pair ("Instructions"). The emulator is
  the F-Emulator app's but for its own raw-image loader
  (docs/EMULATOR-PARITY.md).
- 0.3.0: the block moves below a base register run, all eight modes
  of the block moves are listed (SR-7; "Instructions").
- 0.2.0: SPI1's `CON` writes set and clear bits as written ("The LCD").
- 0.1.0: the first published image.
