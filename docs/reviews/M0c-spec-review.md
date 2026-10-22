<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# M0c: review of docs/HARDWARE-SPEC.md before release

- Reviewed: the draft of 2026-10-22 (47 entries, 12 open questions), before
  the firmware side read it (R-SPEC-3).
- Reviewer: a fresh subagent of session M0c (`claude-opus-5-5`), given only
  `docs/HARDWARE-SPEC.md`, `CONTRIBUTING.md` and sections 1 and 2 of
  docs/prompts/M0c.md, and told to open nothing else (no other file, no
  git, no web). Its report is below, unedited. The response that follows it
  says what was changed for each finding.

## The reviewer's report

# M0c review of docs/HARDWARE-SPEC.md

## Summary

I read only `docs/HARDWARE-SPEC.md` and `CONTRIBUTING.md`, using the rules in sections 1 and 2 of the M0c prompt. The spec has 47 entries (HW-1 to HW-47) and 12 open questions (Q-1 to Q-12).

The document is well structured. I found no code, pseudo-code or init sequence copied from source, and nothing that is plainly taken from forbidden material. It is not ready to release yet:

- **One wrong command code:** HW-31 gives `0x22` as inversion off.
- **One unstated clash in the memory map:** the core 1 start-address word is also the vector of software interrupt 6.
- **Unclear scope in the key, LED and encoder entries:** they read as facts about the chip, but their only sources are fwtest experiments.
- **Smaller issues:** some "confirmed" standings cover more than the experiment tested, and three facts lean on how the stock firmware behaves rather than on hardware.

Limits of this review: I could not compare identifiers against `vendor/emulator/`, so C-SEP-TERMS remains the check for category 2. I could not open the cited SDK, RE or datasheet files, so citations were checked for consistency, not content. The `0x20`/`0x21` codes in HW-31 come from my own knowledge of the ST7789V and should be checked against DS before editing.

## Findings

