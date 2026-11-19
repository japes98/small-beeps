>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

If clean-br17-protect (the 0.12.0 pin, the store's protection cases, the first-1-MiB reads, the comments, the give-back's `BAUD`) is still open, build this on top of it, in the same cumulative branch.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-core1.md.
- Wait until the spec side's #199 has merged. Then read:
  - HARDWARE-SPEC HW-135 (section 32: what the chip's release of core 1 takes, beyond HW-9), with HW-9, HW-10, HW-53, HW-133 and HW-134;
  - the notes on Q-17 and Q-18;
  - docs/SPEC-REQUESTS.md, SR-18 (your request, answered).
- Take every fact from those.

## 1. A core 1 probe for the unit
Change start3's core 1 step (`hw_core1_start` and its rows) so that the next unit run tells which of HW-135's steps core 1 needs:
- **The release, in HW-135's order.** Read `SYS_DIV` first, and put back exactly the value read, never a constant, so the dividers m-bootloader set are kept (HW-135).
- **Core 1's own sign.** Core 1 sets its own flag when it starts. Core 0 waits for it with a timeout, never forever, and the screen says if the wait timed out.
- **What the screen shows:**
  - `SYS_DIV` before and after;
  - `C1_CON` after each write;
  - the start word read back.
- **A sign that core 1 runs that doesn't rest on Q-18.** A counter stuck at 0 can't tell "not running" from "not seen". Show the `corex2` per-core counters for core 1 (Q-17 names the words) before the release and a second after, as observed values only: the SDK doesn't say what they count.
- **The hold-up.** Keep the rows on screen as start3b does, so a hang shows where.

If it fits on the screen, add a second variant behind a build flag. It does steps 1 and 3 only, with bit 1 cleared and `SYS_DIV` untouched, so one unit run of each tells the two steps apart. Say which variant the default build is.

## 2. fwtest
In fwtest, core 1 starts at the first of the two release steps, once only (HW-10), so fwtest can't show which step the chip needs. The seams cases `hw`, `hw3` and `finder` should still pass. Say what they show for the new rows, and add a case for the variant if you build one.

## 3. Core 1 elsewhere
Until a unit run settles it, nothing in the hardware build depends on core 1 (as clean-br17-protect says). Say in DESIGN-NOTES what the firmware does without core 1, and what would change once the probe shows that core 1 runs.

## 4. For the owner
Give the owner what to photograph on the unit: the rows and what each value means. Keep it to what the result needs, so the next spec request (if any) can be exact.

Finish with "done, ready to clear", Questions, one merge order.
