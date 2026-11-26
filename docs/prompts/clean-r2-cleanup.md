>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

**Working (the owner's rule for every clean prompt):**
- While iterating, run only the seams cases the change touches. Whenever the build identity changes, run seams case report1 as well.
- Run tools/check-emulator-terms.py with COMMIT_RANGE=origin/main..HEAD before every push, and don't push while it fails. It reads commit messages and PR text too: keep renamed names out of them.
- Open the PR once those pass and the .fwsc files are packed. CI runs the full suite; don't do a full local run before the PR.
- The owner flashes once the file has been checked, without waiting for CI.
- Say how long the build took and where the time went: compiling, fwtest runs, container start-up, packing, other.
- **New from round 1 (#253):** commits carry `Model:` and `Co-Authored-By:` but no `Claude-Session:` line, and PR text carries no session link.

This is round 2 of the owner's plan to finish small-beeps as a public, useful project: clean-up and speed. USB works on the unit (#249; HW-181 to HW-183). The owner's rulings (2026-11-24) are filled in below. Nothing new is written on the unit: no new register, no clock or `0x16A00` write.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-r2-cleanup.md.
- Read, on main:
  - HARDWARE-SPEC HW-176, HW-177, HW-179, HW-180 and HW-181 to HW-183;
  - R-USB-1 and R-HW-1;
  - docs/HARNESS.md "USB" and "Versions" (0.15.0);
  - docs/AUDIT.md "Data tables".

## 1. Two builds
- **Release:** the instrument, the store and the USB device.
  - **Published:** built without USB (not compiled in), with no product ID in it, by R-USB-1.
  - **Owner-only:** the same build with USB on and the test product ID. Its name says owner-only, as U3-U's did.
- **Test:** the release with USB on, plus the bring-up code: the test screen, the SARADC and matrix sweeps, the probe, U2's readings. Owner-only; never published.
- **The flags:** fold `SB_HW_AUDIO1` to `SB_HW_AUDIO14`, `SB_HW_U3U` and the other bring-up flags into the two configurations. Keep USB on or off as the one separate choice. fwtest's `SB_TEST_*` hooks stay for seams. Say which flags went and where each one's code now is.
- **Checks:**
  - The published file and the owner-only file differ by USB alone. Check this from the build, not from a run.
  - Each build has its own identity.

## 2. Start-up under 1 s, the release build
- **What's timed:** from the app's first instruction to the instrument ready (sound running, panel up, keys read), timed by the app and written in the summary record.
- **Under 1 000 ms on the unit.** Say what fwtest measures. Fill times have differed from the unit's by about 7 times (HW-175), so only the unit's number counts.
- **Checks that hold the start:** remove from the release build only those a HARDWARE-SPEC entry settles, and keep them in the test build. The owner's list to start from:
  - U2's readings (HW-177);
  - the `0x16A00` read (HW-180, HW-183);
  - the test screen's start before the instrument (HW-176, HW-177);
  - L2's start-up check and its one-second hold (L2 is the start's set-up since audio8; the start from cold works, HW-176, HW-177);
  - ARP's step record (HW-180).
- **For each check removed, say:** what it was, the entry that settles it, and the time it saved. Keep any check you can't tie to an entry, and say why.
- **The USB cable check stays,** as U3-U has it: it is the release's own behaviour.

## 3. The log, the release build
- **Problems only:** a give-up, a fault or trap, a late half or underrun, a store error, a USB stall, drop or storm, a stack low-water warning. At most 16 problem records a power-on.
- **One summary record a power-on,** written once the start is done: identity, start time in ms, each start-up stage's time in ms (so a slow start shows where the time went), and the counts. A quiet power-on writes that one record and nothing else.
- **The test build** keeps today's records.
- **The decoder** reads both builds' records, and the layouts before them.

## 4. hw_audio.c
- **Settled bring-up code:** delete it; it stays in history. Name the HW entry that settles each part.
- **What the test build still needs:** move it out of `hw_audio.c` into its own files, built only into the test build.
- **What's left:** say what of `hw_audio.c` is left in the release build, and why.
- **The audit after this round:** it still covers all of `firmware/`. It is re-run after this round, and any file still flagged goes to an auditor session. Don't open the audit's matched code or targets (docs/AUDIT.md).

## 5. fwtest 0.15.0
- **The pin:** move `config/fwtest-image` to 0.15.0, published from main at #253's merge as `ghcr.io/japes98/small-beeps@sha256:81fd8b40d4e68973a361d7f2a58e7dabbfc2bbd367b668873f12dfec7ffb2fc1`.
- **Seams usbmidi:** drop the one expected problem (`FADDR is 0 after set the address 1`). The host now checks the address after the status stage.
- **Without `--usb`:** `CON0` bits 16 and 17 now change from read to read (docs/HARNESS.md "USB"), so USB no longer starts in fwtest. Update whatever seams expected of that case.

## 6. CI: seams in parallel
- Seams takes `--shard k/n` and runs every n-th case from k, spread by the cases' measured times.
- `.github/workflows/ci.yml`'s matrix runs 4 seams parts, and `tools/record.py` assembles them as one C-SEAMS. Change only what the split needs, and keep the checks job's 120-minute limit.
- Bring-up cases may merge where the test build now covers them in one.
- **Target:** a PR's checks in about 20 to 30 minutes. Say the times per part.

## 7. Not included
- No new register, no clock or `0x16A00` write, no store format change, no level change (D8 is round 4), no new editing (round 3).

## 8. For the owner
- **Recovery first:** if the unit hangs or won't start, power off, hold PLAY at power-on for about a second: m-bootloader's menu opens before any app runs (HW-117, HW-173). Reflash U3-U's final file from there.
- **The files:**
  - the published release file (USB off);
  - the owner-only release file (USB on), which is the one to flash for this run;
  - the test file (owner-only).
- **The run,** with the owner-only release file, no test screen and no key held:
  1. Power off. Power on on the battery, cable out, and keep tapping a key; count the seconds until it sounds. It should sound within about a second. (The instrument makes no sound until a key is pressed.)
  2. Play a few keys and a chord: each sounds and stops.
  3. ARP on: it plays even, at the right speed (by ear); ARP off.
  4. Plug the cable into the Mac, which is awake. "small-beeps" appears in Audio MIDI Setup's MIDI Studio.
  5. Notes from the Mac sound on the unit; the unit's keys reach the Mac, one note-on and one note-off each.
  6. Unplug; play a few keys: the instrument carries on.
  7. Power off. The log's summary record holds the start time, each stage's time and the counts; any problem is a record of its own.
- **What each outcome means:**

  | Outcome | Next step |
  |---|---|
  | All as above, start under 1 s | Round 2 done |
  | Start over 1 s | The summary's stages show where the time goes; the next try changes only that |
  | No sound, or a hang | Recover as above, reflash U3-U's final file, report the last record |
  | USB doesn't appear, or notes go one way | Compare with U3-U's final file; the change list in section 1 shows what moved |
  | A problem record | Report its name and counts |

- **Timing:** how long the build took, and where the time went.

Finish with "done, ready to clear", Questions, one merge order.