| ID | Cat. | Severity | Problem | Suggested fix |
|----|------|----------|---------|---------------|
| HW-31 | 5 | must-fix | "inversion on/off (`0x21`/`0x22`)". On the ST7789V, INVOFF is `0x20` and INVON is `0x21`; `0x22` is not inversion off. No DS page is cited for these commands, `0x28`/`0x29` or `0x36`. | Correct this to `0x21`/`0x20`, checking DS first, and cite the DS pages. If fwtest really treats `0x22` as inversion off, say that it is a quirk of fwtest. Because this entry is new, a correction now is fine; after release it needs a new ID. |
| HW-9, HW-18, HW-19, HW-6 | 5 | must-fix | Core 1's start word `0x01C7FFF8` is `0x01C7FE00 + 4 × 126`, so it is also the vector of source 126 (software interrupt 6, HW-19). No entry says so. A firmware that uses software interrupt 6, or fills the whole table, would overwrite the core 1 start address, or the reverse. | Say this in HW-9 and HW-18. Also say whether source 127 (`0x01C7FFFC`) is free. |
| HW-33, HW-34, HW-38, HW-42 | 3, 5 | must-fix | The pins (PA1/PA3/PA4, PA0/PA5-8/PB7, PA9/PA10/PH6/PH9), "two cascaded 8-bit shift registers" and the contact positions are written without "In fwtest". The spec's own convention then makes them hold on the chip too. Their only sources are E-6 and E-7, and the SDK lines cited give only the port addresses. For the chip, the real source is the emulator model. | Begin each fact with "In fwtest". Add an open question asking whether the chip has the same wiring, or cite an RE hardware document if one covers it. HW-42 should also say whether the real board has an LED for every key. |
| HW-11 | 4, 3 | should-fix | "the system clock runs at 240 MHz from a PLL" rests on RE's description of what the stock firmware sets up, which is software behaviour, not a hardware fact. "HARNESS for fwtest" is not a confirming source under the standing definitions. The entry also doesn't say whether core 1 runs at one instruction per cycle too. | Give the 24 MHz crystal as the hardware fact, and give 240 MHz as a supported rate, citing SDK or DS if possible. Say what the 1-instruction-per-cycle figure rests on (HARNESS or an experiment) and cover core 1. |
| HW-44, HW-45 | 4 | should-fix | "the synth's output is driven through this block" and "the synth runs at 44 118 Hz" (RE audio §3.4, §5.2, §5.3) describe what the stock firmware does. | Cite RE only for register semantics (`CON2` bit 7, `CON0` bit 15). Rest the rate on E-9 alone, with chip set-up left to Q-9. |
| HW-37 | 4, 2 | should-fix | "14 is F3 ... 40 is G5" gives octave numbers, which are a software choice of pitch, not a printed or hardware fact. "the emulator's own name for it differs from the printed `SEL`" reveals how the emulator names things. | Give the key order by position, leftmost to rightmost, plus lower or raised. Drop the parenthetical. |
| HW-36 | 3, 4 | should-fix | The first PANEL source is a screenshot of the F-Emulator app, part of the same project as the forbidden `crates/` and `fm1-sid/`, and not on CONTRIBUTING's list of permitted sources. The M-VAVE photo is not archived and has no hash. | Make the M-VAVE photo the only source, and record a hash or an archived copy reference in P-12. Drop the screenshot or mark it as a non-source. |
| HW-47 | 5 | should-fix | "Needed by: M7". The rules say to include only what M0d to M4 and open spec requests need, and none are open. The SPI NOR commands are cited to RE's storage document, which describes what the stock firmware uses. | Remove the entry until M7 makes a spec request. HW-5 can stand without it. If it is kept, cite a flash datasheet for the commands. |
| Q-2 | 4 | should-fix | "Settled by the SDK's clock code, which is in prebuilt libraries". CONTRIBUTING forbids the SDK's prebuilt libraries, so this points the firmware side at off-limits material. | Say instead: "settled by a spec request from permitted sources, or a hardware experiment". |
| HW-2 | 3 | should-fix | "every other register reads 0" is marked confirmed (E-1), but "r1 could not be observed". | Say that r1 rests on HARNESS only. |
| HW-5 | 3, 5 | should-fix | "Writes to the window are ignored" was not tested in E-1. It is also unclear whether the image itself sits at chip offset `0x4000` or covers it: HW-47 says the window shows "the image's own changes". | Cite HARNESS for the ignored writes. State exactly how the image relates to chip offsets in the window. |
| HW-6 | 5 | should-fix | "ends the program's RAM 128 bytes below `0x01C7FE00`, less a 52-byte boot-information area" is ambiguous. | Give the resulting end address, say where the 52-byte area is, and explain why the firmware should care. |
| HW-7 | 5 | should-fix | "zero at the start" conflicts with HW-4's block at `0x01C7FC00`. | Add "except the block of HW-4". |
| HW-9 | 3, 4 | should-fix | "The start address must be in the code window or in RAM" has no source. It is also unclear whether the start word is a hardware feature or a loader or SDK convention (RE calls it a "mailbox"). | Cite a source or mark it emulator-only. Say whether a raw image on the chip can depend on it, or add it to Q-11. |
| HW-13, HW-15 | 3 | should-fix | E-3 measures TIMER4 against TIMER5, whose 6 MHz clock comes from the emulator model. The test shows only the 4:1 ratio, not the absolute 24 MHz. HW-15 also doesn't say whether TIMER5 has the `CON` bits 4-7 prescaler that HW-16 gives TIMER0-3. | Name an independent time reference for E-3, or downgrade. Say how TIMER5's prescaler bits behave. |
| HW-16 | 3 | should-fix | "Prescaler setting 0 divides by 1" was not tested: E-3 used setting 2 only. | Test setting 0 or mark it emulator-only. |
| HW-17, HW-23 | 5 | should-fix | The `TTMR_*` and `ILAT_SET`/`ILAT_CLR` addresses are given "for core 0" only, although HW-20 gives both cores. | Give core 1's addresses. |
| HW-18 | 5 | should-fix | It isn't said whether the two cores share one vector table. | State it, or add it to Q-10. |
| HW-22 | 5 | should-fix | "only once that handler has saved `reti` on its stack" doesn't say what the core can observe. The firmware can't tell what makes a handler nestable. | Describe the condition the hardware can see, or keep only "nesting: see Q-10". |
| HW-24 | 3 | should-fix | "`idle` stops the core until an interrupt is pending" reads as true on the chip, but it rests on fwtest only. It also doesn't say whether `idle` wakes while the gates of HW-21 are closed. | Cite SDK use of `idle` or limit it to fwtest. Cover the masked case. |
| HW-29, HW-30 | 5, 3 | should-fix | HW-29 doesn't say whether it holds on the chip, where SPI1 needs `CON`/`BAUD` and pin set-up. HW-30 relies on RE's "medium confidence" yet is marked plainly confirmed, and leaves out what RE says about bit 7. | Limit the "finishes at once" part to fwtest, and say that the chip needs SPI set-up (Q-6). Note the medium confidence and point PC7 to Q-6. |
| HW-32 | 5 | should-fix | Missing ST7789V timing: wait 120 ms after a software reset before sleep out. The timings come from the ST7789V datasheet, while HW-27 says only "ST7789-family". | Add the timing, citing DS page 163. Say which controller variant is assumed. |
| HW-38 | 5 | should-fix | "Clockwise" is fwtest's input-script direction, not a confirmed physical direction. | Say "the direction HARNESS calls clockwise". |
| HW-40, HW-41 | 5 | should-fix | Unclear whether "The pot is channel 4" holds on the chip. In HW-41, acknowledging "without bit 4" clears the enable bit, and the entry doesn't say whether the ADC must then be enabled again. | Say what applies on the chip, or point to Q-8. Make the effect on bit 4 explicit. |
| HW-26 | 3 | note | `--watchdog` was not exercised by E-1 or E-3. "a RAM marker works on both" doesn't say how it can be seen on the chip. | Cite HARNESS for the watchdog. Clarify what "works" means on the chip. |
| HW-10 | 5 | note | The "Needed by" (M1) differs from HW-9 (M0d). The release through `SYS_DIV` bit 3 is useful mainly as a warning. | Write it as a warning to avoid that bit, or align the milestones. |
| HW-19 | 5 | note | `SPI2` (37) is used nowhere else. "`ALNK0`" differs from the SDK's `IRQ_ALNK_IDX`. TIMER4 is listed as source 62, but HW-14 says it raises no interrupt in fwtest. | Trim SPI2 and cross-reference HW-14. |
| HW-21 | 5 | note | The special register `icfg` and the words `ICFG00` to `ICFG31` have nearly the same names. The `sti` gate's state at entry isn't shown by HW-2. | Point out the name clash. Say what the closed `sti` gate rests on. |
| HW-44 | 5 | note | "24-bit signed sample in its low bits" doesn't match `0x01000000` clamping to 32767, which shows fwtest uses the whole 32-bit word. | Say that fwtest shifts the full word arithmetically. |
| General | 3 | note | HARNESS is the spec side's own description of the emulator, not an independent source, yet several "confirmed" entries rest partly on it. | List in each entry which parts the E-n experiment tested. |

