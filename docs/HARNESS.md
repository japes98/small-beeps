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
| Core 1 | Does not run until the image releases it (`HARDWARE-SPEC.md` says how). Then it runs alongside core 0. |

## Time

- Emulated time starts at 0 when the image starts. One instruction of core 0
  takes one cycle; there are 240 000 cycles in an emulated millisecond.
- When core 0 waits (the wait-for-interrupt instruction, or a tight loop
  outside an interrupt handler that does nothing but read the chip's
  free-running timer), time jumps ahead to the next timed event: the next
  interrupt source, script event or capture. Waiting therefore costs (almost)
  no instructions, and instruction counts measure work.
- Everything happens at exact emulated times. Captures and checks are taken
  at the first instruction boundary at or after the time asked; fwtest stops
  to look at least every 1024 core-0 instructions, and exactly at each
  capture time while core 0 is busy.
- While core 0 waits, a capture can come late. Each wait can move time
  ahead to the next timed event, and fwtest looks only between runs of up
  to 1024 instructions, so a capture (an LED sample, the watchdog, the end
  of the run) can be taken several milliseconds after the time asked when
  the image waits often, for example between interrupts every 100 µs.
  `result.json`'s `emulated_ms` says when the run really ended. To capture
  at an exact time, keep core 0 busy (not waiting) around it.

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
