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
storage, for SR-9 (open: Q-21 to Q-24). Session spec-a1-fwsc (spec side, 2026-10-27)
added section 21, the update package and the loader chain, for Phase A1
(open: Q-25, Q-26); its HW-91 supersedes HW-81. Session spec-br17-package (spec
side, 2026-11-17) added section 24, the package as JieLi's packaging
tools write it, for BR-17 (Q-25 answered in part; Q-26 narrowed). Session
spec-br17-tools (spec side, 2026-11-18) added section 25, what the unit's
installer and bootloader check (Q-25 and Q-26 answered in large part).
Session spec-sr14 (spec side, 2026-11-18) added section 26, the FM-1's
panel, backlight, keys and LEDs and the state at the app's entry, for
SR-14 (Q-2, Q-6 and Q-7 answered in part). Session spec-sr15 (spec side,
2026-11-18) added section 27, the FM-1's two flash parts, for SR-15
(Q-21 and Q-23 answered in part). Session spec-sr16 (spec side,
2026-11-18) added section 28, what the hardware build still needs on
the chip, for SR-16 (Q-3, Q-10, Q-13 and Q-22 answered in part).

## How to read it

Every fact is an entry:

- **ID**: `HW-n`. IDs are never reused or renumbered. A corrected fact gets a
  new ID, and the old entry stays, marked superseded.
- **Fact**: the property or requirement. "On the chip" means the AC791N on
  the FM-1; "in fwtest" means how fwtest presents it (docs/HARNESS.md). Where
  an entry says neither, it holds for both as far as the sources go.
- **Sources**: as precisely as possible (the keys are under "Sources" below).
- **Standing**:
  - **confirmed**: an independent source agrees: the JieLi SDK (its
    packaging tools' output included, PKG), the unit's installer and
    bootloader's own sources (MF, MB), what the owner observes on the
    unit (UNIT), FM-1-RE's
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
| UCUN | UCUN Technology's UC25HQ80 datasheet ("Ultra Low Power, 8M-BIT Serial Flash Memory with Dual, Quad SPI"), Version 1.2, 2022-01-04, 61 pages, from UCUN's own site, `http://www.ucuntech.com/uploads/20220324/d8602ea203b2303c2162d067ce715c4c.pdf`, accessed 2026-11-18, SHA-256 `0c4f3dc7…a9e2ccc7eb` (PROVENANCE P-73). Page numbers as printed. Not copied into this repository. It describes the part newer FM-1s carry (HW-120). |
| PANEL | The FM-1's printed panel labels, from two sources that agree: the owner's screenshot of the F-Emulator app's panel with its default labels, `docs/sources/panel-app-default-labels.png` (secondary: the app's drawing of the panel); and M-VAVE's product photo of the FM-1, `https://www.m-vave.com/images/products/fm-1.webp` on `https://www.m-vave.com/product.html?id=fm-1`, accessed 2026-10-22, SHA-256 `e610a746…df14b95`, not copied into this repository (PROVENANCE P-12). Only the printed labels are taken from them. The owner chose these two sources. |
| MAN | M-VAVE's user manuals: the FM-1's, the English part (pages 1-12) of `https://m.media-amazon.com/images/I/A1WOydif9HL.pdf`, SHA-256 `69bfea10…8b715da`, accessed 2026-10-24 (PROVENANCE P-41); the SMK-37 Pro's, as `https://www.manualslib.com/manual/4132288/M-Vave-Smk-37-Pro.html` shows it, accessed 2026-10-24 (PROVENANCE P-42). Neither copied into this repository. Only what they say about the connections is used. |
| MPLUS | Manuals+'s "M-VAVE SMK-37 PRO MIDI Controller User Manual", `https://manuals.plus/asin/B0GQZP7C8G.pdf`, 13 pages, SHA-256 `77d9d537…3e3745`, accessed 2026-10-24, supplied by the owner and checked by the planning conversation, not fetched by a session here (PROVENANCE P-49). A third party's write-up, not M-VAVE's manual: secondary, it never confirms an entry on its own. Not copied into this repository. |
| PKG | JieLi's packaging tools from the SDK (as SDK, same commit), `cpu/wl82/tools/loader_tools/`: `isd_download.exe` (4.2.52), `fw_add.exe` and `ufw_maker.exe`, run under wine 8.0 in a throwaway container with no network, on our own input (PROVENANCE P-65). They show what JieLi's packaging writes, not what the chip checks. |
| MF | m-flasher, the FM-1 installer on the owner's unit, `https://github.com/jvitkauskas/m-flasher` at `8fbece7348d758ac284325eed455781675ac95ff` (2026-11-15), MIT: `src/formats.rs`, `src/ops.rs`, `docs/usage.md`, `docs/safety.md` only, read under the owner's ruling for BR-17 (PROVENANCE P-67). Only the package format and what it checks are taken. |
| MB | m-bootloader, the bootloader on the owner's unit, `https://github.com/jvitkauskas/m-bootloader` at `3ac7651a019fa44daba061b05654278496477b64` (2026-11-13), MIT: `docs/SPEC.md`, its flash formats and checked start (PROVENANCE P-67); since SR-14 also `src/board.c`, `src/display.c`, `src/platform.c`, `src/boot.c` and `src/startup.S`, for board facts (PROVENANCE P-68). No stock firmware's details are taken from it. |
| UNIT | What the owner observes on the owner's FM-1 unit (identified as in HW-120 by flash ID `856014`, running m-bootloader as MB), running this repository's own test builds, relayed by the owner; each entry gives the build and the date. A fact source by the owner's ruling of 2026-11-19 (docs/prompts/spec-unit-facts.md). It shows what one unit does, not what the chip's documentation guarantees. |
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
- Standing: superseded by HW-91 (its window address is wrong: the window
  starts at flash `0x4000`; its other points stand, restated there)
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

## 20. The USB core's register port (the F-Emulator app's note)

HW-86 confirms, from the SDK and RE, the behaviour the F-Emulator app
found missing in the emulator (PROVENANCE P-59), which fwtest 0.7.0 now
has (HARNESS.md, "USB").

### HW-86: The USB core's registers through one port, `JL_USB->CON1`
- Fact: The chip's USB device core is MUSB-style, with byte registers by
  index: 0 `FADDR`, 1 `POWER`, 2 and 3 `INTRTX1/2`, 4 and 5 `INTRRX1/2`,
  6 `INTRUSB`, 7 to 11 the matching interrupt enables, 12 and 13 the frame
  number, 14 `INDEX`, 15 `DEVCTL`, 16 onwards the endpoint registers. A
  firmware reaches them through one word, `JL_USB->CON1` at `0x11804`
  (`JL_USB` at `0x11800`): to write, it writes `index << 8 | byte` with
  bit 14 (`MC_RNW`) clear; to read, `index << 8` with bit 14 set; then
  it polls the word until bit 15 (`MACK`) is set, and a read's byte is in
  bits 0-7. The FM-1's stock firmware uses the port this way.
  The requirement: a firmware that touches the USB core bounds every
  poll of bit 15 and does not depend on how long an access takes. A firmware that leaves USB alone needs nothing.
  In fwtest (0.7.0) every access is done at once, the interrupt flags
  read 0 and no bus event ever happens (HARNESS.md, "USB").
- Sources: SDK `WL82.h` lines 15-16 (`lsfr_base`, `map_adr`) and 464-485
  (`JL_USB`, `CON1` its second word); SDK
  `include_lib/driver/cpu/wl82/asm/usb.h` lines 42-44 (`USB_CON1`:
  `MC_RNW` 14, `MACK` 15) and 148-150 (`musb_read_usb`,
  `musb_write_usb`; their code is in the SDK's prebuilt libraries, not
  opened); SDK `include_lib/driver/device/usb/usb_phy.h` lines 61-90 (the
  `MUSB_*` indexes); RE `docs/io/06-usb.md` §2.1 (the indexed access,
  `(idx<<8)|val` with completion on the halfword's sign bit, and the same
  index map, in the stock firmware); SDK63 `include_lib/driver/cpu/br23/asm/usb.h`
  and four other chips' (`MACK` 15 there too; corroboration only).
- Standing: confirmed (SDK, RE). Not from the sources: what the chip's
  registers read before a write and the time an access takes; RE calls
  bit 2 of `0x11800` the port's busy bit, which the SDK names `USB_NRST`
  (open, unused by fwtest).
- Needed by: M9 (the app's emulator), USB MIDI (not planned)

## 21. The update package (`.fwsc`) and the loader chain (Phase A1)

What a JieLi update package for the FM-1 is, byte by byte, as far as the
allowed sources give it, and what each step that loads one checks: the
emulator's package path (which the upstream web build and fwtest's
`--package` share, and the F-Emulator app too, HW-93 and HW-94) and the chip's own chain
(HW-92). Written by session spec-a1-fwsc for a packager of our own
(docs/A1-PLAN.md). No stock package was opened for it; what only a stock
file could show is left open (Q-25, Q-26). HW-91 corrects HW-81's
window address. Offsets are in bytes from the start of the structure
named; all multi-byte fields are little-endian.

### HW-87: JieLi's CRC-16 and the header mask
- Fact: Two rules recur in the package:
  - **CRC-16** ("JieLi's CRC-16" below): polynomial `0x1021`, initial
    value 0, bits taken most significant first, no reflection, no final
    XOR (the CRC-16/XMODEM parameters). Check value: the ASCII bytes
    `123456789` give `0x31C3`. A structure's own CRC sits in its first
    two bytes and covers the rest of it, from byte 2 to its end.
  - **The mask** with a 16-bit seed: keep a 16-bit value `k`, starting at
    the seed; XOR each byte, in order, with `k`'s low 8 bits; after each
    byte, shift `k` left by one, keeping 16 bits, and if `k`'s top bit was
    1 before the shift, XOR it with `0x1021`. The mask is its own inverse.
    The first four mask bytes from seed `0xFFFF` are `FF DF 9F 1F`. The
    "header key `0xFFFF`" below is this mask with seed `0xFFFF`.
  M9-PLAN.md called the CRC CRC-16/CCITT-FALSE (initial value `0xFFFF`),
  after RE; that is wrong for these structures: the SDK's own packer and
  the emulator's package path start from 0.
- Sources: SDK `cpu/wl82/tools/packufw/source/JLpack.cpp` lines 23-44
  (the CRC: table of `0x1021` multiples, initial 0) and 181, 198 (a
  head's CRC over the head after its first two bytes, stored first); RE
  `docs/io/11-ota-protocol.md`, "The .fwsc logical image" (the header key
  `0xFFFF`) and "Known open items" (`jl_crc16` named CCITT-FALSE); the
  emulator's package path (HW-93: the mask, and CRCs from 0 that pass on
  the stock packages it boots).
- Standing: confirmed (SDK for the CRC; the mask emulator-only, its seed
  RE)
- Needed by: A1

### HW-88: The package file: header blocks, header, entries
- Fact: A package is a header in blocks, then data:
  - **Blocks.** The file's first 960 bytes are 20 blocks of 48 (`0x30`)
    bytes. In each block the first 47 (`0x2F`) bytes are header data and
    the last is a marker. The 20 data parts, in order, make the **logical
    header** (940 bytes). Everything from file offset 960 on is data,
    plain. The **logical image** is the logical header followed by the
    file from offset 960: logical offset `n` is file offset `n + 20` for
    `n` ≥ 940.
  - **Markers.** Block `i`'s marker (file offset `48·i + 47`) is the
    package's identity's character `i` plus `i + 1` (modulo 256) while
    the identity lasts, and `0x7D` after it; the stock FM-1 package's
    identity is its name (`FM-1_0nn`, 8 characters, so blocks 8 to 19
    carry `0x7D`). The emulator reads the identity back from the markers;
    one that starts with `SMK`, `MKE` or `STARRYKEY` (any case) makes it
    boot the SMK-37 keyboard instead of the FM-1, and if the data byte at
    file offset 1007 (where a 21st block's marker would be) is `0x7D` it
    first tries a longer header, then falls back to 20 blocks. So an FM-1
    package's identity is ASCII, at most 19 characters (ending the
    markers with `0x7D`, as stock does), and starts with none of those.
  - **Header.** The logical header's first 64 (`0x40`) bytes are masked
    with the header key (HW-87). Unmasked: bytes 0-1 the header's
    CRC-16 over bytes 2-63; bytes 8-9 the entry count. RE names the
    header's fields, in order, header CRC, list CRC, image size and entry
    count; where the list CRC and the image size sit, and what they
    cover, is not given (Q-25).
  - **Entries.** Entry `k` is the 80 (`0x50`) bytes at logical offset
    `64 + 80·k`, masked on its own with the header key. Unmasked: bytes
    0-1 its type, type 0 being the **flash image**; bytes 8-11 its data's
    logical offset; bytes 12-15 its data's length. Its name, its CRC and
    its other fields are not given (Q-25). The stock package has eight
    entries, the flash image (`flash.bin`), `info.log`, `USR`, the
    loader's configuration (`isd_config.ini`), the update loader
    (`ota.bin`), `script.ver`, `blimit.bin` and `tail.bin`; the SDK's
    packaging adds the update loader as type 100 and `script.ver` (the
    packaging tool's version, `AC791N-v0.01-cfg_tool-v0.10` in the SDK)
    to the package before turning it into the update file.
  The emulator's package path reads only the header's CRC, the entry
  count and the first type-0 entry; a package for it needs no other
  entry. What the chip's updater needs is Q-26.
- Sources: RE `docs/io/11-ota-protocol.md`, "The .fwsc logical image"
  (the 20 blocks, 47 + 1 bytes, the logical image, the header's fields,
  the eight entries); RE `docs/architecture.md` §2 (a UFW package for the
  chip "AC791N"); SDK `cpu/wl82/tools/download.c` lines 258-264 (the
  update loader added with `-type 100`, then `script.ver`, then the
  conversion to the update file) and `cpu/wl82/tools/script.ver`; the
  emulator's package path (the markers, the identity, the field offsets
  read, the board chosen by the identity).
- Standing: confirmed (RE) for the blocks and the logical image; the
  markers, the entry's field offsets and the header's emulator-only
- Needed by: A1

