<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Hardware spec

What the spec side knows about the board, and about how fwtest presents it,
as numbered facts. It is the firmware side's only window onto that knowledge
(CONTRIBUTING.md, "Roles"). It holds facts, never code, and never how any
firmware or the emulator is written: each entry states a property of the
hardware, or a requirement it imposes, and leaves the design of the code to
the firmware side.

Written by session M0c (spec side), 2026-10-22. Ask for anything missing
through docs/SPEC-REQUESTS.md. Open spec requests at the time of writing:
none. Session SR-1-SR-2 (spec side, 2026-10-22) added sections 9 to 11 for
SR-1 and SR-2, which are answered in part; what stays open is Q-2, Q-13
and Q-14. Session SR-3 (spec side, 2026-10-23) added section 12 for SR-3,
answered in part (open: Q-6, Q-15), and section 13, which confirms HW-41's
fwtest part for M3. Session SR-4-6 (spec side, 2026-10-23) added section 14
for SR-5 and SR-6, answered in part (open: Q-16 to Q-18). Session SR-7
(spec side, 2026-10-24) added section 15 for SR-7 (open: Q-19). Session
midi-in-out (spec side, 2026-10-24) added section 16 for SR-8, answered in
part (open: Q-12), and section 17 for MIDI output (open: Q-20). Session
pin-050 (spec side, 2026-10-24) added section 18, the UART as another
JieLi chip's open driver sets it up (SDK63), for Q-12 and Q-20, which stay
open. Session day-1024 (spec side, 2026-10-24) added section 19, flash
storage, for SR-9 (open: Q-21 to Q-24).

## How to read it

Every fact is an entry:

- **ID**: `HW-n`. IDs are never reused or renumbered. A corrected fact gets a
  new ID, and the old entry stays, marked superseded.
- **Fact**: the property or requirement. "On the chip" means the AC791N on
  the FM-1; "in fwtest" means how fwtest presents it (docs/HARNESS.md). Where
  an entry says neither, it holds for both as far as the sources go.
- **Sources**: as precisely as possible (the keys are under "Sources" below).
- **Standing**:
  - **confirmed**: an independent source agrees: the JieLi SDK, FM-1-RE's
    documents, a datasheet, the panel sources, or a spec-side black-box
    experiment in fwtest (E-n). An experiment confirms how fwtest behaves,
    not how the chip behaves; the sources say which kind of confirmation it
    is.
  - **emulator-only**: the only source is the emulator model, which was
    partly written from GPL code. Rely on it in fwtest, but prefer to confirm
    it with your own black-box test.
  - **other chip (SDK63)**: the source is a JieLi SDK for different chips
    (SDK63), whose peripheral looks like the FM-1's chip's. A strong hint,
    never a confirmation for the FM-1's chip: the two chips are known to
    differ elsewhere (HW-75).
  - **superseded by HW-n**: no longer true; see the newer entry.
- **Needed by**: the milestone that first needs it.

Numbers are hexadecimal with `0x`; registers are 32 bits wide and
little-endian unless an entry says otherwise. "Bit n" counts from bit 0, the
least significant. Register names are the JieLi SDK's.

## Sources

