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

### SR-9: Flash storage: the region firmware may use, the part, and code while the flash is busy
- Asked: 2026-10-24, session M7 (firmware side)
- Question: (a) On an FM-1, which flash chip offsets our firmware may use
  for its own data without harming the boot chain or the update path:
  what lies below `0x4000`, whether anything past an installed image
  (the chip's last sectors, say) is used by the boot chain or the update
  path, and the chip's size on the FM-1. (b) The FM-1's flash part, and
  from its datasheet: the 4 KiB erase's and the page program's times
  (typical and maximum), the endurance (erase cycles a sector), and
  whether it can suspend an erase or program. (c) On the chip, while an
  erase or a program is in progress: what reads through the code window
  do (wait until it ends, read wrong data, fault), for core 1 too.
  (d) On the chip: whether firmware may drive SPI0 with HW-47's commands
  while the code window is in use, or what must be idle or set up first
  (SPI0's clock and mode on the chip, the code window's own controller),
  and how the window is restored after. (e) Whether the code window
  caches the flash on the chip, and what makes it see a change made
  through SPI0. (f) Whether the chip starts with any write protection set
  (the status register's protect bits) that must be cleared before an
  erase or program. (g) In fwtest: SPI0's pace (emulated time per byte),
  what a page program does to bytes that are not erased (clears bits
  only, or overwrites), and to an address range past the end of a
  256-byte page (wraps within the page, or not).
- Why: M7 is flash storage: user patches, the patch selection and the
  settings, written so a power cut at any instant keeps the previous good
  copy, and so saving never makes the audio underrun. Without (a) the
  store sits in the chip's last 64 KiB as an assumption, in one define,
  and the image is kept clear of it. Without (c) to (e) the firmware runs
  every instruction and reads every constant from RAM after start-up, and
  reads its store through SPI0 only, so nothing touches the code window
  while the flash may be busy; (c) says whether that is needed. (b) sets
  the write limits each record kind gets, and the busy time the audio
  tests must survive; (f) and (g) decide whether the driver works on the
  chip and in fwtest alike. Read: HARDWARE-SPEC.md HW-5 and HW-47 (both
  emulator-only or preliminary, "M7 should confirm the chip and its
  timing"), the vendored SDK's `WL82.h` (`JL_SPI0`'s registers, no bits
  beyond HW-47's); HARNESS.md ("The raw image", `--flash`,
  `--flash-out`). Black-box runs in fwtest so far: none beyond a
  `--flash-out` capture of an erased chip.
- Status: answered in part (HARDWARE-SPEC.md, "19. Flash storage (SR-9,
  M7)", HW-76 to HW-82, and HW-47's standing): (a) HW-80 (the layout; the
  chip's last 64 KiB is not safe, its last sector is per-unit); (b) HW-76
  and HW-77 (the P25Q80H, if that is the part: Q-21); (c) HW-78 and
  HW-79 (nothing from the window while busy, either core); (d) open,
  Q-22 (and the chip select pin may not be PD0 on the chip); (e) HW-81
  (read the store over SPI0), the cache itself Q-22; (f) HW-78's protect
  bits, the FM-1's state Q-23; (g) HW-82 (fwtest 0.5.0: no time per
  byte, bits only cleared, no wrap; fwtest's next version is to model the
  busy times, the wrap and the write enable). Also: fwtest 0.5.0 runs a
  dual-issue pair whose two halves write one register differently from
  the compiler's expectation, which a flash driver can meet (HARNESS.md,
  "Instructions", the known gap). Open: Q-21 to Q-24.
- Answered: 2026-10-24, session day-1024 (spec side)

### SR-10: A store with a base update whose stored register is its base
- Asked: 2026-10-27, by the owner, for a downstream firmware built on
  small-beeps (not named here)