### HW-89: The flash image: its header and directory
- Fact: The flash image (the type-0 entry's data) is written to the
  flash chip from offset 0 (the stock one covers `0x00000`-`0x93FFF`,
  HW-80). It starts with 32-byte heads, each masked on its own with the
  header key (HW-87):
  - **The flash header**, the head at offset 0: unmasked, bytes 0-1 its
    CRC-16 over bytes 2-31; 2-3 a size for the programmer
    (`size4burner`); 4-7 the VID (4 bytes); 8-11 the flash size; 12 the
    file system's version; 13 an alignment, in units of 256 bytes; 14
    reserved; 15 a special-options byte; 16-31 the PID (16 bytes). The
    emulator's package path copies it, unmasked, into the boot block
    (HW-91) and checks nothing in it.
  - **Directory heads**, from offset 32, one after another, until the
    first with a non-zero "last" field. Unmasked, each is: bytes 0-1 its
    CRC-16 over bytes 2-31; 2-3 its data's CRC-16; 4-7 its data's flash
    offset; 8-11 its data's length; 12 its attribute; 13 reserved; 14-15
    "last" (non-zero on the directory's last head); 16-31 its name, ASCII,
    padded with zero bytes.
  Two heads are required, found by name (the first match wins):
  - `isd_config.ini`, the loader's configuration: at its data's offset,
    32 bytes (the **key block**, HW-90) and right after them their
    CRC-16 (2 bytes). These are stored as they are, not masked.
  - `app_dir_head` with attribute `0x81`: its offset is the start of the
    **app area** (HW-90). FM-1-RE calls the app area's table
    `app_area_head`; the name the readers match is `app_dir_head`.
  The stock directory also has the second-stage loader `uboot.boot` at
  flash offset `0xA0` (which the mask ROM loads, HW-92) and the loader's
  configuration at `0x38D0` (HW-80). The emulator's package path checks
  no head's CRC or its data's CRC; whether the chip's loader does is Q-26.
  A packager fills them by the rule above.
- Sources: SDK `include_lib/system/boot.h` lines 46-56 (`struct
  flash_head`, the flash header's fields); RE `docs/io/11-ota-protocol.md`,
  "Known open items" (a 32-byte head of this layout, `hdrcrc`,
  `datacrc`, offset, length, attribute, reserved, last, name, with its
  data CRC over the data, on the update loader); RE `docs/architecture.md`
  §2 (the directory's entries and offsets in the stock image) and RE
  `docs/io/01-boot.md` §3 (`app_area_head`); the emulator's package path
  (the heads masked one by one, the two names, attribute `0x81`, the key
  block's CRC, the walk to the last head).
- Standing: confirmed (SDK, RE) for the layouts; the names the readers
  match and the masking of each head emulator-only
  (corrected in part by HW-105: names end with one zero byte and are
  padded with `0xFF`; the masking of each head is confirmed there)
- Needed by: A1

### HW-90: The app area: the chip key and its scrambling
- Fact: The app area starts at the `app_dir_head` head's offset `A`
  (`0x4000` on the FM-1; HW-91 says why it must be). It is scrambled
  with a 16-bit **chip key**:
  - **The key from the key block** (the 32 bytes `b[0]`-`b[31]` of
    HW-89): let `s` be the sum of `b[0]`-`b[15]` modulo 256; if `s` ≥
    `0xE0`, take `s` = `0xAA`; else if `s` ≤ `0x10`, take `s` = `0x55`.
    Then bit `i` of the key (`i` = 0 to 15) is 1 when `b[16 + i]` XOR
    `b[15 − i]` is less than `s`, else 0. Any key block gives a key; the
    stock package's gives `0x980F`.
  - **The scrambling.** From `A`, the area is cut into 32-byte chunks;
    the chunk at offset `r` from `A` (`r` = 0, 32, 64, …) is masked
    (HW-87) with the seed `key XOR (r / 4)`, keeping 16 bits; the last
    chunk may be shorter. The first chunk is the **area head**, a 32-byte
    head (HW-89's layout, not masked again) whose length field (bytes
    8-11) is the length of the scrambled area from `A`, the area head
    included. Bytes past that length are left as they are.
  - **The area's directory**, once unscrambled: 32-byte heads from `A +
    32`, each in HW-89's layout but not masked, until the first with a
    non-zero "last" field or the area's end. `app.bin`, with attribute
    `0x82`, is the app: its offset is from `A`, and its length the app's
    length. The stock directory also lists `cfg_tool.bin` and `cfg`
    (offsets from `A`) and the reserved regions `VM`, `PRCT`, `BTIF` and
    `USR` (whose offsets are flash offsets). With the area head and eight
    heads the directory is `0x120` bytes, so the stock `app.bin` is at
    `A + 0x120` (flash `0x4120`).
  For the chip, the key must be the chip's own (Q-26); for the three
  emulated load paths any key works, as long as the area is scrambled
  with the key its key block gives.
- Sources: RE `docs/architecture.md` §2 (the app area chip-key encrypted,
  base `0x4000`; the chip key `0x980F` in the stock configuration; the
  directory, `app.bin` at `0x4120`) and RE `docs/io/01-boot.md` §3 and
  §5 (the table is `0x120` bytes); the emulator's package path (the key's
  derivation, the per-chunk seed, the area head's length, the
  directory's names and attribute `0x82` as the web build's reader
  requires it, offsets from `A`).
- Standing: emulator-only (the derivation and the scrambling); confirmed
  (RE) for the area's place, its directory and the stock key
  (the scrambling confirmed by HW-105, PKG; the key's derivation agrees
  for the one key block the tools wrote)
- Needed by: A1

### HW-91: The code window and the app's entry, corrected
- Fact: On the chip, and in the emulator's package path:
  - The code window `0x02000000` shows the app area **from its start**:
    window address `0x02000000 + n` is flash offset `0x4000 + n`, the
    area head first. The stock `app.bin` at flash `0x4120` is at window
    address `0x02000120`, and runs there.
  - The app's entry is its first byte: the window's start plus `app.bin`'s
    offset in the area, `0x02000120` for a directory of `0x120` bytes. An
    app in a package is therefore linked to run at `0x02000000` plus its
    offset in the area (the SDK links its apps at `0x02000120`), not at
    `0x02000000` as fwtest's raw images are (HW-1, HW-5). A raw image
    and a package's app are two links of the same code.
  - The loader starts the app with r0 pointing at a boot block (Q-11):
    in the SDK's layout, a pointer to a copy of the flash header (HW-89),
    the window's flash offset (`0x4000`), the app's window address
    (`0x02000000`), the chip ID (16 bits), a trim value (16 bits) and 8
    bytes of Bluetooth address. The emulator's package path builds this
    block with the chip ID, trim and address 0.
  - Still true from HW-81: the area is encrypted with the chip's key and
    the window shows it decrypted, so plain bytes written over SPI0 into
    the area read back changed through the window; the stock firmware
    synchronises the instruction cache after a program (Q-22); address
    a store by chip offset and read it with the flash's read command over
    SPI0, not through the window.
  In the emulator's package path the app area must start at flash
  `0x4000`: the window's flash offset is fixed there. Supersedes HW-81,
  whose window address (`0x02000000` = flash `0x4120`) came from FM-1-RE's
  memory map; FM-1-RE's own boot document finds the stock app's absolute
  addresses `0x120` above where its map puts them, and the container's
  entry point at `0x02000120`.
- Sources: SDK `cpu/wl82/tools/isd_config_rule.c` line 84 (`ENTRY=0x2000120`,
  the entry in flash mode) and `cpu/wl82/sdk_ld_sfc.c` line 36 (the code
  linked from `0x2000120`); SDK `include_lib/system/boot.h` lines 15-18
  and 58-64 (`sfc_info`: the flash address and the app's address, "from
  uboot"; the boot device structure that holds it); RE `docs/io/01-boot.md` §3 and §5 (the
  container's entry point `0x02000120`, and the stock app's absolute
  addresses `0x120` above its map's); RE `docs/architecture.md` §2 (the
  map HW-81 took); the emulator's package path (the window from flash
  `0x4000`, the entry, the boot block).
- Standing: confirmed (SDK, RE)
- Needed by: A1, M9

### HW-92: The loader chain on the chip, and what each step checks
- Fact: On the chip, from power-on:
  1. The mask ROM loads the second-stage loader `uboot.boot` from flash
     offset `0xA0` into RAM (its header gives the load address,
     `0x01C02000`; the SDK's packaging passes the same address) and runs
     it.
  2. `uboot.boot` reads its configuration and the flash directory
     (HW-89), finds the app area, sets up the code window and its
     decryption, and jumps to the app's entry (HW-91) with r0 pointing
     at the boot block.
  3. The app runs from the window.
  What steps 1 and 2 check before going on (CRCs, the key, the
  directory, a version) is not given by the allowed sources: the SDK
  ships both as binaries, and FM-1-RE says only that the loader "maps
  and verifies" the app (Q-26). An update goes another way: the running
  firmware's updater checks the package and stages the update loader
  (`ota.bin`), which writes the flash image (M9-PLAN.md §2); what they
  check is not all known either (Q-26). fwtest and the emulators run
  neither the mask ROM nor `uboot.boot` (HW-93).
- Sources: RE `docs/architecture.md` §3 (the chain; the loader at `0xA0`)
  and RE `docs/io/01-boot.md` §3 (the load address `0x01C02000` in the
  loader's header; "maps/verifies"); SDK `cpu/wl82/tools/download.c` line
  223 (`-boot 0x1c02000`, `-uboot uboot.boot`); RE
  `docs/io/11-ota-protocol.md`, "Session flow" and "Known open items"
  (the update's two steps; its checks not all found).
- Standing: confirmed (RE, SDK) for the steps; their checks open
- Needed by: A1 (what the emulated paths skip), M10

### HW-93: The package path in fwtest and the emulators
- Fact: The upstream web build and fwtest's `--package` (HARNESS.md,
  "Packages") load a package through the same reader, the emulator
  crates', in the host, in place of the chip's steps 1 and 2 (HW-92); the
  F-Emulator app is taken to use that reader unchanged
  (EMULATOR-PARITY.md, "Packages"; for the owner to confirm). The reader
  checks, in this order, and refuses the package at the first failure:
  1. The header's CRC (HW-88).
  2. A type-0 entry whose data lies inside the file.
  3. In the flash image's directory (HW-89): an `isd_config.ini` head and
     an `app_dir_head` head with attribute `0x81`. When no key block's CRC
     checks, the reader still takes the key of the last `isd_config.ini`
     head seen; fwtest refuses the package.
  4. The app area's length (HW-90) inside the flash image.
  5. An `app.bin` in the area's directory; fwtest, like the web build's
     own reader, also needs its attribute `0x82`.
  fwtest also refuses an app area that does not start at `0x4000` (the
  emulators would show the wrong bytes in the window) and a package whose
  identity is another board's (HW-88). Then they boot: the flash chip
  holds the flash image from offset 0, and the rest of the chip is
  erased; the window shows the app area unscrambled, from flash `0x4000`
  to the flash image's end, and the chip directly beyond it; core 0
  starts at the app's entry (HW-91) with r0 pointing at the boot block.
  The emulator's own package boot also gives the `USR` region (HW-80), if
  the directory names one and it is blank, a default patch bank of its
  own; fwtest leaves it as the package has it. Nothing checks a directory
  head's CRC, a data CRC, the list CRC or the other entries (Q-25, Q-26).
  Unlike the chip, the flash chip holds the app area scrambled, so SPI0
  reads of the area give the scrambled bytes, and bytes a firmware
  programs into the area show through the window as written, not
  decrypted (HW-91). fwtest has `--package` from 0.8.0; until
  `config/fwtest-image` pins 0.8.0, `tools/fwtest` refuses the option.
- Sources: the emulator's package path (vendor/emulator, read for this);
  HARNESS ("Packages"); fwtest's harness tests on test packages made from
  HW-87 to HW-91 alone (harness/tests/). The app's part, "for the owner
  to confirm" above, is settled by HW-94 (2026-10-27); the fact's text
  is left as written.
- Standing: emulator-only (with the harness's own tests)
- Needed by: A1

### HW-94: The F-Emulator app's package path
- Fact: The F-Emulator app loads a package through the emulator crates'
  package reader, their conversion to the flash image and their stock
  boot, all unchanged from upstream `43ed558`, so a package boots in it as
  in the upstream web build (HW-93's checks and boot). Around them, the
  app adds checks of its own:
  1. Before the reader, it refuses, with a message, a file over 16 MiB, a
     package under 960 bytes or over 8 MiB, a catalog download whose
     SHA-256 differs from the catalog's, and an M-VAVE version newer than
     015 (by the package's own name).
  2. A package that crashes the reader is refused as malformed.
  3. It loads no patch bank of its own into the user-patch area (`USR`,
     HW-80); the defaults are filled as upstream does.
  4. After boot, the firmware's own saved flash sectors are written over
     the image, after checks: whole 4 KiB sectors, in range, none
     repeated.
  It then runs the interpreted CPU, with idle skipping, each firmware at
  its own measured clock. This settles HW-93's "for the owner to confirm".
- Sources: the app session's own description of its path, behaviour only,
  relayed by the owner on 2026-10-27 (recorded by session spec-1027; this
  side doesn't open the app's branch); EMULATOR-PARITY.md, "Packages".
- Standing: emulator-only (the app's own report)
- Needed by: A1

## 22. A store of its own base register (SR-10)

What a store with a base update does when the register it stores is its
base, from the pinned toolchain (session spec-1027, for a firmware built
on small-beeps). What the chip itself stores is open (Q-27).

### HW-95: A store whose stored register is its base, with a base update
- Fact: The toolchain's stores with a base update, `[++rN=k] = rS` (a
  pre-increment: the access at rN + k, then rN = rN + k) and
  `[rN++=k] = rS` (a post-increment: the access at rN, then rN = rN + k),
  with `b[` and `h[` for a byte or a halfword (the low bits of rS) and k a
  number or a register, take rS = rN in every form; the assembler accepts
  each without a word: `[++r4=748] = r4` (`d2 ec 4f 4e`), `[++r1=8] = r1`
  (`d0 ec 1b 10`), `[++r1=-8] = r1` (`d7 ec 1b 1f`), `[r1++=8] = r1`
  (`d8 ec 19 10`), the 2-byte `[r4++=-4] = r4` (`cc 05`), `[r1++=4] = r1`
  (`91 05`), `h[r5++=2] = r5` (`d5 06`), `b[r6++=1] = r6` (`e6 07`), the
  register steps `[++r1=r2] = r1` (`dc ec 13 12`), `[r1++=r2] = r1`
  (`de ec 13 12`), `h[++r1=r2] = r1` (`dc ed 11 12`), `b[r1++=r2] = r1`
  (`de ee 11 12`), and `h[++r2=8] = r2` (`58 ed 29 20`),
  `h[++r1=-8] = r1` (`5b ed 19 1f`), `b[++r3=8] = r3` (`5a ee 38 30`).
  **The value stored is rN as it was before the instruction**, as the
  compiler uses the form: with the firmware's flags, at `-Os` and `-O2`,
  C that stores a pointer as it was where the moved pointer points
  (`q = p + 187; *q = p; return q;`) compiles to the one instruction
  `[++r0=748] = r0`, `*p = p; return p + 2;` to `[r0++=8] = r0`, and the
  halfword and byte versions to `h[++r0=8] = r0` and `b[++r0=8] = r0`;
  C that stores the moved pointer (`*q = q`, and its post-increment
  version) got the form in none of the functions tried: the compiler
  computes the new base in another register and stores that. fwtest stores the old value in every form since 0.9.0
  (HARNESS, "Instructions"); 0.8.0 and earlier stored the moved base in the
  pre-increment forms with a number step (word, halfword and byte), and
  the old value in the others.
- Sources: TC: the assembler and disassembler for every form above; the
  compiler's code for C with known results (harness/tests/images/selfc.c
  and the session's own functions), built with `-mcpu=r3 -mfprev1` at
  `-Os` and `-O2` (PROVENANCE P-63). The toolchain ships no documentation
  of its instructions; the SDK's `.S` files are version stamps only, and
  the C and header files fetched from its `cpu/wl82/`,
  `include_lib/driver/cpu/wl82/` and `include_lib/system/` (128 of the
  189 there) hold no inline assembly, so the SDK shows nothing either way. fwtest's harness test on the images
  `selfstore.S` and `selfc.c` (harness/tests/images/).
- Standing: emulator-only (the toolchain's use of the form; the chip's
  behaviour is Q-27)
- Needed by: a firmware built on small-beeps (SR-10)

## 23. The instruction forms the toolchain knows (the toolchain audit)

Which instruction forms the pinned toolchain (P-1) knows for the chip's
CPU flags, and what its own decoder table, assembler and compiler show of
their encodings and behaviour (session spec-isa-audit, for firmwares built
on small-beeps with other flags or C++). The toolchain ships no
instruction documentation; what it leaves open is Q-28 to Q-35. HARNESS.md
("Instructions") says which forms fwtest runs.

### HW-96: The forms the toolchain knows, and which the compiler emits
- Fact: The vendor objdump's decoder tables for pi32v2 (the LLVM 4.0.1
  fixed-length format, found in the binary by their content) have 1,019
  leaves, one instruction form each: 140 of 2 bytes, 868 of 4 and 11 of
  6. With the firmware's flags (`-mcpu=r3 -mfprev1`, the SDK's, HW-62)
  948 disassemble and 947 assemble back to themselves or are branch and
  block forms the assembler takes with a label or a body; the other 71
  need features those flags leave out: the assembler refuses them as
  "instruction not enabled" (the double-precision float forms, the
  word forms of `sat8`, `unpack4` and `vsat16`) or as needing
  "instruction rev1" or "rev2" (`sum(r *|*|*|* r)` forms). Of the 947,
  about 330 are SIMD and DSP forms (`(v)`, `(vb)`, `(vh)`, `*|*`,
  `packb`, ...) and the rest scalar. The decoder's predicates
  map to the CPU models: one table predicate holds for `r3` to `r5`,
  another for every model but `r1` and `r5`, another for `r4` only. The
  compiler, with those flags at `-O0` to `-O3`, `-Os` and `-Oz`, with and
  without `-ffast-math`, on C and C++ of our own (every operator on every
  integer and float type, conversions, bit-fields, saturation idioms, 64-bit
  multiply-accumulates, `__fp16`, the float builtins, atomics, switch
  tables, varargs, virtual calls, templates), on main's firmware and on the
  Plaits demo, emits 326 of the 947 (counting only code: data its
  disassembler also decodes left out). Its pi32v2 builtins are 41 (each with
  its type in the compiler's own builtin table); `idle`, `illegal` and
  `swi` do not compile ("cannot compile this builtin function yet"),
  `insert`, the six 64-bit multiply builtins and `sextra` / `uextra` with
  a field in a register stop in the backend ("Cannot select"), and none
  is a SIMD form. One of the corpus's 1,637 C functions crashes the
  compiler at every flag set: `__builtin_frame_address(0)`.
- Sources: TC: the vendor objdump's decoder and name tables, its
  disassembly of encodings made from every leaf (16 each) with
  `-mcpu=r3 -mattr=+fprev1` and with every feature; the assembler on each
  disassembly with `-mcpu=r3 -mfprev1`, and with each CPU model alone;
  the compiler on the corpus above; the compiler's builtin table (the
  builtins' names and types). PROVENANCE P-64.
- Standing: emulator-only (what the toolchain knows; whether the chip
  runs every form is open)
- Needed by: firmwares built on small-beeps (session spec-isa-audit,
  C-HARNESS-ISA)

### HW-97: The float unary row and fcmp
- Fact: The single-precision row `3f e5 b2 b3` (`3f f5`, a dual-issue
  pair's head) with b2's low nibble `f` is a unary operation on rS =
  b3 & 15 into rD = b3 >> 4, chosen by b2: `0f`, `1f`, `2f`, `3f`
  `R = ftoi(R)` rounding to even, toward zero, up and down; `4f` to `7f`
  the same for `ftou`; `8f` `itof`, `9f` `utof`; `af` `rD.l = ftof(rS)`,
  to half precision into rD's low half; `bf` `rD = ftof(rS.l)`, from the
  half in rS's low half; `cf`, `df`, `ef`, `ff` `R = ftof(R)` rounded to
  an integral value, to even, toward zero, up and down. The compiler emits
  `df`, `ef` and `ff` for `truncf`, `ceilf` and `floorf` (so their results
  are C's), `af` and `bf` for `__fp16` stores and loads (it stores only
  the low half after `af`, and loads a halfword before `bf`), `1f` and
  `5f` for casts; the even and up / down conversions to integers only the
  assembler emits. `fcmp rA, rB` is `3f e5 A4 0B` (A = b2 >> 4, B = b3 &
  15), the flag branches' operands (HW-98).
- Sources: TC: the assembler and disassembler for every b2 value with
  several registers; the compiler on `floorf`, `ceilf`, `truncf`, `rintf`,
  `lrintf`, `__fp16` conversions and casts, with the firmware's flags.
  PROVENANCE P-64.
- Standing: emulator-only (the toolchain's encodings and the compiler's use;
  what the chip gives at the edges is Q-28)
- Needed by: firmwares built on small-beeps (session spec-isa-audit)

### HW-98: The flag branches
- Fact: `if<cond> goto #off` is `40 e8` eq, `c0 e8` ne, `40 e9` cs,
  `c0 e9` cc, `40 ec` hi, `c0 ec` ls, `40 ed` ge, `c0 ed` lt, `40 ee` gt,
  `c0 ee` le, off = 2 * bits 16-31 as a signed
  number, from the next instruction; byte
  1 is the compare branches' family (e8 ==, e9 u>=, ec u>, ed >=, ee >)
  and bit 7 the opposite condition. `41 e8` is no instruction. The compiler
  emits only `ifeq` after `testset b[rN]` (its spin on a lock, backwards);
  `fcmp` (HW-97) is the one instruction found that names two operands for
  them.
- Sources: TC: the assembler and disassembler for all ten conditions
  forwards and backwards; the compiler's code for the lock builtins and our
  firmware's spin loops. PROVENANCE P-64.
- Standing: emulator-only (the encodings; what sets the conditions on the
  chip is Q-29)
- Needed by: firmwares built on small-beeps (session spec-isa-audit)

### HW-99: The memory row, and a word index scaled by 8
- Fact: `64 e8`, `66 e8`, `68 e8`, `6c e8` / `6d e8` and `6e e8` share
  one layout: base rB = bits 28-31, a word offset 4 * bits 18-23 as a signed number,
  op = bits 16-17, and the operand in bits 24-27. `64 e8` op 3 is
  `[rB+#i] &= ~rS` (the compiler's `*p &= ~m`); `6e e8` is the shift by a
  register `[rB+#i] <<= rS`, `<<<= rS`, `>>= rS`, `>>>= rS` (op 0 to 3;
  the compiler's `*p <<= n` and `>>= n`); `6c e8` / `6d e8` the shift by a
  number, `6d` adding 16, and `6c` with a field of 0 a shift by 32. In the
  register-pair access `58 ec` with an index register (`d[rB+rI]`), bit 19
  scales the index by 8: `d[rB+rI<<3]` (`58 ec 2a 03` against `d[r2+r3]`
  `58 ec 22 03`); the compiler emits it for 64-bit elements at large
  constant indexes. `d8 ed` with b2 & 7 = 3 stores rS's high half,
  `h[rB+rI] = rS.h`, b2 bit 3 scaling the index by 2.
- Sources: TC: the assembler and disassembler; the compiler on `*p <<= n`,
  `*p >>= n`, `*p &= ~m` and 64-bit array sums. PROVENANCE P-64.
- Standing: emulator-only (the encodings; shifts of 32 or more by a
  register, and `<<<`'s saturation in memory, are Q-30)
- Needed by: firmwares built on small-beeps (session spec-isa-audit)

### HW-100: Builtins whose result the compiler folds, and others it does not
- Fact: `__builtin_pi32v2_zcmp(x)` is `rD = zcmp(rS)` (`80 e1 02 DS`),
  the sign of x: the compiler folds constants to 1 (5, 256, 0x7fffffff),
  0 (0) and -1 (-1, -5, -256, 0x80000000). It folds `clz` (4096 gives 19)
  but not `rotrc`, `sextra`, `uextra` or `qasl`. `__builtin_pi32v2_rotrc(x,
  n)` is `rD = rS <c> n` (`c4 e1`, n 1 to 32, 32 encoded as 0) or `<c>`
  by a register (`cc e1 S1 DT`). The compiler declares the intrinsic
  behind it, like every pi32v2 builtin's, `readnone` and merges two calls
  with the same arguments into one, so to it `<c>` is a function of x and
  n alone; its instruction descriptors give the 32-bit `<c>` forms the
  same implicit flags as the rotate `<>` (they set the flags and read
  none), while the 64-bit `RR <c>= n` reads them. Nothing shows the
  function itself. `shfms64` and `shfmu64` are the plain pair shifts right
  `(s|u)`, not the rounding ones.
- Sources: TC: the compiler with the firmware's flags at `-O2` on constant
  and variable arguments; its LLVM IR (the calls stay intrinsics until the
  backend; the intrinsics' attributes); the objdump binary's instruction
  descriptor table. PROVENANCE P-64.
- Standing: emulator-only (the compiler's folding; `<c>` is Q-32)
- Needed by: firmwares built on small-beeps (session spec-isa-audit)

### HW-101: Halves, fields and special registers
- Fact: `68 e0 X0 DS` is `rD.l|h = rS.l|h` (X bit 2 the source's high
  half, bit 3 the destination's), `74 e0 XY DS` `rD.l|h = sat8(rS.l|h)
  (s|u)` (Y 1 signed), `9c e1 AY DP` `rD = uextra | sextra (Y 1) (rA,
  p:rP[12:8], l:rP[4:0])` and `98 e1 A0 DP` `rD <= insert(rA, p:rP[12:8],
  l:rP[4:0])`; `e0`, `e1` become `f0`, `f1` for a pair's head. The special
  registers are numbered 0 reti, 1 rete, 2 retx, 3 rets, 4 sr4, 5 psr,
  6 cnum, 7 uspn, 8 sspn, 9 icfgn, a icfgs, b icfg, c usp, d ssp, e sp,
  f pc: in the moves `64 e0 00 DN` (`rD = <N>`) and `64 e0 80 DN`
  (`<N> = rD`), and as bit N of the 16-bit mask of the 4-byte push
  `58 e9` and pop `50 e9`, which list them from the highest number down
  (`5c e9` is the same push marked `(c)`).
- Sources: TC: the assembler and disassembler for every register and
  mask bit. PROVENANCE P-64.
- Standing: emulator-only (the encodings; pc, cnum, uspn, icfgn, icfgs and
  the `(c)` push are Q-34, the results' edges Q-35)
- Needed by: firmwares built on small-beeps (session spec-isa-audit)

### HW-102: The rounding pair shifts, the memory multiplies, the npc loads
- Fact: `d2 e1 PX DM` is `rD =` a register pair `>> n` (or `>>>` with M bit 3)
  with a rounding: pair = P >> 1, n = X | (M & 3) << 4 (0 to 63), and P
  bit 0 with M bit 2 the mode ((0, 0) up, (0, 1) round, (1, 0) even,
  (1, 1) zero); `d3 e1 PM DR` the same by register R, M's low three bits
  the sign and the mode (0 up, 1 even, 2 round, 3 zero, times 2, plus 1
  for `>>>`); `d2 f1`, `d3 f1` a pair's head. The multiplies with a
  memory operand put the pair (bits 29-31), the sign (bit 28, `(s)`) and
  a register in byte 3, the first base and its increment in byte 2:
  `[rA ++= i]*rB` is `e0|e4|e6 ee` (=, +=, -=; `e8|ec|ee ee` with `h[`),
  `[rA ++= rI]*rB` `60|64|66 ee` (`68|6c|6e`), `[rA ++= rI.h]*[rB ++= rI.l]`
  `e0..ee e8`, and `[rA ++= i]*[rB ++= j]` byte 1 e9, ec or ed with byte 0
  `6j` or `ej` (=, +=, -=, then the three with `h[`). The assembler counts
  i in the first operand's size (2 with `h[`, 4 without) and j in words
  even with `h[`, so the second operand is always a word. `rD = [npc + rI]`
  is `60 e8 00 DI` and `rD = [npc + #i]` the 6-byte `aD ff` followed by the 32-bit #i
  (#i even). `rD = rev16(rS)` is `70 e0 40 DS`, beside the byte
  reversal's `70 e0 00`. The compiler emits none of these.
- Sources: TC: the assembler and disassembler for every mode, size,
  operation, register and increment sign; the decoder table's masks.
  PROVENANCE P-64.
- Standing: emulator-only (the encodings; the results' details are Q-31
  to Q-33)
- Needed by: firmwares built on small-beeps (session spec-isa-audit)

## 24. The update package as JieLi's packaging tools write it (Q-25)

What JieLi's own packaging tools write when they are run on our own
input (session spec-br17-package, for BR-17: a package a unit's
installer accepts). The tools are the SDK's `cpu/wl82/tools/loader_tools/`
set, run as the SDK's `download.bat` runs them, under wine in a container
with no network (PROVENANCE P-65). Their inputs were our own: four
synthetic apps (4 096 and 8 192 bytes of zeros, one with a byte changed,
one of a counting pattern), the SDK's configuration rule preprocessed for
the FM-1 (1 MiB of flash, code from flash, no SDRAM, a single bank), and
the SDK's own loader files. No stock package was opened. The SDK's other
copy of the packager, in `cpu/wl82/tools/`, exits at once under wine
without output, so nothing here comes from it. These entries say what the
tools *write*. What the chip's loaders and an installer *check* stays
Q-26, except where an entry says otherwise. Offsets are in bytes from the
start of the structure named. All multi-byte fields are little-endian.

### HW-103: JieLi's packaging chain
- Fact: The SDK makes its update file in four steps:
  1. `isd_download` takes the loader's configuration (`isd_config.ini`),
     the second-stage loader (`uboot.boot`), the app (`app.bin`) and
     `cfg_tool.bin`. It writes the **flash image** (`jl_isd.bin`, from
     flash offset 0), a package of it (`jl_isd.fw`), and an **OTA
     update file** (`db_update_files_data.bin`, HW-106). With no device
     attached it prints its report and "Device Offline", and still writes
     them.
  2. `fw_add` adds the update loader `ota.bin` as type 100.
  3. `fw_add` adds `script.ver`.
  4. `ufw_maker -fw_to_ufw` turns `jl_isd.fw` into the **update file**
     (`jl_isd.ufw`, HW-104), which the SDK copies to `update.ufw`.
  Runs on the same inputs give the same flash image and the same OTA
  update file, byte for byte. Only one entry of the update file,
  `blimit.bin` (HW-104), and the CRCs over it change from run to run.
- Sources: PKG (P-65): every run; SDK `cpu/wl82/tools/download.c` lines
  223-264 and `cpu/wl82/tools/loader_tools/download.bat` (the steps and
  their options).
- Standing: confirmed (PKG)
- Needed by: BR-17, M10

### HW-104: The update file: header and entry list (Q-25)
- Fact: The update file is HW-88's **logical image** byte for byte, from
  its first byte. The tools do not write HW-88's 48-byte blocks or their
  markers (see HW-107).
  - **Header**: 64 bytes, masked whole with the header key (HW-87).
    Unmasked:

    | Bytes | Field |
    |---|---|
    | 0-1 | The header's CRC-16 over bytes 2-63 |
    | 2-3 | The **list CRC**: the CRC-16 of the entry list as stored (masked), `80 × count` bytes from offset 64 |
    | 4-7 | The **image size**: the update file's whole length in bytes |
    | 8-9 | The entry count |
    | 10-11 | 4 in every run (meaning not known) |
    | 12-15 | `0x200` in every run (meaning not known) |
    | 16-31 | The chip's name, `AC791N` (the configuration's `CHIP_NAME`), padded with zero bytes |
    | 32-63 | Zero |

  - **Entries**: entry `k` is the 80 bytes at offset `64 + 80·k`, each
    masked on its own with the header key. Unmasked:

    | Bytes | Field |
    |---|---|
    | 0-1 | The type |
    | 2-3 | Its index `k` |
    | 4-5 | The CRC-16 of its data before the entry's own scrambling (below); for `flash.bin`, of the flash image as written to flash (6-7 are zero) |
    | 8-11 | Its data's offset in the update file |
    | 12-15 | Its data's length |
    | 16-19 | That length rounded up to a multiple of 32 |
    | 20-23 | Zero |
    | 24-27 | The rounded length again on a scrambled entry, otherwise zero |
    | 28-63 | Zero |
    | 64-79 | Its name, ASCII, padded with zero bytes |

  - **The entries the chain writes**, in this order: `flash.bin` (type
    0, the flash image, at offset `0x400`), `info.log` (type 2, length
    0), `isd_config.ini` (type `0x34`, the configuration's text),
    `ota.bin` (type 100), `script.ver` (type `0xFB`), `blimit.bin` (type
    `0xA1`, 144 bytes), `tail.bin` (type `0xFF`, 64 bytes, last). Each
    entry's data starts on a multiple of 32 bytes. The file ends with
    `tail.bin`'s data.
  - **Scrambled entries**: the data of `isd_config.ini`, `script.ver` and
    `blimit.bin` is stored scrambled by HW-90's 32-byte chunk rule with
    key `0xFFFF`: the chunk at file offset `o` is masked with the seed
    `0xFFFF XOR (o / 4)`. The other entries' data is stored as it is.
  - **`tail.bin`**: the flash image's key block (HW-89, 32 bytes) and its
    CRC-16, then six bytes not identified, eight zero bytes, and `JLUFW`
    at bytes 48-52.
  - **`blimit.bin`**: its 144 bytes differ on every run with the same
    inputs, even unscrambled. What it holds is not known.
  For a `.fwsc`, it follows from HW-88 and this entry that the list CRC
  and the image size cover the logical image. The tools write no
  `.fwsc` (HW-107), so this is a deduction, not something they show:
  - the list CRC is the CRC-16 of the `80 × count` entry bytes as stored
    (masked) from logical offset 64, with the block markers taken out.
    In the file those bytes start at offset 65 and cross the markers at
    file offsets 95, 143 and so on;
  - the image size is the logical image's length, the file's length
    less 20.
- Sources: PKG (P-65): the four apps and a repeat of one; the header's and
  every entry's CRC computed and matched; the list CRC matched on every
  run, and changing with the app; the image size following the app's
  length.
- Standing: confirmed (PKG)
- Needed by: BR-17 (`tools/fwsc.py`'s header and entries), M10

### HW-105: The flash image as the tools write it
- Fact: What HW-89 and HW-90 describe, with these details:
  - **The flash header** (32 bytes at offset 0): its CRC-16 (bytes 0-1)
    is over bytes 2-31 of the head unmasked whole with the header key.
    On flash, the VID (bytes 4-7, `0.01`) and the PID (bytes 16-31,
    `AC791N_STORY` padded with `0xFF`) read as plain ASCII. Only the other
    bytes are masked. So the unmasked head holds those two fields masked.
    With the FM-1's configuration, unmasked: bytes 2-3 (`size4burner`)
    `0x8020`; 8-11 (the flash size) `0xFF000`, the space the image needs,
    1 MiB less the last 4 KiB; 12 `0x10`; 13 (the alignment) `0x10`, in
    units of 256 bytes, 4 KiB; 14 `0xA4`; 15 `0xFF`. Changing the
    configuration's PID and VID changes only those fields and the CRC.
  - **Names** in every directory head (the flash's and the app area's)
    end with one zero byte, and the rest of the 16 bytes is `0xFF`, not
    zero as HW-89 says. A reader matches a name up to its first zero
    byte.
  - **The flash directory**, in this order, each head's CRC-16 matching:
    `uboot.boot` (data at `0xA0`, the loader's length, attribute 0; its
    data CRC is the CRC-16 of the `uboot.boot` file given to the tool,
    but the bytes at `0xA0` differ from that file); `isd_config.ini`
    (attribute 2, reserved byte `0x80`; 765 bytes at `0x3628`, a binary
    configuration that starts with the key block and its CRC; its data
    CRC over those 765 bytes); `app_dir_head` (offset `0x4000`, length
    `0xFFFFFFFF`, data CRC `0xFFFF`, attribute `0x81`, reserved `0xFF`);
    `key_mac` (offset `0xFF000`, the flash's last 4 KiB, length `0x1000`,
    data CRC `0xFFFF`, attribute `0x12`, reserved 1, last `0xFFFF`).
  - **The chip key.** With no key file (the SDK's `-key` option, HW-108),
    the key block gives the key `0xFFFF` by HW-90's rule, and the app area
    is scrambled with `0xFFFF` by HW-90's chunk rule. The whole area
    unscrambles and every CRC in it matches. This confirms HW-90's
    scrambling, until now known only from the emulator. The key's
    derivation agrees for this one key block, the only one the tools
    wrote.
  - **The area head**, unscrambled: offset field `0x02000120` (the
    configuration's `ENTRY`), length the area's (head, directory and
    files), data CRC the CRC-16 of the area from byte 32 to that length,
    attribute `0x83`, reserved `0xFF`, name `app_area_head`.
  - **The area's directory**: `app.bin` (attribute `0x82`, offset
    `0x120`) and `cfg_tool.bin` (attribute `0x82`), each with its data's
    CRC-16; then the regions `VM`, `PRCT` and `BTIF` (flash offsets,
    attribute `0x12` or `0x92`, data CRC `0xFFFF`), the last with "last"
    set. With these five heads `app.bin` is still at `0x120`, as in the
    stock directory of eight.
  - **After the area**, the flash image has 64 more bytes, the same on
    every run with the same app. What they hold is not known. The
    configuration follows the loader directly (`0x3628`), and every byte
    the image doesn't use, up to `0x4000` and after the area's 64 bytes,
    is `0xFF`.
  Our own reader (`tools/fwsc.py`, HW-93's checks), run on these
  packages wrapped in HW-88's blocks, passes every check and gives back
  each app byte for byte, once it matches names up to their first zero
  byte.
- Sources: PKG (P-65): four apps and a PID and VID change; every head's
  CRC and data CRC computed; the reader run on each.
- Standing: confirmed (PKG); corrects HW-89 on the names' padding
- Needed by: BR-17, M10

### HW-106: The OTA update file: the app area alone
- Fact: `isd_download` also writes `db_update_files_data.bin`. The SDK's
  `upgrade.bat` copies it to `update-ota.ufw`, "for network OTA
  updates". It holds the flash image from `0x4000` only, with nothing
  below `0x4000`:
  - **Head 1** (32 bytes at offset 0, HW-89's layout, not masked):
    `update_data`, offset 32, length the whole file's, data CRC over the
    file from byte 32 to its end, attribute 3, reserved `0xFF`, "last" 1.
  - **Head 2** (at offset 32): `app_core`, offset 64, length the area's
    length plus 64, data CRC over those bytes, attribute 2, reserved
    `0xFF`.
  - **The data** (from offset 64): the flash image's bytes from `0x4000`
    for the area's length plus 64, the 64 bytes of HW-105 after the area
    included. These bytes are still scrambled with the chip key.
  Which updater, if any, takes this file on the FM-1, and whether it
  keeps everything below `0x4000`, is Q-26. The FM-1's stock updater
  takes `.fwsc` files.
- Sources: PKG (P-65): three apps; SDK `cpu/wl82/tools/loader_tools/upgrade.bat`
  (the copy to `update-ota.ufw`, in its "OTA" mode).
- Standing: confirmed (PKG) for the layout; its use on the chip is Q-26
- Needed by: BR-17 (an app-area-only package)

### HW-107: What the tools do not write
- Fact: For the `loader_tools` copy that ran, with the options the
  SDK's `download.bat` passes:
  - The tools write no `.fwsc` blocks. HW-88's 48-byte blocks, with an
    identity in their markers, wrap the update file. Which program adds
    them to stock packages is not known.
  - With this configuration they write no `USR` entry, which the stock
    package has (HW-88).
  - `isd_download` prints no usage text. No option it was given wrote a
    `.ufw` without the flash image from offset 0. Options the SDK uses
    elsewhere and this session didn't try, such as `-output-ufw` in
    `download_linux.c`, are not covered.
  The SDK's other copy, in `cpu/wl82/tools/`, never ran (HW-103's
  introduction), so none of this covers it.
- Sources: PKG (P-65); SDK `cpu/wl82/tools/loader_tools/download.bat` and
  `upgrade.bat` (the chain ends with `update.ufw` and `update-ota.ufw`,
  and no step adds blocks).
- Standing: confirmed (PKG)
- Needed by: BR-17

### HW-108: The chip key's source in the SDK's packaging
- Fact: The SDK's packaging takes the chip key from a key file passed to
  `isd_download` (`-key JL_791N-XXXX.key`, or `-key1` with `-mkey`).
  Its scripts leave that option commented out. Without a key file the key
  block gives the key `0xFFFF` (HW-105). The stock package's key,
  `0x980F` (HW-90), is not that default. Whether a unit runs an app
  scrambled with `0xFFFF`, or any key but its stock one, is Q-26.
- Sources: SDK `cpu/wl82/tools/loader_tools/download.bat` (the commented
  `KEY_FILE` lines) and `cpu/wl82/tools/download.c` lines 193-194; PKG
  (P-65).
- Standing: confirmed (SDK, PKG)
- Needed by: BR-17, M10

## 25. What an FM-1 installer and the bootloader check (Q-25, Q-26)

What the installer and bootloader on the owner's unit check before they
write or start a package's firmware, from their own MIT sources: the
installer **m-flasher** (MF) and the bootloader **m-bootloader** (MB),
read under the owner's ruling for BR-17 (2026-11-18, PROVENANCE P-67).
Only the package format and the checks are taken. Nothing here comes
from a stock package or from what any stock firmware holds. Phase B
round 1 (the owner, 2026-11-18) agrees with HW-109: both candidates were
refused before anything was written, with "unexpected flash image size".

### HW-109: What the installer checks in a package, in order
- Fact: m-flasher's firmware install refuses a `.fwsc` at the first of
  these that fails, before it writes anything:
  1. The file is at least 4 096 bytes.
  2. **Prefix blocks.** It takes at least the first 20 48-byte blocks,
     and goes on taking blocks while the next block's byte 47 is `0x7D`.
     So file byte `48·20 + 47` (1007) must not be `0x7D`, nor byte 47 of
     any later block it would reach. The identity is read from the
     markers up to the first `0x7D` (HW-88's rule).
  3. The header's CRC-16 (HW-104): "not a firmware package, or a damaged
     one (header CRC)".
  4. The list `64 + 80 × count` bytes fits in the image.
  5. **The list CRC**: the CRC-16 of the stored (masked) list bytes must
     equal header bytes 2-3: "damaged firmware package (file list CRC)".
  6. Every entry's data lies inside the image.
  7. An entry named `flash.bin` with type 0, and its data's CRC-16 (over
     the bytes as stored) equal to the entry's bytes 4-5.
  8. **The flash image's size**: longer than `0x4000` bytes and a
     multiple of `0x1000`: "unexpected flash image size N".
  Then, against the unit:
  9. **The model**: the identity up to its last `_` must be one of the
     connected board's models. An FM-1 takes `FM-1`, so the identity is
     `FM-1_` followed by a version with no `_` in it: in
     `FM-1_A_1` the model is `FM-1_A`, which is refused.
  10. The flash image is no longer than the flash (1 MiB).
  11. **The chip key** (HW-111): the app area, read with the unit's own
      key, must hold a valid file table with at least one file of
      attribute `0x82`, and every such file's CRC-16 over its unscrambled
      data must match its head ("does not decrypt with this unit's chip
      key").
  No other entry, field or CRC is checked, and no entry other than
  `flash.bin` is used. Header bytes 10-15 and the other entries (HW-104)
  are not read.
- Sources: MF `src/formats.rs` (`Package::parse`, `app_table`,
  `app_files_status`), `src/ops.rs` (`plan_firmware`), `docs/safety.md`;
  `docs/usage.md` (the FM-1's packages named `FM-1_…`); MB `docs/SPEC.md`
  §5.6. Phase B round 1 (step 8).
- Standing: confirmed (MF, MB)
- Needed by: BR-17 (a package the unit's installer accepts)

### HW-110: What the installer writes, and where the image goes
- Fact: m-flasher writes `flash.bin` from flash `0x4000` to its end, only
  the 4 KiB sectors that differ, and never the boot area
  (`0x0000`-`0x3FFF`), which stays the unit's own. It erases nothing
  outside the image, verifies every sector it writes, and saves a full
  backup first. So:
  - `flash.bin` must start at flash 0, because the installer takes
    offsets in it as flash offsets, but its first `0x4000` bytes are
    never written. Their content is not checked by the firmware install.
  - Everything from `0x4000` to the end of `flash.bin` replaces the
    unit's flash, `0xFF` filler included. An image longer than its app
    erases whatever the unit keeps there. It should end at the 4 KiB
    boundary after the app area.
  Its separate "put back the stock bootloader" action writes a package's
  boot area, and only if that boot area can start the unit. A firmware
  install never does.
- Sources: MF `src/ops.rs` (`plan_firmware`, `Plan`), `docs/safety.md`,
  `docs/usage.md` ("The actions").
- Standing: confirmed (MF)
- Needed by: BR-17

### HW-111: The unit's chip key, and how it is checked
- Fact: On the chip the key comes from efuse: bank 1, row 3, bits 23-8.
  When that reads `0xFFFF`, the bootloader instead takes the last 256
  bytes of the flash: when the CRC-16 of their bytes 0-7 equals the
  halfword at +8, the key is bytes +5 and +6. The installer asks the
  unit for its key over the download-mode connection, and shows it under
  "chip key" (`m-flasher info`). Every unit and package known to the
  bootloader's author uses `0x980F`, but neither tool assumes it: both
  read the unit's key. A package's app area must be scrambled (HW-90)
  with that key, or the installer refuses it (HW-109 step 11). The key
  the installer is given is the efuse key itself, without the
  bootloader's fallback. On a unit whose efuse reads `0xFFFF`, the key
  the installer checks against and the key the bootloader starts with
  can differ.

  The key block in the boot area (HW-89 and HW-90, 34 bytes with its CRC)
  is not what the bootloader starts with. Other firmwares' install
  loaders find the unit's key through that record and refuse a unit
  whose record is damaged. Both tools decode it by HW-90's rule.
- Sources: MB `docs/SPEC.md` §3.5 and §5.3; MF `src/ops.rs` (the key
  read from the unit, the note when it isn't the expected one),
  `src/formats.rs`.
- Standing: confirmed (MB, MF)
- Needed by: BR-17, Phase B

### HW-112: The bootloader's checked start
- Fact: Before it starts the app, m-bootloader:
  1. finds `app_dir_head` in the flash directory by name, and takes the
     app area at its offset (length 0 or `0xFFFFFFFF` for one bank);
  2. reads the area with the unit's key. Its first record must be the
     area head, attribute `0x83`, name `app_area_head`, its offset field
     the entry address (normally `0x02000120`). After it come at most
     eight records, ending at the first whose own CRC fails;
  3. checks every attribute-`0x82` file (`app.bin`, `cfg_tool.bin`):
     its CRC-16 over its unscrambled data, and its bounds inside the
     flash. `app.bin` must be non-empty, with the entry inside the
     mapped area. The area head's own data CRC is not this check;
  4. sets up the window with the key, and calls the entry with r0
     pointing at the boot block at `0x01C7FE08`: the decoded flash
     header's address (`0x01C7FE20`), the area's flash offset (`0x4000`),
     the window's address (`0x02000000`), the key (16 bits; HW-91's "chip
     ID"), a trim value (16 bits) and the 8 bytes at flash `0xFFF40`.
  A failed check, no app, or an app that returns opens its recovery
  menu. A normal start writes nothing to the flash. Region records
  (attributes `0x12`, `0x92`) give flash offsets and carry no data CRC.
- Sources: MB `docs/SPEC.md` §5.4, §6.5, §7.
- Standing: confirmed (MB)
- Needed by: BR-17, Phase B

### HW-113: What else a package's header holds
- Fact: Header bytes 10-11 and 12-15 (HW-104) hold 4 and `0x200` in
  M-VAVE's packages, as in JieLi's tools' output. M-VAVE's updater
  (M-UPGRADE, over USB MIDI) accepts a package holding only `ota.bin`
  with those values, `AC791N` at 16, the entry's data at `0x400` and its
  rounded size at entry bytes 16-19. What the values mean is not given.
  m-flasher doesn't read them (HW-109).
- Sources: MB `docs/SPEC.md` §5.6; PKG (P-65, HW-104).
- Standing: confirmed (MB, PKG)
- Needed by: BR-17

### HW-114: The flash image's length, and the unused directory slots
- Fact: In the update files JieLi's tools write (HW-103, HW-104), the
  `flash.bin` entry's data, the flash image, runs from flash 0 to the
  first 4 KiB boundary at or after the end of the app area's 64 trailing
  bytes (HW-105). Everything past them is `0xFF`. With the 4 096-byte
  apps that is `0x6000` (the area and its 64 bytes end at `0x52DF`).
  With the 8 192-byte app it is `0x7000` (they end at `0x62DF`). That
  agrees with the 4 KiB alignment in the flash header's byte 13
  (HW-105). It is not the header's flash size field. This length passes the installer's size rule
  (HW-109 step 8: longer than `0x4000`, a multiple of `0x1000`). The
  installer then writes the image from `0x4000` to its end, never below
  (HW-110).
  In the app area's directory, the unused head slots up to `0x120` hold
  `0xFF` before scrambling, so their CRC fails and a reader's walk ends
  there (HW-112). An all-zero slot would pass its own CRC (the CRC-16 of
  zeros is 0) and be read as a record.
- Sources: PKG (P-65): the four apps' flash images and their area
  directories; MF `src/formats.rs` (`Package::parse`, `app_table`) and
  `src/ops.rs` (`plan_firmware`).
- Standing: confirmed (PKG, MF)
- Needed by: BR-17 (SR-13)

## 26. The FM-1's panel, backlight, keys and LEDs, and the state at the app's entry (SR-14)

The board's wiring as the bootloader on the owner's unit, m-bootloader
(MB), drives it, and the state it leaves when it calls an app. Read
under the owner's ruling for SR-14 (2026-11-18, PROVENANCE P-68): its
`src/board.c`, `src/display.c`, `src/platform.c`, `src/boot.c`,
`src/startup.S` and the matching sections of `docs/SPEC.md`, at
`3ac7651a019f`. Only hardware facts are taken. The panel's set-up and the
key and LED facts below are what it runs on FM-1 hardware: its recovery
menu draws on the panel and lights the PLAY and octave LEDs. Port
registers are HW-56's (`JL_PORTx` at `0x00050000 + 0x40 × x`, A = 0 to
H = 7). "Output" means `DIR` clear, "input" `DIR` set.

### HW-115: The panel's pins and bring-up on the FM-1 (Q-6)
- Fact: On the FM-1 the panel is on SPI1's pin group B
  (`JL_IOMAP->CON1` bit 4 set; HW-56): clock PC9, data out PC10. Its chip
  select is PC7, active low, and its data/command line PC8 (0 for a
  command byte, 1 for data). No reset pin is driven: the panel is reset
  by its software reset command. The backlight is PA2 (HW-116). The
  bootloader brings the panel up like this:
  1. PC7 an output driven high; PC8, PC9 and PC10 outputs driven low.
     No pull-up, pull-down or strong drive (`HD0`, `HD`) is set on them.
  2. SPI1 `CON` `0x4021` and `BAUD` 4. With the low-speed bus at 60 MHz
     (HW-119) that is about 12 MHz, under the panel's limit (HW-57). The
     frequency is inferred from SPI1's clock being the bus clock divided
     by `BAUD + 1`.
  3. Each command is sent with PC7 low, PC8 low for the command byte,
     then PC8 high for its data bytes, then PC7 high. The steps: `01`
     (software reset), wait 150 ms; `11` (sleep out), wait 120 ms; `3A`
     with `55` (16-bit pixels); `36` with `00`; `21` (inversion on);
     `13` (normal display); the whole 240 × 240 area filled black; `29`
     (display on); then the backlight on.
  4. A window is `2A` and `2B`, each with a big-endian 16-bit start and
     end (inclusive), then `2C` and the pixels. Pixels are RGB565, high
     byte first. With `36` = `00`, the visible 240 × 240 starts at (0, 0),
     no row offset.
  Pixel data goes by SPI1's DMA, a byte buffer write for each command
  and data byte, waiting for `CON` bit 15 and clearing it with bit 14.
- Sources: MB `src/display.c` (the FM-1 board's pins, `CON`, `BAUD`, the
  steps), `docs/SPEC.md` §8.4 and §2.2 (the SPI1 registers and `CON`'s
  bits).
- Standing: confirmed (MB, SDK for the registers)
- Needed by: BR-17 (Phase B), real hardware (Level 2)

### HW-116: The backlight
- Fact: On the FM-1 the backlight is PA2, active low: an output driven
  low lights it, and driven high or left an input it is dark. PA2 also
  enables the key matrix (HW-117). The ROM leaves PA2 undriven, an input.
  The bootloader drives it low only while it scans keys or shows its
  menu, and puts it back before it calls the app (HW-119).
- Sources: MB `src/display.c` (PA2 high during the panel's set-up, low
  after it), `src/board.c`, `docs/SPEC.md` §8.2 and §8.4.
- Standing: confirmed (MB)
- Needed by: BR-17 (Phase B)

### HW-117: The keys: the matrix, PLAY, REC and the octave keys (Q-7)
- Fact: On the FM-1 the key columns are selected through two cascaded
  shift registers:
  - **Pins.** Data PA4, clock PA3, latch PA1, all outputs. Sixteen bits
    go most significant first, each with a clock pulse high then low,
    then a latch pulse high then low. A column is selected by a 0 bit,
    and `0xFFFF` selects none. Each edge should be its own
    read-modify-write of the port's `OUT`, taking real bus time. Edges
    that were too short have been seen to select the neighbouring column.
  - **Rows.** They are read on PA5 to PA8, inputs with `DIE` and the
    pull-up on and the pull-down off. A closed key reads low, sampled
    10 µs after the column changes.
  - **PA2 must be an output driven low** while the matrix is scanned. With
    PA2 high or an input, no key reads closed. This also lights the
    backlight (HW-116).
  - **Four keys measured on FM-1 hardware:** OCT− reads on PA8 with the
    word `0xF7FE`, OCT+ on PA8 with `0xEFFD`, PLAY on PA6 with `0xFBFF`,
    and REC on PA6 with `0xFF7F`.
  The bootloader opens its recovery menu when PLAY is held for about a
  second at power-on, and goes to download mode when REC is.
- Sources: MB `src/board.c` (the pins, the words, the rows),
  `src/platform.c` (the port registers), `docs/SPEC.md` §8.2 (the FM-1
  scan facts, PA2, measured on FM-1 hardware).
- Standing: confirmed (MB)
- Needed by: BR-17 (Phase B), M3 on real hardware

### HW-118: The LEDs (Q-7)
- Fact: On the FM-1 an LED is lit by selecting its column (HW-117) and
  driving its line high. The lines are PA9, PA10, PH6 and PH9, outputs,
  one for each row PA5 to PA8 in that order. PLAY's LED is the column
  `0xFBFF` with PA10 high. The octave keys' LEDs are the columns `0xF7FE`
  (OCT−) and `0xEFFD` (OCT+) with PH9 high. The bootloader keeps all four
  lines low while it changes or reads a column. It lights its three menu
  LEDs one per millisecond in turn, at about a third of the time each.
  Whether PA2 must be low for the LEDs as for the keys isn't stated; the
  bootloader always has it low when it lights them.
- Sources: MB `src/board.c` (the lines, the columns, the multiplexing),
  `docs/SPEC.md` §8.2 (the LED lines; the three LEDs light on FM-1
  hardware).
- Standing: confirmed (MB)
- Needed by: BR-17 (Phase B), M3 on real hardware

### HW-119: The state when m-bootloader calls the app (Q-2)
- Fact: When m-bootloader starts an app (HW-112):
  - **Clocks:** system 360 MHz, high-speed bus 180 MHz, low-speed bus
    60 MHz. SPI0, SPI1 and TIMER0 run from the low-speed bus. The code
    runs from the flash through the window (HW-91) with the cache on.
  - **Voltages:** core 1.26 V, the 1.4 V domain 1.40 V, and the I/O
    supply 3.2 V on the FM-1.
  - **Watchdog** off, cleared at the bootloader's start. **Interrupts**
    off: it disables them just before the call.
  - **Ports A and H:** every register as the ROM left them. The
    bootloader saves them before its key check and restores them before
    the call, so PA2 (the backlight), the scan pins and the LED lines are
    not set up.
  - **Port C and the panel:** on a normal start the bootloader doesn't
    touch them. After its menu or an update has drawn on the panel, PC7
    to PC10 stay outputs and `JL_IOMAP->CON1` bit 4 stays set. SPI1 is
    switched off (`CON` 0), the panel is not set up again, and the
    backlight is dark (PA2 back to the ROM's state).
  - **The flash's pins** (port D, SPI0) were set up for the bootloader's
    own reads. SPI0 is switched off and the flash is read through the
    window only.
  - **TIMER0** is stopped (`CON` bit 14 written).
  - **Stacks:** `sp` and `ssp` are in the bootloader's own RAM, below
    `0x01C0A800`.
  - **The call:** an ordinary call of the entry, with r0 pointing at the
    boot block at `0x01C7FE08` (HW-112). If the app returns, the
    bootloader opens its recovery menu with the reason "APP EXITED". It
    reads no return value. A return works if the app keeps the calling
    convention's saved registers and the stack pointer, and leaves the
    bootloader's RAM (`0x01C02000` to below `0x01C0A800`) and the
    retained area from `0x01C7FD80` (the boot block included) as it found
    them.
- Sources: MB `src/boot.c` (the start and the call), `src/board.c` (the
  save and restore of ports A and H), `src/display.c` (what the panel's
  release leaves), `src/platform.c` (the watchdog, TIMER0, the window's
  set-up, SPI0's release), `src/startup.S` (the stacks), `docs/SPEC.md`
  §2.1, §3.1, §3.2, §3.3, §6.5 and §7.
- Standing: confirmed (MB)
- Needed by: BR-17 (Phase B)

## 27. The FM-1's two flash parts (SR-15)

Units sold since autumn 2026 carry a second flash part. Read under the
owner's request for SR-15 (2026-11-18, PROVENANCE P-73): the two parts'
datasheets, the P25Q80H's (PUYA, as before) and the UC25HQ80's (UCUN),
and m-bootloader's flash code (MB: `src/platform.c`, `src/boot.c`,
`src/loader.c` and `docs/SPEC.md` §3.4 and §3.5, at `3ac7651a019f`).
HW-120 gives the two parts, HW-121 the commands small-beeps uses on both,
HW-122 the differences between the datasheets and whether they matter,
HW-123 what m-bootloader does with either part, and HW-124 what a
firmware does so one image works on both. HW-76 to HW-78 stand as they
are: everything they say of the P25Q80H holds, and HW-121 adds the
UC25HQ80's side. Page numbers are as printed.

### HW-120: The two parts and their IDs (Q-21)
- Fact: Two 1 MiB SPI NOR parts answer the JEDEC ID read (`0x9F`) with
  the same memory type and capacity bytes, `0x60 0x14`, and different
  manufacturer bytes:
  - `0x85 0x60 0x14`: Puya's P25Q80H (HW-76).
  - `0xB3 0x60 0x14`: UCUN's UC25HQ80. The ID reads `0x90`, `0x92` and
    `0x94` give `B3 13`, and `0xAB` gives `13`.
  Both are organised alike: 256-byte pages, 4 KiB sectors, 32 KiB and
  64 KiB blocks, 1 MiB in all, from `0x000000` to `0x0FFFFF`. Both work
  from 2.3 to 3.6 V, in SPI modes 0 and 3. Both datasheets give 100 000
  program/erase cycles and 20 years' retention. The owner relays (not
  taken as a fact here) that the owner's unit reports `0x856014` in
  m-flasher's information and in m-bootloader's recovery menu ("flash
  856014 1024K"), and that units sold since autumn 2026 report
  `0xB36014`.
- Sources: PUYA p. 1, p. 22 (the ID read) and p. 54 (the ID table);
  UCUN p. 4 (features), p. 6 (Table-2.0 and Table-3.0, the
  organisation), p. 14 (Table-8.0, the IDs) and p. 39 (the ID read: the
  manufacturer byte, then the memory type, then the capacity).
- Standing: confirmed (PUYA, UCUN; which units carry which part only as
  the owner relays it)
- Needed by: M7, BR-17 (Phase B)

### HW-121: The commands small-beeps uses, on both parts
- Fact: The store's commands work the same on both parts. Times are
  typical / maximum.

  | Command | Code | P25Q80H | UC25HQ80 |
  |---------|------|---------|----------|
  | Read the ID | `0x9F` | `85 60 14` | `B3 60 14` |
  | Read | `0x03`, 3 address bytes | up to 55 MHz | up to 50 MHz |
  | Status register 1 | `0x05` | bit 0 WIP, bit 1 WEL | the same |
  | Write enable | `0x06` | sets WEL | the same |
  | Sector erase, 4 KiB | `0x20`, 3 address bytes | 8 / 12 ms | 7 / 10 ms |
  | Page program, 1 to 256 bytes | `0x02`, 3 address bytes, data | 2 / 3 ms | 1.5 / 3 ms |

  Every other command in the table runs at up to 104 MHz on both. On both
  parts:
  - WIP (bit 0 of status register 1) is 1 from the moment chip select
    goes high after an erase or program until it ends. The status read
    works throughout and may be repeated within one selection.
  - WEL (bit 1) must be set by `0x06` before every erase, program and
    status register write. It clears when that operation ends, and at
    power-up.
  - An erase or program starts only if chip select goes high at a byte
    boundary.
  - A page program wraps within its 256-byte page. Of more than 256 bytes
    only the last 256 are kept, and fewer change only the bytes sent.
  - Reads (`0x03`, `0x0B` and the dual and quad reads) and the ID reads
    are ignored while WIP is 1.
  - An erase or program of an area the block-protect bits cover is
    ignored: it is not carried out. (How a firmware tells is HW-124's
    item 4, a read-back.)
  - The chip select must stay high at least 30 ns between a write, erase
    or program and the next status register read, and at least 15 ns
    between two reads.
- Sources: PUYA p. 10 (fR, fC, tSHSL), p. 11 (tPP, tSE), p. 18 (the
  byte boundary; reads ignored while busy), p. 21 (the commands),
  p. 25-26 (the status reads and bits), p. 40 and p. 43 (erase and
  program), p. 54; UCUN p. 8 (Table-4, WIP and WEL), p. 11 (note 2: a
  protected erase or program is ignored), p. 12-13 (Table-7; chip select
  at a byte boundary), p. 14-15 (WREN, and WEL cleared), p. 16 (RDSR),
  p. 18 (READ, rejected while busy), p. 26 (SE), p. 28 (PP: the wrap and
  the last 256 bytes), p. 39 (RDID not decoded while busy), p. 52-53
  (Table-17.1 and Table-18: fR, fC, tSHSL, tPP, tSE).
- Standing: confirmed (PUYA, UCUN)
- Needed by: M7, BR-17 (Phase B)

### HW-122: The differences between the two parts, and which matter
- Fact: Compared, the two datasheets' command sets, status registers,
  protected-area tables, AC timing tables, power-up timing and delivery
  state. Not compared: the DC currents, the SFDP tables' contents, the
  security registers' and unique ID's details, and the packages.
  - **Identical:**
    - the status register's sixteen bits: S0 WIP, S1 WEL, S2-S6 BP0-BP4,
      S7 SRP0, S8 SRP1, S9 QE, S10 SUS2, S11-S13 LB1-LB3, S14 CMP,
      S15 SUS1;
    - the protected-area tables, row for row, for CMP 0 and CMP 1;
    - the state at delivery: the array erased (`0xFF`) and the status
      register `0x00`, so QE is 0 and nothing is protected;
    - the command codes besides those below: the reads `0x03`, `0x0B`,
      `0x3B`, `0xBB`, `0x6B` and `0xEB`; the erases `0x81`, `0x20`,
      `0x52`, `0xD8`, `0x60` and `0xC7`; the programs `0x02`, `0xA2` and
      `0x32`; `0x06`, `0x04`, `0x50`, `0x05`, `0x35`, `0x25` and `0x01`;
      the security registers `0x44`, `0x42` and `0x48`; deep power-down
      `0xB9` and its release `0xAB`; the ID reads `0x90`, `0x92`, `0x94`
      and `0x9F`; suspend and resume `0x75`/`0xB0` and `0x7A`/`0x30`;
      reset `0x66` and `0x99`; `0x77`, `0x4B`, `0x5A`, and `0xFF`, which
      ends a continuous read;
    - the maximum page program time (3 ms) and the status register write
      time (8 / 12 ms).
  - **Different:**

    | What | P25Q80H | UC25HQ80 | Matters to small-beeps |
    |------|---------|----------|------------------------|
    | The ID's first byte | `0x85` | `0xB3` | Yes: a firmware that checks the whole ID refuses one of them. |
    | Erase times (page, 4 KiB, 32 KiB, 64 KiB, chip), typical / maximum | 8 / 12 ms | 7 / 10 ms | No, if it waits on WIP. The longest is the P25Q80H's 12 ms. |
    | Typical page program | 2 ms | 1.5 ms | No: the maximum is 3 ms on both. |
    | `0x03`'s clock limit | 55 MHz | 50 MHz | Only if SPI0 runs faster than 50 MHz. |
    | Clock limits for `0x3B`, `0xBB`, `0x6B` and `0xEB` | 104 MHz each | 104, 66, 66 and 50 MHz | Not to the store. The window's reads are set by the bootloader (HW-123). |
    | Quad page program `0x32` | up to 104 MHz | up to 83 MHz | No: not used. |
    | A configure register: read `0x15`, write `0x31` | Yes. Its bit 7, DP, makes the page 512 bytes and `0x81` erase 512 bytes. 0 by default. | No such register, and no `0x15` or `0x31` command | Only a firmware that sends `0x31` or `0x15`. small-beeps sends neither. |
    | `0x01` with one data byte | Clears CMP, QE and SRP1 (S14, S9 and S8) | Not stated: the text says both "after the eighth bit" and "at the 8 or 16 bit boundary" | Only a firmware that writes the status register. Use the two-byte form (HW-124). |
    | Suspend latency | 30 µs | 45 µs | No: not used. |
    | Recovery after a reset (`0x66`, `0x99`) | 30 µs | 40 µs | No: not used. |
    | Power-up to first command (tVSL) | 70 µs | 300 µs | No: the bootloader runs first. |
    | Write-inhibit voltage | 1.45 to 1.55 V | 1 to 1.55 V | No. |

  So for the commands small-beeps sends (HW-121), only the ID differs.
- Sources: PUYA p. 10-11 (Table 5-3 and 5-4), p. 14 (power-up; the
  delivery state), p. 15-16 (Table 6-1), p. 21-22 (the command set),
  p. 26-27 (the status register), p. 28 (the configure register),
  p. 29-31 (WRSR and WRCR); UCUN p. 8-11 (Table-4 to Table-6.1),
  p. 12-13 (Table-7), p. 17 (WRSR), p. 40-41 (suspend), p. 43 (reset),
  p. 49 (`0xFF`), p. 50 (Table-13; the delivery state), p. 52-54
  (Table-17.1 and Table-18).
- Standing: confirmed (PUYA, UCUN)
- Needed by: M7, BR-17 (Phase B)

### HW-123: What m-bootloader does with either part (Q-23)
- Fact: m-bootloader works either part with the same code:
  - **Identifying:** it reads the ID and uses only the capacity byte
    (`2^n` bytes for n from 16 to 24). It boots an app only when the
    capacity is 1 MiB, so both parts pass, and it shows the whole ID in
    its recovery menu.
  - **Before its first command:** it sends `0xFF` twice under one chip
    select, to end any continuous read it might have inherited.
  - **Before each of its own erases and programs:** it reads both status
    bytes. If any of BP0-BP4 (status 1 mask `0x7C`) or CMP (status 2 mask
    `0x40`) is set, it clears them with a two-byte `0x01`, keeping the
    other bits. If that doesn't take, it writes status 1 with `0x01` and
    status 2 with `0x31` separately. It doesn't set them again
    afterwards, so after a unit has been written through m-bootloader,
    nothing is protected.
  - **For quad reads:** when its reads and the window are to run at quad
    width, it sets QE (status 2 bit 1) the same way, with up to three
    tries, and leaves it set. QE is non-volatile, so it stays set across
    power cycles. Its `docs/SPEC.md` notes that the separate `0x31` write
    is a fallback that has been seen to work. On the P25Q80H `0x31`
    writes the configure register instead (HW-122).
  - **Erases** are 4 KiB (`0x20`) or 64 KiB (`0xD8`), aligned. **Programs**
    send one page per `0x02`, each after a `0x06`.
  - **Waiting:** it reads status 1 every 100 µs until WIP is 0, and gives
    up after 30 000 reads (about 3 s).
  - **Before it calls an app:** it switches SPI0 off and gives the flash
    back to the code window at the width it chose (HW-119).
  The code window's own clock and width come from the bootloader's
  configuration, not from the app. At quad width the window needs QE set.
- Sources: MB `src/platform.c` (the ID and capacity, `0xFF` twice, the
  protection clear, the QE set, the erase and program commands, the
  status polling, the release before the call), `src/boot.c` (the 1 MiB
  check; the ID in the menu), `docs/SPEC.md` §3.4 and §3.5 (the
  quad-enable fallback; the protection masks). `src/loader.c` adds
  nothing here: it erases and programs through the same calls.
- Standing: confirmed (MB)
- Needed by: M7, BR-17 (Phase B)

### HW-124: What a firmware does so one image works on both parts
- Fact: From HW-120 to HW-123, one image works on both parts when its
  flash code:
  1. **Takes either ID:** `0x856014` and `0xB36014`, or any ID whose
     capacity byte is `0x14` with one of those two manufacturer bytes.
     A firmware that refuses an unknown part (as HW-76 suggested) lists
     both.
  2. **Sends only HW-121's commands** (`0x9F`, `0x03`, `0x05`, `0x06`,
     `0x20`, `0x02`), and `0x35` for item 5, each as both datasheets give
     it. Never `0x31` or `0x15` (the P25Q80H's configure register), never
     the one-byte form of `0x01`, and no quad or dual command of its own.
  3. **Waits on WIP**, never for a fixed time, and allows at least the
     larger maximum: 12 ms for an erase, 3 ms for a page program, 12 ms
     for a status register write.
  4. **Reads every write back** with `0x03` and treats a difference as a
     failure. That includes an erase, which should read back all `0xFF`.
     A protected erase or program does nothing, and WIP doesn't show it.
  5. **Leaves the status register alone** unless it must. If block
     protection covers its region (BP0-BP4 in status 1, read by `0x05`;
     CMP in status 2, read by `0x35`, the same on both parts; by the
     table both parts share), either refuse to write or clear it with a
     two-byte `0x01` that keeps every other bit, QE above all. QE
     cleared while the window reads at quad width stops the window as
     soon as the firmware gives the flash back. After a unit has been
     written through m-bootloader nothing is protected (HW-123), but a
     firmware can't count on that.
  6. **Runs `0x03` at 50 MHz at most** (SPI0's clock).
  These hold for any region, a store at `0xFC000` or one at `0x80000`
  alike: the "upper 1/2" row (BP2 alone) would protect both. Handing the
  flash from the code window to SPI0 and back (Q-22) is the same on both
  parts.
- Sources: HW-120 to HW-123; PUYA p. 10, p. 15-16 and p. 29-30; UCUN
  p. 10-11, p. 17 and p. 52-53.
- Standing: confirmed (PUYA, UCUN, MB)
- Needed by: M7, BR-17 (Phase B)

## 28. What the hardware build still needs on the chip (SR-16)

Session spec-sr16 answered SR-16 (2026-11-18, PROVENANCE P-500), as the owner's request gives it
(docs/prompts/spec-sr16.md; docs/prompts/spec-ci-speed.md, item 3), from the
sources the owner's rulings allow, under section 25's and 26's guardrails:
- the SDK: its timer example again, and `adc_api.h` and `cache.h`, new;
- m-bootloader (MB) at `3ac7651a019f`: the files P-68 and P-73 name, and
  `docs/SPEC.md` §2.1, §3.3, §3.6, §4.4, §6.1, §6.5, §8.2 and §11.8;
- FM-1-RE (RE), its allowed documents.

The entries:
- HW-125: the timers' `CON` bits and clocks (item 1).
- HW-126: interrupts and the vector table after the call (item 2).
- HW-127: code run from RAM (item 3).
- HW-128: taking the flash from the code window and giving it back, for
  the store (Q-22).
- HW-129: the pot's channels and the encoders (items 4 and 5).
- HW-130: audio, core 1 and MIDI (item 6).

Much of SR-16 no allowed source gives. Each entry says what is still open
and what would settle it; mostly that is a probe on a unit.

### HW-125: The timers' `CON` bits and clocks on the chip (Q-3, Q-13)
- Fact: On the chip, for TIMER0 to TIMER5:
  - **Bits 1-0** pick the mode. 1 counts up from `CNT` to `PRD`. 2
    captures on a rising edge, and 3 on a falling edge.
  - **Bit 3** picks the input clock. With it set the timer counts the
    oscillator; with it clear, the low-speed bus (LSB). The FM-1's
    oscillator is 24 MHz, and its LSB is 60 MHz after m-bootloader
    (HW-119).
  - **Bits 7-4** pick the prescaler, with the settings HW-48 gives
    (setting 0 divides by 1).
  - **Bit 15** reads 1 while the period's interrupt is pending. Writing
    bit 14 clears it. The SDK's handler acknowledges by setting bit 14 in
    `CON` and does nothing else to the timer.
  - **Stopping:** the SDK stops a timer by writing `CON` with bit 14
    alone.
  So `CON` = `0x1` runs a timer from the 60 MHz LSB, one count per clock.
  The hardware build's TIMER0 does this, and so does m-bootloader's
  TIMER0 on FM-1 units. m-bootloader uses only TIMER0. It writes `CON`
  only as `0x4000` (stop, clear pending) and `0x1` (start). It sets
  `CNT` to 0 and `PRD` to the count wanted, then waits for bit 15. A
  free-running time base at 24 MHz, as fwtest's TIMER4 is (HW-13), needs
  `CON` bit 3 set on the chip, with bits 1-0 at 1 and prescaler 0. With
  bit 3 clear it counts the 60 MHz LSB.
  Still open:
  - whether the acknowledge restarts the count (Q-13). m-bootloader
    never acknowledges a running timer; it stops it first.
  - what bit 2 does.
- Sources: SDK `apps/common/example/peripheral/timer/test2.c` lines
  100-120 (the set-up: `CON` 0, `CNT` 0, bit 14, `PRD`, the prescaler
  "of lsb_clk" in bits 7-4, then bit 0), 131-136 (the handler: bit 15,
  then bit 14), 176-188 (TIMER4 from the oscillator: `CON` = prescaler
  << 4 | bit 0 | bit 3, its period computed from the "osc" clock), 194
  and 209 (stop: `CON` = bit 14), 259-265 (capture: bits 1-0 at 3 and
  2); MB `docs/SPEC.md` §1 (the 24 MHz oscillator) and §3.3 (TIMER0's
  `CON` written only as `0x4000` and `1`, one count per LSB clock, used
  on hardware).
- Standing: confirmed (SDK, MB)
- Needed by: BR-17 (Phase B), M1

### HW-126: Interrupts and the vector table after m-bootloader's call (Q-10)
- Fact: The vector table's place, `0x01C7FE00` to `0x01C7FFFF` (HW-18),
  is inside m-bootloader's retained area, which starts at `0x01C7FD80`.
  Its slots overlap what m-bootloader puts there:
  - the app's boot block at `0x01C7FE08` (24 bytes: slots 2 to 7);
  - the copy of the flash header at `0x01C7FE20` (32 bytes: slots 8
    to 15);
  - two words, `0x01C7FE58` and `0x01C7FE60`, that must be zero
    (slots 22 and 24).
  m-bootloader writes all of these before each call. What it reads at
  its next start lies below the table: the boot status at `0x01C7FD80`
  and the update request at `0x01C7FD88` (80 bytes, up to `0x01C7FDD7`).
  So an app that never returns may write the whole table, once it has
  taken what it needs from the boot block that r0 points at (the chip
  key, HW-112, at +12). It must leave `0x01C7FD80` to `0x01C7FDD7` alone
  unless it means to ask for an update. m-bootloader's own documents say
  that an app using interrupts there resets rather than returns.
  m-bootloader runs with interrupts off throughout and calls the app
  with them off (HW-119). It sets both stack pointers, `ssp` and `sp`,
  to its own stacks at its start. Its documents say that the CPU has a
  main stack and a system (exception) stack, and that the CPU's full
  control state and the interrupt vector arrangement are not
  established. So:
  - an app sets both `ssp` and `sp` itself before it enables interrupts;
  - which of the two an interrupt runs on is still open (HW-3 is
    fwtest's);
  - what `idle` does on the chip is not shown by any allowed source.
    m-bootloader executes it only in a loop after asking for a reset
    (Q-10).
- Sources: MB `docs/SPEC.md` §2.1 (the two stacks; the control state and
  vector arrangement not established), §6.1 (the retained area's map),
  §6.5 (the boot block written before the call), §11.8 (the vector
  table's usual place is in the retained area: an app with interrupts
  resets); MB `src/startup.S` (both stack pointers set),
  `src/platform.c` (`idle` only after the reset request); HW-18, HW-112,
  HW-119.
- Standing: confirmed (MB)
- Needed by: BR-17 (Phase B)

### HW-127: Code written to RAM and then run
- Fact: m-bootloader runs code it has just written to main RAM after a
  core synchronisation (`csync`) and nothing more, in three places:
  - its own second stage, which its first stage unpacks to RAM and jumps
    to on every start of every unit;
  - a staged updater;
  - a RAM app, after a `csync`.
  It invalidates the cache only for the flash window, before it sets up
  XIP. The SDK declares data cache calls with 32-byte lines: flush, flush
  and invalidate, a way choice, and a write-through range. It doesn't say
  which addresses are cached.
  So on the chip, code copied into main RAM with ordinary stores runs
  after a `csync` as m-bootloader's does. An app that then changes the
  flash under the window needs the window's cache invalidated as HW-128
  says.
  Still open: whether main RAM is behind a data cache that DMA (SPI1,
  the audio DMA, UART1's) must see flushed.
- Sources: MB `src/boot.c` (the RAM app called after `sync_cpu`, and the
  same after an updater), `src/platform.c` (the cache invalidation in
  the XIP set-up only), `docs/SPEC.md` §4.4 (the second stage unpacked
  to RAM and run), §2.2 and §3.6 (the cache control and its ranges); SDK
  `include_lib/driver/cpu/wl82/asm/cache.h` (`CACHE_LINE_COUNT` 32,
  `flush_dcache`, `flushinv_dcache`, `dcache_way_use_select`,
  `dcache_cwt_set`).
- Standing: confirmed (MB, SDK)
- Needed by: BR-17 (Phase B), M7

### HW-128: Taking the flash from the code window, and giving it back (Q-22)
- Fact: m-bootloader works the flash over SPI0 only while nothing runs
  from the window.
  - **To take it:** it writes 0 to the window controller's `CON`
    (`0x40200`) and to the peripheral cipher's control (`0x13000`). It
    clears bit 1 of `JL_IOMAP->CON1` and bit 5 of `CON0`, so SPI0 uses
    port D (HW-85). It sets up the flash's pins:
    - PD0, the chip select: an output, high;
    - PD4, the clock, and PD5, data out: outputs, low, with PD4's
      drive-strength bit (`HD` bit 4) set;
    - PD1, data in: an input with no pulls;
    - PD2 and PD3: outputs, high.
    It then writes SPI0's `CON` as `0x28`, sets `BAUD`, and sets bits 14
    and 0. Before its first command it sends `0xFF` twice (HW-123).
  - **To give it back before an app runs:**
    1. It writes 0 to SPI0's `CON`, to `0x13000` and to the window
       cipher's control (`0x40300`).
    2. It clears bit 16 of `JL_IOMAP->CON0`, the window's pin route.
    3. It writes `0x00F00000` then 0 to the window controller's `CON`,
       sets its `BAUD`, and writes its mode word. At quad width with
       output reads that is `0x00280381`, with bits 23-20 set to 9 at
       HSB 180 MHz for about 45 ns of chip-select high.
    4. It writes the app area's flash base (`0x4000`) to `0x4020C` and
       the chip key to `0x40304`.
    5. It invalidates the cache: it clears bits 8 and 9 of `0x01EEE008`,
       clears four internal ranges with word writes (`0x01F00000` to
       below `0x01F04000`, `0x01F08000` to below `0x01F0A200`, and
       `0x01F0B000` to below `0x01F0B200`), and sets the two bits again.
    6. With interrupts off, it waits for bit 14 of `0x01EEE008` (idle),
       sets the window cipher's control to 1, and does a `csync`.
  - **SPI0's clock** is the LSB (60 MHz) divided by `BAUD` + 1. That is
    inferred in m-bootloader's documents. At its default divider of 1 it
    is about 30 MHz, within both flash parts' 50 and 55 MHz for `0x03`
    (HW-124 item 6).
  This goes past HW-85: the flash's port D pins are set up for SPI0, but
  only while the window is not in use. HW-85 stands for an app that
  runs from the window and doesn't take the flash.
  Not shown by any allowed source: taking the flash and then giving the
  window back within one run of an app, without a reset. That is the
  round trip the store needs. m-bootloader never does it: after a failed
  XIP start it resets before setting XIP up again, because a direct
  retry failed on an SMK-37 Pro. Settled by a probe on a unit: code in
  RAM takes SPI0, reads the ID, gives the window back as above, and then
  runs code from the window again.
- Sources: MB `src/platform.c` (`flash_init`: the take and the pins;
  `flash_release` and the XIP set-up: the give-back and the cache
  invalidation), `docs/SPEC.md` §3.4 (SPI0's set-up and pins), §3.6 (the
  window's set-up, the mode words, the cache ranges, the failed direct
  retry), §2.2 (the clock relation, inferred); HW-85, HW-123, HW-124.
- Standing: confirmed (MB; the round trip within one run not shown)
- Needed by: M7, BR-17 (Phase B)

### HW-129: The pot's ADC channels and the encoders (Q-7, Q-8)
- Fact: The SDK's SARADC channel numbers name their pins:

  | Channel | Pin |
  |---------|-----|
  | 0 | PA7 |
  | 1 | PA8 |
  | 2 | PA10 |
  | 3 | PB1 |
  | 4 | PB6 |
  | 5 | PB7 |
  | 6 | PC0 |
  | 7 | PC1 |
  | 8 | PC9 |
  | 9 | PC10 |
  | 10 | PH0 |
  | 11 | PH3 |
  | 12 | USB D− |
  | 13 | USB D+ |
  | 14 | the RTC |
  | 15 | internal sources: the PMU, audio, PLL and others, chosen further |

  FM-1-RE says the FM-1's firmware reads SARADC channels 3 and 4, so PB1
  and PB6. fwtest's pot is channel 4 (HW-40). FM-1-RE also says the FM-1
  has two rotary encoders, read as GPIO. No allowed source gives their
  pins, or the rest of the key matrix beyond HW-117's four keys. That
  includes what bits 11 to 15 of the column word select (OCT−'s `0xF7FE`
  and OCT+'s `0xEFFD` clear two bits each).
  Open, and settled by probes on a unit:
  - which channel the pot is on;
  - the pin set-up a channel needs (digital input off is the SDK's
    usual choice; not taken from its driver here);
  - the encoders' pins and pulls;
  - each column word against rows PA5 to PA8.
- Sources: SDK `include_lib/driver/cpu/wl82/asm/adc_api.h` lines 8-27
  (`AD_CH_PA07` 0 to `AD_CH_PMU` 15); RE `docs/architecture.md` (two
  rotary encoders; SARADC channels 3 and 4 at `0x13100`) and
  `docs/reversing/01-hardware-map.md` (encoders on GPIO, polled);
  HW-40, HW-117.
- Standing: confirmed (SDK, RE; the board's use of the channels and the
  encoders' pins open)
- Needed by: M3, BR-17 (Phase B)

### HW-130: Audio, core 1 and MIDI after m-bootloader's call (Q-20)
- Fact:
  - **Audio.** Beyond HW-43 to HW-45's registers, FM-1-RE names other
    audio blocks the FM-1's firmware uses. It gives each at its own
    confidence and marks some names as borrowed from a sibling chip:
    - an analogue DAC block at `0x11904`, `0x11908`, `0x1190C` and
      `0x1191C` (analogue control, DC-offset trim, trim codes);
    - a DAC clock gate, bit 14 of `0x119CC`;
    - a codec serial port at `0x3101C`;
    - the audio clock's source and divider in `0x10014` (bits 8 and 10)
      and `0x119A8` (bit 25).
    It also says that the FM-1's firmware feeds its synthesis through
    the audio link at `0x12E00` (HW-43) by DMA, a half at a time, on
    interrupt source 11; that it sets up four pins there, which it
    numbers 32, 33, 34 and 38; and that it reaches the codec's analogue
    side through the serial port with long tables of register writes.
    It reports the firmware's rate as 44 118 Hz.
    Not taken here: a bring-up order, the tables, or which physical pins
    those numbers are. So these stay open per part of the output:
    - **clocks:** which of the audio clock's settings give 44 118 Hz
      from the 360 MHz system;
    - **output:** the analogue set-up and the pins;
    - **DMA:** whether the audio link plays its halves on the chip as in
      fwtest (HW-44, HW-45: the sample format is Q-9).
  - **Core 1.** m-bootloader never starts core 1, and no allowed source
    shows whether HW-9's release works after its call. HW-9's method
    stays the only one known.
  - **MIDI.** UART1's pins on the board stay open (Q-20; HW-73 lists the
    candidates). m-bootloader uses USB, not a UART.
  Settled by probes on a unit:
  - a tone after HW-43 to HW-45's set-up alone, to show what more the
    output needs;
  - core 1 released as HW-9 says, with a counter it increments;
  - bytes received on UART1 on each candidate pin.
- Sources: RE `docs/io/03-audio-dac.md` (the register table and its
  confidence marks; the 44 118 Hz rate); MB `src/boot.c`,
  `src/platform.c` and `docs/SPEC.md` (no core 1; MIDI over USB only,
  §11.6); HW-9, HW-43 to HW-45, HW-73.
- Standing: confirmed (RE, MB; the bring-up, core 1 after the call and
  UART1's pins open)
- Needed by: M4, M5, M6, BR-17 (Phase B)

## 29. Block protection on both flash parts (a harness request)

Read under the owner's request of 2026-11-18 (clean's #193: fwtest's chip
should ignore a protected erase or program, so the store's read-back can
be tested; PROVENANCE P-501), from the same two datasheets as section 27
(PUYA, UCUN). HW-121 says a protected erase or program is ignored, and
HW-124 item 5 names the bits; HW-131 gives which bytes each setting
protects.

### HW-131: The protected area for each setting of BP0-BP4 and CMP
- Fact: Both parts share one table, row for row (HW-122). BP4 to BP0 are
  status register 1's bits 6 to 2, CMP is status register 2's bit 6.
  Addresses are in the 1 MiB chip.
  - **CMP = 0:**
    - BP2-BP0 = `000`: nothing is protected, whatever BP4 and BP3.
    - BP4 = 0 and BP2-BP0 = `001`, `010`, `011` or `100`: 64, 128, 256 or
      512 KiB are protected, at the top of the chip (`0xF0000`,
      `0xE0000`, `0xC0000` or `0x80000` to `0xFFFFF`) when BP3 = 0, at the
      bottom (`0x00000` to `0x0FFFF`, `0x1FFFF`, `0x3FFFF` or `0x7FFFF`)
      when BP3 = 1.
    - BP4 = 0 and BP2-BP0 = `101`, or BP2 and BP1 both 1 (any BP4, BP3,
      BP0): the whole chip is protected.
    - BP4 = 1 and BP2-BP0 = `001`, `010`, `011`, or `10x`: 4, 8, 16 or
      32 KiB are protected, at the top (`0xFF000`, `0xFE000`, `0xFC000` or
      `0xF8000` to `0xFFFFF`) when BP3 = 0, at the bottom (`0x00000` to
      `0x00FFF`, `0x01FFF`, `0x03FFF` or `0x07FFF`) when BP3 = 1.
  - **CMP = 1:** each row protects exactly the bytes its CMP = 0 row
    leaves unprotected: nothing becomes the whole chip, the whole chip
    becomes nothing, and the top 64 KiB becomes `0x00000` to `0xEFFFF`.
  - **Which commands are ignored:** an erase or program whose range holds
    any protected byte is ignored, wholly. A chip erase (`0x60`, `0xC7`)
    is carried out only when nothing is protected.
  - **WEL and WIP after an ignored command:** PUYA says a protected
    32 KiB block erase (`0x52`) changes nothing and still resets WEL.
    Neither datasheet says so of the other erases and the page program,
    nor whether WIP goes to 1 for any time; UCUN says neither for any
    command.
  - So a store at `0xFC000` is protected by, among others, BP0 alone
    (the top 64 KiB), BP2 alone (the top half, which also covers
    `0x80000`) and BP4 with BP1 and BP0 (the top 16 KiB).
  - fwtest follows this table from 0.12.0, resetting WEL after every
    ignored erase or program and never setting WIP for one, its own
    choice where the datasheets are silent (HARNESS "The flash chip"); HW-83's chip, 0.6.0 to
    0.11.0, has no block protection.
- Sources: PUYA p. 15-16 (the two tables and note 2: an erase or program
  touching protected data is ignored), p. 24 (when WEL resets), p. 26-27
  (the bits), p. 40-43 (each erase and the page program: a protected one
  not carried out; the 32 KiB erase's WEL), p. 42 (chip erase); UCUN
  p. 9-10 (the bits), p. 10-11 (Table-6.0, Table-6.1 and
  note 2), p. 15 (when WEL resets), p. 25-29 (each erase and program),
  p. 28 (chip erase ignored if any block is protected).
- Standing: confirmed (PUYA, UCUN)
- Needed by: M7, BR-17 (Phase B); fwtest 0.12.0 (HARNESS.md, "The flash
  chip")

## 30. The code window's BAUD, its CON and its width (SR-17)

Read under the owner's request for SR-17 (2026-11-19, PROVENANCE P-502),
from m-bootloader at the commit HW-123 and HW-128 used (`src/platform.c`,
`src/boot.c`, `docs/SPEC.md` §3.4, §3.6, §5.3 and §7) and the SDK's
`WL82.h` (as HW-84), with the owner's start3 and start3b results from a
unit (HW-133). HW-132 adds to HW-128, and HW-134 supersedes HW-132 with
the unit's `CON` reading and the owner's give-back; HW-128 stands.

### HW-132: The window's BAUD and mode word as m-bootloader sets them, and what CON reads
- Fact: For the code window's controller (`JL_SFC`, `0x00040200`, HW-84):
  1. **`BAUD`** is at `0x00040204` (`JL_SFC` +4). The SDK marks it write
     only. In its give-back (HW-128 step 3) m-bootloader writes there the
     same divider it gives SPI0's `BAUD`: its built-in SPI divider, **1**.
     The order is `CON` = `0x00F00000`, `CON` = 0, `BAUD` = 1, then the
     mode word. Its built-in values (`docs/SPEC.md` §5.3) equal every known
     FM-1 configuration's `SPI` record, `4_1_0_0`: width 4, divider 1,
     output reads. m-bootloader reads no configuration for them.
  2. **The mode word written** is the width's output-read word with bits
     23-20 replaced by 9. m-bootloader writes the 9 as a constant. Its
     `docs/SPEC.md` gives it as the HSB clock in MHz times 45 / 1000,
     plus one, which is 9 at 180 MHz. So the word written is:
     - `0x00980381` at quad width (HW-128's `0x00280381` with 9 in bits
       23-20);
     - `0x00980281` at dual width;
     - `0x00900089` at single width.
     m-bootloader writes only output-read words. The other columns of
     `docs/SPEC.md`'s table are not verified on hardware.
  3. **The width it chooses:** quad (4) unless it falls back. Before the
     window is set up, at each start, it:
     - reads 32 bytes at single width;
     - sets QE (status 2 bit 1), up to three more tries if it doesn't
       stick, as HW-123 gives. Without QE it takes dual width;
     - reads the same 32 bytes at that width, halving the width (quad,
       dual, single) until they match.
     The width it ends with is the window's. A fallback shows as "SPI
     WIDTH FALLBACK" in its recovery menu, and an app at a narrower width
     runs markedly slower (its `docs/SPEC.md`). Nothing tells the app which
     width it got, except the mode word, if `CON` reads it back (item 4).
  4. **Whether `CON` reads back:** the SDK marks `CON` read and write;
     `BAUD`, `CODE` and `BASE_ADR` are write only. m-bootloader never
     reads `CON`, and no allowed written source says that a read returns
     the mode word last written. The owner relays (not taken as a fact
     here beyond what was read) that on the owner's unit, after
     m-bootloader's call, `CON` reads **`0x009803B5`**: start3b's "win"
     row, from a clear photo. start3's earlier photo (image `99e769ea…`,
     identity `FM-1_0.10.0-hw3`) gave `0x0098038?`, a digit uncertain.
     So `CON` reads back, but not as the quad word m-bootloader writes
     (`0x00980381`, item 2): bits 2, 4 and 5 read set. What those bits
     are, and whether the read differs from what the controller holds,
     no allowed source says.
  5. **Whether writing `CON` changes `BAUD`:** no allowed source says.
     m-bootloader writes `BAUD` after its two `CON` writes and before the
     mode word, every time, so a give-back in that order doesn't depend
     on it.
  6. Beyond HW-128's step 6, after setting the window cipher's control to
     1, m-bootloader sets bits 8 and 9 of `0x01EEE008` again, then does
     the `csync`. They are already set from step 5.
  So, by the owner's ruling, a give-back reads `CON` before the take and
  restores the value read, after `0x00F00000`, 0 and `BAUD` = 1, rather
  than writing m-bootloader's word. Writing `0x00980381` itself, as
  before, would leave bits 2, 4 and 5 clear where the unit had them set;
  that it works on the unit is not shown.
- Sources: MB `src/platform.c` (`hal_xip`: the writes, their order, the
  constant 9, the output-read words; `flash_init` and `flash_quad`: the
  width checks), `src/boot.c` (the built-in values, the width carried to
  `hal_xip`, the fallback line), `docs/SPEC.md` §3.4 (a fallback is
  visible; single width is markedly slower), §3.6 (the mode word table,
  bits 23-20), §5.3 (the built-in values, `SPI` `4_1_0_0`), §7 (the
  start's flash steps); SDK `WL82.h` lines 39-44 (`JL_SFC`, which
  registers are read-write and which write-only); the owner's start3 and
  start3b results (item 4, relayed).
- Standing: superseded by HW-134
- Needed by: M7, BR-17 (Phase B)

### HW-134: The window's BAUD and mode word, what CON reads, and the give-back (supersedes HW-132)
- Fact: As HW-132, corrected by the owner's start3b result and rulings
  (item 4 and the give-back). For the code window's controller (`JL_SFC`, `0x00040200`, HW-84):
  1. **`BAUD`** is at `0x00040204` (`JL_SFC` +4). The SDK marks it write
     only. In its give-back (HW-128 step 3) m-bootloader writes there the
     same divider it gives SPI0's `BAUD`: its built-in SPI divider, **1**.
     The order is `CON` = `0x00F00000`, `CON` = 0, `BAUD` = 1, then the
     mode word. Its built-in values (`docs/SPEC.md` §5.3) equal every known
     FM-1 configuration's `SPI` record, `4_1_0_0`: width 4, divider 1,
     output reads. m-bootloader reads no configuration for them.
  2. **The mode word written** is the width's output-read word with bits
     23-20 replaced by 9. m-bootloader writes the 9 as a constant. Its
     `docs/SPEC.md` gives it as the HSB clock in MHz times 45 / 1000,
     plus one, which is 9 at 180 MHz. So the word written is:
     - `0x00980381` at quad width (HW-128's `0x00280381` with 9 in bits
       23-20);
     - `0x00980281` at dual width;
     - `0x00900089` at single width.
     m-bootloader writes only output-read words. The other columns of
     `docs/SPEC.md`'s table are not verified on hardware.
  3. **The width it chooses:** quad (4) unless it falls back. Before the
     window is set up, at each start, it:
     - reads 32 bytes at single width;
     - sets QE (status 2 bit 1), up to three more tries if it doesn't
       stick, as HW-123 gives. Without QE it takes dual width;
     - reads the same 32 bytes at that width, halving the width (quad,
       dual, single) until they match.
     The width it ends with is the window's. A fallback shows as "SPI
     WIDTH FALLBACK" in its recovery menu, and an app at a narrower width
     runs markedly slower (its `docs/SPEC.md`). Nothing tells the app which
     width it got, except the mode word, if `CON` reads it back (item 4).
  4. **Whether `CON` reads back:** the SDK marks `CON` read and write;
     `BAUD`, `CODE` and `BASE_ADR` are write only. m-bootloader never
     reads `CON`, and no allowed written source says that a read returns
     the mode word last written. On the owner's unit, after
     m-bootloader's call, `CON` reads **`0x009803B5`** (HW-133). So it
     reads back, but not as the quad word m-bootloader writes
     (`0x00980381`, item 2): bits 2, 4 and 5 read set. What those bits
     are, and whether the read differs from what the controller holds,
     no source says.
  5. **Whether writing `CON` changes `BAUD`:** no allowed source says.
     m-bootloader writes `BAUD` after its two `CON` writes and before the
     mode word, every time, so a give-back in that order doesn't depend
     on it.
  6. Beyond HW-128's step 6, after setting the window cipher's control to
     1, m-bootloader sets bits 8 and 9 of `0x01EEE008` again, then does
     the `csync`. They are already set from step 5.
  So, by the owner's rulings (2026-11-19), a give-back reads `CON` before
  the take, then writes `CON` = `0x00F00000`, `CON` = 0, `BAUD` = 1 and
  `CON` = the value read, in m-bootloader's order: `BAUD` can't be read
  back, so the give-back follows m-bootloader's sequence for it. Writing
  `0x00980381` instead would leave bits 2, 4 and 5 clear where the unit
  had them set; that it works on the unit is not shown.
- Sources: MB `src/platform.c` (`hal_xip`: the writes, their order, the
  constant 9, the output-read words; `flash_init` and `flash_quad`: the
  width checks), `src/boot.c` (the built-in values, the width carried to
  `hal_xip`, the fallback line), `docs/SPEC.md` §3.4 (a fallback is
  visible; single width is markedly slower), §3.6 (the mode word table,
  bits 23-20), §5.3 (the built-in values, `SPI` `4_1_0_0`), §7 (the
  start's flash steps); SDK `WL82.h` lines 39-44 (`JL_SFC`, which
  registers are read-write and which write-only); UNIT (item 4, HW-133);
  the owner's rulings of 2026-11-19 (the give-back's order,
  docs/prompts/spec-start3b.md and spec-unit-facts.md).
- Standing: confirmed (MB, SDK, UNIT; whether a `CON` write changes
  `BAUD`, not shown)
- Needed by: M7, BR-17 (Phase B)

## 31. What the owner's unit shows (start3, start3b)

Observed by the owner on the owner's unit and relayed, recorded as facts
by the owner's ruling of 2026-11-19 (source UNIT). The builds are this
repository's own test builds start3 (image `99e769ea…`, identity
`FM-1_0.10.0-hw3`) and start3b (clean's #195 at `7c7276a2`), each started
by m-bootloader (MB).

### HW-133: The window's CON, the store, core 1, MASTER and KNOB1 on the unit (Q-7, Q-8, Q-17, Q-22)
- Fact: On the owner's unit, started by m-bootloader:
  1. **The window's `CON`** (`0x00040200`, HW-84) reads `0x009803B5`
     after m-bootloader's call (start3b's "win" row, a clear photo;
     start3's photo gave `0x0098038?`, a digit unreadable). It is not
     the quad word m-bootloader writes, `0x00980381` (HW-134).
  2. **The flash round trip** works within one run: the flash taken from
     the code window, ID `856014`, status 1 `00`, status 2 `02`, and the
     window given back, with the app running on from it (start3 and
     start3b).
  3. **The store's power-on counter** goes up by one at each power-on
     (start3b), so a save to the flash survives power-off and reads back
     at the next start.
  4. **Core 1** does not run after m-bootloader's call when released as
     HW-9 gives: its counter stays 0, and `C1_CON` (`0x01EEE004`) reads
     `0x01000002` afterwards (start3b). What it needs to run then is
     open (Q-17).
  5. **MASTER** (the pot, PANEL) is SARADC channel 4 (PB6, HW-129).
  6. **KNOB1** is in the key matrix at columns 8 and 9 (HW-117).
- Sources: UNIT: start3 and start3b on the owner's unit, relayed by the
  owner on 2026-11-19 (docs/prompts/spec-start3-unit.md,
  docs/prompts/spec-start3b.md); recorded as facts by the owner's ruling
  of 2026-11-19 (docs/prompts/spec-unit-facts.md). MB for what
  m-bootloader writes (HW-134).
- Standing: confirmed (UNIT; one unit, flash part `856014`)
- Needed by: M7, BR-17 (Phase B)

## 32. Releasing core 1 after m-bootloader's call (SR-18)

Read under the owner's request for SR-18 (2026-11-19, PROVENANCE P-503),
from FM-1-RE's boot document (an allowed boot-chain document; facts only,
never code, under the owner's spec-1027 ruling, as HW-9 used it), the
SDK's `csfr.h` and `WL82.h` (vendored), m-bootloader (as HW-123) and
HW-133's unit fact. HW-135 adds to HW-9, which stands; HW-9's release is
the whole release only in fwtest.

### HW-135: What the chip's release of core 1 takes, beyond HW-9 (Q-17)
- Fact: On the chip, FM-1-RE (medium confidence) gives the FM-1's
  firmware releasing core 1 with these register steps, in this order:
  1. core 1's start address in the word at `0x01C7FFF8` (HW-9);
  2. bit 3 of `JL_CLOCK->SYS_DIV` (`0x00010008`, HW-53) set;
  3. bit 3 of `C1_CON` (`0x01EEE004`) set, then bit 1 of `C1_CON`
     cleared;
  4. after core 1 has started (the firmware waits for a sign from core 1
     in RAM), `SYS_DIV` put back as it was before step 2.
  HW-9 gives steps 1 and the first half of 3 only. On the owner's unit,
  after m-bootloader's call, a release by HW-9 alone left core 1 not
  running, with `C1_CON` reading `0x01000002`: bit 1 still set, bit 3
  clear, bit 24 set (HW-133). That fits step 3's clear of bit 1 being
  needed, but no source says so; a probe on a unit settles it. Further:
  - **`C1_CON`'s bits:** the SDK names the register (read-write) but none
    of its bits. What bits 1 and 24 are, and whether bit 3 reads back
    once set or clears itself, no allowed source says.
  - **`SYS_DIV` bit 3:** FM-1-RE is the only source; the SDK switches its
    definitions of `SYS_DIV`'s fields off (HW-53). m-bootloader writes
    `SYS_DIV` only to set its bus dividers (bits 8-10 and 16-17, keeping
    the other bits as they were), so it leaves bit 3 as the chip had it.
    A release that sets bit 3 puts back the whole value it read, so the
    dividers m-bootloader set are kept.
  - **Anything else:** no allowed source names a clock gate, reset or
    power bit, or a cache or protection set-up for core 1 beyond these
    steps. m-bootloader never starts core 1 (HW-130).
  - **What core 0 sees of core 1's RAM stores:** open (Q-18). FM-1-RE's
    wait for a sign from core 1 in RAM suggests core 0 sees at least
    that store; with what cache operation, if any, is not given.
  - **In fwtest** core 1 starts at step 2 or at `C1_CON` bit 3, whichever
    comes first, once only (HW-10); fwtest can't show which step the
    chip needs.
- Sources: RE `docs/io/01-boot.md` §5.2 (the release's register steps
  and their order, `[med]`); SDK `csfr.h` lines 106-112 (`corex2`: `C1_CON`
  read-write, no bits named), `WL82.h` (`JL_CLOCK`, HW-53); MB
  `src/platform.c` (its `SYS_DIV` writes: the dividers only) and
  `docs/SPEC.md` §2.2 (the clock dividers' bits); UNIT (HW-133 item 4);
  HW-9, HW-10, HW-53, HW-130.
- Standing: confirmed (RE, MB, UNIT; whether step 2 or the clear of
  bit 1 is what core 1 lacked on the unit, the meaning of `C1_CON`'s
  bits, and core 0's view of core 1's stores, not shown)
- Needed by: M1, BR-17 (Phase B)

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
  *Answered in part by session spec-sr14 (HW-119):* the clock m-bootloader
  starts an app with (system 360 MHz, buses 180 and 60 MHz). The PLL
  fields and the steps of a safe change are left to the bootloader's own
  specification; this spec doesn't take them.
- **Q-3. TIMER0-3 prescaler settings in fwtest.** The SDK gives the chip's
  table (HW-48); fwtest's settings other than 0 and 2 were not measured.
  Measure with a black-box test, or ask.
  *Answered in part by session spec-sr16 (HW-125):* on the chip `CON`
  bits 7-4 prescale the input clock, bit 3 picks the 24 MHz oscillator
  instead of the 60 MHz LSB, bits 1-0 the mode.
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
  *Answered in part by session spec-sr14 (HW-115, HW-116):* the chip
  select (PC7, active low), no reset pin driven, the backlight (PA2,
  active low), the pins' set-up, a `BAUD` near 12 MHz, `MADCTL` `00`
  with no row offset and inversion on. Still open: `CON`'s other mode
  bits, and which orientation shows the picture upright.
- **Q-7. The panel's wiring on the chip.** Whether the board's key matrix,
  encoders and LEDs are wired as fwtest presents them (HW-33, HW-34,
  HW-38, HW-42: the pins, the shift registers, an LED for every key, which
  physical turn is "clockwise"); pull-ups, directions and drive for the
  pins, LED polarity and current. fwtest needs no pin set-up.
  *Answered in part by session spec-sr14 (HW-117, HW-118):* the shift
  registers' pins, the rows' pins and pull-ups, PA2's role, four keys'
  columns and rows, the LED lines and their polarity. Still open: the
  other keys' columns and rows, the encoders, and LED current.
  *Session spec-sr16 (HW-129):* no allowed source gives the rest of the
  matrix or the encoders' pins; probes on a unit.
  *Answered in part by session spec-unit-facts (HW-133):* KNOB1 is at
  matrix columns 8 and 9. A note, not a fact: PRESETS looks like an
  encoder read through an ADC channel (start3b, relayed); a fact once a
  build names the channel.
- **Q-8. The other ADC channels.** What channel 3 and the other channels
  carry on the board (fwtest gives them fixed values).
  *Session spec-sr16 (HW-129):* the SDK maps channel 3 to PB1 and 4 to
  PB6, and FM-1-RE says the FM-1's firmware reads both; which is the pot
  stays open.
  *Answered in part by session spec-unit-facts (HW-133):* MASTER is
  channel 4. A note, not a fact: PRESETS looks like an encoder read
  through an ADC channel, which one not yet named (start3b, relayed).
- **Q-9. Audio on the chip.** How `JL_ALNK0`'s output reaches the DAC or
  codec on real hardware, which bits of each word it uses, its clock set-up
  and true rate, and the analog set-up (FM-1-RE's audio document names DAC
  registers at `0x00012F00`; not used here).
- **Q-10. Interrupt details on the chip.** Whether the chip switches
  stacks on an interrupt from user mode exactly as HW-3 says; its nesting
  rules and choice among pending sources (HW-22); whether the two cores
  share one vector table; what `idle` does with interrupts masked (HW-24).
  The toolchain's interrupt attribute works in fwtest.
  *Answered in part by session spec-sr16 (HW-126):* after m-bootloader's
  call an app sets both `ssp` and `sp` before enabling interrupts; which
  one an interrupt uses, and `idle`, stay open.
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
  *Narrowed by session spec-sr16 (HW-125):* the SDK's handler acknowledges
  with bit 14 and nothing else, and m-bootloader stops a timer before
  reusing it; whether the acknowledge restarts the count stays open.
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
  *Session spec-unit-facts (HW-133):* after m-bootloader's call, core 1
  does not run when released as HW-9 gives (`C1_CON` reads
  `0x01000002`). What it needs then is still open.
  *Session spec-sr18 (HW-135):* the chip's release, as FM-1-RE gives it,
  also sets `SYS_DIV` bit 3 for the release and clears `C1_CON` bit 1.
  Which of them core 1 needs is settled by a probe on a unit.
- **Q-18. Memory seen across the cores on the chip.** Whether main RAM is
  cached, and whether a plain store by one core is seen by the other's
  next load without `csync` or a cache operation (HW-65). Settled by a
  probe on real hardware.
  *Session spec-sr18 (HW-135):* still open. A core 1 probe should show
  that core 1 runs by a sign that doesn't rest on this.
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
  *Session spec-sr16 (HW-130):* still open; a probe on a unit.
- **Q-21. The FM-1's flash part.** Which part the FM-1 carries: its
  JEDEC ID read on a unit (fwtest answers `85 60 14`, the Puya P25Q80H,
  HW-76), or the marking on the chip. If it differs, HW-77's times and
  HW-78's rules need that part's datasheet. The SDK lists an AC791N
  package with 1 MiB of flash inside it (`7911B8`, "内置flash",
  `apps/demo/demo_uvc/board/wl82/board_7911B_cfg.h` lines 11-15), so the
  FM-1's flash may have no package of its own to photograph. Settled by a
  probe on real hardware or a photo of the board.
  *Answered in part by session spec-sr15 (HW-120 to HW-122):* there are
  two parts, the P25Q80H (`85 60 14`) and, on units sold since autumn
  2026, UCUN's UC25HQ80 (`B3 60 14`), which part a unit carries only as
  the owner relays it; for the commands a store sends only the ID
  differs. Open: the ID read by our own firmware on a unit of each kind.
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
  *Answered in part by session spec-sr16 (HW-128):* m-bootloader's take
  and give-back of the flash, SPI0's clock, and the cache invalidation;
  the round trip within one run of an app is not shown.
  *Answered in part by session spec-unit-facts (HW-133):* on the unit
  the round trip within one run works, and the store's counter survives
  power-off; what `CON` reads and how to give it back, HW-134 and
  HW-133.
- **Q-23. Write protection on the FM-1's flash.** Whether the status
  register's block-protect bits (HW-78) are set on a shipped unit or by
  the loader, which would make erases and programs in the protected range
  silently do nothing. Read status register 1 on a unit; the SDK's own
  write-protect switch is off by default. Settled by a probe on real
  hardware.
  *Answered in part by session spec-sr15 (HW-123):* both parts are
  delivered unprotected, and m-bootloader clears BP0-BP4 and CMP before
  its own writes and leaves them clear, so a unit written through it has
  nothing protected. Open: a unit's status registers read by our own
  firmware.
- **Q-24. What an update rewrites.** Which regions a stock-style update
  erases or writes beyond its flash image (`0x00000`-`0x93FFF`, HW-80):
  where in the VM region it stages its loader, whether its `USR` entry
  rewrites `0xEA000`-`0xFBFFF`, and whether our own packaging (M9) can
  mark a region to be kept. Decides whether stored patches survive an
  update. Settled in M9, from FM-1-RE's update documents and the SDK's
  packaging settings (HW-80's sources), or by a test on real hardware.
- **Q-25. The package's fields no load path reads.** Where the package
  header's list CRC and image size sit and what they cover; an entry's
  name, CRC and other fields; what the flash header's fields must hold
  for the chip; the directory heads' attributes other than `0x81` and
  `0x82`. The allowed sources name these fields but do not place or
  define them, and none of the emulated load paths reads them (HW-88,
  HW-89, HW-93). They could be learned from a stock package, which no
  session opens, or from the SDK's packaging tools run on our own input
  (M10, the owner's answer 4 in M9-PLAN.md). A packager fills them by the
  head rule of HW-87 and HW-89 where that rule applies, and records the
  rest as unknown.
  *Answered in part by session spec-br17-package (HW-103 to HW-107):*
  the list CRC, the image size, the entries' fields and the flash
  header's fields as JieLi's tools write them. Still open: header bytes
  10-15 (4 and `0x200`), `blimit.bin`'s content, six bytes of
  `tail.bin`, the 64 bytes after the app area, and the `.fwsc` blocks'
  origin (HW-107).
  *Then by session spec-br17-tools (HW-109 to HW-113):* what the FM-1's
  installer reads and checks. Bytes 10-15 hold 4 and `0x200` in M-VAVE's
  packages, and no checker reads them. `blimit.bin`, `tail.bin` and the
  bytes after the area are read by no checker found. The `.fwsc` blocks
  are M-VAVE's (HW-109).
- **Q-26. What the chip's loaders and updater check.** What the mask ROM
  and `uboot.boot` check before running the next step (CRCs, the key
  block, the directory), whether the chip key is the same on every unit,
  and what the stock updater and the update loader `ota.bin` accept
  (HW-92; FM-1-RE has not found all of the updater's check). Settled only
  on a unit (Phase B; M9-PLAN.md section 5) or by JieLi's documentation.
  *Narrowed by session spec-br17-package:* the tools write a CRC on the
  header, the list, each entry, each head and each head's data, and a
  key block from which the key `0xFFFF` follows without a key file
  (HW-104, HW-105, HW-108). Which of these a loader or an installer
  checks, whether a unit runs an app scrambled with `0xFFFF`, and whether
  any FM-1 updater takes an app-area-only file (HW-106) stays open: only
  a unit settles them.
  *Answered in large part by session spec-br17-tools:* m-flasher's
  checks (HW-109) and writes (HW-110), the key's source on the chip and
  how installers check it (HW-111), m-bootloader's checked start
  (HW-112). Still open: what the mask ROM and JieLi's own `uboot.boot`
  check beyond HW-112's description, M-VAVE's updater's checks beyond
  HW-113, and whether a unit's key is ever other than `0x980F`.
- **Q-27. A store of its own base on the chip.** Whether the chip stores
  the base as it was for `[++rN=k] = rN`, `[rN++=k] = rN` and their byte
  and halfword forms, as the toolchain's compiler relies on and fwtest
  0.9.0 does (HW-95), or the moved base, or something else, for a number
  and a register step alike. No allowed source searched settles it: the
  toolchain ships no instruction documentation, and the SDK's sources
  searched (HW-95) hold no assembly using them; its prebuilt libraries
  were not disassembled. Settled by a probe on real hardware (Phase B; M9-PLAN.md
  section 5). Related: a write-back load into its own base, and a block
  move whose base is in its list (Q-19).

- **Q-28. The float conversions at their edges.** What the chip gives for
  a NaN or an out-of-range value converted to an integer by the rounding
  `ftoi` / `ftou` forms (fwtest saturates, and gives 0 for a NaN, as for
  the truncating ones, HW-63), which NaN the rounding to integral forms
  return, how `ftof` to half precision rounds and whether it keeps
  subnormals (fwtest: to nearest even, kept, overflow to infinity, as C's
  default the compiler relies on), and whether it leaves rD's high half
  (fwtest: kept; the compiler uses only the low half). HW-97.
- **Q-29. What sets the flag branches' conditions.** Which instructions
  set what `ifeq` .. `ifle` test (HW-98): fwtest takes the last `fcmp`'s
  operands, compared as that family's float compare, and after a `testset`
  only eq / ne (its flag); whether other instructions (add, subtract,
  compares) set them, and what `testset` leaves for the others, the
  toolchain does not show.
- **Q-30. Shifts by 32 or more, in memory.** What `[rB+#i] <<= rS` and its
  `>>=`, `>>>=` and `<<<=` do with an amount of 32 or more (fwtest: bits
  0-4 of it, as its register shifts), and whether `<<<=` saturates as the
  register form the qasl builtin gives (fwtest: it does). HW-99.
- **Q-31. The memory multiply-accumulates.** For `RR op= [rA ++= x]*y`,
  `h[..]` and their two-load forms (48 forms, assembler only; HW-102):
  how (s) and (u) apply to the halfword's extension and to the product,
  whether the increments come after the loads, in which order two
  increments of one register apply, and which wins when the pair is a base.
  fwtest 0.10.0: (s) and (u) both, addresses from the registers before,
  the first increment then the second, the pair written last.
- **Q-32. Operations the toolchain names but does not define.** The
  rounding pair shifts `R = RR >> n (even|round|up|zero)` and `>>>`
  (fwtest 0.10.0: to nearest with ties to even, to nearest with ties up,
  toward +inf, toward zero, then saturated as the plain forms; HW-102),
  `rev16` (fwtest: the halves swapped), and `R = R >< R`, `RR ><= R`
  (with or without `(sat)`), `<c>` (also the compiler's
  `__builtin_pi32v2_rotrc`: a function of its two arguments alone, as
  the compiler declares and combines it, HW-100) and `copex`, which fwtest
  does not run. The compiler folds none of them and emits none from C.
- **Q-33. The `npc` loads.** What `R = [npc + R]` and `R = [npc + #i]`
  load from (fwtest 0.10.0: the next instruction's address plus the
  offset); the compiler's position-independent code uses r15 instead.
- **Q-34. System instructions and unmodelled registers.** What `bkpt`,
  `hbkpt`, `swi`, `syscall`, `trigger`, `rte`, `rtx`, `rtns`, `rtss`,
  `rthw`, `sevg`, `sevl`, `wfe`, `gotoss` and `ifs2ns` do, the registers
  pc, cnum, uspn, icfgn and icfgs as moved, pushed and popped, and what
  the pushes marked `(c)` clear. The compiler emits `bkpt` for
  `__builtin_trap` and `syscall` and `trigger` for their builtins. fwtest
  ends a run on `bkpt` as a trap and on the others as an instruction it
  does not run.
- **Q-35. Halves, fields and special registers at their edges.** What
  `sat8 (u)` gives for a negative half (fwtest: 0, as the 16-bit `(u)` clamp of a word gives for a
  negative word), what the field forms give for l = 0 or p + l over 32
  (fwtest: as the immediate forms, l = 0 the whole word, bits shifted out
  lost), and in which order the 4-byte special-register push and pop store
  the registers and what pushing or popping `sp` itself gives (fwtest: the
  highest number at the highest address, as the 2-byte forms; `sp` as it
  is when its turn comes). HW-101.