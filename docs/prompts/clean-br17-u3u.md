>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

**Working (the owner's rule for every clean prompt):**
- While iterating, run only the seams cases the change touches. Whenever the build identity changes, run seams case report1 as well.
- Run tools/check-emulator-terms.py with COMMIT_RANGE=origin/main..HEAD before every push, and don't push while it fails. It reads commit messages and PR text too: keep renamed names out of them.
- Open the PR once those pass and the .fwsc is packed. CI runs the full suite; don't do a full local run before the PR.
- The owner flashes once the file has been checked, without waiting for CI.
- Say how long the build took and where the time went: compiling, fwtest runs, container start-up, packing, other.

This is U3-U, built on audio14 (on main with #247, which replaced #245). audio14 on the unit:
- ARP's record: 123 gaps of 5 514 or 5 515 frames. audio13's missing record was REC not being pressed; your save works.
- The block at `0x16A00` reads off at the app's start, from power-off and after MIDI mode.
- U2-A read as in audio13.

U3-U puts U3-F's device on the unit: the first USB write on the unit. The owner's rulings (2026-11-23):
- USB starts only once the cable reading shows an awake computer, checked at the app's start and then about once a second.
- The port's spacing stays in its one place, starts generous (MIDI needs little speed), and is logged.
- On a poll's give-up: log the stage and the index, write nothing more to USB until the next power-on, keep the instrument running.
- The order: HW-172's, with `usb_slave_init`'s writes (HW-178) straight after the SIE's start, and `SIEIE` set last.
- One unit file with USB on, for the owner's flash only, its name marking it so (for example `small-beeps-u3u-usb-owner-only-key-980f.fwsc`).
- No write to `0x16A00` or any clock register.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-u3u.md.
- Read, on main:
  - HARDWARE-SPEC section 52 (HW-178: the first core's device start as writes) and section 53 (HW-179, HW-180: audio14 on the unit);
  - section 51 (HW-176, HW-177) and section 49 (HW-171 to HW-173) with HW-86 and HW-117;
  - Q-36;
  - R-USB-1.
- Take every fact from those.

## 1. The set-up on the unit
- **Replace U3-F's one set-up function** with HW-178's writes, in HW-178's order: the pins' input enables; the pads given to USB; the reset bits cleared; `CON1` 0; `PHY_ON`; the pull-downs and pull-ups cleared, then D+'s pull-up; the reset bits set; then the device's interrupts and `POWER`, by the owner's ruling, in HW-172's order: `usb_slave_init`'s writes (HW-178: `INTRUSBE` 0, the transmit and receive enables cleared) straight after the SIE's start; then `POWER`, endpoint 0's buffer, `INTRUSBE` set to reset and suspend, endpoint 0's enable, the interrupt registered; `SIEIE` set last.
- **Every write has a source:** name the HW entry beside each one. Write nothing HW-178 or HW-172 doesn't.
- **Nothing to `0x16A00` or any clock register,** by the owner's direction. MIDI mode ran USB with that block reading off; U3-U tries without it first.
- **Either start state:** the unit may start with `PHY_ON` set (from power-off) or clear (after MIDI mode), HW-177. HW-178's order covers both; don't skip a step because a bit already reads set.
- **The access port:** use it only while `CON0` bit 2 reads set; poll bit 15 up to 20 000 times, as HW-178 gives it. On a give-up, by the owner's ruling: log the stage and the index, write nothing more to USB until the next power-on, and keep the instrument running. No stop sequence: none has a source.
- **The spacing,** by the owner's ruling: in its one place, generous to start with (MIDI needs little speed), and logged with the set-up.
- **DMA buffers:** keep the 4 bytes past each receive packet (HW-172).
- **When USB starts,** by the owner's ruling: only once the cable reading (`CON0` bits 16 and 17 steadily 0, HW-177) shows an awake computer, checked at the app's start and then about once a second. On the battery, with a charger or with a sleeping computer, nothing is written to USB. Log the cable reading each time it changes.

## 2. The log
- Log each stage to the boot record, so a hang shows where it stopped, with the stage's time: the cable reading; each of HW-178's steps; the interrupts on; `POWER`; the host's reset; the address set; the configuration set; the first MIDI packet in; the first packet out; any give-up.
- Read back `CON0`, `CON1` and IO `CON0` after the set-up and log them in hex, with the cable reading.
- Count babble and dropped packets if the device can see them, and log the counts.

## 3. fwtest
- **With `--usb`:** U3-F's cases still pass with the new set-up: enumeration as `1209:0001` with both strings "small-beeps", the host's notes in `audio.wav`, the panel's notes in `usb-midi-out.csv`, and no problems in `result.json`'s `usb` object.
- **Without `--usb`:** nothing written to USB, since with no host the cable reading doesn't show one.
- **The cable reading in fwtest:** with `--usb`, say what fwtest's host shows in `CON0` bits 16 and 17. If it doesn't hold them steadily 0, USB never starts there: say so in Questions, and don't bypass the reading in the unit's file.
- **The published build:** no USB write. Check this from the build, not from a run.
- **The unit's file:** USB on, `1209:0001`, for the owner's flash only; its name says so (for example `small-beeps-u3u-usb-owner-only-key-980f.fwsc`). Say how it differs from the published build.

## 4. Not included
- No write to `0x16A00` or any clock register.
- No store write; no level change.

## 5. For the owner
- **Recovery first:** if the unit hangs or won't start, power off, hold PLAY at power-on for about a second: m-bootloader's menu opens before any app runs (HW-117, HW-173). Reflash audio14 from there. REC held at power-on goes to download mode; the USB_KEY dongle forces the ROM's.
- **The run:**
  1. Power on the unit on the battery, cable out, nothing held: the instrument, with sound.
  2. Plug the cable into the Mac, which is awake.
  3. Open Audio MIDI Setup's MIDI Studio window. Does "small-beeps" appear?
  4. Notes from the Mac to the unit: do they sound?
  5. Notes from the unit's keys to the Mac: do they arrive (in any app that shows incoming MIDI)?
  6. Unplug, play a few keys to check the instrument carries on, then power off. The log holds the stages.
- **What each outcome means, and what comes next:**

  | Outcome | Next step |
  |---|---|
  | "small-beeps" appears, notes go both ways | U3 done. Our own product ID stays an open question for the owner; published builds keep USB off until then |
  | It appears, then drops or comes and goes, or notes stick | The port's spacing; the next round changes only that value |
  | Nothing appears; the log shows the set-up done but no host reset | The PHY or its clock. Back to the spec side; any write to `0x16A00` or a clock register comes to the owner first |
  | Nothing appears; the log shows the host's reset but no address or configuration | The device code or the descriptors; fwtest should have caught it. Fix both |
  | Notes go one way only | That direction's endpoint; the log's first-packet stages show which |
  | A poll gives up | The stage and index in the log; nothing more is written to USB and the instrument carries on |
  | The unit hangs or the instrument stops | Recover through m-bootloader's PLAY menu (above), reflash audio14, and report the last stage in the log |
  | The Mac warns or the port shuts down | Unplug at once and recover as above; report what the Mac said |

- How long the build took, and where the time went.

Finish with "done, ready to clear", Questions, one merge order.