| Key | Source |
|-----|--------|
| SDK | JieLi AC79 SDK, `Jieli-Tech/fw-AC79_AIoT_SDK` (Gitee), commit `5fa84a9b2f723a5e9337ad79dc2ad741fc98fe2d`, Apache-2.0 (PROVENANCE P-2, P-10). `WL82.h` and `csfr.h` are vendored in `vendor/jieli-sdk/include_lib/driver/cpu/wl82/asm/`; the other files cited are at the same commit and path prefix. Line numbers refer to that commit. |
| SDK63 | JieLi AC63 Bluetooth SDK, `https://github.com/Jieli-Tech/fw-AC63_BT_SDK`, commit `fdc018de81629e21e594d677cf05f87d288be0f0` (2025-03-18), Apache-2.0 (its `LICENSE`, SHA-256 `c71d239d…5d0ab4`) (PROVENANCE P-48). **Different chips:** its `cpu/br23/`, `cpu/br25/` and `cpu/bd29/` parts, not the FM-1's chip. Read file by file, not vendored; line numbers refer to that commit. |
| RE | AL-255/FM-1-RE (GitHub, WTFPL), commit `ec832f281ca165a7d5e0722985f3acb1465046d5`: its hardware and boot documents `docs/reversing/01-hardware-map.md`, `docs/io/01-boot.md`, `docs/io/03-audio-dac.md`, `docs/io/08-display.md`, `docs/io/09-storage.md` (PROVENANCE P-9); since SR-8 also `docs/io/05-midi.md`, `docs/io/06-usb.md` and `docs/reversing/04-subsystems.md` (PROVENANCE P-41); since SR-9 also `docs/architecture.md`, `docs/io/11-ota-protocol.md`, `docs/io/12-v15-reflash-proof.md` and `docs/reversing/02-boot-and-runtime.md` (PROVENANCE P-51). Only their hardware facts are used here. Since evening-1024 `docs/io/09-storage.md` is for the spec side only (CONTRIBUTING.md); the firmware side takes its facts from here. |
| JL7911B | Zhuhai Jieli Technology's "AC7911B Datasheet", V1.1, 2021-09-03, 16 pages, as LCSC serves it from `https://atta.szlcsc.com/upload/public/pdf/source/20241209/7B2C0C261932781E1CA5530337098F4C.pdf`, accessed 2026-10-25, SHA-256 `c7f35c89…2bf1022` (PROVENANCE P-56). The AC7911B is one of the AC791N's packages (the SDK builds its AC791N apps for it, `board_7911B_cfg.h`); which package the FM-1 carries is not known, so its pin numbers are not the FM-1's, only its pin functions are used. Page numbers as printed. |
| DS | Sitronix ST7789V datasheet, version 1.3 (2014-03), 316 pages, from `https://www.newhavendisplay.com/appnotes/datasheets/LCDs/ST7789V.pdf`, SHA-256 `8ecf0e43…5d04ca1` (PROVENANCE P-11). Page numbers as printed. |
| PUYA | Puya Semiconductor's P25Q80H datasheet ("Ultra Low Power, 8M-bit Serial Multi I/O Flash Memory"), Ver1.3, 2017-05-30, 71 pages, as LCSC serves it from `https://datasheet.lcsc.com/lcsc/PUYA-P25Q80H-SSH-IT_C194872.pdf`, accessed 2026-10-24, SHA-256 `d54401e9…bb12ea6c` (PROVENANCE P-53). Page numbers as printed. Not copied into this repository. It describes the part fwtest's chip identifies as (HW-76). |
| PANEL | The FM-1's printed panel labels, from two sources that agree: the owner's screenshot of the F-Emulator app's panel with its default labels, `docs/sources/panel-app-default-labels.png` (secondary: the app's drawing of the panel); and M-VAVE's product photo of the FM-1, `https://www.m-vave.com/images/products/fm-1.webp` on `https://www.m-vave.com/product.html?id=fm-1`, accessed 2026-10-22, SHA-256 `e610a746…df14b95`, not copied into this repository (PROVENANCE P-12). Only the printed labels are taken from them. The owner chose these two sources. |
| MAN | M-VAVE's user manuals: the FM-1's, the English part (pages 1-12) of `https://m.media-amazon.com/images/I/A1WOydif9HL.pdf`, SHA-256 `69bfea10…8b715da`, accessed 2026-10-24 (PROVENANCE P-41); the SMK-37 Pro's, as `https://www.manualslib.com/manual/4132288/M-Vave-Smk-37-Pro.html` shows it, accessed 2026-10-24 (PROVENANCE P-42). Neither copied into this repository. Only what they say about the connections is used. |
| MPLUS | Manuals+'s "M-VAVE SMK-37 PRO MIDI Controller User Manual", `https://manuals.plus/asin/B0GQZP7C8G.pdf`, 13 pages, SHA-256 `77d9d537…3e3745`, accessed 2026-10-24, supplied by the owner and checked by the planning conversation, not fetched by a session here (PROVENANCE P-49). A third party's write-up, not M-VAVE's manual: secondary, it never confirms an entry on its own. Not copied into this repository. |
| TC | The pinned JieLi toolchain (PROVENANCE P-1, P-36): its assembler and disassembler (clang's integrated assembler and `objdump`), and the code its compiler emits for C whose meaning is known. It is the vendor's compiler for this CPU, so how its code uses an instruction says what the instruction does; it carries no documents. |
| HARNESS | docs/HARNESS.md, fwtest's manual. It is the spec side's own description of fwtest, so it never confirms an entry on its own. |
| E-n | A spec-side black-box experiment: a small image run in fwtest (the pinned image, `config/fwtest-image`). Its result is stated in the entry. C-SPEC-EXPERIMENTS re-runs every one in CI, so a cited result that stops holding fails CI. |

---

## 1. The raw image and boot (M0d)

### HW-1: Load address and entry
- Fact: In fwtest, the image is a flat binary whose first byte is at
  `0x02000000`, the start of the code window, and core 0 starts executing
  at that first byte. Link the image to run there.
- Sources: HARNESS ("The raw image"); E-1: an image whose first
  instructions record the registers ran from its first byte.
- Standing: confirmed (E-1)
- Needed by: M0d

### HW-2: Registers at entry
- Fact: In fwtest, at the first instruction r0 = `0x01C7FC00` and every
  other register reads 0, including `sp`, `usp`, `ssp`, `icfg` and `psr`.
  No stack is usable until the image sets one. `cnum` reads 0 (core 0).
- Sources: HARNESS ("The raw image"); E-1: r0 = `0x01C7FC00`; r2 to r15,
  `sp`, `usp`, `ssp`, `icfg`, `psr` and `cnum` read 0. r1 could not be
  observed (the experiment needed it first): for r1 the only source is
  HARNESS.
- Standing: confirmed (E-1)
- Needed by: M0d

### HW-3: Core 0 starts in user mode
- Fact: In fwtest, core 0 starts in user mode. An interrupt taken in user
  mode continues on the supervisor stack pointer `ssp` (the user `sp` is
  kept in `usp`), and its return goes back to user mode and `usp`. An
  interrupt taken in supervisor mode stays on the current stack. So `ssp`
  must point at a valid stack before interrupts are enabled.
- Sources: HARNESS ("The raw image"); the emulator model.
- Standing: emulator-only
- Needed by: M0d, M1

### HW-4: The block r0 points to at entry
- Fact: In fwtest, r0 points to a 64-byte block in RAM whose first word
  holds `0x01C7FC40` (the address just past the block) and whose other
  bytes are 0. On the chip, the loader that starts an installed app passes
  a boot-parameter block in r0; its contents are not described here (see
  Q-11).
- Sources: HARNESS ("The raw image"); E-1: the block's first word is
  `0x01C7FC40`, the other 15 words 0; RE `docs/io/01-boot.md` §3 (a pointer
  in r0 at the hand-over).
- Standing: confirmed (E-1)
- Needed by: M0d

### HW-5: The code window and the flash chip
- Fact: In fwtest, the code window shows the 1 MiB flash chip from chip
  offset `0x4000`: window address `0x02000000 + n` reads chip offset
  `0x4000 + n`. At the start fwtest writes the image into the chip at
  offset `0x4000`, so the window's first bytes are the image and the bytes
  past it are the rest of the chip. With no `--flash` file the rest is
  erased and reads `0xFFFFFFFF`. Writes to the window are ignored; changes
  made to the chip through SPI0 show through the window (HW-47).
- Sources: HARNESS ("The raw image": the flash chip, past the image,
  writes to the window); E-1: the first word past the image and the word
  4 KiB further both read `0xFFFFFFFF`.
- Standing: confirmed (E-1)
- Needed by: M0d

### HW-6: Main RAM on the chip
- Fact: On the chip, main RAM is 512 KiB at `0x01C00000` to `0x01C7FFFF`.
  Its top 512 bytes, from `0x01C7FE00`, hold the interrupt vector table
  (HW-18), and the word at `0x01C7FFF8` inside it is also core 1's start
  address (HW-9). Below the table the SDK's own layout reserves
  `0x01C7FD4C` to `0x01C7FDFF` (52 bytes of boot information, then 128
  bytes of update data), which the chip's loader and update path may use;
  FM-1-RE finds the boot information block at `0x01C7FD50`. A raw image in
  fwtest doesn't need that area, but keeping out of it keeps an image
  compatible with the chip's loader. Keep code, data and stacks in this
  512 KiB, below `0x01C7FD4C`.
- Sources: SDK `cpu/wl82/sdk_ld_sfc.c` lines 14, 23-24, 38 (RAM0 from
  `0x01C00000`, its size `0x01C7FE00 - 0x01C00000 - 52 - 128`, the update
  area from `0x01C7FE00 - 128`); SDK `hwi.h` line 123 (`ISR_ENTRY`); RE
  `docs/io/01-boot.md` §1 and RE `docs/reversing/01-hardware-map.md`
  ("Address space").
- Standing: confirmed (SDK, RE)
- Needed by: M0d

### HW-7: RAM in fwtest
- Fact: In fwtest, main RAM is 1 MiB at `0x01C00000` (more than the chip
  has; HW-6), all zero at the start except the block of HW-4. There are two
  more RAM banks: 256 KiB at `0x01F00000` and 512 KiB at `0x04000000`. All
  three can hold code and data and can be saved with `--ram`. Whether the
  chip has the last two, and of what size, is open (Q-1): don't rely on
  them.
- Sources: HARNESS ("The raw image", "--ram"); E-1: a written word reads
  back at `0x01C7FDFC`, `0x01CFFFFC`, `0x01F3FFFC` and `0x0407FFFC`.
- Standing: confirmed (E-1)
- Needed by: M0d

### HW-8: Two cores, and which one is running
- Fact: The chip has two cores. The special register `cnum` reads the
  number of the core executing (0 or 1).
- Sources: SDK `include_lib/driver/cpu/wl82/asm/cpu.h` line 43
  (`CPU_CORE_NUM 2`) and line 82 (`cnum`); SDK `csfr.h` line 245 (`CNUM`);
  E-4: `cnum` read 0 on core 0 and 1 on core 1.
- Standing: confirmed (SDK, E-4)
- Needed by: M0d

### HW-9: Releasing core 1
- Fact: Core 1 does not run until core 0 releases it. To release it, put
  core 1's start address in the word at `0x01C7FFF8`, then set bit 3 of
  `C1_CON` (`0x01EEE004`, the second word of the `corex2` block at
  `0x01EEE000`). Core 1 then starts at the address in that word and runs
  alongside core 0. That word is also the vector table's slot for source
  126 (software interrupt 6, HW-18): don't use software interrupt 6 while
  the word holds core 1's start address, and don't overwrite the word
  before core 1 has started.
- Sources: SDK `csfr.h` lines 41, 106-112 (`C1_CON`); SDK `hwi.h`
  lines 114-123 (source 126 is `0x01C7FE00 + 4 × 126` = `0x01C7FFF8`); RE
  `docs/io/01-boot.md` §1 (the word at `0x01C7FFF8` holds core 1's start
  address) and §5.2 (bit 3 of `C1_CON`); E-4: with the entry in that word,
  setting `C1_CON` bit 3 started core 1 there.
- Standing: confirmed (RE, E-4)
- Needed by: M1

### HW-10: Core 1's state when it starts, in fwtest
- Fact: In fwtest, core 1 starts in supervisor mode, and its start address
  must be in the code window or in RAM. Its stack pointers hold values the
  firmware must not rely on: core 1's first instructions set its own `sp`
  (and `ssp`, `usp` if it will use them). fwtest releases core 1 once;
  later writes do not restart it. Warning: fwtest also releases core 1 when
  bit 3 of `JL_CLOCK->SYS_DIV` (`0x00010008`) goes from 0 to 1, so leave
  that bit alone unless releasing core 1 is meant; use `C1_CON` (HW-9).
  Whether a raw image on the chip can rely on the same release is part of
  Q-11.
- Sources: the emulator model; E-4 (core 1 ran on stacks it set itself).
- Standing: emulator-only
- Needed by: M1

## 2. Clocks and timers (M1)

### HW-11: The clocks
- Fact: On the chip, the board's reference crystal is 24 MHz. In fwtest
  the clock is fixed: each core executes one instruction per cycle at
  240 MHz (240 000 cycles an emulated millisecond) from the start, writes
  to the clock registers have no effect, and no clock set-up is needed. How
  to set the clocks up on the chip, and which system clock rates it
  supports, is open (Q-2).
- Sources: RE `docs/io/01-boot.md` §5.2 (the reference clock detected is
  24 MHz on the FM-1); HARNESS ("Time": 240 000 cycles a millisecond, one
  instruction of core 0 a cycle); the emulator model (core 1 at the same
  rate, the clock registers).
- Standing: confirmed (RE)
- Needed by: M1

### HW-12: Timer registers
- Fact: The six timers `JL_TIMER0` to `JL_TIMER5` are at `0x00010400`,
  `0x00010500`, ..., `0x00010900` (one every `0x100`), each with `CON` at
  +0, `CNT` at +4, `PRD` at +8 and `PWM` at +12.
- Sources: SDK `WL82.h` lines 15-16, 384-409.
- Standing: confirmed (SDK)
- Needed by: M1

### HW-13: TIMER4, the free-running time base
- Fact: In fwtest, setting `JL_TIMER4->CON` bit 0 starts `JL_TIMER4->CNT`
  counting up at 24 MHz of emulated time.
- Sources: E-3: TIMER4 was started at the beginning of a run that ended
  at 52.300 emulated ms (`result.json`), when it read 1 255 200 (52.3 ms ×
  24 MHz); between two TIMER5 interrupts 100 µs apart it advanced by 2400.
- Standing: confirmed (E-3)
- Needed by: M1

### HW-14: TIMER4 and TIMER5 details in fwtest
- Fact: In fwtest, `JL_TIMER4->CNT` reads 0 while `CON` bit 0 is clear,
  writing any value to `CNT` restarts the count from 0, and TIMER4 raises
  no interrupt (source 62 never becomes pending). TIMER5 ignores its `CON`
  bits 4-7: it always counts a 6 MHz clock (HW-15).
- Sources: the emulator model.
- Standing: emulator-only
- Needed by: M1

### HW-15: TIMER5, a periodic interrupt
- Fact: In fwtest, setting `JL_TIMER5->CON` bit 0 makes TIMER5 raise
  interrupt source 63 every `PRD` counts of a 6 MHz clock (`PRD` = 600 gives
  100 µs). `CON` bit 15 reads 1 while the interrupt is pending; writing
  `CON` with bit 14 set clears it (write bit 0 set as well to keep the timer
  running).
- Sources: SDK `hwi.h` line 109 (`IRQ_TIMER5_IDX` 63); E-3: with `PRD` =
  600, interrupts came every 100 µs of emulated time (523 by 52.3 ms, and
  TIMER4, HW-13, advanced 2400 between two), acknowledged as above.
- Standing: confirmed (SDK, E-3)
- Needed by: M1

### HW-16: TIMER0 to TIMER3
- Fact: In fwtest, `JL_TIMERn->CON` bits 0-1 non-zero run timer n (n = 0
  to 3); `CON` bits 4-7 select a prescaler of the 24 MHz clock. The timer
  counts up from `CNT` and, on reaching `PRD`, raises interrupt source
  4 + n and starts again from 0. `CON` bit 15 reads 1 while pending;
  writing `CON` with bit 14 set clears it. Prescaler setting 2 divides by
  16; the other settings were not measured (Q-3).
- Sources: SDK `hwi.h` lines 42-45 (`IRQ_TIMER0_IDX` 4 to
  `IRQ_TIMER3_IDX` 7); E-3: TIMER0 with prescaler setting 2 and `PRD` 1500
  interrupted every 1 ms (52 by 52.3 ms), and `CON` read `0x8021` in its
  handler (pending, prescaler 2, running).
- Standing: superseded by HW-48
- Needed by: M1

### HW-17: The core tick timer
- Fact: Each core has a tick timer, `TTMR_CON`, `TTMR_CNT`, `TTMR_PRD`:
  core 0's at `0x01EEF0EC`, `0x01EEF0F0`, `0x01EEF0F4`, core 1's `0x200`
  higher (`0x01EEF2EC` ...). Its interrupt source is 3. In fwtest (core 0's
  only, HW-22), `TTMR_CON` bit 0 runs it, bit 7 reads 1 while its interrupt
  is pending, and writing bit 6 acknowledges it (write bit 0 as well to
  keep it running); it fires every 10 ms whatever `TTMR_PRD` holds. On the
  chip the period comes from `TTMR_PRD` (Q-4).
- Sources: SDK `csfr.h` lines 208-214 (one block per core, `0x200`
  apart), 274-276; SDK `hwi.h` line 41 (`IRQ_TICK_TMR_IDX` 3); E-3: with
  `TTMR_PRD` = 1234 it interrupted every 10 ms (5 by 52.3 ms),
  acknowledged as above.
- Standing: confirmed (SDK, E-3)
- Needed by: M1

## 3. Interrupts (M1)

### HW-18: The vector table
- Fact: The handler for interrupt source n is the 32-bit address in the
  word at `0x01C7FE00 + 4 × n`, in RAM. The firmware writes the table. The
  slot of source 126 (`0x01C7FFF8`) is also core 1's start address (HW-9);
  the slot of source 127 (`0x01C7FFFC`) has no other use known here. In
  fwtest both cores use this one table.
- Sources: SDK `hwi.h` lines 114-123 (`ISR_ENTRY 0x1c7fe00`, sources up
  to 127); RE `docs/io/01-boot.md` §1 and §4.1; E-3, E-9: handlers
  installed this way ran.
- Standing: confirmed (SDK, RE, E-3)
- Needed by: M1

### HW-19: Interrupt source numbers
- Fact: The sources this spec uses: 3 core tick timer, 4-7 TIMER0-3,
  11 the audio link `JL_ALNK0` (the SDK's `IRQ_ALNK_IDX`), 16 SPI1 (LCD),
  24 SARADC, 63 TIMER5, 120-127 software interrupts 0-7. (TIMER4 is
  source 62 on the chip; it never fires in fwtest, HW-14.) The SDK's
  `hwi.h` lists the rest.
- Sources: SDK `hwi.h` lines 41-121.
- Standing: confirmed (SDK)
- Needed by: M1

### HW-20: Enabling a source, and its priority
- Fact: Each core has its own enable and priority words, `ICFG00` to
  `ICFG31`: core 0's at `0x01EEF100` to `0x01EEF17C`, core 1's at
  `0x01EEF300` to `0x01EEF37C`. Source n uses 4 bits of word n / 8, at bit
  position 4 × (n mod 8): bit 0 enables it, bits 1-3 are its priority 0-7.
  A higher number is a higher priority. A source interrupts only the cores
  whose words enable it.
- Sources: SDK `csfr.h` lines 208-214, 280-312; SDK `hwi.h` line 135
  ("0~7, larger is higher"); RE `docs/io/01-boot.md` §4.1 (the 4-bit
  encoding and the two arrays); E-3, E-9 (sources enabled this way).
- Standing: confirmed (SDK, RE, E-3)
- Needed by: M1

### HW-21: The global interrupt gates
- Fact: A core takes interrupts only while both gates are open: bit 8 of
  its special register `icfg` (the master enable; not to be confused with
  the `ICFG00`-`ICFG31` words of HW-20) and the enable set by the
  instruction `sti` (cleared by `cli`). At entry `icfg` reads 0, so bit 8
  is clear: set it and execute `sti` before expecting interrupts.
- Sources: SDK `include_lib/driver/cpu/wl82/asm/irq.h` lines 19-21 (bit 8
  of `icfg` as the enable); RE `docs/io/01-boot.md` §4.1, §5.2; E-1
  (`icfg` 0 at entry); E-3 (interrupts taken after setting `icfg` bit 8
  and executing `sti`).
- Standing: confirmed (SDK, RE, E-3)
- Needed by: M1

### HW-22: Entering and leaving a handler, in fwtest
- Fact: In fwtest, when a core takes an interrupt the address to return to
  is put in the special register `reti` and the core jumps to the handler;
  the handler returns with `rti`. A handler compiled with the toolchain's
  interrupt function attribute returns correctly. A running handler can be
  interrupted by a pending source of higher priority only after it has
  stored `reti` to its stack, and only until it loads `reti` back; sources
  of the same or lower priority wait until it returns. When several enabled
  sources are pending, the one with the highest priority is taken; between
  equal priorities the order is not specified. fwtest models only core 0's
  tick timer and software-interrupt words (HW-17, HW-23), and one vector
  table for both cores. Whether the chip behaves the same way is Q-10.
- Sources: the emulator model; E-3 and E-9 show only that handlers written
  with the toolchain's interrupt attribute run repeatedly and return.
- Standing: emulator-only
- Needed by: M1

### HW-23: Software interrupts
- Fact: Writing bit b (0-7) to `ILAT_SET` makes source 120 + b pending;
  writing bit b to `ILAT_CLR` clears it. Core 0's are at `0x01EEF1A0` and
  `0x01EEF1A4`, core 1's `0x200` higher (fwtest has core 0's only, HW-22).
  The handler must clear its source, or it is taken again on return.
- Sources: SDK `csfr.h` lines 208-214, 322-323; SDK `cpu.h` line 59 (the
  SDK raises one this way); E-3: `ILAT_SET` bit 0 ran the handler of
  source 120 once, which cleared it.
- Standing: confirmed (SDK, E-3)
- Needed by: M1

### HW-24: Waiting for an interrupt, in fwtest
- Fact: In fwtest, the instruction `idle` waits until something is due:
  time skips ahead to the next timed event, and with interrupts enabled the
  pending one is then taken. A loop that only reads TIMER4 is skipped the
  same way. Waiting therefore costs almost no instructions, and captures may
  come late while core 0 waits (HARNESS, "Time"). What `idle` does on the
  chip with interrupts masked is part of Q-10.
- Sources: HARNESS ("Time"); E-3, E-9 (main loops of `idle` woke for each
  interrupt).
- Standing: confirmed (E-3)
- Needed by: M1

## 4. The debug channel (M0d)

### HW-25: The debug message register in fwtest
- Fact: `DBG_MSG` is at `0x01EEE244` (in the `corex2` block, next to
  `DBG_WR_EN` at `0x01EEE240` and `DBG_MSG_CLR` at `0x01EEE248`). In fwtest
  each 32-bit write to `DBG_MSG` appends the word's 4 bytes, lowest first,
  to the console that `--console` saves. A byte or halfword write appends 4
  bytes too: the bytes written, merged into the word last written. Write
  whole words.
- Sources: SDK `csfr.h` lines 106-108, 136-138; HARNESS ("--console");
  E-2: word writes appended "abcd" and "12:\n"; a byte write of "X" then
  appended "X2:\n" and a halfword "YZ" appended "YZ:\n".
- Standing: confirmed (SDK, E-2)
- Needed by: M0d

### HW-26: Markers in RAM
- Fact: A marker word or heartbeat counter at a fixed RAM address is
  visible to fwtest through `--ram` captures and `--watchdog` (any address
  in the RAM of HW-7). On the chip, the SDK marks `DBG_MSG` read-only, so
  the console of HW-25 may not exist there (Q-5).
- Sources: HARNESS ("--ram", "--watchdog"); SDK `csfr.h` line 137
  (`___RO` `DBG_MSG`); E-1, E-3 (results read back from RAM with `--ram`;
  `--watchdog` was not exercised).
- Standing: confirmed (SDK, E-1)
- Needed by: M0d

## 5. The LCD (M2)

### HW-27: The panel
- Fact: The display is a 240 × 240 pixel colour TFT driven by a Sitronix
  ST7789-family controller, on SPI1. This spec assumes the ST7789V's
  command set and timing (DS). Pixels are 16-bit: 5 bits red, 6 green, 5
  blue.
- Sources: RE `docs/io/08-display.md` §1 ("240×240 RGB565 TFT on SPI1",
  ST7789-style commands); DS; HARNESS ("lcd-WHEN.png").
- Standing: confirmed (RE, DS)
- Needed by: M2

### HW-28: SPI1's registers
- Fact: `JL_SPI1` is at `0x00011D00`: `CON` +0, `BAUD` +4, `BUF` +8, `ADR`
  +12, `CNT` +16.
- Sources: SDK `WL82.h` lines 548-560.
- Standing: confirmed (SDK)
- Needed by: M2

### HW-29: Sending bytes to the LCD
- Fact: Writing a byte to `JL_SPI1->BUF` sends it to the panel. Writing a
  count to `JL_SPI1->CNT` sends that many bytes by DMA from the address in
  `JL_SPI1->ADR`. `CON` bit 15 reads 1 when a transfer is done; setting
  `CON` bit 13 makes a finished transfer raise interrupt source 16; writing
  `CON` with bit 14 set clears it. In fwtest a transfer finishes at once,
  the DMA may read RAM or the code window, and no other set-up of SPI1 is
  needed. On the chip SPI1 also needs its clock (`BAUD`), mode and pins
  set up (Q-6).
- Sources: RE `docs/io/08-display.md` §1 (`CON` bit 15 pending, bit 14
  clear, bit 13 interrupt enable; bytes and DMA bursts); SDK `hwi.h`
  line 56 (`IRQ_SPI1_IDX` 16); E-5: a whole screen sent by DMA from RAM,
  480 bytes a row, and squares sent byte by byte, all drawn.
- Standing: confirmed (RE, E-5)
- Needed by: M2

### HW-30: Command or data
- Fact: The panel's data/command line is PC8, bit 8 of `JL_PORTC->OUT`
  (`0x00050080`): low while a command byte is sent, high for its parameters
  and for pixel data. In fwtest the line's level when each byte (or each
  DMA transfer) starts decides how it is taken, and the pin needs no
  set-up. FM-1-RE also sees bit 7 (PC7) toggled with it, probably the
  panel's chip select (Q-6).
- Sources: SDK `WL82.h` lines 252, 269 (`JL_PORTC`, `OUT` at +0); RE
  `docs/io/08-display.md` §1 (bits 7 and 8 of `0x50080`, which FM-1-RE
  rates medium confidence); E-5.
- Standing: confirmed (RE, E-5)
- Needed by: M2

### HW-31: The commands fwtest acts on
- Fact: fwtest's panel acts on: column address set `0x2A` and row address
  set `0x2B` (4 parameter bytes each: start and end, each high byte
  first); memory write `0x2C` (then pixels, 2 bytes each, high byte first,
  filling the window row by row and wrapping to its start); software reset
  `0x01` (the picture becomes black). `0x36` and `0x3A` take one parameter
  byte that fwtest ignores (it always takes 16-bit pixels). Display off and
  on (`0x28`, `0x29`) and inversion off and on (`0x20`, `0x21`) are
  accepted, but the captured picture shows the pixels as written either
  way. Other commands are accepted and ignored.
- Sources: DS pages 163 (`SWRESET`), 188-190 (`INVOFF`, `INVON`), 194-196
  (`DISPOFF`, `DISPON`), 198-203 (`CASET`, `RASET`, `RAMWR`), 215
  (`MADCTL`), 224 (`COLMOD`); E-5: the window commands and pixel order as
  above, the picture unchanged after inversion on and display off, black
  after a software reset.
