>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

**Working (the owner's rule for every clean prompt):**
- While iterating, run only the seams cases the change touches. Whenever the build identity changes, run seams case report1 as well.
- Run tools/check-emulator-terms.py with COMMIT_RANGE=origin/main..HEAD before every push, and don't push while it fails.
- Open the PR once those pass and the .fwsc is packed. CI runs the full suite; don't do a full local run before the PR.
- The owner flashes once the file has been checked, without waiting for CI.
- Say how long the build took and where the time went: compiling, fwtest runs, container start-up, packing, other.

This is audio14, built on audio13 (on main with #244, which carries #243 and your report1 fix; #243 was closed unmerged). audio13 on the unit:
- Power-on into the instrument worked, with sound.
- ARP was heard even and at the right speed, but no ARP record reached the log: the panel's REC save after ARP wrote none.
- U2's reads hung nothing; a computer that is on is found by reading alone.

audio14 does three things:
- **R:** fix the panel's save, so the ARP gaps reach the log.
- **P:** a read-only check of the block at `0x16A00`, with U2-A's reads.
- **U3-F:** the USB MIDI device, built and tested in fwtest only. The unit build carries no USB write.

The owner's rulings (2026-11-22): audio14 approved as drafted, with P added; clean runs seams case report1 whenever the build identity changes; flash it now for R; U3-F has no serial-number string; any clock or PLL change gets its own ruling before a unit write. Our own product ID is an open question for the owner, and published builds keep USB off until then.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio14.md.
- Read, on main (the spec side's round PR has merged):
  - HARDWARE-SPEC section 51 (HW-176, HW-177: audio13 on the unit);
  - section 49 (HW-171 to HW-173) with HW-86;
  - Q-36;
  - R-USB-1;
  - HARNESS.md's "USB" section.
- Take every fact from those.

## 1. R: the panel's save writes the ARP record
- **REC in the panel** writes a record holding ARP's step log: the shortest and longest gaps in frames and in µs, the number of steps, and the last steps' frame counts and times.
- Say why audio13's save wrote none.
- **fwtest:** run ARP in the panel, press REC, and check that the record is in the log with gaps of 5 514 or 5 515 frames.

## 2. P: the block at `0x16A00`, read only (the owner's ruling)
- **Read** the four words at `0x16A00`, `0x16A04`, `0x16A08` and `0x16A0C` alongside U2-A's five words, at the same points: at the very start of the app, before the audio path, and a second later. Keep them in each start's boot record, as audio13 does for U2-A, so they reach the flash log with no save key.
- **Nothing is written** to that block or to any clock register.
- **Log each word in hex.** Show them in the test screen's large area with U2-A's.
- **Say** whether bit 1 of `0x16A00` reads set. The spec side will read the result against its facts on that block, which come with U3-U's round.

## 3. U3-F: the USB MIDI device, in fwtest only
- **A MIDI-only device** on the first core, by HW-171, HW-172 and HW-86:
  - endpoint 0 answers the standard requests;
  - one MIDI streaming interface with one bulk OUT and one bulk IN endpoint;
  - MIDI in from the host plays the engine as the panel's keys do;
  - the panel's notes go out to the host.
- **Identity, by R-USB-1:**
  - vendor `0x1209`, product `0x0001` (pid.codes' test PID);
  - manufacturer and product strings "small-beeps" (never FM1, FM-1 or M-VAVE).
  - no serial-number string (index 0), by the owner's ruling.
  - A comment beside the IDs says the test PID is for in-house testing only and must not ship on redistributed devices.
- **Built only behind a flag** that fwtest's builds set and the unit's builds don't. The published builds and this round's unit file carry no USB write. Say how the build keeps it out.
- **The core's set-up in fwtest** is only what HARNESS.md's "USB" section says the host waits for, with `POWER`'s value from HW-172. On the unit the set-up waits for Q-36's writes and a ruling, so keep it in one function that U3-U will replace.
- **Hold the device's spacing rule** in the code now: space accesses through `CON1`'s port apart (HW-172), with the spacing in one place.
- **Before connecting,** read `CON0` bits 16 and 17 (HW-177): steadily 0 means a computer that is on. Log the reading. In fwtest, say what the host model shows there.
- **Pin fwtest 0.14.0** (`ghcr.io/japes98/small-beeps@sha256:0c8f53240494b8aa7ba7e0767b432963e4aa0e23fbc3045677530b1ce9cef470`, HARNESS.md "Versions") for the cases that use `--usb`.

## 4. Not included
- No USB register written on the unit; no pin changed.
- No register written beyond audio13's; nothing written to `0x16A00` or any clock register.
- No store write; no level change (D8 is later).

## 5. fwtest
Extend or add the seams cases you touch:
- **R:** the save with ARP's record (section 1).
- **P:** the four words read and logged with U2-A's, before the audio path, in both starts; without a model of that block, fwtest reads them as last written (0).
- **U3-F, with `--usb`:**
  - the host enumerates the device as `1209:0001` with both strings "small-beeps";
  - the host's `usbmidi` notes sound in `audio.wav`;
  - the panel's notes appear in `usb-midi-out.csv`;
  - `result.json`'s `usb` object lists no problems.
- **U3-F, without `--usb`:** outputs as before.
- **The unit's build:** no USB register write. Check this from the build, not from a run.

## 6. For the owner
- **The flash:** R and P are new on the unit, on the battery with no USB cable.
  1. Power on with nothing held: the instrument. This start reads P from power-off. In the panel, run ARP for about 20 s, press REC, then power off.
  2. Open m-bootloader's menu, enter MIDI mode and leave it by a key into the app. This start reads P after MIDI mode.
  3. Power off. The log should hold ARP's record and both starts' P and U2-A words.
- **What each outcome means:**
  - **R: the record is there with 5 514 or 5 515 frames and about 125 ms per step:** ARP is right on the unit.
  - **R: frames right, ms off:** the audio's rate isn't the one assumed. That is a Q-9 question.
  - **P: `0x16A00` bit 1 set in both starts:** the SDK's start of that block would be skipped. U3-U can be written without it, though it doesn't show the first core needs nothing more.
  - **P: bit 1 clear in either start:** that block is down at the app's start. Whether U3-U must start it goes to the owner before any write.
  - **U3-F passes in fwtest:** the device side is ready for U3-U, its own round, written from the spec side's facts on the set-up and ruled by the owner first.
- How long the build took, and where the time went.

Finish with "done, ready to clear", Questions, one merge order.
