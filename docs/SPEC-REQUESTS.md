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
- Status: open

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
- Status: open

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
- Status: open
