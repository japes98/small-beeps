>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

This adds to the core-1 probe you are already building (the count at fixed points, the key that stops and restarts ALNK0 without the clock step, core 1's data in its own block, the 0x80–0x8F words). Build it into that same build and branch, so the owner flashes one file. If that probe is already in an open PR, build on top of it, cumulatively.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio3.md.
- Wait until the spec side's #213 has merged. Then read:
  - HARDWARE-SPEC section 39: HW-147 (audio2: bit 9 alone does not start ALNK0; the readback), HW-148 (what the values say), HW-149 (core 1 stops once ALNK0 is started; your hypothesis, recorded as one);
  - with them HW-45, HW-144 to HW-146, and the notes on Q-9.
- Take every fact from those.

## 1. Two more steps, each by its own key, each undoable
The owner has allowed two steps, A and B, and nothing else. Keep audio2's bit-9 step as it is. Each step:
- is taken only by a key press, and a second press of the same key undoes it exactly (the value read before the first press put back);
- shows, before and after, the rows audio2 shows (the interrupt count, `CON0` bit 15, frames per second, `CLK_CON2`, `CON0`), with **core 1's count alongside**, so whether core 1 runs is seen at each step;
- shows which state it is in (not taken, taken, undone), and keeps the rows on screen as start3b does, so a hang shows where.

**Step A: restart the link after its clock (HW-148).** With bit 9 set by audio2's step, clear `CON0` bit 11, then set it again (HW-45's start). Undo: put `CON0` back as read before the press. Source: HW-45 (fwtest only); no source says a restart is needed, so this is a probe.

**Step B: the other clock choice (HW-145).** Set `CLK_CON2` bit 8, by read-modify-write of that bit alone, with bit 9 set. Undo: put back `CLK_CON2` exactly as read before the press. Bit 8 = 1 is the SDK's other choice (12.31 MHz; its two lists name it two ways); if ALNK0 runs with it, expect about 48 077 frames a second rather than 44 117.6 (if a frame is 256 clocks, which no source says). Source: the SDK's switched-off definitions only.

**Not included:**
- Step C (`CON3`'s data 3 enable): dropped. FM-1-RE gives no bit for each data channel without the stock firmware's writes, which may not be used (note on Q-9).
- Any `JL_IOMAP` write, any PLL register, `CLK_CON2`'s low byte or bits 10 and 11, any port C register: not allowed until A and B have been tried.

Suggested order on the unit: bit 9 (audio2's key), then A, then undo A, then B, then A again with B taken. Your key-to-step mapping is yours; say it on the screen.

## 2. fwtest
In fwtest, `CLK_CON2` has no effect (HW-53), and A restarts the link as HW-45 says. Extend audio2's seams case: press A and B and their undos, and check the tone still plays in `audio.wav` at 44 117.6 frames a second and that every undo restores the value read before. The existing cases should pass unchanged.

## 3. For the owner
Tell the owner, in one list:
- the keys: the core-1 probe's, audio2's bit-9 step, A and B;
- the order to press them, and what to photograph after each (with core 1's count);
- what each outcome means:
  - ALNK0 runs after A: it needed starting after its clock; note frames per second; routing comes next (a spec request);
  - ALNK0 runs after B (alone or with A): the other clock choice works; note frames per second;
  - neither: bit 9 with either choice is not enough; the spec side sets out D to F for the owner's ruling;
  - core 1 stops or starts at any step: which step, with the count before and after.

Finish with "done, ready to clear", Questions, one merge order.