- Question: a store with a pre- or post-increment base update whose
  stored register is the base itself, as the pinned compiler emits it for
  pi32v2: `[++r4=748] = r4` (bytes `d2 ec 4f 4e`; also `[++r1=8] = r1`,
  `d0 ec 1b 10`). fwtest stores the updated base; the compiler's code
  expects the value from before the instruction. A black-box run showed
  it: with r1 = `0x01C38250`, `[++r1=8] = r1` wrote `0x01C38258` at
  `0x01C38258`. Code the compiler emitted this way faulted in fwtest,
  depending only on register allocation. Which value does the chip store,
  and what should fwtest do? Does small-beeps' own firmware contain the
  form (the downstream report says it doesn't)?
- Status: answered (HARDWARE-SPEC.md, "22. A store of its own base
  register (SR-10)", HW-95; docs/HARNESS.md, "Instructions"):
  - **The toolchain intends the old value.** With the firmware's flags,
    at `-Os` and `-O2`, the compiler emits the one instruction
    `[++r0=748] = r0` for `q = p + 187; *q = p; return q;` (the pointer
    stored as it was), and `[r0++=8] = r0`, `h[++r0=8] = r0` and
    `b[++r0=8] = r0` for the post-increment, halfword and byte versions.
    For the same C storing the moved pointer (`*q = q`) it did not use
    the form in any function tried. Its assembler takes every such form
    without a warning. The toolchain ships no documentation of its
    instructions; the SDK's `.S` files are version stamps only, and the C
    and header files searched (its CPU and system folders, 128 of 189
    fetched) hold no inline assembly, so neither says more. Its prebuilt
    libraries were not disassembled.
  - **What the chip stores is not established without a unit:** Q-27,
    for Phase B. The compiler's intent is strong evidence, since the vendor
    ships it for this chip, but it is not a measurement.
  - **fwtest matches the compiler** from 0.9.0 (patch 0013): every such
    store keeps the base as it was. 0.8.0 got the pre-increment forms
    with a number step wrong (word, halfword and byte: the moved base,
    as reported); its post-increment forms and the register steps already
    stored the old value, so the report's "or post-increment" does not
    reproduce in fwtest. A harness test runs all fifteen forms the
    assembler takes, and the compiler's own code for such C, and fails
    on 0.8.0.
  - **small-beeps' own firmware has no such store** (main at `fd07f7f5`,
    `app.elf` and `app-pkg.elf`: 65 stores with a base update, none
    storing its own base), as the report said. The firmware side's
    `tools/build.sh` check against the form (R-BUILD-3, #158) can stay
    until Q-27 is settled on a unit.
  - fwtest 0.9.0 reaches `tools/fwtest` when its image, published from
    this answer's merge, is pinned.
- Answered: 2026-10-27, session spec-1027 (spec side)

### SR-11: Where the app area ends, and what an update writes past our image
- Asked: 2026-10-28, session clean-store-region (firmware side), for the
  owner's answer that each firmware built on small-beeps chooses its own
  store region
- Question: on the FM-1, for a package our packager makes (HW-87 to
  HW-91: the app area from flash `0x4000`, its area head's length the
  length of our scrambled app, our flash image ending there), three
  facts:
  1. **The app area's end.** Is `0x93FFF` (where the stock layout's app
     area ends and its VM region begins, HW-80) the last flash offset a
     firmware's own app area may reach, or does the chip's loader or the
     stock layout allow an app area past it? HW-87 to HW-93 give the
     area's start and its length as its area head says, but no fixed end.
  2. **Flash between our image's end and `0x93FFF`.** Does the chip's
     loader (`uboot.boot`, HW-92) read, check, decrypt or change flash
     past the area head's length? Does an update (the running
     firmware's updater and `ota.bin`, HW-92, or the stock updater
     installing our package) erase or write flash past the end of the
     package's flash image, up to `0x93FFF` or beyond, or only the
     flash image's own sectors?
  3. **The code window past the area.** Does the window's decryption
     (HW-84, HW-91) cover flash past the area head's length, so that a
     region there, written over SPI0, reads differently through the
     window? (The store never reads through the window; this only says
     whether anything else could.)
