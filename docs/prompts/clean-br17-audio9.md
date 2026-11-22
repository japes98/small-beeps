>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

**Working (the owner's rule for every clean prompt):**
- While iterating, run only the seams cases the change touches.
- Open the PR once those pass and the .fwsc is packed. CI runs the full suite; don't do a full local run before the PR.
- The owner flashes once the file has been checked, without waiting for CI.
- Say how long the build took and where the time went: compiling, fwtest runs, container start-up, packing, other.

This is audio9, built on audio8 (#229). audio8 found the sound path: with L2 running, PC0, PC1, PC2 and PC6 as outputs and ALNK0's `CON0` bits 7 and 8 set, the speaker plays the tone, with `JL_IOMAP->CON5` left at 0. audio9 makes that the running state and puts the synth on it. The owner has ruled (the spec side saves the rulings with the next round's PR): S0 allowed; S1 allowed, off at start-up and switched by a key; S2 allowed; each half's fill sized separately for the unit and fwtest this round, with fwtest's `LEN` change left for a later spec PR.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio9.md.
- Read, on main, once the spec side's #230 has merged (it also carries your #229). If it hasn't merged yet, build the parts that need no facts first and read section 45 when it lands; don't open the spec branch:
  - HARDWARE-SPEC section 45: HW-161 (audio8 on the unit) and HW-162 (what it settles: path 2, `CON5` at 0 is port C, no enable for the speaker, PB5 follows the plug, port C's `IN` can't see the link's pins);
  - with them HW-56, HW-141, HW-156, HW-159, HW-160 and the notes on Q-9.
- Take every fact from those.

## 1. S0: the route at start-up, a steady tone, PB5 on screen
- **At start-up,** once the test screen is up, in this order:
  1. L2, as audio8 does (audio7's write order, log, 1 s watch and matrix check). If the link doesn't move, or the check fails, undo it, log and show it, and go no further.
  2. R2, as audio8 does: PC0, PC1, PC2 and PC6 `OUT` high, then `DIR` 0, then `DIE` on, by read-modify-write of those four bits alone.
  3. The route: hold the matrix and LED scan, latch `0xFFFF`, check the rows are idle, then set `CON0` bits 7 and 8, read back. `CON5` is not written.
  4. Port A sampled for 100 ms as in audio8, then D's matrix check. If port A moved or the check fails, the firmware undoes the route itself (bits 7 and 8, then R2), re-checks, and logs and shows it. Otherwise the scan resumes and the route stays.
  - There is no port C movement check: port C's `IN` can't show the link's pins (HW-162).
- **The tone:** steady, the same 16-bit form as audio8 (one sample in both halves of each word), at `MASTER`'s level, quiet. `MASTER` at 0 must give silence.
- **Undo by key:** one key takes the route down (bits 7 and 8 clear, then port C back as read) and puts it back up with steps 3 and 4. Say which key.
- **PB5 on screen as the headphone state:** read port B's `IN` bit 5 every scan and show it as 0 or 1, with a count of changes; log each change with its time. Which level means "plugged" is not given: show the raw bit, and the owner says which. Write nothing to port B.
- **`DAA_CON7`:** read and logged at start-up, after the route and each minute; never written.

## 2. S1: the synth on this path
- The synth's output (fm_play) fills the halves in place of the tone, in the same 16-bit form, the same sample in both halves, so the keys play notes. One key switches between the tone and the synth; the synth is off at start-up, so S0's tone is heard first.
- The rate is 44 117.6 frames a second (HW-160); say what rate the engine assumes and what that does to pitch.
- A half is `LEN` frames, 128 at audio1's set-up: about 2.9 ms. Count halves the engine filled late (the link reached a half before the engine finished it), show the count on screen and log it with the longest fill time, against the timer audio1 uses.
- The matrix and knobs must keep working with the route up; that is what the keys playing notes shows.
- fwtest plays its own format (HW-44): say how the build picks the synth's output format by target.
- **The fill length differs by target.** On the unit a half is `LEN` frames of one word each (HW-160); fwtest plays `LEN` words a half in its own format, half as many frames. The owner's ruling: the build sizes each half's fill per target and states both sizes; fwtest's `LEN` change comes in a later spec PR. So the fwtest case shows the notes play, not the unit's fill timing; the unit's late-half count is that check.

## 3. S2: which half of the word is left
On headphones only.
- One key cycles the tone through: both halves; the upper half only (the lower 0); the lower half only (the upper 0); back to both. The screen names the state.
- The owner listens on headphones for the left and right ears. If the headphone output is mono, both will sound alike; that is a result too.

## 4. Not included
- `JL_IOMAP` (`CON5` included; no word is written), any PLL register, `CLK_CON1`, `CLK_CON2`'s low byte, the analogue registers (`DAA_CON7` included), ALNK1, `CON1` beyond `0x1000`.
- No pin driven to find an amplifier enable or a mute. No port B write.
- No key-matrix pin written beyond leds1's scan and the `0xFFFF` latch.
- The CON5 sweep, step 1's two-part sampling and the sense scan: their keys may go; say what stays.

## 5. fwtest
- Extend the seams cases you touch:
  - the start-up chain (L2, R2, the route) with its self-undo forced through the test seam (a port A movement, a failed check);
  - the route's undo and redo by key, port C back as read;
  - PB5's display with the seam toggling port B's `IN`;
  - S1: notes play into `audio.wav` at 44 117.6 frames a second, and the late-half count stays 0;
  - S2: each state's words as expected.

## 6. For the owner
In one list:
- how long the build took, and where the time went;
- the keys and order;
- **before plugging in headphones, turn `MASTER` down**, then bring it up;
- what to listen for: the tone on the speaker; then headphones in: the speaker muted or not, the tone in the headphones or not; PB5's state each way;
- what each outcome means:
  - **the tone on the speaker; headphones in mutes it and the tone is in the headphones; PB5 follows:** the output path is whole, and the mute is in the hardware. Next: the synth (S1), then levels.
  - **the tone on the speaker, and in the headphones, but the speaker isn't muted:** the mute needs a pin the firmware sets, keyed by PB5. Next: the board photo (R1) or the owner's list of candidate pins, for a ruling.
  - **the tone on the speaker, silent on headphones:** the headphone path needs something not yet set (an enable, or a separate output). Next: R1.
  - **no tone at start-up, though L2 ran and the route held:** the start-up order differs from audio8's in some way that matters. Next: compare the logs with audio8's.
  - **the route's self-undo fires:** unexpected, since audio8's step 1 passed. Note what port A read.
  - **S1: notes play cleanly, with no late halves:** the synth's path is done. Next: levels, the sample order (S2) and the engine's load.
  - **S1: notes break up, or late halves count:** the engine can't fill a half in time on the unit. Next: the engine's load, a longer `LEN`, or core 1.
  - **S2: one state sounds in one ear only:** that half is that side. **Alike in both:** the headphone output is mono, or both halves are mixed.

Finish with "done, ready to clear", Questions, one merge order.