- Standing: confirmed (DS, E-5)
- Needed by: M2

### HW-32: The panel controller's own requirements
- Fact: On the chip, the controller needs: 5 ms after a software reset
  before the next command, and 120 ms after a software reset sent in sleep
  mode before sleep out; 5 ms after sleep out (`0x11`) before the next
  command, and 120 ms before a sleep in; the pixel format set to 16 bits
  (`0x3A` with `0x55`) to write 16-bit pixels; sleep out and display on
  (`0x29`) before anything shows. fwtest needs none of these delays, and
  doesn't check them: on the chip a firmware that skips them may show
  nothing.
- Sources: DS pages 163 (`SWRESET`), 184 (`SLPOUT`), 196 (`DISPON`), 224
  (`COLMOD`).
- Standing: confirmed (DS)
- Needed by: M2

## 6. Keys, encoders, the pot and LEDs (M3)

### HW-33: The key matrix's columns, in fwtest
- Fact: In fwtest the matrix has 11 columns, selected through two cascaded
  8-bit shift registers with output latches: serial data on PA4, shift
  clock on PA3 (each rising edge shifts in one bit), latch clock on PA1 (a
  rising edge copies the 16 shifted bits to the outputs). The 16 bits go
  most significant first; output bit c drives column c (0-10; bits 11-15
  are not used). A column is selected while its bit is 0. The pins are
  bits of `JL_PORTA->OUT` (`0x00050000`) and need no set-up in fwtest.
  Whether the board is wired this way is Q-7.
- Sources: SDK `WL82.h` lines 252, 263 (`JL_PORTA`); E-6: a scan selecting
  one column at a time this way saw every key and encoder contact.
- Standing: confirmed (E-6)
- Needed by: M3

### HW-34: The key matrix's rows, in fwtest
- Fact: In fwtest the matrix has 6 rows, read as inputs: row 0 on PA0,
  rows 1-4 on PA5 to PA8, row 5 on PB7, through `JL_PORTA->IN`
  (`0x00050004`) and `JL_PORTB->IN` (`0x00050044`). A row reads 0 while a
  closed key or encoder contact connects it to a selected column, and 1
  otherwise, with no pin set-up. Whether the board is wired this way, and
  what pull-ups it needs, is Q-7.
- Sources: SDK `WL82.h` lines 252-253, 263, 266 (`OUT`, `IN`; ports A
  and B); E-6.
- Standing: confirmed (E-6)
- Needed by: M3

### HW-35: Where each fwtest key is in the matrix
- Fact: In fwtest, key N closes the contact at (column, row):

  | Row | Column 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
  |-----|---|---|---|---|---|---|---|---|---|---|---|
  | 1 | 5 | 11 | 4 | 10 | 3 | 9 | 2 | 8 | - | - | - |
  | 2 | 34 | 35 | 36 | 37 | 38 | 40 | 39 | 13 | 7 | 6 | 12 |
  | 3 | 23 | 24 | 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 | 33 |
  | 4 | 0 | 1 | 15 | 14 | 17 | 16 | 19 | 18 | 20 | 21 | 22 |

  Rows 0 and 5 hold no keys (encoder contacts only, HW-38); "-" is no key.
- Sources: E-6: each key pressed alone closed exactly the contact above.
- Standing: confirmed (E-6)
- Needed by: M3

### HW-36: The panel's printed labels
- Fact: The FM-1's panel has, as printed: 14 buttons, `OCT-` and `OCT+`
  (lower left), and two rows of six: `FX`, `SEL`, `ENV`, `LFO`, `EDIT`,
  `GLO`, then `HOME`, `SAVE`, `ARP`, `SEQ`, `PLAY`/`STOP` (one button),
  `REC`; eight knobs, `MASTER`, `SELECT`, `PRESETS`, `ALGORITHM` (left of
  the screen) and `KNOB1` to `KNOB4` (right of it); and 27 keys: 16 lower
  keys and 11 raised keys between them, in groups of 3, 2, 3, 2 and 1 like
  a keyboard's black keys. Ten raised keys carry second labels: `OP1`,
  `OP2`, `OP3`, `OP4`, `OP5`, `OP6`, `PIT`, `GLO`, `MONO`, `POLY`; the last
  raised key has none.
- Sources: PANEL (the app screenshot and M-VAVE's product photo agree on
  every label above).
- Standing: confirmed (PANEL)
- Needed by: M3

### HW-37: Which button and key each fwtest key number is
- Fact: fwtest keys 0-13 are the buttons `OCT-` (0), `OCT+` (1), `FX` (2),
  `SEL` (3), `ENV` (4), `LFO` (5), `EDIT` (6), `GLO` (7), `HOME` (8),
  `SAVE` (9), `ARP` (10), `SEQ` (11), `PLAY`/`STOP` (12), `REC` (13).
  Keys 14-40 are the 27 keys in order from left to right, lower and raised
  keys interleaved as on a keyboard: 14 is the leftmost lower key, 15 the
  first raised key (`OP1`), 16 the second lower key, and so on, to 40, the
  rightmost lower key; the last raised key (no second label) is 39.
- Sources: the emulator model (which panel control each fwtest key number
  is); PANEL (the labels and layout, HW-36: 16 lower keys and 11 raised
  keys in groups of 3, 2, 3, 2, 1, which interleave this way).
- Standing: emulator-only
- Needed by: M3

### HW-38: The encoders, in fwtest
- Fact: In fwtest each encoder has two contacts in the matrix, A and B,
  both open at rest: encoder 0: A at (column 0, row 0), B at (1, 0); 1:
  (2, 0), (3, 0); 2: (8, 1), (9, 1); 3: (8, 0), (9, 0); 4: (6, 0), (7, 0);
  5: (4, 0), (5, 0); 6: (0, 5), (1, 5). One detent is a full quadrature
  cycle of four changes, 2 ms apart. In the direction an input script
  calls clockwise (`enc N +C`): B closes, A closes, B opens, A opens. In
  the other: A closes, B closes, A opens, B opens. Which way the knob
  physically turns for each is Q-7.
- Sources: HARNESS ("Input scripts"); E-6: one detent each way on each
  encoder gave these contacts in this order.
- Standing: confirmed (E-6)
- Needed by: M3

### HW-39: Which knob each fwtest encoder number is
- Fact: fwtest encoders 0-6 are the knobs `SELECT` (0), `ALGORITHM` (1),
  `KNOB1` (2), `KNOB2` (3), `KNOB3` (4), `KNOB4` (5), `PRESETS` (6).
  `MASTER` is not an encoder: it is the pot (HW-41).
- Sources: the emulator model; PANEL (the labels, HW-36).
- Standing: emulator-only
- Needed by: M3

### HW-40: The pot and the SARADC
- Fact: The SARADC, `JL_ADC`, is at `0x00013100`: `CON` +0, `RES` +4. In
  fwtest: `CON` bits 8-11 select the channel, bit 4 enables, and writing
  bit 6 with bit 4 starts a conversion, which finishes at once; bit 7 then
  reads 1, and `RES` holds the 10-bit result (0-1023). Each conversion is
  started by a write with bits 4 and 6 (and the channel) set. The pot is
  channel 4: 900 until a script sets it. Channel 3 reads 640 and the others
  512, fixed in fwtest. Which channel carries the pot on the chip, and what
  the others carry, is Q-8.
- Sources: SDK `WL82.h` lines 723-729 (`JL_ADC`); HARNESS ("pot V");
  E-8: channel 4 read 900, then the script's 300, 0 and 1023, with the
  bits above; channel 3 read 640, the others 512.
- Standing: confirmed (SDK, E-8)
- Needed by: M3

### HW-41: The SARADC's interrupt, and which knob the pot is
- Fact: In fwtest, with `JL_ADC->CON` bit 5 set a finished conversion
  raises interrupt source 24. Writing `CON` with bit 6 set and bit 4 clear
  acknowledges it; that write also clears the enable bit 4, which the next
  start write sets again. The pot is the `MASTER` knob (HW-36).
- Sources: SDK `hwi.h` line 65 (`IRQ_SARADC_IDX` 24); the emulator model
  (the interrupt condition, the acknowledge, `MASTER`).
- Standing: superseded by HW-60 (and HW-61)
- Needed by: M3

### HW-42: The LEDs, in fwtest
- Fact: In fwtest each of the 41 LEDs belongs to the key or button with
  the same number. LED N is lit while key N's column is selected (HW-33)
  and the LED line of key N's row is high: row 1 PA9, row 2 PA10 (bits of
  `JL_PORTA->OUT`), row 3 PH6, row 4 PH9 (bits of `JL_PORTH->OUT`,
  `0x000501C0`). LEDs and keys share the column selection, so the firmware
  multiplexes them; `leds.csv` reports each LED's share of time lit.
  Whether the board has an LED for every key, wired this way, is Q-7.
- Sources: SDK `WL82.h` lines 252, 263, 284 (`JL_PORTA`, `JL_PORTH`);
  HARNESS ("leds.csv"); E-7: each line high with one column selected lit
  exactly the LED of the key at that row and column (HW-35).
- Standing: confirmed (E-7)
- Needed by: M3

## 7. Audio output (M4)

### HW-43: The audio link's registers
- Fact: `JL_ALNK0` is at `0x00012E00`: `CON0` +0, `CON1` +4, `CON2` +8,
  `CON3` +12, `ADR0` to `ADR3` at +16 to +28, `LEN` +32. Its interrupt
  source is 11.
- Sources: SDK `WL82.h` lines 664-677; SDK `hwi.h` line 50
  (`IRQ_ALNK_IDX` 11).
- Standing: confirmed (SDK)
- Needed by: M4

### HW-44: The output buffer and sample format, in fwtest
- Fact: In fwtest the output plays from a buffer in RAM at the address in
  `JL_ALNK0->ADR3`: two halves, one after the other, each of `LEN` 32-bit
  words. Words alternate left, right, left, right (`LEN` / 2 stereo frames
  a half). Write each sample as a 24-bit signed value in the word's low
  bits, sign-extended: fwtest's WAV takes the whole word shifted right
  arithmetically by 8 bits, clamped to -32768..32767. Which bits the chip
  uses is Q-9.
- Sources: E-9: with `LEN` 128 each half played 64 frames; the words
  `0x007FFFFF`, `0xFF800000`, `0x01000000` and `0x00000080` came out as
  32767, -32768, 32767 and 0, and a left ramp written as value × 256 came
  out as the values; HARNESS ("audio.wav").
- Standing: confirmed (E-9)
- Needed by: M4

