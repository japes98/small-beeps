>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

## 0. Start
The owner merged #169 to #171. Clean setup checks, archive clean-1028's transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-store-region.md.

## 1. The owner's answer: each firmware chooses its own store region
- small-beeps keeps today's three sectors as its default, and M-VAVE's user-patch region below it stays untouched, as M8a promised.
- A firmware built on small-beeps can set its store region's start and size itself, in its linker settings (platform.ld, or a documented symbol pair), for example a larger region inside the flash space its own image occupies.
- The build refuses a region that overlaps the image, crosses the end of the app area as HARDWARE-SPEC defines it (HW-87 to HW-93), overlaps the stock user-patch region, isn't sector-aligned, or is too small for the store's minimum. Say in each error what's wrong and what would fit.
- The store works unchanged in any region of 3 sectors or more; BR-12's atomic rewrite works wherever there's room for both copies (state the sizing rule plainly).
- Tests: the store model and fwtest's power-cut tests in a 5-sector and a 16-sector region placed after a small image; the overlap checks each refusing what they should.
- Document it in BUILDING-ON-SMALL-BEEPS.md (with a worked example: 16 sectors for several 4 096-byte records) and DESIGN-NOTES.
- If HARDWARE-SPEC doesn't say clearly enough where the app area ends, file a spec request (SR) saying exactly what you need, use the most conservative reading meanwhile, and say so.

## 2. BR-13 (from the same downstream firmware)
The write-back build check (R-BUILD-3) misreads float instructions unless it disassembles with the float extension enabled (-mattr=+fprev1). Make the check disassemble with the same CPU and feature flags the build compiled with, and add a test with a float-heavy object that it reads correctly.

Finish with "done, ready to clear", Questions, and one merge order.
