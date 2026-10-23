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
- Status: open
