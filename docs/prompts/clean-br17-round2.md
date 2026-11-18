>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

## 0. Start
Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-round2.md.

## 1. BR-17, round 2: a hardware package that passes the unit's installer
Round 1 (2026-11-18): the unit's installer refused both of #181's app-area candidates (keys 0xFFFF and 0x980F) before writing anything, with "unexpected flash image size". The unit is unchanged. #181 (section 24's fields, the app-area-only package, `fm1-unit`) and #182 are merged. Your #183 (the OTA form, SR-13) was merged into the spec side's pull request for this round.

The spec side has added HARDWARE-SPEC section 25 (HW-109 to HW-114): what the unit's installer checks, in order, what it writes, the chip key, and the bootloader's checked start. It has also answered SR-13 (HW-114). This is in the spec side's pull request #184, which merges before this work starts (check that it has). Read sections 21, 24 and 25. Take every fact from there. Don't work any out yourself, and don't learn any from a stock package or any tool's source. If the packager needs a fact HARDWARE-SPEC doesn't give, file a spec request (SR) that names the field exactly.

Two consequences:
- The installer writes only from 0x4000 up and keeps the unit's boot area (HW-110). So a `flash.bin` from flash 0, sized as HW-114 says, is BR-17's app-area-only package. SR-13's concern doesn't arise.
- HW-106's OTA form has no type-0 `flash.bin`, so the installer refuses it (HW-109 step 7). Make no more OTA candidates for this installer, and say so in DESIGN-NOTES.

**(a) A hardware package that passes every check at once.** Give `tools/fwsc.py pack` a hardware mode (for example `--hardware --key K`), or change #181's app-area mode, so that its output passes every check of HW-109, in its order, and HW-112's checked start. This is BR-17's app-area-only package: the installer writes only from 0x4000 up and keeps the unit's boot area (HW-110). In particular:
- The flash image starts at flash 0. Its first 0x4000 bytes are never written to a unit (HW-110). Keep today's own flash header, directory and key block there, with every field and CRC written as HW-104 and HW-105 give them.
- The flash image's length is as HW-114 gives it: from 0 to the 4 KiB boundary HW-114 names, padded with 0xFF, never further. Everything from 0x4000 to its end replaces the unit's flash (HW-110), so it must not reach the stock regions or the store region.
- The app area is scrambled with the key K given on the command line (HW-111). K has no default: the owner reads the unit's key with `m-flasher info`.
- The area head (attribute 0x83, `app_area_head`, offset field the entry) and every attribute-0x82 file with its data CRC, as HW-112 needs. Unused head slots up to 0x120 are 0xFF before scrambling, not zero (HW-105).
- The header's CRC, list CRC, image size and count (HW-104), and the `flash.bin` entry's CRC over its stored bytes.
- The identity is `FM-1_` followed by the version, with no `_` in the version (HW-109 step 9). It has at most 19 characters, and no marker byte equals 0x7D. File byte 1007 must not be 0x7D (step 2).
- One entry, `flash.bin`, is enough (HW-109). Don't copy `blimit.bin` or any other entry.

**(b) A check of its own.** Add `fwsc.py check FILE --key K`: it runs HW-109's checks 1 to 11 and HW-112's checks 1 to 3 against a package, in that order, and stops at the first failure with the installer's own message where HW-109 gives one. Its tests: a good hardware package passes. One broken package per check (wrong size, list CRC, flash.bin CRC, model, an identity with a `_` in its version, key, a file CRC, byte 1007, zero-filled head slots) fails exactly that check. A package made with key 0xFFFF fails check 11 for K = 0x980F. Fix the reader's name matching (HW-105, up to the first zero byte) in the same change. Keep today's emulator mode and its tests unchanged; the emulated paths still take it (HW-93).

**(c) The hardware target** `fm1-unit` stays as #181 made it. No release gets it in this change.

**Not in this change:** no hardware target on any existing or new release, and no claim that a package will install on a unit. The owner tries the first candidate on the unit (Phase B round 2). End with the exact file to try (the hardware package made with K = the unit's key, after `fwsc.py check` passes on it), its SHA-256, the flash range it will write (from `m-flasher`'s plan: 0x4000 to its end), and what the unit should show.

Tests for each part; docs in DESIGN-NOTES and BUILDING-ON-SMALL-BEEPS.md (what a downstream firmware's pack step calls).

Finish with "done, ready to clear", Questions, and one merge order.