- Why: a firmware built on small-beeps may now put its store in the app
  area after its own image (docs/DESIGN-NOTES.md, "Each firmware chooses
  its own store region"; R-STORE-12), a larger region than the unused
  three sectors at `0xFC000`. `tools/build.sh` refuses a region that
  crosses the app area's end; until this is answered it takes the most
  conservative reading, `0x94000` (HW-80's stock layout), and refuses
  anything in the VM region, the Bluetooth sector, the stock user patch
  region and the last sector. Whether a region after the image survives
  an update (item 2) decides whether BUILDING-ON-SMALL-BEEPS.md can
  recommend it for data that must survive one; it now says this is
  open. Read: HW-80, HW-84, HW-87 to HW-94; Q-24, Q-26.
- Status: open

### SR-12: Where an update package puts its data at flash 0x4000
- Asked: 2026-11-17, session clean-br17 (firmware side), for BR-17 (a
  package a unit's installer accepts) and the owner's answer that the
  candidate is a `.fwsc` holding the app area only
- Question: two fields, for a package that must write nothing below flash
  `0x4000`:
  1. **The field that places an entry's data.** HW-89 says the type-0
     entry (`flash.bin`) is written from flash offset 0, and HW-104's
     entry fields give only file offsets. Is there an entry type, an
     entry field, or a field of the flash image's or the update file's
     header by which an update file or a `.fwsc` says its data goes at
     flash `0x4000` (or any offset but 0)? If JieLi's tools can write
     such a package, which option makes them do it (HW-107: `-output-ufw`
     in `download_linux.c` and other options were not tried), and what do
     the entry's fields hold then?
  2. **`isd_config.ini`'s entry** (HW-104, type `0x34`): its data for the
     FM-1 (the configuration's text the tools write), and in a `.fwsc`
     the offset its `0xFFFF` chunk scrambling counts from (HW-104 gives
     it for the update file, the file offset `o`; in a `.fwsc` the
     logical and file offsets differ by 20). The owner's answer leaves
     five entries out of the first app-area package; this one is not
     among them, but its data is not given and lives below `0x4000`
     (HW-105, `0x3628`), so the candidate leaves it out too (the
     owner confirmed this on merging #181: an app-area-only package
     leaves that region alone). Asked for a later full package.
- Why: `tools/fwsc.py pack --app-area` writes the app area alone (the
  flash image's bytes from `0x4000`, in one `flash.bin` entry) and
  takes it to go at `0x4000`, which is our reading, not a fact: by HW-89
  an installer would write it from 0, over the unit's loader. Its
  `--hardware` mode refuses while this is open, and the owner is told so
  before trying a candidate (docs/DESIGN-NOTES.md, clean-br17). Read:
  HW-87 to HW-94, section 24 (HW-103 to HW-108), Q-25, Q-26.
- Evidence since (2026-11-18, the owner's report from the unit,
  docs/prompts/clean-br17-unit-1.md; relayed here for the spec side, not
  taken as a fact by this side): the unit's third-party installer refused
  both app-area candidates before writing anything, with the words
  "unexpected flash image size 55608". 55608 is the candidates'
  `flash.bin` entry length (the area head and directory, `0x120`, and the
  app). So that installer reads the type-0 entry as a flash image with an
  expected size (SR-13).
- Status: open

### SR-13: The length of the update file's flash image
- Asked: 2026-11-18, session clean-br17 (firmware side), for BR-17's
  second round on the unit
- Question: in the update files JieLi's tools wrote on our own input
  (P-65's runs, HW-103 and HW-104), how long is the `flash.bin` entry's
  data (the flash image), and which field or rule gives that length:
  the flash header's flash size (`0xFF000`, HW-105, "the space the image
  needs"), the app area's end plus its 64 bytes, a rounding (to 32, to
  the flash header's 4 KiB alignment, to a sector), or another? Is the
  image padded with `0xFF` to that length?
- Why: the owner's unit's installer refused our app-area `.fwsc` with
  "unexpected flash image size 55608" (docs/prompts/clean-br17-unit-1.md;
  the owner's observation, relayed, not a fact this side takes), 55608
  being our `flash.bin`'s length. This side does not guess the length:
  a `flash.bin` sized to pass that check is the one an installer most
  likely writes from flash 0 (HW-89), over the unit's loader. Until this
  is answered `tools/fwsc.py` makes no more app-area `.fwsc` candidates;
  the next candidates are HW-106's OTA file (`--ota`), which has no
  type-0 entry. Read: HW-89, HW-103 to HW-108, Q-25, Q-26; SR-12.
- Status: answered (HARDWARE-SPEC.md, "25. What an FM-1 installer and the
  bootloader check": HW-114, with HW-109 and HW-110)
- Answered: 2026-11-18, session spec-br17-tools (spec side)

### SR-14: What a unit needs from an app after m-bootloader starts it
- Asked: 2026-11-18, session clean-br17-round2 (firmware side), for BR-17
  Phase B round 3
- Question: for an app that m-bootloader starts on the FM-1 (HW-112):
  1. **The panel's port set-up**: the SPI1 pin group and the
     `JL_IOMAP->CON1` bit (HW-56), the pins and active levels of the
     panel's chip select, reset and backlight, and the `DIR`, `PU`, `PD`,
     `HD0`, `HD` and `DIE` bits each needs (Q-6).
  2. **The key matrix and the LEDs on the board**: the column and row
     pins, the levels that select a column and light an LED, and their
     port set-up (Q-7; HW-33, HW-34 and HW-42 give fwtest's).
  3. **The state m-bootloader leaves when it calls the entry**: which
     ports and pins it has set up (the panel's, the backlight's, PLAY's
     and REC's), the system clock and the clocks of the flash, SPI1 and
     the timers (Q-2), whether interrupts and any watchdog are on, the
     stack pointers, and which RAM it still needs if the app returns to
     it (so a probe may write RAM and still return).
  4. **How the call is made**: that the entry is called so that the
     app's `rts` returns into m-bootloader (HW-112: "an app that returns
     opens its recovery menu"), and what it expects in the registers on
     return.
- Why: Phase B round 2 (the owner's report, 2026-11-18; relayed here, not
  taken as a fact by this side): the unit's installer accepted the
  hardware package (`847f3c5a…`), wrote `0x4000`-`0x11FFF`, verified it
  and kept the boot area, and reports "firmware check OK", chip key
  `0x980F`; m-bootloader's recovery menu shows "app OK" and its Boot app
  starts it; then the unit shows nothing: a black screen, no LEDs, no key
  lights, from a normal power-on and from Boot app alike. Our firmware
  sets up no port pin at all (fwtest needs none, HW-29, HW-56), so
  nothing it draws or lights can show until item 1 and 2 are known, and
  it may also stop earlier (item 3). The only probe this side can make
  without these facts is the entry-return probe (R-PROBE-1), which shows
  only whether our entry is reached. m-bootloader draws its menu on the
  same panel and reads PLAY and REC, so its sources may hold items 1 to
  4; taking them from there would be outside the owner's ruling for
  section 25 ("only the package format and the checks"), so that is the
  owner's to rule. Read: HW-1 to HW-4, HW-29 to HW-35, HW-42, HW-56,
  HW-57, HW-91, HW-110 to HW-112; Q-2, Q-6, Q-7.
- Status: answered (HARDWARE-SPEC.md, "26. The FM-1's panel, backlight,
  keys and LEDs, and the state at the app's entry": items 1 and 2 in
  HW-115 to HW-118, items 3 and 4 in HW-119)
- Answered: 2026-11-18, session spec-sr14 (spec side), by the owner's
  ruling for SR-14


### SR-15: The FM-1's two flash parts
- Asked: 2026-11-18, by the owner (docs/prompts/spec-sr15.md), for M7's
  store on real hardware and for firmwares built on the base (RevoiceDX
  saves at `0x80000`)
- Question: units sold since autumn 2026 carry a second flash part, which
  reports `0xB36014`.
  For the commands and status bits small-beeps uses (read, page program,
  sector erase, the busy bit), give each one's times (typical and
  maximum) on both parts, and every difference between the two parts
  that matters to small-beeps, or say that there is none. Say what
  small-beeps must do so one image works on both.
- Why: the owner's report (relayed, not taken as a fact by this side):
  the owner's unit reports `0x856014` in m-flasher's information and in
  m-bootloader's recovery menu ("flash 856014 1024K"); other units report
  `0xB36014`. Sources allowed: the two parts' public datasheets and
  m-bootloader's flash code, under section 25's and 26's guardrails.
- Status: answered (HARDWARE-SPEC.md, "27. The FM-1's two flash parts":
  the parts in HW-120, the commands and times in HW-121, the differences
  in HW-122, m-bootloader's handling in HW-123, what one image needs in
  HW-124). For the commands small-beeps sends only the ID differs, and
  that matters: the store writes only to `0x856014` (`STORE_PART`,
  `firmware/src/store.h`), so on a `0xB36014` unit every save is refused
  (`STORE_ERR_PART`). Against HW-124's other items:
  - Item 2 is met: the store sends only `0x9F`, `0x03`, `0x05`, `0x06`,
    `0x20` and `0x02`.
  - Item 3 is met: the store waits on the busy bit, never a fixed delay,
    after every erase and every page program. `erase()` ends with
    `wait_ready()`, and `program()` calls `wait_ready()` after each page's
    `0x02` and stops at the first failure (`firmware/src/store.c`).
    `wait_ready()` reads status 1 (`0x05`) until bit 0 is 0, giving up
    after 3 s (`BUSY_LIMIT_TICKS`), far past either part's longest
    maximum (12 ms). Only the busy test build (`SB_TEST_STORE_BUSY`) adds
    a fixed delay, and it does so before that wait, not instead of it.
  - Item 4 is met in part: every program is read back, but an erase is
    checked only through the sector header programmed after it.
  - Item 5 is not met: the store reads no status register, so it would
    write into a protected region and see each write fail its read-back.
  The clean prompt for SR-15 asks for the two IDs, an erase read-back,
  and a refusal when any protection bit is set. It also requires the busy
  wait to stay after every erase and page program.
- Answered: 2026-11-18, session spec-sr15 (spec side)

### SR-16: What the FM-1 hardware build still assumes on the chip
- Asked: 2026-11-18, session clean-br17-start (firmware side), for BR-17
  Phase B, the first hardware build (R-HW-1)
- Question: on the FM-1, after m-bootloader has called the app (HW-119)
  and the app does not return:
  1. **The timers' set-up and clocks**: the meaning of `JL_TIMERn->CON`
     bits 0 to 3 on the chip (fwtest's reading, HW-48: bits 0-1 non-zero
     run it), so which value runs TIMER0 from the 60 MHz low-speed bus
     with prescaler setting 0 (the build writes `CON` `0x1`); whether the
     acknowledge restarts the count (Q-13); and the input clocks of
     TIMER1 and of TIMER4, the free-running time base (HW-13 gives only
     fwtest's 24 MHz). The build uses TIMER0 alone until then.
  2. **Interrupts after the call**: core 0's mode (HW-3 is
     emulator-only), so which stack (`sp` or `ssp`) an interrupt runs
     on; whether the vector table at `0x01C7FE00` (HW-18), inside the
     retained area HW-119 names, may be written by an app that never
     returns, and whether anything in that area matters to m-bootloader
     at the next power-on; and what `idle` does on the chip (HW-24 is
     fwtest's).
  3. **Code run from RAM**: whether instructions copied into main RAM
     with ordinary stores, over RAM m-bootloader used, may be run at
     once, or need a cache operation first (HW-91 says the stock firmware
     synchronises the instruction cache after a program, Q-22).
  4. **The rest of the key matrix**: every key's and button's column
     word and row on the FM-1 (HW-117 gives four), and in particular
     what bits 11 to 15 of the column word select: OCT−'s `0xF7FE` and
     OCT+'s `0xEFFD` clear two bits each, where fwtest's matrix (HW-33)
     has one column per key and no columns past 10.
  5. **The encoders' rows and the pot**: the set-up of the encoder rows
     (fwtest's PA0 and PB7, HW-34, HW-38: their pull-ups) and of the
     SARADC's pin for the pot (HW-40) on the chip.
  6. **Audio, core 1 and MIDI**: what the audio link and DAC need on the
     chip besides HW-43 to HW-45's registers (clocks, analogue set-up,
     pins), whether releasing core 1 as HW-9 says works after
     m-bootloader's call, and UART1's pins on the board (HW-73).
- Why: the first hardware build (R-HW-1, `SB_HW_FM1`) runs small-beeps'
  own start-up on a unit with the screen, keys, LEDs and a timer, as the
  owner asked after the panel probe worked (docs/prompts/clean-br17-start.md).
  Each item above is something it either assumes (items 1 to 3) or
  leaves out for want of a fact (items 4 to 6). The build draws a band
  on the screen after each assumed step, so the owner's report will show
  where it stops, but the report is a relayed observation, not a fact
  this side may take. Read: HW-3, HW-9, HW-13, HW-18, HW-24, HW-33 to
  HW-35, HW-38, HW-40, HW-43 to HW-45, HW-48, HW-73, HW-91, HW-117 to
  HW-119; Q-3, Q-7, Q-13, Q-22.
- Status: answered (HARDWARE-SPEC.md, "28. What the hardware build still
  needs on the chip"), item by item; where no allowed source gives a fact
  the entry says so and names the probe on a unit that settles it (the
  owner's request: no new SR):
  1. **Timers:** HW-125. `CON` `0x1` runs a timer from the 60 MHz LSB at
     one count per clock, as m-bootloader's TIMER0 does on FM-1 units;
     bit 3 picks the 24 MHz oscillator, so a 24 MHz TIMER4 needs `CON`
     bit 3 on the chip. Open: whether the acknowledge restarts the count
     (Q-13), bit 2.
  2. **Interrupts:** HW-126. The vector table may be written by an app
     that never returns, once it has read the boot block; it covers the
     boot block and the header copy, not what m-bootloader reads at the
     next start (`0x01C7FD80` to `0x01C7FDD7`, which it must leave alone).
     Set `ssp` and `sp` both. Open: which stack an interrupt uses; what
     `idle` does.
  3. **Code run from RAM:** HW-127. Written with ordinary stores, then a
     `csync`, as m-bootloader runs its own second stage and RAM apps.
     Open: whether main RAM is behind a data cache DMA must see flushed.
  4. **The rest of the key matrix:** HW-129: no allowed source; a probe of
     each column word against rows PA5 to PA8.
  5. **The encoders and the pot:** HW-129. SARADC channel 3 is PB1 and 4
     is PB6 (SDK); FM-1-RE says the FM-1's firmware reads both. Open:
     which is the pot, its pin set-up, the encoders' pins (probes).
  6. **Audio, core 1 and MIDI:** HW-130. Audio's further blocks as
     FM-1-RE names them; open: the clocks for 44 118 Hz, the analogue
     set-up and pins, and whether the audio link plays as in fwtest.
     Core 1: no source shows HW-9's release after m-bootloader's call.
     UART1's pins: open (Q-20).
  The store (the owner's request, beyond the six items): HW-128,
  m-bootloader's take and give-back of the flash; the round trip within
  one run of an app is not shown, and a probe settles it.
- Answered: 2026-11-18, session spec-sr16 (spec side)

### SR-17: The code window's BAUD register, and whether its CON reads back
- Asked: 2026-11-19, session clean-br17-start3 (firmware side), for BR-17
  start3's flash round trip (R-HW-1)
- Question: for the code window's controller after m-bootloader's call
  (HW-128):
  1. **Its `BAUD` register:** the address, and the value m-bootloader
     writes there in step 3 of its give-back ("sets its BAUD").
  2. **Whether its `CON` (`0x40200`) reads back** the mode word last
     written, so an app can read it before taking the flash and write it
     back when it gives the flash back.
  3. **Whether writing `CON` (0 in the take; `0x00F00000`, then 0, in the
     give-back) changes `BAUD`.**
  4. **Which width m-bootloader chooses for the window on FM-1 units**,
     and so which mode word: HW-128 gives the quad one, `0x00280381` with
     bits 23-20 at 9.
- Why: start3's round trip (`firmware/src/hw_start3.c`) takes the flash
  and gives it back as HW-128 lists. It doesn't write the window's `BAUD`,
  since no address is given and the take never writes it, and it writes
  back the `CON` it read before the take rather than a mode word of its
  own. If `CON` doesn't read back, the build shows "window CON reads 0"
  and tries nothing. Either way the build doesn't depend on the answer,
  but the owner's result can't tell these cases apart. Read: HW-84,
  HW-85, HW-91, HW-123, HW-126 to HW-128.
- Status: answered (HARDWARE-SPEC.md, "30. The code window's BAUD, its
  CON and its width", HW-132):
  1. **`BAUD`:** `0x00040204`, write only (SDK). m-bootloader writes 1,
     the same built-in divider it gives SPI0, after `CON` = `0x00F00000`
     and `CON` = 0 and before the mode word.
  2. **Whether `CON` reads back:** the SDK marks it read-write, and
     m-bootloader never reads it. On the owner's unit (start3b, relayed)
     it reads `0x009803B5`, not the quad word `0x00980381` m-bootloader
     writes. By the owner's ruling the give-back restores `CON` as read
     before the take (HW-132).
  3. **Whether a `CON` write changes `BAUD`:** not shown. Writing `BAUD`
     after the two `CON` writes, as m-bootloader does, doesn't depend on
     it.
  4. **The width:** quad, output reads, unless m-bootloader's start-up
     checks fall back to dual or single (shown as "SPI WIDTH FALLBACK" in
     its menu). The word it writes is `0x00980381`, HW-128's quad word
     with 9 in bits 23-20 (dual `0x00980281`, single `0x00900089`).
- Answered: 2026-11-19, session spec-sr17 (spec side)

