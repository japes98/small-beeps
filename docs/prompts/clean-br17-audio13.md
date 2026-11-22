>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

**Working (the owner's rule for every clean prompt):**
- While iterating, run only the seams cases the change touches.
- Run tools/check-emulator-terms.py with COMMIT_RANGE=origin/main..HEAD before every push, and don't push while it fails.
- Open the PR once those pass and the .fwsc is packed. CI runs the full suite; don't do a full local run before the PR.
- The owner flashes once the file has been checked, without waiting for CI.
- Say how long the build took and where the time went: compiling, fwtest runs, container start-up, packing, other.

This is audio13, built on audio12b (#241). audio12b worked on the unit:
- SEL's instrument start logged every stage in order, with sound.
- The sweep in Bell gave 982 to 1 018 µs for 8 voices in every algorithm, nothing clipped and no half late.
- The algorithms were heard to differ, so G is confirmed.
- The stop worked and `MASTER` was smooth.
- ARP was not tried.

audio13 does three things in one flash:
- power-on goes straight to the instrument (D5);
- the USB block is read, never written (U2);
- ARP is checked, with each step's timing logged.

The owner's rulings: D5 as ruled; U2 as ruled (docs/prompts/spec-usb-u2-rulings.md and spec-usb-u2-rulings2.md, on main with #242); the ARP check in the run steps. The owner approved this prompt's run order, ARP settings, keys and outcomes as drafted (2026-11-22). The unit runs with or without the cable, so state a (no cable, on the battery) works as written. D8 (levels), the store (saving patches) and the fwtest harness change come in later rounds.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio13.md.
- Read, on main (the spec side's round PR has merged):
  - HARDWARE-SPEC section 50 (HW-174, HW-175: audio12b on the unit);
  - section 49 (HW-171 to HW-173, Q-36: the USB block);
  - HW-86, HW-91, HW-117 and HW-129.
- Take every fact from those.

## 1. D5: power-on goes straight to the instrument (the owner's ruling)
- **Power-on with nothing held:** audio12's instrument start (#240), from cold:
  - the engine, then the synth, ALNK0 in N, L2, port C's four pins, and the route with the matrix check and its self-undo;
  - then the panel with sound and no test screen.
  - Keep audio12b's record and step row before each stage (`Inst synth` … `Inst panel`), so a hang names its stage.
- **HOME held at power-on gives the test screen,** as audio12 built it. Its keys work there and nowhere else, and SEL there runs the instrument start as in audio12b.
- **If the self-undo fires,** the instrument still runs, silent, and the panel shows "NO SOUND: <reason>".
- **Pack from the package link** (`app-pkg.bin`, entry `0x02000120`, HW-91). Say that `fwsc pack` refused nothing else on the way.

## 2. U2: the USB block, read only (the owner's rulings)
Reads only:
- No USB register is written, and no pin's set-up changes.
- Nothing is written through the core's access port (`CON1`), because an access there is itself a write (HW-86).
- USB stays off in every build (R-USB-1).

Pick a test-screen key for each of: U2-A's re-read, the state key and U2-C. Use keys the test screen doesn't use already (LFO, EDIT, SEL and HOME are taken), and say which you chose.

### U2-A: what the USB block holds when the app starts
- **When:** at the very start of the app, before anything else runs and **before the audio path starts** in either start, the instrument's or the test screen's. Read again a second later, and on its key in the test screen.
- **What:** the first core's `CON0` and `CON1` (`0x11800`, `0x11804`), and the pins' block's three words (`0x51000`, `0x51004`, `0x51008`).
- Keep the first reading in RAM until the log is up.
- Log each word in hex, and show the start's reading in the test screen's large area.
- **Keep each start's reading** in the log, the last few starts at least, so both of the owner's starts (section 5) are there to read. Each start's reading must reach the flash log without a save key, because the owner powers off between starts (in that start's boot record, say). Say how it gets there.

### U2-B: cable detect, by reading
- **While the test screen shows it:** read U2-A's five words every 100 ms, and log every change with its time.
- **The state key** marks each change of cable state in the log, stepping a, b, c, d, e:
  - a: no cable, on the battery;
  - b: a cable to a USB charger, power only;
  - c: a cable to a computer that is on;
  - d: that computer asleep;
  - e: the cable out again.

  The owner never reads numbers.
- **The large area** shows the state letter, and whether any of the five words differs from its value in state a: "same as a", or "changed" with which word.
- **Say which bits follow the cable.** HW-171 names the candidates in `CON0`: bit 5 `VBUS`, bit 4 `CID`, bit 15 `CHKDPO`, bits 16 and 17 `DM_SE` and `DP_SE`. Their meanings are not given, so the reading decides.

### U2-C: the D− and D+ pads through the SARADC
- **Its own key, off at start-up,** so it can't affect U2-A or U2-B. The screen shows whether it is on.
- **While on:** channels 12 and 13 (USB D− and D+, HW-129, HW-173) join audio11's SARADC sweep, one channel a pass, as the others. Log their readings with the state letter.
- **The only write is the SARADC's own `CON`,** as audio11 writes it.
- Say whether the readings move the moment a channel is chosen.

## 3. ARP: checked on the unit, its step timing logged
- **In the instrument (the panel),** ARP on at 120 beats a minute in sixteenths, the settings of fwtest's ARP suite. Say how the owner turns it on and off from the panel.
- **For each step, log:**
  - the engine's frame count;
  - the time by a timer the audio interrupts don't drive (say which: the one the fill times use, say).
- **Summarise over at least 64 steps:** the shortest and longest gap in frames and in µs.
- **The large area** shows the last gap in frames and in ms while ARP runs.
- **A save in the panel:** the ARP log must reach the flash log before the owner powers off. Give the panel a key, or a hold, that writes the log (not the store), and name it.
- **Expected:**
  - 5 514 or 5 515 frames apart, as in fwtest's two layouts (#240).
  - 125 ms apart (a sixteenth at 120 beats a minute). That holds only if the audio's rate is the one assumed: 128 frames in 2 902 µs.

## 4. Not included
- No register written beyond audio12b's: U2 only reads; U2-C writes only the SARADC's `CON`, as audio11 does.
- No pin driven beyond audio12b's; no port B write.
- No store write; the store stays unstarted on the unit.
- No level change or bass boost (D8 is later).
- `--audio-chip` stays unadopted; the harness change is later.

## 5. For the owner (the run, one flash)
Keys and order, on the battery with no USB cable unless a step says otherwise:
1. **Power on with nothing held.** This is U2-A's first start, from power-off. The panel should come up with sound and no test screen. Play some keys and turn `ALGORITHM`.
2. **Turn ARP on** as section 3 says, and hold a chord for about 20 s. Listen for even steps, about 8 a second. Then turn ARP off, and **save the log** with the panel's save (section 3) before powering off.
3. **Power off.** Open m-bootloader's menu, enter MIDI mode and leave it by a key into the app, with no cable. This is U2-A's second start.
4. **Power off. Power on with HOME held,** for the test screen (a third start; its U2-A reading goes in the log as well). Run U2-B with U2-C off: states a to e, about 10 s each, pressing the state key at each change.
5. **Turn U2-C on** and run U2-B again: states a to e.
6. **EDIT to save the log.**
- **If the power-on start hangs:** the step row and the last `Inst …` record name the stage. HOME held still gives the test screen, and m-bootloader's menu is still at power-on.
- **If a U2-A read hangs the unit:** m-bootloader's power-on key still opens its menu (HW-173). Report it; U3 then waits on Q-36.

## 6. fwtest
Extend the seams cases you touch:
- **D5:** the power-on start reaches the panel with sound. HOME held reaches the test screen. The self-undo is forced through the test seam. Run it on the package link through `--package`, as #241's case does.
- **U2-A:** the five words read and logged at the start, before the audio path in both starts, and on the key. Without `--usb`, fwtest reads them as last written, so 0.
- **U2-B:** the state key steps a to e, and the large area shows the letter and "same as a" / "changed" (a word changed through the test seam).
- **U2-C:** off at start-up, and channels 12 and 13 are in the sweep only while it is on.
- **ARP:** steps 5 514 or 5 515 frames apart on both layouts, with each step's two times logged.
- No `--usb` run is needed.

## 7. What each outcome means
- **D5: sound at power-on with no test screen:** the audio path is the instrument's.
- **D5: "NO SOUND: <reason>":** the start from cold differs from the test screen's start, and the reason names the check.
- **D5: a hang:** the stage is named, and the next round fixes that stage.
- **ARP: steps 5 514 or 5 515 frames apart, and about 125 ms:** ARP is right on the unit.
- **ARP: frames right, ms off:** the audio's rate isn't the one assumed. That is a Q-9 question for the spec side.
- **ARP: frames off:** the engine's frame count is wrong on the unit, and clean fixes it.
- **U2-A: every word 0 in both starts:** the core is off at the app's start. U3 needs Q-36 settled first.
- **U2-A: bits set after MIDI mode only:** m-bootloader's stop leaves part of the core up.
- **U2-A: bits set from power-off as well:** the ROM or m-bootloader's normal start leaves them.
- **U2-A: a read hangs:** the block isn't clocked at the app's start. Q-36 comes first.
- **U2-B: a bit follows the cable:** cable detect is solved by reading.
- **U2-B: no bit follows:** cable detect needs the PHY on (a write, a later ruling) or U2-C's pads.
- **U2-C: the pads differ per state:** they tell charger from computer from nothing, with no USB write.
- **U2-C: the pads are the same in every state:** U2-C is dropped.

In one list for the owner: how long the build took and where the time went; the candidate and its checks; the keys you chose; the run as in section 5.

Finish with "done, ready to clear", Questions, one merge order.