### HW-45: The output's rate and halves
- Fact: In fwtest, writing `JL_ALNK0->CON0` with bit 11 set starts the
  output with half 0; a half lasts `LEN` / 2 frames of 544 / 24 MHz each:
  44 117.6 frames a second (fwtest's WAV header says 44 100). Writing
  `CON0` without bit 11 stops it. `CON0` bit 15 reads the half now
  playing, so the half that has just finished, and is free to refill, is
  that bit inverted. Each finished half sets `CON2` bit 7 and raises
  interrupt source 11 (while `CON0` bit 11 is set and the source is
  enabled); writing `CON2` with bit 3 set clears it.
- Sources: E-9: with `LEN` 128, halves finished 1.451 ms apart (the first
  at 1.459 ms), the first to finish was half 0, and `CON0` bit 15 inverted
  named it each time; RE `docs/io/03-audio-dac.md` §5.3 (the meaning of
  `CON2` bit 7 and of `CON0` bit 15 in this block); HARNESS ("audio.wav").
- Standing: confirmed (RE, E-9)
- Needed by: M4

### HW-46: When fwtest takes the samples, and what it measures
- Fact: In fwtest, a half's words are read from RAM at the moment that half
  finishes playing, so they must be complete by then: refill a half while
  the other plays. `ipb.csv` has one row per finished half, with the
  instructions each core ran since the previous one (HARNESS, "Outputs").
- Sources: HARNESS ("ipb.csv"); the emulator model (when the words are
  read); E-9.
- Standing: emulator-only
- Needed by: M4

## 8. Flash storage (M7, preliminary)

Later: only what fwtest presents. M7 should ask for more through spec
requests. Section 19 completes it (SR-9).

### HW-47: The flash chip, in fwtest
- Fact: In fwtest the flash chip is a 1 MiB SPI NOR chip on SPI0
  (`JL_SPI0`, `0x00011C00`: `CON` +0, `BUF` +8). Its chip select is PD0,
  bit 0 of `JL_PORTD->OUT` (`0x000500C0`), low to select; each command is
  sent while selected and ends when PD0 goes high. A write to `BUF` sends
  one byte; with `CON` bit 12 set the byte received lands in `BUF`. `CON`
  bit 15 reads 1 when a byte is done; writing bit 14 clears it. The chip
  answers JEDEC ID `0x85 0x60 0x14` and understands the common SPI NOR
  commands read `0x03`, fast read `0x0B`, status `0x05`/`0x35`, write
  enable/disable `0x06`/`0x04`, 4 KiB erase `0x20`, 64 KiB erase `0xD8`,
  page program `0x02` (committed when PD0 goes high). Erase and program
  finish at once and the status never reports busy. Changes show through
  the code window (HW-5). Preliminary: M7 should confirm the chip and its
  timing through a spec request (a datasheet for the part).
- Sources: SDK `WL82.h` lines 548-557, 272 (`JL_SPI0`, `JL_PORTD`); RE
  `docs/io/09-storage.md` §1 (the flash is on SPI0; `CON` bits 15 and 14);
  HARNESS ("The flash chip", "Past the image"); the emulator model (JEDEC
  ID, chip select, commands, timing); E-22 (the ID, the status bits, the
  commands and their timing in fwtest; HW-82). Chip select on the chip:
  Q-22.
- Standing: superseded by HW-83
- Needed by: M7

## 9. TIMER0 to TIMER3, corrected (M1)

### HW-48: TIMER0 to TIMER3, and what the acknowledge does in fwtest
- Fact: In fwtest, `JL_TIMERn->CON` bits 0-1 non-zero run timer n (n = 0
  to 3); `CON` bits 4-7 select a prescaler of the 24 MHz clock. The timer
  counts up from `CNT` and, on reaching `PRD`, raises interrupt source
  4 + n and starts again from 0. `CON` bit 15 reads 1 while pending;
  writing `CON` with bit 14 set clears it. That acknowledging write also
  restarts the count, from the value last written to `CNT` (0 after an
  interrupt), and the period from the moment of the write. So in fwtest the
  time between
  two interrupts is `PRD` prescaled counts plus the time from the interrupt
  to the write that acknowledges it: with prescaler setting 2 and `PRD`
  1500, 24 000 time-base ticks (HW-13) plus about 1 tick when the handler
  acknowledges first, and more when it acknowledges later. This is fwtest,
  not a firmware setting: the period does not depend on anything but `PRD`,
  the prescaler and where the acknowledge sits. Whether the chip restarts
  the count on the acknowledge is Q-13. On the chip, the SDK names the
  prescaler settings 0 to 15 as dividing by 1, 4, 16, 64, 2, 8, 32, 128,
  256, 1024, 4096, 16384, 512, 2048, 8192, 32768; in fwtest only setting 2
  (16) was measured (Q-3). Supersedes HW-16, which said the count starts
  again from 0 on reaching `PRD` without saying what the acknowledge does.
- Sources: SDK `hwi.h` lines 42-45 (`IRQ_TIMER0_IDX` 4 to `IRQ_TIMER3_IDX`
  7); SDK `apps/common/example/peripheral/timer/test2.c` lines 58-75 (the
  prescaler table); E-3 (the 1 ms period, `CON` read `0x8021` in the
  handler); E-13: over 100 periods, 2 400 100 ticks (24 001.0 a period)
  with the acknowledge first in the handler (1 tick after entry), and
  2 408 160 ticks (24 081.6) with it 82 ticks after entry; `CNT` read 5
  just before the acknowledge and 0 just after.
- Standing: confirmed (SDK, E-13)
- Needed by: M1

## 10. CPU exceptions (SR-1)

### HW-49: The exception interrupt, source 1, on the chip
- Fact: On the chip, faults raise interrupt source 1, the exception
  interrupt. The SDK installs one handler on it, at priority 7, and reads
  the cause from two words: the core's `EMU_MSG` (HW-50) and the shared
  `DBG_MSG` (HW-51). Its exception demonstration lists the conditions that
  end there, each with the cause it reports: a misaligned halfword or word
  access (`EMU_MSG` bit 0); a read of an address beyond the chip's limits
  (`DBG_MSG` bit 4); a write there (bit 5); a call to such an address, an
  instruction fetch (bit 16 or 19, core 1 or 0); a stack that outgrows its
  limits (`EMU_MSG` bit 3); a division by zero (`EMU_MSG` bit 2); code
  running outside a set code range (`DBG_MSG` bit 10 or 12); a write inside
  a protected range (bit 11 or 13); a watchdog time-out (bit 0). FM-1's own
  firmware also installs a handler on source 1 at priority 7, and programs
  the per-core registers from `0x01EEF0D0` (HW-50's) and per-core exception
  stack bounds (FM-1-RE rates the last medium). Which of these are on
  when an installed app starts, and how the exception is entered, is Q-14.
- Sources: SDK `hwi.h` line 39 (`IRQ_EXCEPTION_IDX` 1); SDK
  `cpu/wl82/debug.c` lines 1137-1145 (the handler on source 1, priority 7),
  555-760 (the causes read from both words);
  SDK `apps/common/example/system/exception/main.c` lines 1-38 (a sample
  report: `DEBUG_MSG = 0x10`, cause "axi_rd_inv") and 51-140 (each
  condition and the cause it reports); RE `docs/io/01-boot.md` §4.1 (source
  1, priority 7) and §5.2 (the per-core registers from `0x01EEF0D0` and the
  per-core exception stack bounds).
- Standing: confirmed (SDK, RE)
- Needed by: M1

### HW-50: EMU_CON and EMU_MSG, per core
- Fact: Each core has `EMU_CON`, `EMU_MSG`, `EMU_SSP_H`, `EMU_SSP_L`,
  `EMU_USP_H` and `EMU_USP_L`: core 0's at `0x01EEF0D0`, `0x01EEF0D4`,
  `0x01EEF0D8`, `0x01EEF0DC`, `0x01EEF0E0`, `0x01EEF0E4`, core 1's `0x200`
  higher. `EMU_MSG` says which core-level condition raised the exception,
  one bit each: bit 0 misaligned access, bit 1 illegal instruction, bit 2
  division by zero, bit 3 stack overflow, bit 8 watchpoint 0, bits 16 to
  20 floating point invalid, infinite, tiny, huge, inexact. The SDK clears
  it by writing all ones. `EMU_CON` bit 3 turns on the stack check against
  `EMU_SSP_L` and `EMU_SSP_H` (the SDK's values: the bottom and top of the
  supervisor stack) and `EMU_USP_L` and `EMU_USP_H` (the SDK's values: 0
  and `0xFFFFFFFF`, no user-stack check). The SDK also sets `EMU_CON`
  bits 2 and 8. That `EMU_CON` bit n turns on the
  condition of `EMU_MSG` bit n is suggested by these settings but not
  stated (Q-14).
- Sources: SDK `csfr.h` lines 208-214 (one `q32DSP` block per core from
  `0x01EEF000`, `0x200` apart) and 267-272 (the six words, 0x34 to 0x39);
  SDK `cpu/wl82/debug.c` lines 70-110 (the bit names), 1098-1099 (the
  clear), 1113-1117 and 1164-1169 (bit 3 and the limits), 1193 (bits 2 and
  8); RE `docs/io/01-boot.md` §5.2 (FM-1's own firmware programs these
  registers).
- Standing: confirmed (SDK, RE)
- Needed by: M1

### HW-51: DBG_MSG on the chip reports exception causes
- Fact: On the chip, `DBG_MSG` (`0x01EEE244`, HW-25) is read-only and
  holds the system-level causes of the exception, one bit each: 0 watchdog
  time-out; 1 peripheral MMU read error; 2 peripheral write outside its
  limit; 3 peripheral MMU write error; 4 bus read of an invalid address;
  5 bus write to an invalid address; 6 and 7 MMU read exception of core 1
  and core 0; 8 and 9 MMU write exception of core 1 and core 0; 10 and 12
  code outside its set range on core 1 and core 0; 11 and 13 write inside
  a protected range by core 1 and core 0; 14 the SDRAM controller; 15 the
  debug unit; 16, 17, 18 an invalid instruction fetch, read and write on
  the bus by core 1; 19, 20, 21 the same by core 0. Writing all ones to
  `DBG_MSG_CLR` (`0x01EEE248`) clears it. `DBG_EN` (`0x01EEE340`) holds
  enables; the SDK sets its bits 4, 5 and 16 to 21 (that bit n enables
  cause n is not stated, Q-14). The debug registers are write-protected
  through `DBG_WR_EN` (`0x01EEE240`): its bit 0 reads 1 while writes to
  them are enabled, and the SDK's value for it is `0xE7`. So on the chip
  a write to `DBG_MSG` is not a console (Q-5), and a firmware that reports
  faults through `DBG_MSG` in fwtest has to report them another way there.
- Sources: SDK `csfr.h` lines 107-108 (`corex2` at `0x01EEE000`), 136-138
  (`DBG_WR_EN`, `DBG_MSG` read-only, `DBG_MSG_CLR`, words 0x90 to 0x92),
  171 (`DBG_EN`, word 0xD0); SDK `cpu/wl82/debug.c` lines 31-68 (the bit
  names), 773-786 (the write enable), 1096 (the clear), 1160-1161 (the
  `DBG_EN` bits); SDK `apps/common/example/system/exception/main.c` lines
  6 and 32 (`DEBUG_MSG = 0x10` reported as a bus read of an invalid
  address).
- Standing: confirmed (SDK)
- Needed by: M1

### HW-52: The conditions of SR-1 in fwtest
- Fact: fwtest models no CPU exception: none of these conditions raises
  source 0, 1 or 2 (handlers installed and enabled on all three never
  ran), and the registers of HW-50 and HW-51 have no effect.
  - A misaligned word load, from RAM or from the code window, returns the
    4 bytes at the address asked, lowest first, and a misaligned word store
    to RAM writes the 4 bytes at the address asked. A halfword load from an
    odd address in RAM ignores the address's lowest bit: it returns the
    halfword at the even address below.
  - A read of an address outside every memory and register fwtest models
    returns 0, and a write there is ignored; both are listed as unmodelled
    accesses.
  - A write to the code window is ignored and listed (HW-5).
  - A division by zero gives 0, signed or unsigned; C's remainder by zero,
    as the pinned toolchain compiles it, gives the dividend.
  - `EMU_CON` and the four limit words read back what was written; with
    every `EMU_CON` bit the SDK names set and limits that exclude the
    stacks, the image ran on; `EMU_MSG` reads 0; `DBG_EN` reads 0 and is
    listed as unmodelled. Writes to `DBG_WR_EN` and `DBG_MSG_CLR` leave
    fwtest's console (HW-25) as it was.
  - An instruction fwtest cannot decode ends the run with fwtest's fault
    outcome (exit code 3). fwtest may report it at the start of the
    straight-line code that holds it, before any of that code has run.
  - A call to an address outside every memory runs what fwtest reads there
    (zeros) until fwtest's next check, up to 1024 instructions later, then
    ends the run as a fault ("the pc left every memory that can hold
    code").
  So in fwtest a firmware's exception handler is never entered by a
  fault. The sources don't establish enough of the chip's behaviour
  (Q-14) for fwtest to model one.
- Sources: E-10 (loads, stores, unmapped accesses, the code window,
  divisions, the exception registers, both before and after setting
  them; the console), E-11 (an undecodable halfword in a function of its
  own: the store before the call ran), E-14 (the same halfword right after
  a store in the same code: the store did not run, and the fault's pc was
  the start of that code), E-12 (a call to `0x00ABCDEE`);
  HARNESS ("Outcomes and exit codes", "unmodelled_accesses").
- Standing: confirmed (E-10, E-11, E-12, E-14)
- Needed by: M1

## 11. The clocks on the chip (SR-2, real hardware)

### HW-53: The clock registers
- Fact: `JL_CLOCK` is at `0x00010000`: `PWR_CON` +0, `SYS_DIV` +8,
  `CLK_CON0` +12, `CLK_CON1` +16, `CLK_CON2` +20, `CLK_CON3` +24. In
  `CLK_CON0`: bit 0 turns the RC oscillator on and bit 1 picks its rate
  (0: 250 kHz, 1: 16 MHz); bits 4-5 pick the oscillator input (0: the
  crystal oscillator, the SDK's "BT OSC"; 2: the RTC's low-frequency
  oscillator; 3: a pad); bits 6-8 pick the main (system) clock source:
  0 the RC oscillator, 4 the crystal oscillator, 6 the RTC's low-frequency
  oscillator, 7 the PLL. In `CLK_CON1`: bits 2-3 the DAC clock (0: PLL
  24 MHz, 1: oscillator, 2: low-speed bus clock, 3: off); bits 10-11 the
  UART clock (0: oscillator, 1: PLL 48 MHz, 2: low-speed bus clock, 3:
  off). The SDK's definitions of the PLL's control fields and of `SYS_DIV`'s
  fields are switched off in its header (they may belong to another chip),
  so they are not given here (Q-2). In fwtest none of these registers has
  an effect (HW-11), and `SYS_DIV` bit 3 releases core 1 (HW-10).
- Sources: SDK `WL82.h` lines 15-16, 347-358 (`JL_CLOCK`); SDK
  `include_lib/driver/cpu/wl82/clock_hw.h` lines 235-341 (the fields in
  use) and 344 (the PLL and `SYS_DIV` fields under `#if 0`).
- Standing: confirmed (SDK)
- Needed by: real hardware (Level 2)

### HW-54: System clock rates, and FM-1's own setting
- Fact: On the chip, the SDK sets the system clock anywhere from 24 MHz to
  396 MHz, and names the rates 320, 240, 192, 160, 120, 96, 48, 40, 24, 12
  and 8 MHz. The high-speed bus clock is the system PLL clock divided by 1
  to 4, and the low-speed bus clock that divided again by 1 to 8; the SDRAM
  clock runs from 96 MHz to 244 MHz. FM-1's own firmware runs the PLL from
  the 24 MHz reference (HW-11) to 240 MHz. It tells a 24 MHz reference
  from a 40 MHz one by bits 26-27 of the word at `0x000119A0`
  (`JL_ANA->PLL_CON0`): the value 2 means 40 MHz, any other 24 MHz; the
  FM-1 takes the 24 MHz path. fwtest runs at 240 MHz from the start
  (HW-11), the rate FM-1's own firmware sets.
- Sources: SDK `include_lib/driver/cpu/wl82/asm/clock.h` lines 44-55 (the
  named rates), 94 and 97 (24 MHz to 396 MHz; SDRAM 96 MHz to 244 MHz),
  109 (the bus clock dividers); SDK `WL82.h` lines 488-546 (`JL_ANA` at
  `0x00011900`, `PLL_CON0` its word 0x28); RE `docs/io/01-boot.md` §5.1
  (the PLL from 24 MHz to 240 MHz, high confidence) and §5.2 (the
  reference detect, the 24 MHz path on the FM-1).
- Standing: confirmed (SDK, RE)
- Needed by: real hardware (Level 2)

## 12. The LCD on the chip, and SPI1 in fwtest (SR-3)

### HW-55: SPI1's CON on the chip
- Fact: On the chip, `JL_SPI1->CON` is an ordinary read/write register: a
  write sets each bit as written (the SDK sets and clears its bits with
  ordinary read-modify-write), except that bit 15, the pending (done) flag,
  is read, and writing bit 14 as 1 clears the pending flag. The bits the
  SDK names: bit 0 turns SPI on; bit 12 set is receive mode; bit 13 makes a
  finished transfer raise interrupt source 16; bit 14 clears the pending
  flag (the SDK's handler sets it, keeping the other bits); bits 2, 10 and
  11 are cleared for what the SDK calls one-bit mode. `BAUD` is one byte
  wide. When FM-1's own firmware sets up the panel it writes
  `CON` = `0x4020` and `BAUD` = 4. The sources don't give the meaning of
  `CON` bit 5 or of the other mode bits, how `BAUD` sets the clock, or what
  state SPI1 is in when an installed app starts (Q-6).
- Sources: SDK `apps/common/example/peripheral/spi/spi_slave/spi_nomask_interrupt.c`
  lines 59 (bit 14 set in the handler), 116-119 (bits 2, 10, 11 cleared;
  bits 12, 13, 0 set, with their meanings); SDK
  `include_lib/driver/cpu/wl82/asm/spi.h` lines 107-115 (`BAUD` a byte);
  RE `docs/io/08-display.md` §1 (bit 15 pending, 14 clear, 13 interrupt
  enable; `CON` = `0x4020` and `BAUD` = 4 at the panel's set-up, high
  confidence).
- Standing: confirmed (SDK, RE)
- Needed by: real hardware (Level 2)

### HW-56: SPI1's pins, and the port set-up registers
- Fact: On the chip SPI1 has two pin groups: A, clock PB6, data out PB7,
  data in PB5; B, clock PC9, data out PC10, data in PC8. Neither has a
  chip select pin of its own: a chip select is an ordinary port pin.
  `JL_IOMAP->CON1` (`0x00051020`; `JL_IOMAP` is at `0x0005101C`) bit 4
  picks the group: clear A, set B. On the FM-1 the panel is probably on
  group B: PC8 is the panel's data/command line (HW-30), used as a port
  pin, not as data in; and during the panel's set-up FM-1's own firmware
  makes GPIO 39 an input and GPIO 40 to 42 outputs driven low (FM-1-RE,
  which suggests they may be the panel's reset and backlight). If those
  numbers follow the SDK's numbering, 16 pins a port, they are PC7, and
  PC8 to PC10, the group B pins. That the FM-1 uses group B is inferred
  from these sources together; none of them states it. Each port's
  registers (`JL_PORTC` at `0x00050080`) are `OUT` +0, `IN` +4, `DIR` +8,
  `DIE` +12, `PU` +16, `PD` +20, `HD0` +24, `HD` +28, one bit per pin:
  `DIR` bit 0 makes the pin an output, 1 an input; `PU` and `PD` turn on
  its pull-up and pull-down; `HD0` and `HD` its two strong-drive
  settings; `DIE` its digital input. Which pin is the panel's chip select
  (FM-1-RE sees PC7 toggled with PC8, HW-30; if the numbering above
  holds, it is also set up as an input), and whether the clock and data
  pins need strong drive, is Q-6. fwtest needs none of this set-up
  (HW-29).
- Sources: SDK `include_lib/driver/cpu/wl82/asm/spi.h` lines 212-243
  (SPI1's two pin groups, no chip select, `JL_IOMAP->CON1` bit 4); SDK
  `WL82.h` lines 12, 16, 251-270 (the port registers, `JL_PORTC`), 307-320
  (`JL_IOMAP`); SDK `include_lib/driver/cpu/wl82/asm/gpio.h` lines 5,
  50-53 (16 pins a port: PC7 is 39, PC10 is 42); SDK
  `apps/common/example/peripheral/gpio/gpio.c` lines 63-122 (`DIR` 0
  output, 1 input; `HD0`, `HD`, `PU`, `PD`, `DIE` set to turn on); RE
  `docs/io/08-display.md` §1 (GPIO 39 an input, GPIO 40 to 42 outputs
  driven low during the panel's set-up; PC7 and PC8 toggled; both medium
  confidence).
- Standing: confirmed (SDK, RE)
- Needed by: real hardware (Level 2)

### HW-57: The panel's serial clock and its reset line
- Fact: The controller takes a serial write clock cycle of at least 66 ns
  (a clock of at most about 15 MHz), high and low each at least 15 ns,
  with its 4-line serial interface (a data/command line, as on the FM-1).
  Its reset input `RESX` is active low: a low pulse of at least 10 µs
  resets it. After the pulse ends it needs 5 ms before the next command,
  and 120 ms before a sleep out command; a reset in sleep out mode blanks
  the display for up to 120 ms. Whether the board wires `RESX` to a port
  pin, or the backlight to one, and which, is Q-6. fwtest needs neither
  (HW-29).
- Sources: DS page 44 (4-line serial interface timing: `TSCYCW` 66 ns,
  `TSHW` and `TSLW` 15 ns), pages 48 and 49 (reset timing, table 9 and
  its notes 3 and 5 to 7: `TRW` 10 µs, `TRT` 5 ms in sleep in mode and
  120 ms in sleep out mode; 5 ms before commands, 120 ms before sleep
  out).
- Standing: confirmed (DS)
- Needed by: real hardware (Level 2)

### HW-58: The longest transfer
- Fact: On the chip, the SDK's limit on one SPI DMA transfer for the
  AC791N is `0x7FFFFFFE` bytes (its examples say 2^31; 65 535 on the
  AC790N), so a whole 240 × 240 frame (115 200 bytes) fits in one `CNT`
  write. How wide the `CNT` counter itself is, the sources don't say. In
  fwtest one `CNT` write of 115 200 bytes sends a whole frame: the screen
  shows every pixel in order.
- Sources: SDK `include_lib/driver/cpu/wl82/asm/spi.h` line 8
  (`SPI_MAX_SIZE`); SDK `apps/common/example/peripheral/spi/spi_1bit/main.c`
  line 37 (the AC791N and AC790N limits); E-16: one transfer of a whole
  frame from RAM drew it, the first and last pixels in place.
- Standing: confirmed (SDK, E-16)
- Needed by: M2

### HW-59: SPI1's interrupt in fwtest
- Fact: In fwtest `JL_SPI1->CON` reads back as last written, with bit 15
  always 1 (a transfer finishes at once) and bit 14 reading 0; before any
  write it reads `0x8000`. A transfer that finishes while bit 13 is set
  raises interrupt source 16, a DMA transfer (`CNT`) or a single byte
  (`BUF`) alike; with bit 13 clear neither raises anything. A write with
  bit 14 set acknowledges it, and sets the other bits as written: a write
  of bit 14 alone also clears bit 13. A transfer that finished with bit 13
  set stays pending until acknowledged, even if bit 13 is cleared and the
  source enabled only afterwards. This agrees with HW-29 and HW-55. It
  holds from fwtest 0.2.0; before, a `CON` write could set bits but not
  clear them, so once bit 13 had been set every later transfer raised
  source 16 (SR-3). What the chip does with a transfer that finished while
  bit 13 was clear, when bit 13 is set later, is Q-15.
- Sources: E-15: with bit 13 never set, or written clear, no interrupt
  for a DMA transfer or a byte; with it set, one for each; `CON` read
  `0x8000`, then `0xA000` while bit 13 was set; a transfer done with the
  source disabled and bit 13 then cleared was still taken once the source
  was enabled; HARNESS ("The LCD").
- Standing: confirmed (E-15)
- Needed by: M2

## 13. The SARADC's interrupt, confirmed (M3)

### HW-60: The SARADC's interrupt in fwtest
- Fact: In fwtest, a conversion started (`JL_ADC->CON` written with bits
  4 and 6) with `CON` bit 5 set raises interrupt source 24 when it
  finishes, which is at once; started without bit 5 it raises nothing. In
  the handler `RES` holds the result and `CON` reads as written with bit 7
  set. Writing `CON` with bit 6 set and bit 4 clear acknowledges it; that
  write also clears bit 4, the enable, and bit 7, and the next start write
  sets bit 4 again. `CON` writes set and clear bits as written: a start
  without bit 5 after one with it raises nothing. The fwtest part of HW-41,
  now confirmed; which knob the pot is moved to HW-61.
- Sources: SDK `hwi.h` line 65 (`IRQ_SARADC_IDX` 24); E-17: one
  interrupt for each start with bit 5 and none without, `RES` 900 (the
  pot) and `CON` `0x4F0` in the handler, `0x40` after the acknowledge,
  `0x4D0` after a start without bit 5.
- Standing: confirmed (SDK, E-17)
- Needed by: M3

### HW-61: The pot is the MASTER knob
- Fact: The pot that fwtest reads on SARADC channel 4 (HW-40), and that
  input scripts move with `pot V`, is the `MASTER` knob (HW-36). Which
  channel carries it on the chip is Q-8.
- Sources: the emulator model (which panel control the pot is); PANEL
  (the label, HW-36).
- Standing: emulator-only
- Needed by: M3

---

## 14. Floating point and the second core (SR-5, SR-6)

### HW-62: The core's CPU model, and hardware single-precision float
- Fact: JieLi builds the SDK's AC791N code for the toolchain's CPU model
  `r3` with its hardware single-precision float extension `fprev1`:
  clang's `-mcpu=r3 -mfprev1`, and for link-time optimisation the linker
  plugin's `mcpu=r3` and `-mattr=+fprev1`. So the vendor's own code for
  this chip uses the extension's instructions, and each core reports five
  float conditions in `EMU_MSG` (bits 16 to 20, HW-50). Build firmware for
  the chip with `-mcpu=r3 -mfprev1`, as the SDK does. What `r1` to `r5`
  differ in, and how the extension behaves at its edges and in cycles on
  the chip, the sources don't say (Q-16).
- Sources: SDK `apps/demo/demo_hello/board/wl82/Makefile` lines 74-75
  (`-mcpu=r3`, `-mfprev1`), 233 and 273-274 (the linker plugin's
  `mcpu=r3`, `-mattr=+fprev1`); the same flags at lines 74-75 of eight
  more of the SDK's `board/wl82/Makefile`s (`demo_DevKitBoard`,
  `demo_audio`, `demo_ble`, `demo_edr`, `demo_matter`, `demo_ui`,
  `demo_wifi_ext`, `wifi_ipc`; the other six were not read); SDK `csfr.h`
  lines 267-272 and SDK
  `cpu/wl82/debug.c` lines 70-110 (the float bits of `EMU_MSG`, HW-50).
  The sources are the vendor's build settings and register map; no
  datasheet states it.
- Standing: confirmed (SDK)
- Needed by: M5 (SR-5)

### HW-63: Floating point in fwtest
- Fact: fwtest executes the `fprev1` instructions (add, subtract,
  multiply, divide, min, max, multiply-add and multiply-subtract, the
  conversions between float and signed or unsigned integer, and the float
  compares) on the ordinary registers, as IEEE 754 single precision:
  - results rounded to nearest, ties to even, with subnormals kept (no
    flush to zero); a division of a non-zero number by zero gives an infinity of
    the right sign, and 0/0 a NaN;
  - multiply-add and multiply-subtract round the product before the add
    (not fused);
  - a conversion to integer truncates toward zero and saturates at the
    integer type's limits; a NaN converts to 0;
  - min and max with one NaN operand give the other operand;
  - ordered compares are false when either operand is a NaN, their
    unordered negations true.
  No float condition sets an `EMU_MSG` bit or raises source 1 (HW-52).
  Each of these instructions is one instruction and one cycle, like every
  other (HW-11); fwtest models no extra cost for divide or the conversions,
  and has no square-root instruction. Whether the chip
  rounds, keeps subnormals and treats NaNs the same way, and its cycle
  costs, is open (Q-16).
- Sources: the emulator model; HARNESS ("Time").
- Standing: emulator-only
- Needed by: M5 (SR-5)

### HW-64: The two cores in fwtest: pace, memory and interrupts
- Fact: In fwtest, once released (HW-9), core 1 executes one instruction
  per cycle at 240 MHz like core 0 (HW-11). The cores take turns: core 0
  runs 1024 instructions, then core 1 runs as many cycles as passed. They
  share one memory with no caches, no bus or memory contention and no
  wait states, so neither core slows the other, and a store by one core
  is seen by the other core's next load; but because of the turns, the
  other core sees it up to one turn (1024 cycles, about 4.3 µs) later.
  `testset` is atomic between the cores and `csync` has no effect. Core 1
  takes interrupts: the sources its own `ICFG` words enable (HW-20, from
  `0x01EEF300`), behind its own gates (HW-21), through the one vector table
  (HW-18, HW-22). The tick timer and software-interrupt words are core
  0's only (HW-17, HW-23): a source pending there interrupts every core
  whose `ICFG` words enable it, so enable each source on one core only.
  When core 1 loops with nothing changing (a polling loop), fwtest ends
  its turn early; its instruction counts are kept per turn (HARNESS,
  `ipb.csv`).
- Sources: the emulator model; HARNESS ("The raw image", "Outputs").
- Standing: emulator-only
- Needed by: M5 (SR-6)

### HW-65: Sharing memory between the cores, on the chip
- Fact: On the chip, the SDK's lock between the two cores is a byte taken
  with the atomic test-and-set instruction `testset` (repeated while the
  byte was already set), with `csync` before and after; it is released by
  `csync` and then a plain store of 0. Its atomic read executes `csync`
  before the load. The chip has instruction and data caches with shared
  controls (`CACHE_CON`, `DCACHE_WAY`, `ICACHE_WAY` in the `corex2` block,
  words 2 to 4 from `0x01EEE000`); the SDK flushes and invalidates the data
  cache by address range, and chooses how many of its ways the cores and
  the peripherals use. Its uncached-address macro gives an
  address at or above `0x04000000` an uncached alias `0x04000000` higher,
  and returns lower addresses, main RAM's included (HW-6), unchanged. So
  for data shared between the cores, follow the SDK: `testset` for locks,
  `csync` before a shared load and around a lock. Whether main RAM is
  behind the data cache, and whether a plain store is seen by the other
  core's load without `csync`, the sources don't say (Q-18).
- Sources: SDK `include_lib/driver/cpu/wl82/asm/cpu.h` lines 49-50 (the
  uncached alias), 134-148 (`csync`, the atomic read), 189-190 (the
  lock); SDK `include_lib/system/spinlock.h` (the lock used when there are
  two cores); SDK `include_lib/driver/cpu/wl82/asm/cache.h` lines 24-28 (flush,
  invalidate, the way split); SDK `csfr.h` lines 106-115 (`corex2`, its
  cache words).
- Standing: confirmed (SDK)
- Needed by: M5 (SR-6)

## 15. Block moves with a register base (SR-7)

### HW-66: The block moves with a register base, and fwtest
- Fact: a 4-byte instruction moves the registers in a list to or from
  consecutive words at a base register: bytes `xm eb` then a 16-bit
  register mask, low byte first (bit k: register rk, r0 to r15). In the
  first byte, bits 0 to 3 are the base register and bits 4 to 6 the mode;
  bit 7 must be 0 (with it set the bytes are a different instruction).
  The toolchain writes the eight modes as:
  - `0x0`: `{list} = [rN+]`, `0x1`: `{list} = [rN++]`,
    `0x2`: `[rN+] = {list}`, `0x3`: `[rN++] = {list}`;
  - `0x4`: `{list} = [-rN]`, `0x5`: `{list} = [--rN]`,
    `0x6`: `[-rN] = {list}`, `0x7`: `[--rN] = {list}`.

  Mode bit 4 is the `++` / `--` form, bit 5 a store, bit 6 a block below
  the base. With n registers in the list: the lowest-numbered register
  takes the lowest address; `[rN+]` and `[rN++]` cover the n words from
  rN up, `[-rN]` and `[--rN]` the n words just below rN (rN - 4n to
  rN - 4). Without `++` / `--` the base keeps its value, and every address
  comes from the base as it was, so a base that is also in a loaded list
  ends with its loaded word. The toolchain's compiler emits `[rN+]` and
  `[-rN]`, loads and stores, on its own (SR-7's `{r3, r0} = [-r4]` is mode
  `0x4`, mask `0x0009`): SR-7's reproduction leaves r0 `0x29F3A1C5`, r3
  `0x7E41D60B` and r4 `0x01C00010`, unchanged. `[rN++]` and `[--rN]` are
  assembler forms the compiler was not seen to emit; fwtest runs them with
  the base moved past the block (rN + 4n, rN - 4n). fwtest runs all eight
  modes this way since 0.3.0 (HARNESS, "Instructions"); before, `[-rN]` and
  `[--rN]` ended the run as a fault. On the chip, what `[rN++]` and
  `[--rN]` leave in the base, a write-back form whose base is also in its
  list, and an empty list, are open (Q-19).
- Sources: TC: the assembler and disassembler for every mode, base and
  mask tried (the encoding); the compiler's code for C with known results,
  built with `-mcpu=r3 -mfprev1` at `-Os`, `-O2` and `-O3` (the order, the
  block below the base, the base kept, the base in the list); E-18 (fwtest,
  all eight modes: the result above for each); HARNESS ("Instructions").
- Standing: confirmed (E-18)
- Needed by: M5 (SR-7)

## 16. MIDI input (SR-8)

### HW-67: The FM-1's MIDI inputs, and the one fwtest feeds
- Fact: The FM-1 takes MIDI in three ways, all active at once: a 3.5 mm
  MIDI IN jack carrying serial MIDI at 31 250 baud, USB MIDI (the FM-1 is a
  class-compliant USB device with a MIDI and an audio interface), and MIDI
  over Bluetooth LE. Its manual lists no MIDI OUT jack. On the chip, the
  jack's serial MIDI is received by UART1 (`JL_UART1`, HW-68), through its
  receive DMA. fwtest models only the jack:
  a script's `midi` event (HARNESS, "Input scripts") delivers its bytes to
  UART1's receiver, and fwtest has no USB or Bluetooth MIDI. Which pin the
  jack reaches, and how the TRS socket is wired (type A or B), the sources
  don't say (Q-12).
- Sources: MAN (the FM-1's manual, English part, p. 10, "MIDI
  Connectivity": the three interfaces, the jack's 31 250 baud; "What the
  FM-1 sends via MIDI"); RE `docs/io/05-midi.md` §1 and §2 (the three
  transports; UART MIDI on the UART at `0x00012100`, received by DMA),
  `docs/io/06-usb.md` §1 (a USB composite device, audio and MIDI),
  `docs/reversing/01-hardware-map.md` (MIDI I/O: USB and UART MIDI); SDK
  `WL82.h` lines 569-591 (UART1's base); E-19 (fwtest's `midi` bytes reach
  UART1's ring).
- Standing: confirmed (MAN, RE, SDK, E-19)
- Needed by: M6a (SR-8)

### HW-68: The UARTs' registers, sources, pins and clocks
- Fact: The chip has three UARTs, `JL_UART0`, `JL_UART1` and `JL_UART2`,
  at `0x00012000`, `0x00012100` and `0x00012200`. Each has the words, from
  its base: `CON0` +0x00, `CON1` +0x04, `BAUD` +0x08, `BUF` +0x0C, `OTCNT`
  +0x10, `TXADR` +0x14, `TXCNT` +0x18, `RXSADR` +0x1C, `RXEADR` +0x20,
  `RXCNT` +0x24, `HRXCNT` +0x28. `CON0`, `CON1`, `BAUD`, `TXCNT` and
  `HRXCNT` are 16 bits and `BUF` 8 bits, each in the low part of its word;
  `BAUD` and `TXCNT` are write-only and `HRXCNT` read-only. Their interrupt
  sources are 19, 20 and 21. A UART's transmit and receive pins are either
  one of its fixed pin pairs, given as transmit then receive (UART1: PH6 and
  PH7, PC3 and PC4, PB3 and PB4, or the USB pins), or any pin, through an
  output and an input channel of the port map (`JL_IOMAP`). The UART clock
  is the low-speed bus clock, the crystal oscillator or the PLL's 48 MHz
  (`CLK_CON1` bits 10-11, HW-53). The SDK's driver receives into a circular
  buffer by DMA, with an interrupt after a given number of bytes and an
  idle timeout counted in clocks, and each of the transmit, receive and
  timeout interrupts can be left off. The SDK gives no bit meanings for
  `CON0`, `CON1` or `BAUD` (its UART driver is a prebuilt library).
- Sources: SDK `WL82.h` lines 12-16 (the bases, `map_adr`) and 569-591
  (`JL_UART_TypeDef`, the three bases); SDK
  `include_lib/driver/cpu/wl82/asm/hwi.h` lines 59-61 (sources 19 to 21);
  SDK `include_lib/driver/cpu/wl82/asm/uart.h` (three UARTs, the pin pairs,
  the input and output channels); SDK `include_lib/driver/device/uart.h`
  (the clock choices, the circular buffer, the byte count and idle timeout,
  the interrupts that can be left off).
- Standing: confirmed (SDK)
- Needed by: M6a (SR-8)

### HW-69: UART1's receive flags, their acknowledge and the count latch
- Fact: In UART1's `CON0`, read: bit 14 is set when the receive DMA has
  taken the set number of bytes (receive pending), bit 11 when the line has
  been idle for the set time after a byte (timeout pending). Written as 1:
  bit 12 clears the receive pending, bit 10 the timeout pending, bit 13 the
  transmit pending; bit 7 latches into `HRXCNT` how many bytes the receive
  DMA has written since the previous latch, and `HRXCNT` keeps that count
  until the next latch. FM-1's own firmware receives MIDI from the jack
  this way, by DMA, on source 20.
- Sources: RE `docs/io/05-midi.md` §2.1 (the UART's flags at `0x00012100`:
  `0x4000` receive pending, `0x800` timeout; acknowledged with `0x80`,
  `0x1000`, `0x400`, `0x2000`; the count at `0x00012128` read in the
  handler); E-19 (the same bits in fwtest).
- Standing: confirmed (RE, E-19)
- Needed by: M6a (SR-8)

### HW-70: UART1's receive set-up bits, the ring, the count and the timeout
- Fact: In UART1's `CON0`: bit 0 turns the UART on; bit 2 enables the
  transmit interrupt, bit 3 the receive interrupt (bit 14, HW-69), bit 5
  the timeout interrupt (bit 11); bit 6 turns the receive DMA on. The DMA
  writes each byte at the next address of the ring from `RXSADR` up to,
  not including, `RXEADR`, and wraps to `RXSADR`; writing `RXSADR` starts
  it again at the ring's start. `RXCNT` is the number of bytes since the
  last latch that sets the receive pending (0: never). `OTCNT` is the idle
  time, in UART clocks (48 MHz from the PLL), after a byte that sets the
  timeout pending. The sources give no receive by `BUF` a byte at a time,
  no error flags (framing, overrun) and no `BAUD` formula (Q-12).
- Sources: the emulator model; SDK `include_lib/driver/device/uart.h`
  (that the receive is a DMA ring with a byte count and an idle timeout,
  not the bits); E-19, E-20 (fwtest behaves so).
- Standing: emulator-only
- Needed by: M6a (SR-8)

### HW-71: UART1's receive in fwtest
- Fact: In fwtest a `midi` byte arrives 320 µs after the one before it,
  whatever `BAUD`, `CON1`, `CLK_CON1` and the pins are set to: none needs
  setting. fwtest counts as "a MIDI receiver set up" (HARNESS, `result.json`'s
  `midi_bytes_dropped`) `CON0` with bits 0 and 6 set and `RXEADR` −
  `RXSADR` from 1 to 65 536. A byte arriving otherwise is dropped and
  counted: no interrupt, nothing in RAM, and `BUF` reads 0; fwtest has no
  receive through `BUF`. So does a byte with more than 3 125 waiting (about
  a second). Received bytes go into the ring as HW-70 says: a byte that
  arrives before the firmware has read the one before is kept; past the
  ring's size the oldest are overwritten, with no flag in `CON0`. The
  receive pending is set when the bytes since the last latch reach `RXCNT`,
  so a handler that clears it without latching gets it again on every
  later byte. The timeout comes `OTCNT` × 5 cycles (at 240 MHz) after the
  last byte, and at least one byte time (320 µs). Source 20 then interrupts
  as any source does (HW-20, HW-22). E-19: with `RXCNT` 4 and `OTCNT`
  48 000, six bytes from 3 ms give a receive pending at 4.28 ms with
  `HRXCNT` 4, and a timeout at 5.92 ms with `HRXCNT` 2.
- Sources: E-19, E-20; HARNESS ("Input scripts", "Outputs").
- Standing: confirmed (E-19, E-20)
- Needed by: M6a (SR-8)

## 17. MIDI output (M6b)

### HW-72: The SMK-37's MIDI OUT, and the FM-1's
- Fact: M-VAVE's SMK-37 Pro, the FM-1's sibling keyboard, has a 3.5 mm
  MIDI OUT jack on its rear panel. It reaches an external device's MIDI IN
  through a 3.5 mm-to-MIDI adapter, so it carries serial MIDI: the MIDI 1.0
  wire format, a current loop at 31 250 baud, each byte one start bit,
  eight data bits from the least significant, one stop bit, no parity. It
  also sends MIDI over USB (a class-compliant device) and Bluetooth LE. So
  its MIDI OUT is a UART's transmit side, not USB or Bluetooth. The FM-1
  has no MIDI OUT jack (HW-67). Which UART and pin drive the SMK-37's jack,
  and how its TRS socket is wired (type A or B), the sources don't say
  (Q-20). Whether the SMK-37 has the FM-1's chip, the allowed sources don't
  say either: the emulator runs the SMK-37's own firmware on the FM-1's
  chip with a different panel, which is the emulator's view only.
- Sources: MAN (the SMK-37 Pro's manual, English part p. 3, "MIDI OUT":
  a 3.5 mm to MIDI adapter to an external device's MIDI In; Chinese part
  p. 15, USB MIDI, class-compliant; p. 16, Bluetooth; p. 17, the rear
  panel's MIDI output port); the MIDI 1.0 specification (the wire format);
  the emulator model (the SMK-37 board). Secondary, since pin-050: MPLUS
  p. 4 (the rear panel's "3.5mm MIDI output (requires adapter)"), p. 12
  (specifications, "3.5mm MIDI OUT"), p. 5 ("3.5mm TRS to 5-pin DIN MIDI
  adapters", the TRS type not given). Its p. 3 (features) and p. 11
  (troubleshooting) say "3.5mm MIDI input/output" instead: unresolved, and
  not taken as evidence of a MIDI input jack.
- Standing: confirmed (MAN)
- Needed by: M6b (MIDI out)

### HW-73: The UARTs' transmit side, and UART1's on the FM-1
- Fact: Each UART (HW-68) transmits as well as receives, the two sides
  independent: `BUF` for a byte at a time, and a transmit DMA from RAM,
  `TXADR` the start address and `TXCNT` (write-only) the number of bytes,
  written last. The SDK's example keeps a DMA transmit buffer 4-byte
  aligned. The SDK's own byte-at-a-time output, on UART2, sends only while
  `CON0` bit 0 (the UART on) is set: it clears the transmit pending by
  writing `CON0` bit 13, writes the byte to `BUF`, and waits until `CON0`
  bit 15 (transmit pending) is set, which means the byte has gone. On the
  FM-1, FM-1's own firmware sends MIDI bytes through UART1's
  transmit DMA (`TXADR` then `TXCNT`), the UART that receives the MIDI IN
  jack, although the FM-1 has no MIDI OUT jack. So a MIDI output on UART1
  shares the input's UART, its baud rate and its clock. UART1's transmit
  pin is one of PH6, PC3, PB3 or a USB pin in its fixed pairs, or any pin
  through an output channel of `JL_IOMAP` (HW-68); which, if any, the
  FM-1's board connects, the sources don't say (Q-20).
- Sources: SDK `WL82.h` lines 569-591 (`TXADR`, `TXCNT`, `BUF`); SDK
  `include_lib/driver/device/uart.h` (transmit by DMA, the transmit
  interrupt that can be left off, the transmit pin); SDK
  `cpu/wl82/debug.c` lines 390-404 (`CON0` bits 0, 13 and 15, a byte by
  `BUF`); SDK
  `apps/common/example/peripheral/uart/uart_test.c` (the DMA transmit
  buffer 4-byte aligned); SDK `include_lib/driver/cpu/wl82/asm/uart.h` (the
  pin pairs, transmit first); RE `docs/io/05-midi.md` §1 and §2.1 (FM-1's
  firmware writes UART1's transmit address and count to send MIDI; the
  transmit pending acknowledged with `0x2000`).
- Standing: confirmed (SDK, RE)
- Needed by: M6b (MIDI out)

### HW-74: UART1's transmit in fwtest, and on a real FM-1
- Fact: Since fwtest 0.5.0, UART1 transmits: writing `TXCNT` sends that
  many bytes from `TXADR` (fwtest reads them from RAM at the write), and
  writing `BUF` sends one byte. Bytes go out one every 320 µs (31 250
  baud, whatever `BAUD`, `CON1`, `CLK_CON1` and the pins say), each after
  any still going, so a `BUF` byte written during a transfer goes after
  it. When the last byte has gone, `CON0` bit 15 (transmit pending) is set,
  and source 20 is raised if `CON0` bit 2 is set; writing bit 13 clears it
  (HW-69). With `CON0` bit 0 clear nothing is sent, and the bytes are
  counted in `result.json`'s `midi_out_bytes_dropped`. `--midi-out` saves
  every byte sent with the time its stop bit ended, and the MIDI messages
  they make (HARNESS, "MIDI output"). Before 0.5.0 a `TXCNT` write set the
  pending at once and sent nothing. On a real FM-1 these bytes reach no
  socket: it has no MIDI OUT jack (HW-67), and which pin, if any, its
  board gives UART1's transmit side is open (Q-20). `CON0` bits 0, 13 and
  15 and a byte by `BUF` behave as the SDK's own output relies on (HW-73);
  the interrupt enable (bit 2) and the DMA's pace are the emulator's
  (HW-70). The SMK-37's MIDI OUT is a UART's transmit side (HW-72), which
  this models for the FM-1's chip.
- Sources: E-21 (the timing, the order, the pending and its interrupt,
  nothing sent with the UART off); HARNESS ("MIDI output"); the emulator
  model with vendor patch 0009.
- Standing: confirmed (E-21)
- Needed by: M6b (MIDI out)

## 18. The UART on other JieLi chips (Q-12, Q-20)

### HW-75: The UART as three other JieLi chips' open driver sets it up
- Fact: Three other JieLi chips, the ones SDK63 calls br23, br25 and
  bd29, have three UARTs with the FM-1's chip's eleven words in the same
  order, widths and access (HW-68), at the same three bases, and SDK63's
  drivers for them are open source. All three drivers do the same:
  - The rate: `BAUD` is f / baud rounded to the nearest whole number,
    divided by 4 (rounded down), less 1, where f is the UART clock; so
    the rate is f / (4 × (`BAUD` + 1)). For 31 250 baud that is 383 from a
    48 MHz clock and 191 from 24 MHz, both exact.
  - Set-up: the pending flags cleared (`CON0` bits 13, 12 and 10 written
    as 1) with bit 0 clear; then `BAUD`, and `OTCNT` when bit 5 is set;
    then bit 0 set with the same three clears.
  - `CON0` bit 1 set gives 9-bit frames, clear 8-bit.
  - The receive ring: `RXSADR` its first byte and `RXEADR` one past its
    last (the buffer's start plus its size); `RXCNT` the bytes per receive
    pending; bits 6, 5 and 3 set together to receive by DMA.
  - The idle timeout: `OTCNT` is the time in the low-speed bus clock
    (milliseconds × that clock / 1000), not in the UART clock.
  - Receive without the DMA (bit 6 clear): wait for bit 14, read `BUF`,
    then write bit 12. The drivers only poll for such a byte, never take
    it by interrupt.
  - The receive and timeout interrupts write bit 7, then 10, then 12, and
    then read `HRXCNT`; the driver's comment says the order must not
    change.
  - Transmit: a byte by writing `BUF`, waiting for bit 15 and clearing it
    with bit 13; a DMA by clearing bit 13, setting bit 2 (the transmit
    interrupt, taken when bits 2 and 15 are set), then writing `TXADR` and
    then `TXCNT`.
  - `CON0` bits 4, 8 and 9 are never used, and no error flag (framing,
    overrun, parity) is read or cleared.
  On br23's UART1 only, `CON1` holds hardware flow control: bit 0 turns
  RTS on and bit 2 CTS, and bit 4 sets the RTS line by hand; when bit 0 is
  set, each receive or timeout interrupt also writes bit 13; while bits 2
  and 15 are set the sender waits, writing bit 14 (by that use, 15 is CTS
  holding the sender off and 14 clears it). Where the bits overlap the FM-1's
  chip's (`CON0` bits 0, 2, 3, 5, 6, 7 and 10 to 15: HW-69, HW-70, HW-73)
  they mean the same. But the chips differ: br23's clock header encodes
  the UART clock in `CLK_CON1` bits 10-11 as 0 the PLL's 48 MHz, 1 the
  oscillator, 2 the low-speed bus clock, while the FM-1's chip's SDK has
  0 and 1 the other way round (HW-53). So none of this is confirmed for
  the FM-1's chip, and fwtest is not changed for it. Two points differ
  from fwtest: fwtest counts `OTCNT` in 48 MHz UART clocks (HW-70,
  emulator-only), and fwtest has no 9-bit frames, receive by `BUF` or
  `CON1` (HW-71).
- Sources: SDK63 `cpu/br23/uart_dev.c` (lines 22-23, the UART and
  timeout clocks; UART1's put-byte, get-byte, interrupt, read, write,
  set-rate and open functions at lines 300, 321, 354, 406, 448, 473 and
  490, and UART0's and UART2's alike; the flow control at lines 899-923),
  `cpu/br25/uart_dev.c` and `cpu/bd29/uart_dev.c` (the same functions,
  without `CON1`); SDK63 `include_lib/driver/cpu/br23/asm/br23.h` lines
  372-393, `br25/asm/br25.h` lines 380-401 and `bd29/asm/bd29.h` lines
  426-447 (the UART's words and bases); SDK63
  `include_lib/driver/cpu/br23/asm/clock_hw.h` line 298 (the UART clock
  field). For the FM-1's chip: SDK `WL82.h` lines 569-591; HW-53.
- Standing: other chip (SDK63)
- Needed by: real hardware (Level 2); M6a and M6b (the UART's set-up)

## 19. Flash storage (SR-9, M7)

Completes section 8 for SR-9. HW-76 to HW-79 are the chip and its flash
part, HW-80 and HW-81 the FM-1's flash layout and what the boot chain and
the update path need, HW-82 fwtest 0.5.0's flash, superseded by HW-83,
fwtest 0.6.0's; HW-84 the code window's controller on the chip; HW-85
the flash's pins and what a firmware leaves alone at start-up. Open:
Q-21 to Q-24.

### HW-76: The flash part's identity
- Fact: In fwtest the flash chip answers the JEDEC ID read (`0x9F`) with
  `0x85 0x60 0x14`. The Puya P25Q80H datasheet gives exactly that ID for
  that part (Puya's manufacturer ID `0x85`; `0x60 0x14`, 8 Mbit, so
  1 MiB). Whether the FM-1 carries that part is known only from the
  emulator, whose model says it answers as real units do; no allowed
  source names the part, and FM-1-RE says only that the firmware reads the
  ID and takes the capacity from it. Read the ID on the chip and, if it
  differs, look up that part's datasheet before relying on HW-77's times
  (Q-21). A firmware that reads the ID at start-up and checks it can
  refuse to write to a part it doesn't know.
- Sources: PUYA p. 54 (table "ID Definitions": RDID `85 60 14`); E-22
  (fwtest's answer); RE `docs/io/09-storage.md` §1 (the ID read, capacity
  as 2^n); the emulator model (the part on real units).
- Standing: emulator-only
- Needed by: M7

### HW-77: The P25Q80H's sizes, times and endurance
- Fact: The P25Q80H, from its datasheet: 1 MiB; programming only clears
  bits (1 to 0), and only an erase sets them back to 1. Erase units: a
  256-byte page (`0x81`), a 4 KiB sector (`0x20`), a 32 KiB block
  (`0x52`), a 64 KiB block (`0xD8`), the whole chip (`0x60` or `0xC7`);
  program: up to 256 bytes within one 256-byte page (`0x02`). Times,
  typical / maximum: page program 2 / 3 ms; page, sector, 32 KiB, 64 KiB
  and whole-chip erase each 8 / 12 ms; status register write 8 / 12 ms.
  Endurance 100 000 program/erase cycles; data retention 20 years. An
  erase or program can be suspended (`0x75` or `0xB0`) and resumed
  (`0x7A` or `0x30`): the suspend takes effect within 30 µs, and an erase
  makes progress only if at least 200 µs (a program 100 µs) pass between
  a resume and the next suspend. While suspended, the array outside the
  sector being erased or the page being programmed can be read. The
  requirement: wait for the end of each operation by reading the status
  register (HW-78), never by a fixed delay, and plan for the maximum
  times.
- Sources: PUYA p. 1 and p. 4 (100K cycles, 20-year retention), p. 11
  (AC table: tPP, tPE, tSE, tBE1, tBE2, tCE, tW, tESL, tPSL, notes 4 and
  5), p. 21-22 (command table), p. 40-43 (erase and page program), p. 55
  (suspend and resume).
- Standing: confirmed (PUYA)
- Needed by: M7

### HW-78: The P25Q80H's command rules and the busy state
- Fact: From the datasheet: a write enable (`0x06`, which sets the status
  register's WEL bit) must come before every program, erase and status
  register write; without it the command is ignored, and WEL clears again
  when the operation ends. A program or erase starts when chip select goes
  high, and only if it goes high at a byte boundary (after the eighth bit
  of a byte); otherwise the command is rejected. A page program whose
  bytes run past the end of the 256-byte page wraps round to the page's
  first byte (bytes before the start address are then written); of more
  than 256 bytes only the last 256 are kept; fewer than 256 change only
  the bytes sent. Status register 1 (`0x05`): bit 0 WIP (1 while a
  program, erase or status write is in progress), bit 1 WEL, bits 2-6
  block protect BP0-BP4 (non-volatile: an erase or program in a protected
  area is not executed), bit 7 SRP0. While WIP is 1 the chip ignores
  array reads (`0x03`, `0x0B` and the dual and quad reads) and the ID
  reads; reading the status register works throughout.
- Sources: PUYA p. 18 (chip select at a byte boundary; array access
  ignored during a program, erase or status write), p. 25-26 (status
  register bits, block protect), p. 31-32 (reads rejected while busy),
  p. 40 (erase needs WEL, starts on chip select high), p. 43 (page
  program, the wrap, the last 256 bytes), p. 54 (ID read not decoded
  while busy).
- Standing: confirmed (PUYA)
- Needed by: M7

### HW-79: Code, interrupts, core 1 and audio while the flash is busy
- Fact: On the chip one SPI NOR flash holds everything, and the code
  window reads it (FM-1-RE). While the firmware works the flash directly,
  from its first command until the operation ends (WIP 0, HW-78), nothing
  may be fetched or read from the code window: no code, no constant
  tables or strings, no interrupt handler, nothing on core 1. The JieLi
  SDK's example of direct flash access says so: everything between
  entering and leaving that mode, code, data and constants, must be in
  RAM, and nothing may be printed when the system runs from flash; and
  the chip ignores array reads while busy (HW-78), so the window cannot be
  served then. The stock firmware keeps its flash routines and several
  interrupt handlers in RAM (FM-1-RE). So: put the routine that works the
  flash, and everything it calls and reads, in RAM; for its whole length
  either keep interrupts masked, or have every handler that can run, and
  everything it reaches, in RAM; and keep core 1 off the window too
  (stopped, or running from RAM). How the window's own controller hands
  the flash over to SPI0 and back on the chip is Q-22. Audio: the output
  plays its halves from RAM by itself (HW-44, HW-45), so it keeps playing
  as long as each half is refilled in time. A 4 KiB erase can take 12 ms,
  about 530 frames at 44 117.6 frames a second, more than a half lasts
  unless `LEN` is over about 1 060 words. To keep the audio going through
  an erase, either the refill handler and the synthesis it runs are in RAM
  and interrupts stay on, or the erase is cut into pieces with suspend and
  resume (HW-77) so the window can be used between them, or the output is
  muted and the gap accepted. fwtest checks none of this today (HW-82).
- Sources: SDK `apps/common/example/peripheral/flash/flash_register/main.c`
  lines 9-22 and 39-46 (the comments around the direct-access section:
  code, data and constants in RAM; no printing when running from flash);
  PUYA p. 18, p. 31-32 (array reads ignored while busy); RE
  `docs/io/09-storage.md` (one flash holds everything; the code window
  reads it) and `docs/io/01-boot.md` §1 (flash routines and interrupt
  handlers RAM-resident); HW-45 (the half's length).
- Standing: confirmed (SDK, RE, PUYA)
- Needed by: M7

### HW-80: The FM-1's flash layout, and the region a firmware may use
- Fact: On an FM-1 with M-VAVE's firmware, the 1 MiB flash is laid out
  as follows (chip offsets):
  - `0x00000`-`0x03FFF`: the boot area: a header, the second-stage loader
    from `0x000A0` (which the mask ROM loads), the loader's configuration
    from `0x038D0`. Never erase or write it: the chip boots from it.
  - `0x04000`-`0x93FFF`: the app area: a file table, then the app and its
    configuration, encrypted with the chip's key (HW-81). The update
    package's flash image covers `0x00000`-`0x93FFF`.
  - `0x94000`-`0xE8FFF` (340 KiB): the stock firmware's key-value store
    ("VM"). The update path also stages its loader in "the VM/loader
    flash area" (FM-1-RE; where in it, not stated).
  - `0xE9000`-`0xE9FFF`: Bluetooth information ("BTIF").
  - `0xEA000`-`0xFBFFF` (72 KiB, 18 sectors): the stock firmware's user
    patch storage ("USR"); the update package carries a `USR` entry.
  - `0xFC000`-`0xFEFFF` (12 KiB): unused.
  - `0xFF000`-`0xFFFFF`: holds a per-unit key and address (`key_mac`).
    Never erase it: nothing can restore it. The SDK's packaging tool also
    reserves a flash's last 4 KiB by default.
  So a firmware's own storage must stay out of the boot area, out of its
  own image, and out of the last 4 KiB, and should stay out of the
  Bluetooth sector. In particular "the chip's last 64 KiB" includes the
  last sector: end a store at `0xFEFFF` at the latest. Where our firmware
  sits on the chip, and so what is free, is set when M9 packages it. Of
  the stock layout's regions past the app area: the USR region,
  `0xEA000`-`0xFBFFF` (72 KiB), holds the stock firmware's saved user
  patches, so a store there erases them, and the stock firmware reads that
  region back if the unit returns to it; `0xFC000`-`0xFEFFF` is unused
  but only 12 KiB (three sectors); the VM region is the stock firmware's
  settings and the update's staging area. Which one a store takes is a
  product choice, for the owner; keep it in one definition. FM-1-RE adds
  that its free regions have not been validated as safe for writes from
  outside the stock firmware, and whether an update rewrites the USR or
  VM region is not known (Q-24). In fwtest the whole chip past the image
  is erased and free (HW-5, HW-82).
- Sources: RE `docs/architecture.md` §2 ("Flash layout", from the update
  package's file table) and §3 (the mask ROM loads the loader from
  `0xA0`); RE `docs/io/01-boot.md` §3 (the loader reads the file table's
  section tags); RE `docs/io/09-storage.md` §3 and §6 (the VM store; the
  free regions not validated); RE `docs/io/11-ota-protocol.md` (the
  package's entries, among them `flash.bin` and `USR`; the loader staged
  in the VM/loader area); SDK `cpu/wl82/tools/isd_config_rule.c` lines
  106 and 306-334 (the last 4 KiB reserved; reserved regions and whether
  a download erases, keeps or protects each).
- Standing: confirmed (RE, SDK)
- Needed by: M7, M9

### HW-81: The code window on the chip differs from fwtest's
- Fact: On the chip:
  - The app area from `0x04000` is encrypted with the chip's key, and the
    window shows it decrypted; the stock firmware scrambles data it
    writes below its app area's end so that it reads back through the
    window. Plain data written over SPI0 inside that area therefore
    reads back changed through the window.
  - The stock window starts at chip offset `0x04120` (the app's first
    byte after the file table): window address `0x02000000 + n` is chip
    offset `0x4120 + n`. In fwtest it is `0x4000 + n` (HW-5).
  - The stock firmware synchronises the instruction cache after a
    program, so the window may keep showing old bytes after a change
    (Q-22).
  The requirement: address the store by chip offset, and read it back with
  the flash's read command (`0x03`) over SPI0, not through the code
  window; then the same code reads the same bytes on the chip and in
  fwtest.
- Sources: RE `docs/architecture.md` §2 (the window as flash offset −
  `0x4120` + `0x02000000`; the app area encrypted with the chip key from
  `0x4000`); RE `docs/io/09-storage.md` §1 (the cache synchronised after a
  program; writes below the encrypted region's end scrambled); HW-5.
- Standing: confirmed (RE)
- Needed by: M7

### HW-82: The flash chip in fwtest 0.5.0
- Fact: In fwtest as pinned (0.5.0), beyond HW-47: an SPI0 byte takes no
  emulated time of its own (64 bytes cost only the instructions that send
  them); an erase or program completes when its command does, and the
  status register's WIP bit is never 1, so a firmware's wait for WIP ends
  at its first read; a page program sent without a write enable still
  writes (the chip ignores it, HW-78); bytes programmed past the end of a
  256-byte page go on into the next page (the chip wraps them to the
  page's start); programming clears bits only, as on the chip; a 4 KiB
  erase clears its aligned sector and a 64 KiB erase its aligned block;
  reading through the window during or after a flash operation always
  works. Not modelled: the 32 KiB block erase (`0x52`), the page erase
  (`0x81`), the chip erase, suspend and resume, block protection. The
  flash persists between runs only through files: `--flash FILE` gives the
  chip's starting bytes (the image is then written at `0x4000` again) and
  `--flash-out` saves the whole chip at the end of the run, whatever its
  outcome. A run that ends (`--ms`) stops with the flash as it is then;
  with operations instantaneous, that can't fall inside one. fwtest's
  next version is to model the busy times, the page wrap and the write
  enable, and a power cut during an operation (HARNESS.md will say when).
- Sources: E-22 (64 bytes in 45 TIMER4 ticks; erase, then one status read
  with WIP 0; `F0 0F AA FF` then `3C` ×4 gave `30 0C 28 3C`; a program
  without WREN wrote; "ABCD" at `0x800FE` put "CD" at `0x80100`; the erase
  extents); HARNESS ("The flash chip", `--flash`, `--flash-out`); the
  emulator model (the commands not modelled).
- Standing: superseded by HW-83
- Needed by: M7

### HW-83: The flash chip in fwtest 0.6.0
- Fact: In fwtest from 0.6.0 the flash chip is a 1 MiB SPI NOR chip on
  SPI0 (`JL_SPI0`, `0x00011C00`: `CON` +0, `BUF` +8), selected by PD0
  (bit 0 of `JL_PORTD->OUT`, `0x000500C0`) low; a command is the bytes
  sent while selected. A write to `BUF` sends one byte and takes no
  emulated time of its own; with `CON` bit 12 set the byte received lands
  in `BUF`; `CON` bit 15 reads 1 when a byte is done and writing bit 14
  clears it. It answers JEDEC ID `0x85 0x60 0x14` and takes the
  P25Q80H's commands as HW-78 gives them: read `0x03`, fast read `0x0B`,
  status `0x05` (bit 0 busy, bit 1 write enable) and `0x35`, write enable
  and disable `0x06` and `0x04`, erases of 256 bytes `0x81`, 4 KiB
  `0x20`, 32 KiB `0x52`, 64 KiB `0xD8` and the whole chip `0x60`/`0xC7`,
  page program `0x02`. An erase or program needs a write enable first
  (otherwise nothing happens), starts when PD0 goes high, and keeps the
  chip busy for the datasheet's maximum time, a program 3 ms and an erase
  of any size 12 ms (HW-77); meanwhile status bits 0 and 1 read 1 and
  every command but the status reads is ignored. A program wraps within
  its 256-byte page and only clears bits. While the chip is busy, a core
  that is about to run code in the code window, or reads it, ends the run
  as a fault (HW-79 says why). The chip's contents show through the
  window (HW-5). Not modelled: suspend and resume, block protection,
  dual and quad reads. Supersedes HW-47 and HW-82 (fwtest 0.5.0: no busy
  time, no write enable needed for a program, no wrap). Until
  `config/fwtest-image` pins 0.6.0, `tools/fwtest` runs 0.5.0, which
  HW-82 describes.
- Sources: E-22 (with fwtest 0.6.0: a 4 KiB erase and its status reads
  288 005 TIMER4 ticks, 12.0 ms; a program without write enable left the
  bytes erased; "CD" programmed past the end of a page landed at the
  page's start, ANDed with what was there; the ID, the status bits, the
  erase extents as before); HARNESS ("The flash chip"); the emulator
  model with vendor patch 0010 (the commands; the busy rule).
- Standing: confirmed (E-22)
- Needed by: M7

### HW-84: The code window's controller and its decryption, on the chip
- Fact: On the chip the code window is served by a flash controller,
  `JL_SFC`, at `0x00040200`: `CON` +0 (read and write), `BAUD` +4, `CODE`
  +8 and `BASE_ADR` +12 (write only). Its decryption has a block of its
  own, `JL_SFCENC`, at `0x00040300`: `CON` +0 (8 bits), `KEY` +4 (16
  bits), and four write-only words that bound address ranges,
  `UNENC_ADRH` +8, `UNENC_ADRL` +12, `LENC_ADRH` +16, `LENC_ADRL` +20
  (by their names, an unencrypted range and a second range). The stock
  firmware's direct flash routines first wait for the controller to be
  idle and switch it to a command mode through `0x00040200` (FM-1-RE,
  medium confidence), then drive SPI0. The SDK gives no bit meanings
  (its flash driver is a prebuilt library), so which bits hand the flash
  to SPI0 and back, and how the ranges are set for the stock layout,
  stay open (Q-22). fwtest models neither block: it has no controller to
  hand over, and its window is never encrypted (HW-83).
- Sources: SDK `WL82.h` lines 13-16 (`hsfr_base`, `map_adr`) and 38-60
  (`JL_SFC`, `JL_SFCENC`); RE `docs/io/09-storage.md` §1 (command mode via
  `0x40200`, the idle wait); RE `docs/architecture.md` §2 (the app area
  encrypted with the chip key).
- Standing: confirmed (SDK, RE)
- Needed by: M7 (real hardware), M9

### HW-85: The flash's pins on the chip, and what a firmware leaves alone
- Fact: On the chip the flash is on SPI0's port A, which the code
  window's controller (`JL_SFC`, HW-84) uses too: chip select PD0, clock
  PD4, data out (IO0) PD5, data in (IO1) PD1, and for quad transfers IO2
  PD2 and IO3 PD3. SPI0's other port, C (PC5 chip select, PC3 clock, PC4,
  PC0, PC1, PC2), is chosen by setting bit 5 of `JL_IOMAP->CON0`; port A
  by clearing it (with bit 1 of `CON1` clear). From the AC7911B's
  datasheet alone (JL7911B), not the SDK: PD0 is pulled up by default, so
  the flash is deselected while nothing drives it, and on that package
  PD6 is the flash's power gate (`SFGAT`); the pin assignment above also
  agrees with that datasheet. The SDK's
  board code leaves ports D, E, F and G alone ("the flash and SDRAM
  ports... are controlled internally") even when it sets every other pin
  to high impedance before power-off.
  The requirements: at start-up, a firmware configures no pin of port D
  (direction, pulls, drive, digital input, function) and never sets bit 5
  of `JL_IOMAP->CON0` or bit 1 of `CON1`: the chip is running its code
  from the flash through those pins. To work the flash itself it drives
  the chip select through bit 0 of `JL_PORTD->OUT` only (as in fwtest,
  HW-83), changing no other bit of `JL_PORTD`, and only once the code
  window's controller has handed the flash over (still open, Q-22).
  The SDK's loader settings name other pins for the loader's flash port
  (`cpu/wl82/tools/isd_config_rule.c` lines 117-128: "CS:PD3 CLK:PD0" or
  "CS:PA13 CLK:PD0"). Both the SDK's own SPI0 tables and the AC7911B's
  pin list disagree with that comment and agree with each other, so this
  entry follows them; the comment may come from another chip.
- Sources: SDK `include_lib/driver/cpu/wl82/asm/spi.h` lines 151-178
  (SPI0's two pin sets; the `JL_IOMAP` bits for port A and C) and 190-198
  (the code window's controller on SPI0 with PD0 to PD5);
  SDK `apps/demo/demo_DevKitBoard/board/wl82/DevKitBoard.c` lines 771-772
  (ports D to G skipped: "flash sdram PD PE PF PG口不能进行配置,由内部完成控制");
  SDK `cpu/wl82/tools/isd_config_rule.c` lines 117-128 (the loader's
  port comment, which disagrees); JL7911B Table 1-1, page 9 (pins 37-41:
  PD5 `SPI0_DOA`/`SFC_DOA`, PD4 `SPI0_CLKA`/`SFC_CLKA`, PD6 `SFGAT`, PD1
  `SPI0_DIA`/`SFC_DIA`, PD0 `SPI0_CSA`/`SFC_CSA` with pull-up) and Table
  2-4, page 12 (PB1 and PD0 pulled up by default); HW-83 (fwtest's chip
  select is PD0). The owner accepts JL7911B (its pages marked
  confidential, LCSC serving it publicly, P-56) as the source of the
  three facts taken from it: PD0's pull-up, PD6 the flash's power gate,
  and its pin list agreeing with the SDK's (2026-10-25, recorded by
  session owner-answers-1025); each stays to be confirmed on real
  hardware.
- Standing: confirmed (SDK, JL7911B; PD0's pull-up, PD6 and the datasheet's pin list from JL7911B, which the owner accepts as a source; those three to be confirmed on real hardware)
- Needed by: M7 (real hardware), M9

## Open questions

What isn't known, or is known only from material the spec may not use. A
spec request can turn one into a fact.

- **Q-1. Other RAM on the chip.** Whether the chip has RAM at `0x01F00000`
  and `0x04000000` (HW-7), how much, and whether it can be used. The SDK's
  layout names a cache RAM at `0x01F20000` and an external SDRAM window at
  `0x04000000`.
- **Q-2. Clock set-up on the chip.** Which registers and steps set the PLL
  and system clock on real hardware (fwtest needs none). Since SR-2, the
  clock registers' addresses, the main clock select and the supported rates
  are known (HW-53, HW-54); still open: the PLL's control registers and
  fields (FM-1-RE places the PLL block at `0x00016A00`, which the SDK's
  header names as part of another block; the SDK's own PLL and `SYS_DIV`
  field definitions are switched off), the order of the steps that change
  the system clock safely (the flash and bus clocks with it), and the
  clock when an installed app starts: FM-1-RE says only that the loader
  brings up "clocking sufficient for XIP". Settled by a datasheet or a
  probe on real hardware.
- **Q-3. TIMER0-3 prescaler settings in fwtest.** The SDK gives the chip's
  table (HW-48); fwtest's settings other than 0 and 2 were not measured.
  Measure with a black-box test, or ask.
- **Q-4. The core tick timer's period on the chip.** Which clock `TTMR_PRD`
  counts on real hardware (fwtest always uses 10 ms).
- **Q-5. A debug console on the chip.** Whether `DBG_MSG` writes go
  anywhere on real hardware (the SDK marks it read-only, and reads it as
  the exception's cause word, HW-51), or which UART pins could carry debug
  output.
- **Q-6. LCD wiring.** Since SR-3, SPI1's pin groups, the pin-group
  select, the port set-up registers, `CON`'s named bits, the panel's clock
  limit and reset timing, and FM-1's own `CON` and `BAUD` values are known
  (HW-55 to HW-58); still open: which pin is the panel's chip select
  (probably PC7), whether the panel has a reset pin and a backlight pin,
  which ones and their levels; the drive the pins need; `CON` bit 5 and
  the other mode bits, and how `BAUD` sets the clock (so which value gives
  at most 15 MHz); the panel's offset within the controller's 240 × 320
  memory for each `MADCTL` orientation, which orientation shows the
  picture upright as the FM-1 is held, and whether it needs inversion on
  (`0x21`) to show colours right (none of the sources says; fwtest ignores
  `MADCTL` and inversion, HW-31). Settled by a probe on real hardware.
- **Q-7. The panel's wiring on the chip.** Whether the board's key matrix,
  encoders and LEDs are wired as fwtest presents them (HW-33, HW-34,
  HW-38, HW-42: the pins, the shift registers, an LED for every key, which
  physical turn is "clockwise"); pull-ups, directions and drive for the
  pins, LED polarity and current. fwtest needs no pin set-up.
- **Q-8. The other ADC channels.** What channel 3 and the other channels
  carry on the board (fwtest gives them fixed values).
- **Q-9. Audio on the chip.** How `JL_ALNK0`'s output reaches the DAC or
  codec on real hardware, which bits of each word it uses, its clock set-up
  and true rate, and the analog set-up (FM-1-RE's audio document names DAC
  registers at `0x00012F00`; not used here).
- **Q-10. Interrupt details on the chip.** Whether the chip switches
  stacks on an interrupt from user mode exactly as HW-3 says; its nesting
  rules and choice among pending sources (HW-22); whether the two cores
  share one vector table; what `idle` does with interrupts masked (HW-24).
  The toolchain's interrupt attribute works in fwtest.
- **Q-11. Booting on the chip.** The contents of the boot-parameter block
  the loader passes in r0, and whether a raw image can be started on real
  hardware without M-VAVE's loader (PLAN.md, M9 risk), and whether such an
  image can release core 1 as HW-9 says.
- **Q-12. MIDI input.** Since SR-8, the jack's UART (UART1), its
  registers, source and clock choices, its receive flags, acknowledge and
  count latch, and fwtest's receiver are known (HW-67 to HW-71); still open
  for the chip: which pin the jack reaches, and its port set-up (fixed pin
  pair or an input channel of `JL_IOMAP`; direction, pull-up); how the TRS
  socket is wired (type A or B); `CON1`'s bits; how `BAUD` sets the rate,
  so its value for 31 250 baud from each UART clock; whether the receiver
  can be used without the DMA, a byte at a time from `BUF` with an
  interrupt per byte, and which bits that takes; whether there are framing
  or overrun flags and how they clear; whether `RXEADR` is the ring's last
  byte or one past it; what the DMA does when the ring overflows; which
  clock `OTCNT` counts when the UART clock isn't the PLL's 48 MHz. The SDK
  at the pinned commit gives none of them (its UART driver is a prebuilt
  library). Since pin-050, another JieLi SDK whose UART driver is open
  (SDK63, for other chips with the same UART words; the owner allowed it)
  gives answers for those chips (HW-75), not yet for the FM-1's: the
  `BAUD` formula (so 383 from 48 MHz); 9-bit frames on `CON0` bit 1;
  receive without the DMA by polling bit 14 and reading `BUF`, cleared
  with bit 12; `RXEADR` one past the ring's last byte; `CON1` as flow
  control on one chip's UART1; and `OTCNT` in the low-speed bus clock,
  whatever the UART clock, which differs from fwtest's 48 MHz count
  (HW-70). Still open even there: a receive interrupt per byte without
  the DMA; error flags (none is used); what the DMA does when the ring
  overflows; and for the FM-1 the jack's pin, its port set-up and the TRS
  wiring. Settled for the FM-1's chip by a datasheet or a probe on real
  hardware.
- **Q-13. The timer acknowledge on the chip.** Whether writing a TIMER0-3
  `CON` to acknowledge its interrupt restarts the count, as it does in
  fwtest (HW-48), or the count runs on and the period stays `PRD` counts.
  The SDK's examples acknowledge every interrupt with such a write but
  don't say. Settled by a probe on real hardware.
- **Q-14. CPU exceptions on the chip.** What the sources don't establish
  about source 1 (HW-49 to HW-51): which causes are on when an installed
  app starts, and which `EMU_CON` and `DBG_EN` bits turn each on (the SDK's
  settings suggest bit n for cause n, but its demonstration reports a
  misaligned access although the SDK never sets `EMU_CON` bit 0); whether
  the exception obeys the source's `ICFG` enable, `icfg` bit 8 and `sti`
  like other sources; what `reti` holds (the faulting instruction or the
  next) and whether the faulting access or division completes; how the
  stack limits are compared; whether an undecodable instruction raises it
  (`EMU_MSG` bit 1 is named "illegal instruction"); whether a write to the
  code window does. fwtest models none of it (HW-52). Settled by a probe on
  real hardware.
- **Q-15. SPI1's interrupt on the chip.** Whether source 16 follows the
  pending flag and `CON` bit 13 together (so setting bit 13 while a
  finished transfer is still pending raises it at once, and clearing bit
  13 withdraws it), or only a transfer that finishes while bit 13 is set
  raises it, as in fwtest (HW-59). The SDK's example sets bit 13 before
  it starts a transfer and acknowledges in the handler, which works either
  way. Settled by a probe on real hardware.
- **Q-16. Floating point on the chip.** How many cycles each `fprev1`
  instruction takes (add, multiply, divide, multiply-add, conversions,
  compares) and whether they pair or stall; whether the chip rounds to
  nearest even, keeps subnormals and handles NaNs and out-of-range
  conversions as fwtest does (HW-63); which conditions set `EMU_MSG` bits
  16 to 20 and whether they raise source 1 (Q-14); what the toolchain's
  CPU models `r1` to `r5` differ in. Settled by a timing probe on real
  hardware; the toolchain documents none of it.
- **Q-17. The second core on the chip.** Whether core 1 runs at the same
  clock as core 0; what the two cores cost each other (shared caches,
  buses, flash and RAM wait states) when both run from the code window
  and work in main RAM; what core 1 needs before it runs from a raw image
  (its release, Q-11; its cache and protection set-up); whether a
  peripheral source enabled on both cores interrupts both. The `corex2`
  block has per-core counters (words 0x80 to 0x8F, SDK `csfr.h` lines
  119-134) whose meaning the SDK doesn't state. Settled by a probe on real hardware.
- **Q-18. Memory seen across the cores on the chip.** Whether main RAM is
  cached, and whether a plain store by one core is seen by the other's
  next load without `csync` or a cache operation (HW-65). Settled by a
  probe on real hardware.
- **Q-19. The block moves' write-back forms on the chip.** What
  `{list} = [rN++]`, `{list} = [--rN]` and their stores leave in the base
  (fwtest: rN + 4n, rN - 4n), which wins when such a form's base is also
  in its list, and what an empty list does (HW-66). The toolchain's
  compiler was not seen to emit them. Settled by a probe on real
  hardware.
- **Q-20. MIDI output on the chip.** Which UART and pin drive the
  SMK-37's MIDI OUT jack, and its port set-up (fixed pin pair or an output
  channel of `JL_IOMAP`; drive); how its TRS socket is wired (type A or B);
  whether the SMK-37 has the FM-1's chip; whether the FM-1's board brings
  UART1's transmit pin anywhere; which `CON0` bit enables the transmit
  interrupt (bit 2 on the chips SDK63 covers, HW-75); whether, after a DMA, the pending means the transfer has been
  read from RAM or the last stop bit has left the pin; whether the
  transmit DMA needs a 4-byte aligned address or length; what writing
  `TXCNT` does while a transfer is still going; how `BUF` and the DMA mix.
  Settled by a datasheet or a probe on real hardware (an SMK-37 and an
  FM-1).
- **Q-21. The FM-1's flash part.** Which part the FM-1 carries: its
  JEDEC ID read on a unit (fwtest answers `85 60 14`, the Puya P25Q80H,
  HW-76), or the marking on the chip. If it differs, HW-77's times and
  HW-78's rules need that part's datasheet. The SDK lists an AC791N
  package with 1 MiB of flash inside it (`7911B8`, "内置flash",
  `apps/demo/demo_uvc/board/wl82/board_7911B_cfg.h` lines 11-15), so the
  FM-1's flash may have no package of its own to photograph. Settled by a
  probe on real hardware or a photo of the board.
- **Q-22. Working the flash directly on the chip.** How the code window's
  controller hands the flash to SPI0 and takes it back (the SDK does it in
  its prebuilt library's enter and leave calls); whether, once it has,
  bit 0 of `JL_PORTD->OUT` reaches PD0 (the chip select, HW-85) or the
  controller keeps driving it, and so whether PD0's direction must be set
  for the handover and restored after; SPI0's clock and mode
  for those commands; whether the window caches the flash and what makes
  it see a change (the stock firmware synchronises the instruction cache
  after a program, HW-81); which bits of the controller's `CON` (HW-84)
  hand the flash over and back, and how its decryption ranges are set;
  whether core 1 must be stopped (the emulator's
  model says the stock firmware pauses it around flash work). Settled by
  a probe on real hardware, or a datasheet for the chip.
- **Q-23. Write protection on the FM-1's flash.** Whether the status
  register's block-protect bits (HW-78) are set on a shipped unit or by
  the loader, which would make erases and programs in the protected range
  silently do nothing. Read status register 1 on a unit; the SDK's own
  write-protect switch is off by default. Settled by a probe on real
  hardware.
- **Q-24. What an update rewrites.** Which regions a stock-style update
  erases or writes beyond its flash image (`0x00000`-`0x93FFF`, HW-80):
  where in the VM region it stages its loader, whether its `USR` entry
  rewrites `0xEA000`-`0xFBFFF`, and whether our own packaging (M9) can
  mark a region to be kept. Decides whether stored patches survive an
  update. Settled in M9, from FM-1-RE's update documents and the SDK's
  packaging settings (HW-80's sources), or by a test on real hardware.
