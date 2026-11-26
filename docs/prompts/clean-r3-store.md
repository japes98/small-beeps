>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

**Working (the owner's rule for every clean prompt):**
- While iterating, run only the seams cases the change touches. Whenever the build identity changes, run seams case report1 as well.
- Run tools/check-emulator-terms.py with COMMIT_RANGE=origin/main..HEAD before every push, and don't push while it fails. It reads commit messages and PR text too: keep renamed names out of them.
- Commits carry `Model:` and `Co-Authored-By:` but no `Claude-Session:` line, and PR text carries no session link.
- Say how long each build took and where the time went: compiling, fwtest runs, container start-up, packing, other.

**The fast loop (as for USB):**
- This round is tried on one branch, with no PR and no new prompt for each try.
- Each try: the seams cases it touches, plus report1 when the identity changes; owner-only files, which the owner flashes once they're checked, without waiting for CI. Each try has its own identity, so backups name the try.
- The unit's results reach you through the owner.
- Limits: the writes in section 6 only; anything that needs a new source stops the loop and goes to the spec side and the owner.
- When the owner says the run passes: one PR with full CI, the unit results in its outcomes table, and the backtest (the three files rebuilt from main, byte-identical to the ones tested).

This is round 3 of the owner's plan to finish small-beeps as a public, useful project: the store and editing on the unit. Round 2 is done (#254 to #256): the release starts in 92.9 ms after TIMER0, with 0 problems and 0 underruns; unused stack main 1 524 bytes, interrupts 1 488 to 1 632. The owner's rulings (2026-11-26) are filled in below. The patches are small-beeps' own: RevoiceDX's are not part of this round or planned.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-r3-store.md.
- Read, on main:
  - R-STORE-1 to R-STORE-13, R-UI-1 to R-UI-14;
  - HARDWARE-SPEC HW-80, HW-110, HW-115 to HW-118, HW-120 to HW-124, HW-131, HW-133;
  - docs/STORE-FORMAT.md and docs/PATCH-FORMAT.md.

## 1. The store in the release
- **Start it:** the release starts the store small-beeps already has (M7, M8a): the 16 user slots, the selection and the settings, in its region `0xFC000` to `0xFEFFF` (R-STORE-1).
- **Start-up:** the store is its own stage in the summary record, with its time. Start-up stays under 1 000 ms, in fwtest with a full region and on the unit.
- **REC:** stays as it is unless the store needs it.

## 2. EDIT, ENV and SAVE on the unit, in large text
- **The patches** are small-beeps' own (PATCH-FORMAT), not RevoiceDX's.
- **The key map** stays as M8a has it (R-UI-9 to R-UI-11, R-STORE-9).
- **Text size:**
  - every word and number on the release's screens at scale 2 (10×16 pixels) or more;
  - the screen's title and the value being edited at scale 3 (15×24);
  - the algorithm and envelope drawings stay, laid out around the text.
- **Findable keys:** each screen names, at scale 2, the panel keys it uses by their printed labels (HW-115 to HW-118). For example, SAVE: "hold SAVE, press KEY 1-16".
- **SAVE's result** in large text: "SAVED 1" to "SAVED 16", or the reason it didn't save.
- **Seams:** golden images for each screen; each screen's text at its size; a save and its read-back at the next start.

## 3. The power-cut test
- **fwtest:** R-STORE-11's power-cut cases still pass with the release's store.
- **The test file's save soak, for the unit** (the test build only; the release has none):
  - Hold SAVE with KEY16 for 3 s: user slot 16 is saved again and again, alternating two known patches, A and B, with "SAVING n" in large text, until power-off.
  - At the next power-on the test file checks slot 16 first and shows, in large text, "SLOT 16: A", "SLOT 16: B" or "SLOT 16: BROKEN", with the store's counts. Then it starts as usual.
  - A seams case cuts the power at many points in the soak and checks the verdict each time.

## 4. Faults
- **The red screen** shows the fault's cause and address in large text and stays until power-off. Nothing else: no flash write from a trap, no RAM mark, no reset (no source gives a reset write).
- **The test file only:** OCT- and OCT+ held together for 3 s trap on purpose. The release has no such hook. (SEL with PIT is taken: the pitch envelope, R-UI-11.)
- **Seams:** the red screen's text and its size.

## 5. Stack headroom
- **Floor:** at least 512 bytes unused on the main stack and on the interrupt stack.
- **fwtest's worst case:** a save during notes and USB traffic, measured in seams. Below the floor in fwtest, the PR doesn't open.
- **On the unit:** the summary record keeps both figures; below the floor is a problem record.
- **Say** what the store took from each stack.

## 6. Writes on the unit
- **Flash:** only HW-124's commands, as R-STORE-13 has them, and only in the store's region.
- **The status register is never written.** If block protection covers the region: no save, "STORE LOCKED" in large text, and a problem record.
- **Nothing else:** no new register, no clock or `0x16A00` write.

## 7. Not included
- No store format change, no level change (D8 is round 4), no RevoiceDX format, nothing new in USB.

## 8. For the owner
- **Recovery first:** if the unit hangs or won't start, power off, hold PLAY at power-on for about a second: m-bootloader's menu opens before any app runs (HW-117, HW-173). Reflash round 2's release file from there. The store's region lies outside what a flash writes (R-STORE-1); run B's step 4 checks it.
- **The files:**
  - the owner-only release (USB on), for run A and the end of run B;
  - the owner-only test file, for run B;
  - the published release (USB off), which is not flashed this round.
- **Run A,** with the owner-only release, from a plain power-on:
  1. Flash the owner-only release. Power on, and keep tapping a key: it sounds within about a second.
  2. PRESETS to any preset. Press EDIT: the screen names the keys it uses in large text. Turn the level knob for one operator: you hear it change, and the value shows large.
  3. Press ENV and change one stage's time: you hear it.
  4. Hold SAVE and press KEY1: "SAVED 1" in large text. Power off, then on. PRESETS to user slot 1: your edit is there.
  5. Power off and send the backup: the summary records hold the start time with the store's stage, the store's counts and the unused stack; any problem is a record of its own.
- **Run B,** with the owner-only test file:
  1. Flash the test file. Power on, then hold SAVE with KEY16 for 3 s: "SAVING n" counts up. Switch off while it counts.
  2. Power on: note what the screen shows: "SLOT 16: A" or "SLOT 16: B" (pass), or "SLOT 16: BROKEN" (fail). Do steps 1 and 2 three times in all.
  3. Hold OCT- and OCT+ together for 3 s: the red screen shows the cause and the address in large text. Photograph it. Power off.
  4. Reflash the owner-only release. Power on, PRESETS to user slot 1: run A's edit is still there.
  5. Power off and send the backup.
- **What each outcome means:**

  | Outcome | Next step |
  |---|---|
  | Runs A and B as above | Round 3 done: one PR with full CI and the backtest |
  | No sound, or a hang | Recover as above, report the last record; the next try changes only the store's start |
  | "SAVED" but the edit is gone after power-off | The store's read at start; the backup's store counts show which |
  | "SLOT 16: BROKEN" | The save's order of writes; the soak's seams case is redone at the cut point the unit shows |
  | Slot 1 gone after the reflash | The flash wrote over the store's region: back to the spec side and the owner |
  | "STORE LOCKED" | Block protection is on: back to the owner; no status register write without a ruling |
  | Text too small or a key hard to find | The screen's layout only; the next try changes only that |
  | Start over 1 s | The summary's store stage shows it; the next try reads less at start |
  | A stack below 512 | The save path's buffers; the next try shrinks them |
  | The red screen hard to read in the photo | Its layout only |

- **Timing:** how long each build took, and where the time went.

Finish with "done, ready to clear", Questions, one merge order.
