>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

## 0. Start
Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17.md.

## 1. BR-17 (from the downstream firmware): a package a real unit's installer accepts
The FM-1 unit has arrived. On 2026-11-17 the owner tried a .fwsc made by `tools/fwsc.py pack` at ab16ee2b on it, with a third-party USB installer. The installer refused it before writing anything: "damaged firmware package (file list CRC)". The file matched its SHA256SUMS. The unit runs a third-party bootloader with a recovery menu, and the owner holds a full backup.

BR-17 has four parts. Parts 1 and 2 are hardware facts, so they're the spec side's, not yours. The spec side has answered what JieLi's own packaging tools show: HARDWARE-SPEC section 24 (HW-103 to HW-108; Q-25 answered in part, Q-26 narrowed), in the spec side's pull request #180, which merges before this work starts (check that it has). Read section 24, HW-87 to HW-94, Q-25 and Q-26. Take every fact from there. Don't work any out yourself, and don't learn any from a stock package or a third-party tool. If the packager needs a fact HARDWARE-SPEC doesn't give, file a spec request (SR) that names the field exactly.

Your parts:

**(a) Fields from HARDWARE-SPEC, not 0.** Make `tools/fwsc.py` write every field section 24 defines: the list CRC and the image size, each entry's fields, the flash header's and the heads' fields and data CRCs. Its reader must match head names as HW-105 says, up to the first zero byte. Today's reader refuses JieLi's own packages for this. Fields the spec still leaves open (Q-25's list) keep today's values, and `fwsc.py` says which those are when it packs. Give it a hardware mode that refuses to pack while any field it needs is still open, and print each open Q-number.

**(b) An app-area-only package.** Add a mode that writes the app area only: flash 0x4000 up, never 0x0–0x3FFF. Today's image starts at 0 and carries a flash header, a directory and our own key block below 0x4000. A unit that took it would lose its boot area: the bootloader and its recovery. The new mode must hold no byte below 0x4000, and a test must check that (parse the package as fwsc.py's reader does, and fail on any entry or region that reaches below 0x4000). HW-106 describes the app-area-only form JieLi's own tools write, and HW-107 what they don't write. Whether an FM-1 installer accepts either form, and which key it expects (HW-108), is Q-26. Use what HARDWARE-SPEC says, and file an SR for what it doesn't. Keep today's full-image mode for the emulated load paths, unchanged.

**(c) A hardware target in the release format.** Add the hardware target `fm1-unit` (the owner's name for it; use it exactly) to `release.json`'s `targets` next to `f-emulator-app`. Document it in M9-PLAN's format table and RELEASING.md, and update tools/release.py and its tests. Add it only to a release whose build has been checked on a unit: the release takes it from an explicit, recorded input (for example an entry in config/releases.json naming the unit check), never by default, and the release notes say how much was checked. No release gets it in this change.

**Not in this change:** no hardware target on any existing or new release, and no claim that a package will install on a unit. The owner checks the first candidate on the unit (Phase B); end with the exact files to try and what each should show.

Tests for each part; docs in DESIGN-NOTES and BUILDING-ON-SMALL-BEEPS.md (what a downstream firmware's pack step calls).

Finish with "done, ready to clear", Questions, and one merge order.
