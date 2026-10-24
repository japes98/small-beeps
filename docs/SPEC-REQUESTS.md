<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Spec requests

How the firmware side (clean) asks the spec side (exposed) for a hardware
fact it needs, and how the answer comes back, without anything else passing
between them (CONTRIBUTING.md, "Roles").

## Asking (firmware side)

Add a request at the end of "Requests" below, by pull request:

- a number (`SR-1`, `SR-2`, ...; never reused);
- the date asked;
- the question: one fact about the hardware (an address, a bit, a pin, a
  timing, a protocol step, a limit), asked as narrowly as you can;
- why it is needed: what the firmware is trying to do, the milestone, and
  what you already tried or read (HARDWARE-SPEC.md sections, the JieLi SDK,
  FM-1-RE's documents, datasheets, your own black-box runs in fwtest);
- the status `open`.

Don't ask how another firmware does something, and don't paste or describe
any material you aren't allowed to read. A question about fwtest's
behaviour (a capture, an exit code, an option) is not a spec request: open
an issue or a pull request against docs/HARNESS.md.

## Answering (spec side)

- Answer by adding the fact to `HARDWARE-SPEC.md`, with its source, as
  every fact there has (M0c's rules: facts only, never code or code
  structure; a fact whose only source is the emulator is marked so).
- Then set the request's status to `answered`, with a link to the section,
  in the same pull request. Nothing else goes in the request: no code, no
  explanation of how any other firmware or the emulator does it, no
  excerpts.
- If the fact isn't known, say so (`unknown`), with what would settle it
  (a probe on real hardware, a datasheet). If answering would take
  something the spec side may not pass on, say `declined` and why, in
  general terms.
- The spec side's text discipline applies to the whole exchange
  (CONTRIBUTING.md, "Spec-side text discipline"; C-SEP-TERMS checks it).

## Template

```markdown
### SR-<n>: <the question, in a few words>
- Asked: <YYYY-MM-DD>, <who or which session>
- Question: <one fact, asked narrowly>
- Why: <what the firmware needs it for; what was tried or read>
- Status: open | answered (HARDWARE-SPEC.md, "<section>") | answered in part (..., open: Q-n) | unknown | declined
- Answered: <YYYY-MM-DD>, <who or which session>
```

## Requests

### SR-1: What raises the exception interrupt (source 1)
- Asked: 2026-10-22, session M1 (firmware side)
- Question: (a) On the chip, which conditions make the core raise interrupt
  source 1 (`IRQ_EXCEPTION_IDX` in the SDK's `hwi.h`): for example a
  misaligned access, an access to an unmapped address, a write to the code
  window, an undecodable instruction, a divide by zero, a stack limit; and
  what `EMU_CON` and `EMU_MSG` (`csfr.h`, the `q32DSP` block) report or
  enable for it. (b) Whether fwtest raises source 1 for any of them, or
  could, so that a firmware test can make a real CPU fault and see its
  handler run.
- Why: M1 reports a fault over the debug channel and halts cleanly. The
  handler is installed for sources 0 to 2, but nothing in fwtest reaches
  it: in our own runs a misaligned word load, a read of an address outside
  every memory the spec lists, and a write to the code window completed
  (the last two listed as unmodelled accesses), and an undecodable instruction ended the run with fwtest's
  own fault outcome before any handler ran. HARDWARE-SPEC.md lists no
  exception source (HW-19 names the SDK's `hwi.h` for the rest). Until
  this is answered, M1 tests its fault path with a stack guard it checks
  itself, and the CPU-fault requirement stays open.
- Status: answered in part (HARDWARE-SPEC.md, "10. CPU exceptions (SR-1)":
  (a) in HW-49, HW-50 and HW-51; (b) in HW-52: fwtest raises source 1 for
  none of the conditions, and doesn't model it because the sources don't
  establish enough). Open: Q-14.
- Answered: 2026-10-22, session SR-1-SR-2 (spec side)

### SR-2: Setting the system clock on the chip
- Asked: 2026-10-22, session M1 (firmware side)
- Question: On the chip, which registers and steps set the PLL and the
  system (core) clock from the 24 MHz reference (HW-11), which core clock
  rates are supported, and what the clock is when an installed app starts
  (before it changes anything). This is Q-2.
- Why: M1 sets the clocks the firmware runs at. In fwtest the clock is
  fixed at 240 MHz and clock registers have no effect (HW-11), and HW-10
  warns that one bit of `SYS_DIV` releases core 1 in fwtest, so M1 writes
  no clock register: it measures the core clock against the 24 MHz time
  base (TIMER4, HW-13) instead, and expects 240 MHz. Real hardware needs
  the set-up; `WL82.h` names the clock block's registers but not their
  use.
- Status: answered in part (HARDWARE-SPEC.md, "11. The clocks on the chip
  (SR-2, real hardware)": HW-53, HW-54). Open: Q-2 (the PLL's registers,
  the steps, the clock at app start).
- Answered: 2026-10-22, session SR-1-SR-2 (spec side)

### SR-3: The panel's wiring and SPI1's set-up on the chip; source 16 in fwtest
- Asked: 2026-10-22, session M2 (firmware side)
- Question: (a) On the chip, how SPI1 must be set up to drive the panel:
  its `CON` bits (mode, direction, enable) and `BAUD` (the clock it gives,
  and the fastest the panel takes), which pins carry its clock and data and
  the panel's chip select, and the `JL_IOMAP` selection and port set-up
  (direction, drive) for them and for PC8 (HW-30). (b) Whether the panel
  has a reset pin and a backlight pin, which, and their levels. (c) The
  panel's place in the controller's 240 x 320 memory (any row or column
  offset) for each `MADCTL` orientation, which orientation shows the
  picture upright as the FM-1 is held, and whether the panel needs display
  inversion (`0x21`) to show colours right. This is Q-6. (d) The longest
  transfer one write of `JL_SPI1->CNT` may ask for on the chip (the
  counter's width or limit). (e) In fwtest: a DMA transfer started with
  `CON` bit 13 clear still raises source 16 at its end, whatever the last
  write to `CON` held (our runs); HW-29 says bit 13 makes a finished
  transfer raise it. Which is right for the chip, and what fwtest does
  for single bytes written to `BUF`.
- Why: M2 brings up the panel and sends whole frames by DMA. In fwtest no
  set-up is needed (HW-29, HW-30), so M2 writes no SPI1 `CON` set-up bits,
  no `BAUD`, no pins, no reset or backlight, and leaves inversion off; it
  sends whole frames as 16-row chunks (7 680 bytes) because only 480-byte
  transfers are confirmed (E-5). Real hardware needs all of (a) to (d).
  For (e), the firmware's handler acknowledges a transfer it didn't chain,
  which is right under either behaviour, but the spec and fwtest disagree.
  Read: HARDWARE-SPEC.md sections 5 and 3, Q-6, the ST7789V datasheet
  (P-11, P-22), and `WL82.h`'s `JL_SPI_TypeDef` and port registers.
- Status: answered in part (HARDWARE-SPEC.md, "12. The LCD on the chip,
  and SPI1 in fwtest (SR-3)"): (a) in HW-55 and HW-56 (SPI1's pin groups,
  the group select, the port set-up registers, `CON`'s named bits, FM-1's
  own `CON` and `BAUD` values) and HW-57 (the panel's clock limit); (b)
  open, the panel's reset timing in HW-57; (c) open; (d) in HW-58; (e) in
  HW-59: the spec is right and fwtest was wrong. fwtest kept every `CON`
  bit once written, so after any write with bit 13 set, every transfer
  raised source 16 whatever `CON` was written to later. Fixed in fwtest
  0.2.0, which `config/fwtest-image` pins from the pull request that
  follows this answer: a `CON` write sets and clears bits as written,
  single bytes in `BUF` follow the same rule as DMA transfers, and a write
  of bit 14 alone also clears bit 13, so acknowledge by setting bit 14
  and keeping the other bits. Open: Q-6, Q-15.
- Answered: 2026-10-23, session SR-3 (spec side)

### SR-4: The similarity audit: vendored Plaits as base code (an audit request)
- Asked: 2026-10-23, session M4b (firmware side). Not a hardware question:
  the owner asked for it to be filed here, as a request about the audit's
  tooling, which the spec side keeps.
- Question: Add `vendor/plaits/` (Mutable Instruments' Plaits and stmlib,
  MIT, vendored unmodified at pinned upstream commits; pull request #59) to
  the similarity audit's base code, beside `vendor/jieli-sdk/include_lib`
  (`audit/audit.json`, `base_code`; docs/AUDIT.md, "What is compared"), so
  that matches between a target and code we both took from Plaits are
  dropped. Our own glue in `firmware/demos/plaits/` stays compared.
- Why: M4b ports Plaits as a separate demo build (`firmware/demos/plaits/`)
  to measure the chip. `vendor/` is never compared as ours, but FM-1
  firmwares that ported Plaits would match our glue's calls into it, and
  any of its code a target copied would count against files of ours that
  include its headers. `base_code` takes one path today, so this needs a
  change to the audit tool or its settings, which are spec side. Read:
  docs/AUDIT.md, `audit/audit.json`.
- Status: answered (docs/AUDIT.md, "Base code"; R-AUDIT-4, R-SEP-1), in
  #63, which follows #59; merge #59 first.
  - (1) The audit: `audit/audit.json`'s `base_code` is a list. The JieLi
    SDK is base code for all our files. The vendored Plaits, only the
    files `vendor/plaits/SHA256SUMS` lists and each matching its hash (or
    the audit fails), is base code **only for files under
    `firmware/demos/plaits/`**. Those files get a JPlag pass of their own,
    with the control scored again under the same base code, and the text
    check leaves out base-code pieces the same way. Given to every file,
    Plaits cut the self-test's longest matches in core files that don't
    use it (11 of 15 files found), so the owner chose the demo-only scope.
    A file outside `firmware/demos/plaits/` that includes a Plaits header
    fails the audit (C-AUDIT-BASE): don't include Plaits from the core
    firmware without asking the owner. The self-test finds all 15 of our
    files today; with a trial glue file under `firmware/demos/plaits/`, 16
    of 16, in two passes.
  - (2) The separation check: keep #59's version. It meets the owner's
    four conditions, and the spec side's review found one gap, which #63
    closes: `vendor/plaits/SOURCE.md`, which we
    write, was not scanned; now it is (it has no hit). The checksum code
    moved to `tools/sha256sums.py`, which the audit shares.
  - (3) #59's branch at `247ddfa`, its commits and pull request text:
    C-SEP-TERMS PASS, no hit; the Plaits list takes off 4 terms.
  - Note (the owner's request, 2026-10-23): C-SEP-TERMS never counts
    universal constants as emulator terms: powers of two (sign-bit masks
    among them), 2^n-1, 2^n+1, and IEEE 754's standard single and double
    patterns (infinities, quiet NaNs, one, 2^±23, 2^±52), defined by rule
    in the check (R-SEP-1). #61's branch at `52fa29b`, its commits and
    pull request text: under #61's own copy of the check, 25 hits, its
    only failing check in CI; under the new rule, PASS, no hit (the Plaits
    list takes off 3 terms). So #61 passes once #63 has merged and
    #61 has merged main.
- Answered: 2026-10-23, session SR-4-6 (spec side)

### SR-5: Hardware single-precision floating point on the chip and in fwtest
- Asked: 2026-10-23, session M4b (firmware side)
- Question: (a) Does the AC791N's core execute the toolchain's hardware
  single-precision float instructions (its `fprev1` feature, enabled by
  clang's `-mfprev1`), and which of the toolchain's CPU models
  (`-mcpu=r1` to `r5`) is the chip's core? (b) Does fwtest model those
  instructions as the chip runs them (results, and the floating-point
  exception bits of HW-50's `EMU_MSG`), and at what cost: fwtest counts
  each as one cycle; how many cycles does each take on the chip (add,
  multiply, divide, square root, conversions, loads and stores)?
- Why: M4b measures Plaits (floats throughout) on our base. With our own
  soft-float a block of most engines costs 0.7 to 1.8 million of core 0's
  instructions, more than a block's 348 160 cycles: only one engine plays
  live. Built with `fprev1`, the same engines cost 10 000 to 52 000, and
  fwtest runs them with the same sound bit for bit (the bench's
  checksums). The SDK's own AC791N builds use `-mcpu=r3 -mfprev1`
  (`apps/demo/demo_hello/board/wl82/Makefile` lines 74 and 75, at the
  pinned SDK commit; PROVENANCE P-29), which suggests the chip has them,
  but HARDWARE-SPEC.md says nothing about it, and M5's engine design
  (fixed or floating point, how many operators) depends on it. Read:
  HARDWARE-SPEC.md (HW-50's float exception bits), the toolchain's
  feature list, the SDK's Makefiles.
- Status: answered in part (HARDWARE-SPEC.md, "14. Floating point and the
  second core (SR-5, SR-6)"): (a) in HW-62: the SDK builds its AC791N
  code for `r3` with `fprev1`, so build for the chip the same way; what
  `r1` to `r5` differ in is open. (b) in HW-63: what fwtest computes,
  including the edge cases (rounding, subnormals, NaNs, conversions,
  multiply-add rounded twice); it sets no float flag and raises nothing,
  and every float instruction costs one cycle there, like any other. The
  chip's cycle costs and edge behaviour are open (Q-16). No fwtest change:
  no source establishes different behaviour. Plan M5 for either outcome:
  fwtest's float timings are a lower bound, not a measurement.
- Answered: 2026-10-23, session SR-4-6 (spec side)

### SR-6: Running both cores on the chip
- Asked: 2026-10-23, session M4b (firmware side)
- Question: (a) When both cores run code from the code window and work in
  main RAM, what does each cost the other on the chip: shared caches or
  buses, wait states, and whether core 1 runs at the same clock as core 0
  (HW-11 gives fwtest's)? (b) What core 1 needs before it runs on the
  chip from a raw image (Q-11: the release, its cache and its MMU or
  protection set-up), and whether core 1 can take interrupts (its own
  `ICFG` and `ILAT` registers, HW-20 to HW-23, which fwtest has for core 0
  only). (c) Whether a plain store by one core is seen by the other's next
  load, or needs a barrier or a cache operation first.
- Why: M4b's bench starts core 1 (HW-9, HW-10) on a loop that renders a
  second Plaits voice when core 0 sets a word in RAM, and polls another for
  the result. In fwtest two voices at once take 0.50 to 0.55 of the time of
  one after the other on core 0, so core 1 nearly doubles what the
  firmware can play. M5 decides how to split voices between the cores, and
  needs to know how much of that holds on the chip. Read: HARDWARE-SPEC.md
  HW-8 to HW-11, HW-18 to HW-23, Q-11; docs/HARNESS.md ("Time": core 1's
  timer reads).
- Status: answered in part (HARDWARE-SPEC.md, section 14): (a) in fwtest,
  HW-64: both cores at one instruction a cycle, no caches or contention,
  so the 0.50 to 0.55 measured is fwtest's best case; on the chip, open
  (Q-17), including core 1's clock. (b) Core 1's own interrupt words and
  gates are in HW-17, HW-20, HW-21 and HW-23 (confirmed, SDK). In fwtest
  core 1 takes the sources its own words enable; the tick timer and
  software-interrupt words are core 0's only, and a source pending there
  goes to every core that enables it, so enable each source on one core
  (HW-64). What core 1 needs before it runs on the chip stays open (Q-11,
  Q-17). (c) In fwtest a store is seen by the other core within one turn
  of 1024 cycles (HW-64). On the chip, HW-65 gives the SDK's practice:
  `testset` for locks and `csync` around shared accesses, which you
  should follow; whether a plain store is seen without it, and whether
  main RAM is cached, is open (Q-18). No fwtest change: no source
  establishes different behaviour.
- Answered: 2026-10-23, session SR-4-6 (spec side)

### SR-7: fwtest doesn't run a two-register load the compiler emits (a harness gap)
- Asked: 2026-10-23, session M5 (firmware side)
- Question: fwtest ends a run as a fault ("an instruction the emulator
  does not implement") at the two-register load that moves its address
  down first, which the toolchain's disassembler prints as
  `{r3, r0} = [-r4]` (bytes `44 eb 09 00`). Please make fwtest run it,
  and its kin if the encoding has them (other register pairs, the store
  `[-rN] = {rA, rB}`, a post-incrementing form), as the chip does, and
  say in HARNESS.md or HARDWARE-SPEC.md which forms fwtest runs. This is
  about fwtest only, not the hardware: the compiler emits the form on its
  own, with or without `-mcpu=r3 -mfprev1`.
- Where it came from: M5's FM engine. clang (the pinned toolchain,
  P-1), `-target pi32v2 -mcpu=r3 -mfprev1 -std=c11 -ffreestanding -Os`
  (tools/build.sh), made one of it in `voice_start()` in
  `firmware/src/fm_play.c`, from seven consecutive word copies of one
  struct's array fields into another's (`o->step[0..3] =
  p->op[i].step[0..3]; o->target[0..2] = ...`). The same file built with
  the toolchain's default CPU and no float flag gives the same
  instruction. The engine's first fwtest run faulted there on core 0.
- Minimal reproduction (our own code; assembled with the pinned clang,
  `-target pi32v2 -mcpu=r3`, linked at `0x02000000`, raw image from
  `.text`, run with `tools/fwtest run IMAGE --ms 1 --ram
  0x01c00020:12@end`):

  ```
  _start:
  	r4 = 0x01C00010
  	r1 = 0x29F3A1C5
  	[r4+-8] = r1
  	r1 = 0x7E41D60B
  	[r4+-4] = r1
  	{r3, r0} = [-r4]
  	r5 = 0x01C00020
  	[r5+0] = r0
  	[r5+4] = r3
  	[r5+8] = r4
  	cli
  1:	goto 1b
  ```

  fwtest: exit 3, `fault`, "core 0 at pc 0x02000016: an instruction the
  emulator does not implement", nothing stored. The control image, the
  same with `r4 += -8; r0 = [r4+0]; r3 = [r4+4]` in place of the one
  instruction: exit 4, `halt` as meant, and the stores show r0
  `0x29F3A1C5`, r3 `0x7E41D60B`, r4 `0x01C00008`, which is what we expect
  the one instruction to leave (which register gets which word is part of
  the question).
- Workaround until then: `voice_start()` copies those fields a word at a
  time through a volatile pointer (`copy_words`, fm_play.c), and
  tools/build.sh fails an image whose disassembly holds the form, so
  none reaches fwtest unnoticed (docs/DESIGN-NOTES.md, M5). Both go once
  fwtest runs it.
- Status: answered (HARDWARE-SPEC.md, "15. Block moves with a register
  base (SR-7)", HW-66; docs/HARNESS.md, "Instructions"): the encoding has
  eight modes, loads and stores, up or below the base, with or without
  moving it, for any base and any list of r0 to r15; fwtest 0.3.0 runs all
  eight. The lowest register takes the lowest address, so your r0 and r3
  are right, but the form without `--` leaves the base as it was: r4 stays
  `0x01C00010`, not `0x01C00008` (the compiler's own code relies on this).
  The compiler emits the forms without `++` / `--`; the others, and a base
  that is also in a write-back form's list, are open for the chip (Q-19).
  A corpus check of what the compiler emits for the firmware's flags,
  across registers and immediates, found two more forms fwtest doesn't
  run: a rotate by a register, which the compiler emits, and a 4-byte push
  or pop of a list not starting at r0, which it was not seen to emit
  (HARNESS.md, "Instructions", "Known gaps"). Since fwtest 0.4.0
  (2026-10-24, session emulator-parity) both run (HARNESS.md,
  "Instructions").
  fwtest 0.3.0 reaches `tools/fwtest` when the pull request after this
  one pins its image; then `copy_words` and build.sh's check can go.
- Answered: 2026-10-24, session SR-7 (spec side)

### SR-8: MIDI input: the UART the jack reaches, its receive set-up, and fwtest's model
- Asked: 2026-10-24, session M6a (firmware side)
- Question: (a) Which UART receives the FM-1's MIDI input jack, on which
  pin, and the `JL_IOMAP` selection and port set-up (direction, pull-up)
  for that pin. Whether any other MIDI input path exists on the FM-1
  (USB, say), and which path fwtest's `midi` script event feeds. (b) The
  receive set-up for 31 250 baud, 8 data bits, no parity, one stop bit:
  the `CON0` / `CON1` bits that turn the receiver and its interrupt on,
  the flag that says a byte is waiting and how to acknowledge it, any
  error flags (framing, overrun) and how they clear, and the `BAUD` value
  for 31 250 baud from each `CLK_CON1` UART clock choice (HW-53), or the
  formula. (c) The receive interrupt's source number. (d) Whether the
  receiver can be read a byte at a time from `BUF` with an interrupt per
  byte, or only through the DMA window (`RXSADR`, `RXEADR`, `RXCNT`,
  `HRXCNT`, with `OTCNT` as a timeout), how the window wraps, and which of
  the two fwtest models. (e) In fwtest: what set-up counts as "a MIDI
  receiver set up" for `midi_bytes_dropped` (HARNESS.md, "Outputs"), and
  what happens to a byte that arrives before the previous one was read
  (lost, kept, an overrun flag).
- Why: M6a is MIDI in: a byte parser, note and controller messages to the
  FM engine, a receive channel. The parser and the engine's side don't
  depend on the answer and are being built meanwhile; the receiver and
  every fwtest MIDI test do. MIDI out is M6b and not asked here.
  Read: HARDWARE-SPEC.md Q-12 ("UART1 and the MIDI jack are not covered
  here"), HW-53 (the UART clock field), the interrupt and port sections;
  HARNESS.md's `midi` event (a byte every 320 µs) and
  `midi_bytes_dropped`; the vendored SDK's `WL82.h`, whose
  `JL_UART_TypeDef` names `CON0`, `CON1`, `BAUD`, `BUF`, `OTCNT`, `TXADR`,
  `TXCNT`, `RXSADR`, `RXEADR`, `RXCNT` and `HRXCNT` at UART0 to UART2's
  bases, but no bits.
- Status: answered in part (HARDWARE-SPEC.md, "16. MIDI input (SR-8)",
  HW-67 to HW-71; open: Q-12).
- Answered: 2026-10-24, session midi-in-out (spec side)