## Entries with no problems found

HW-1, HW-3, HW-4, HW-8, HW-12, HW-14, HW-20, HW-25, HW-27, HW-28, HW-35 (the table is a full, consistent record of results: 41 keys, matching HW-37 and HW-38), HW-39, HW-43, HW-46. Open questions Q-1 and Q-3 to Q-12 are fine; Q-6, Q-7, Q-10 and Q-11 should be widened as the findings above suggest.

## Response (session M0c)

The IDs were not yet released, so the entries were corrected in place
(no superseded entries were needed). Every finding was handled:

| Finding | What changed |
|---------|--------------|
| HW-31 inversion code | Checked against DS: `INVOFF` is `0x20` (page 188), `INVON` `0x21` (page 190). HW-31 now says `0x20`/`0x21`, and cites DS pages for `DISPOFF`/`DISPON` (194-196) and `MADCTL` (215) too. fwtest's handling of those commands doesn't change a capture, so nothing about it is fwtest-specific. |
| Core 1's start word is source 126's vector | HW-9 and HW-18 say so, with the rule to follow; HW-18 says source 127's slot has no other known use. |
| Panel wiring scoped to fwtest | HW-33, HW-34, HW-35, HW-38 and HW-42 now say "In fwtest". Q-7 is widened to the board's wiring (pins, shift registers, an LED for every key, physical turn direction). |
| HW-11 clocks | 240 MHz is no longer claimed for the chip. The fact is the 24 MHz crystal (RE §5.2) and fwtest's fixed rate (HARNESS), with core 1 covered (emulator model). Supported rates and set-up are in Q-2. |
| HW-44, HW-45 audio and the stock firmware | RE is cited only for the meaning of `CON2` bit 7 and `CON0` bit 15. The rate rests on E-9 alone. Q-9 is widened (bits used, clock, true rate). |
| HW-37 octave names and the emulator's name | Replaced by the keys' order from left to right, lower and raised interleaved. The parenthetical is gone. |
| HW-36 the app screenshot as a source | Not changed: the owner chose both sources and asked for the screenshot to be committed as a secondary source (CONTRIBUTING lets the owner approve sources; PROVENANCE P-12 logs both). The M-VAVE photo's SHA-256 is now in the Sources table as well as in P-12. Only the printed labels, where both agree, are taken. |
| HW-47 flash, M7 only | Kept: the milestone prompt asks for flash "only as far as M7 will need", marked later. It is now headed "in fwtest", marked preliminary, cites RE only for SPI0 and its `CON` bits, and rests the commands on the emulator model, with a datasheet left to M7's spec request. |
| Q-2 points at prebuilt libraries | Now "a spec request answered from permitted sources, or an experiment on hardware". |
| HW-2 r1 | Says r1 rests on HARNESS only. |
| HW-5 | Cites HARNESS for ignored writes, and says the image is written into the chip at offset `0x4000`, so the window starts with the image and continues with the chip. |
| HW-6 | Gives the SDK's reserved area (`0x01C7FD4C` to `0x01C7FDFF`), what it is for, and why to keep out of it. |
| HW-7 | "all zero at the start except the block of HW-4". |
| HW-9 code window or RAM | Moved to HW-10 (emulator-only); Q-11 asks whether a raw image on the chip can release core 1 this way. |
| HW-13, HW-15 TIMER4's absolute rate | E-3's run ended at 52.300 emulated ms (`result.json`) with TIMER4 at 1 255 200, which is 24 MHz of emulated time; HW-13 now cites that. HW-14 says TIMER5 ignores `CON` bits 4-7 in fwtest. |
| HW-16 prescaler setting 0 | Removed; only setting 2 is stated, the rest is Q-3. |
| HW-17, HW-23 core 1's addresses | Given (`0x200` higher, SDK `csfr.h`), with the note that fwtest models only core 0's. |
| HW-18 one table for both cores | Stated for fwtest; Q-10 asks about the chip. |
| HW-22 nesting | Restated as what the handler does (stores `reti` to its stack, until it loads it back), limited to fwtest; Q-10 covers the chip. |
| HW-24 `idle` | Limited to fwtest; the masked case on the chip is in Q-10. |
| HW-29, HW-30 | "Finishes at once" and "no set-up" are limited to fwtest; the chip needs `BAUD`, mode and pins (Q-6). HW-30 notes FM-1-RE's medium confidence and points PC7 to Q-6. |
| HW-32 | Adds the 120 ms after a software reset sent in sleep mode before sleep out; HW-27 says the spec assumes the ST7789V. |
| HW-38 clockwise | "The direction an input script calls clockwise"; the physical direction is in Q-7. |
| HW-40, HW-41 ADC | HW-40 says which channel is the pot on the chip is Q-8, and that each start write sets bits 4 and 6. HW-41 says the acknowledge clears bit 4 and the next start sets it again. |
| HW-26 | Cites HARNESS for `--watchdog` (not exercised) and drops "works on both". |
| HW-10 milestones and `SYS_DIV` | HW-9 and HW-10 are both M1; the `SYS_DIV` release is now a warning. |
| HW-19 | SPI2 and UART1 dropped; the audio source is named with the SDK's `IRQ_ALNK_IDX`; TIMER4 points to HW-14. |
| HW-21 | Notes the `icfg` / `ICFG00` name clash, and no longer claims the `sti` gate's state at entry: it says what to do. |
| HW-44 sample format | Says fwtest shifts the whole word arithmetically, and to write sign-extended 24-bit values. |
| General: HARNESS as a source | HARNESS no longer counts as confirming: the Sources table says so, and the lint (C-SPEC-LINT) now requires SDK, RE, DS, PANEL or an E-n for a confirmed entry. |

After the changes: C-SPEC-LINT PASS (47 entries), C-SEP-TERMS PASS, and
the experiments (C-SPEC-EXPERIMENTS) still match their golden files.
