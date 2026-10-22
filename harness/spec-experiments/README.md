<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Spec-side black-box experiments (spec side only)

Small images the spec side runs in fwtest to confirm facts in
`docs/HARDWARE-SPEC.md` (M0c). The spec cites them only as E-n and their
result; nothing here leaves `harness/`. They are written from the JieLi
SDK's register map and, where the SDK has no bit meanings, from the vendored
emulator's model (`exp.h` says which). Each confirms how fwtest presents the
board, not how real hardware behaves.

- Build: `sh harness/spec-experiments/build.sh` (the pinned toolchain
  container; writes `images/` and `images/SHA256SUMS`).
- Run: `sh harness/spec-experiments/run.sh OUT` rebuilds, compares with the
  committed images, and runs `experiments.suite` against this checkout's
  fwtest (C-SPEC-EXPERIMENTS, R-SPEC-4). The golden files are the results.
- Not part of fwtest: `harness/ci.sh` leaves this folder out of the fwtest
  build context, and the image-publishing workflow ignores it.

| ID | Image | What it shows (the golden files hold the numbers) |
|----|-------|---------------------------------------------------|
| E-1 | `e1-boot` | At entry: r0 = 0x01C7FC00, r2..r15, sp, usp, ssp, icfg, psr and cnum all 0 (r1 not observable: used as the pointer). The block at r0: first word 0x01C7FC40, the other 15 zero. The code window past the image reads 0xFFFFFFFF (erased flash), also 4 KiB further. A written word reads back at 0x01C7FDFC, 0x01CFFFFC, 0x01F3FFFC and 0x0407FFFC. |
| E-2 | `e2-console` | Word writes to DBG_MSG append their 4 bytes, low byte first. A byte or halfword write appends 4 bytes too: the written bytes merged into the last word written (console "abcd12:\nX2:\nYZ:\nend\n"). |
| E-3 | `e3-timers` | TIMER5 PRD 600: an interrupt (63) every 100 µs; TIMER4 advanced 2400 counts (24 MHz) between two. TIMER0 prescaler index 2, PRD 1500: an interrupt (4) every 1 ms; its CON read in the handler is 0x8021 (bit 15 pending). TTMR with PRD 1234: an interrupt (3) every 10 ms. ILAT_SET bit 0: interrupt 120 once. Counts at 52.3 ms (the capture came late, below): 523, 52, 5, 1. |
| E-4 | `e4-core1` | With core 1's entry in the word at 0x01C7FFF8, setting C1_CON bit 3 starts core 1 there; cnum reads 0 on core 0 and 1 on core 1; core 1 ran on stacks it set itself. |
| E-5 | `e5-lcd` | SPI1 bytes with PC8 low are commands, high data. CASET/RASET/RAMWR with RGB565 pixels high byte first, by single bytes (BUF) and by DMA (ADR, CNT from RAM) both draw. INVON and DISPOFF leave the captured picture as written. A software reset (0x01) clears it to black. |
| E-6 | `e6-matrix` | The log gives each fwtest key's (column, row) and each encoder's two contacts and their order (clockwise: the second contact closes first). Matches the table in the spec. |
| E-7 | `e7-leds` | LED line PA9, PA10, PH6, PH9 lights, in the selected column, the LED of the key at row 1, 2, 3, 4 of that column. |
| E-8 | `e8-adc` | Channel 4 reads the pot (900 at the start, then the script's 300, 0, 1023); channel 3 reads 640; every other channel 512. |
| E-9 | `e9-audio` | A half of 128 words (64 frames) every 1.451 ms after the first at 1.459 ms (44 117.6 frames a second). The first half to finish is half 0; the half just finished is CON0 bit 15 inverted. A sample is the word shifted right by 8, clamped to 16 bits: 0x007fffff gives 32767, 0xff800000 -32768, 0x01000000 32767, 0x00000080 0. |
| E-10 | `e10-faults` | No fault reaches sources 0-2 (handlers count 0), before and after writing EMU_CON 0x001F010F, EMU_SSP/USP limits excluding the stacks, DBG_EN 0x003F0030. Misaligned loads give the bytes at the address (word at RAM+1: 0x04030201; halfwords at +1, +3: 0x0201, 0x0403; word at code+1: 0x14131211); a word stored at RAM+9 lands in bytes 9-12. Unmapped 0x00ABCDEC reads 0, and after a write still 0. A code-window write reads back unchanged. Signed and unsigned 1234/0 give 0; 1234%0 (as compiled) gives 1234. EMU_CON and the limits read back; EMU_MSG 0; DBG_EN 0 (unmodelled). |
| E-11 | `e11-undefined` | A call to a function whose first halfword is 0xFFFF: the run ends as a fault ("cannot decode"), after the marker, with no handler run. Before the call was moved into a function, the fault came at the start of main, before any of its stores ran. |
| E-12 | `e12-badjump` | A call to 0x00ABCDEE: fwtest runs the zeros it reads there for 1024 instructions, then ends the run as a fault ("the pc left every memory"); no handler ran. |
| E-13 | `e13-timer-ack` | TIMER0, prescaler index 2, PRD 1500: 100 periods are 2 400 100 TIMER4 ticks with the acknowledge first in the handler (1 tick after entry) and 2 408 160 with it 82 ticks after entry; CNT reads 5 just before the acknowledge, 0 just after. The periphery model restarts the count and the period at every CON write. |

**Late captures.** While core 0 waits (in `idle`, or polling TIMER4), fwtest
takes captures only between its runs of up to 1024 instructions, and each
wait can jump time ahead by up to the next event, so a capture can come
several milliseconds after the time asked (E-3's "10 ms" capture was taken at
14.1 ms). E-5 and E-7 therefore time themselves by busy counting. This is
fwtest behaviour, reported in docs/HARNESS.md ("Time").
