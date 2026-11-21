>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

This adds to report1, which you are building now (audio3 plus the report log in a flash sector of its own, which the owner reads back as a full flash image after each run). Build H and I into that same build and branch, so the owner flashes one file. If report1 is already in an open PR, build on top of it, cumulatively.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio4.md.
- Read, on main (the spec side's #215 has merged):
  - HARDWARE-SPEC section 40: HW-150 (audio3), HW-151 (the general-purpose counter and the audio clock as its input), HW-152 (the data cache and the cores, your SR-21);
  - with them HW-43, HW-45, HW-53, HW-140, HW-145, HW-147, HW-148, and the notes on Q-9 and Q-18;
  - docs/SPEC-REQUESTS.md, SR-21.
- Take every fact from those.

## 1. Two more steps, each by its own key, each undoable
The owner has allowed H and I, and nothing else new. Keep audio3's steps (bit 9, A, B) as they are. As for A and B, each step:
- is taken only by a key press, and undone by a second press of the same key, which puts back exactly the values read before the first;
- shows its state (not taken, taken, undone), keeps the rows on screen as start3b does, and shows core 1's count alongside;
- **writes every reading to report1's log as well as the screen**: each value read before and after, each count, and the step's state, in the order taken, so a full flash image tells the whole run without the photos.

**Step H: measure the audio clock with the counter (HW-151).** It writes only `CLK_CON1` bits 4–6, by read-modify-write of those bits alone (bits 0–3, 10–11, 16 and the rest left as read), and `JL_GPCNT`'s own `CON`; it reads `NUM`.
- First a check of the counter itself: feed it the high-speed bus clock (`CLK_CON1` bits 4–6 = 3, the counted clock = the clock system's input), gated by the crystal oscillator, with a gate length you choose (32 × 2^n gate cycles). HW-119 gives the high-speed bus as 180 MHz and the crystal as 24 MHz (HW-54), so the count should be 7.5 × the gate's cycles. Log and show the count and the gate length.
- Then the audio clock (`CLK_CON1` bits 4–6 = 5), with the same gate, in each of these states, taken in turn: bit 9 clear; bit 9 set with bit 8 clear; bit 9 set with bit 8 set (audio3's keys set them; H measures whatever state they are in when its key is pressed, and a sub-key or repeated press re-measures). Expected if it is the audio links' clock: about 11.29 MHz with bit 8 clear and 12.31 MHz with it set; any other value, or 0, is the result.
- When `NUM` holds the last gate's count is not given (HW-151). Wait for the pending flag (bit 7), clear it with bit 6, take two readings a gate apart, and log both, so a count that is still running shows itself. Time out rather than wait forever, and say so if it times out.
- Undo: put `CLK_CON1` back exactly as read before the first press, and `JL_GPCNT->CON` as read (or 0 if it read 0).
- Log and show: `CLK_CON1` before and after each write, `JL_GPCNT->CON` before and after, every `NUM` reading, the gate length, and `CLK_CON2` at the moment of each measurement.

**Step I: ALNK1 (HW-140, HW-145).** ALNK1 is at `0x00015100`, the same layout as ALNK0, interrupt source 12. Set it up as ALNK0 is in fwtest (HW-44, HW-45), from its own buffer, but **don't take source 12**: leave that interrupt off and watch ALNK1 by polling its `CON0` bit 15 and its `CON2` bit 7, counting changes. Its clock bits are `CLK_CON2` bit 11 (enable) and bit 10 (choice), the same switched-off SDK definitions as ALNK0's bits 9 and 8:
- I's key sets ALNK1 running (`CON0` bit 11) and `CLK_CON2` bit 11, by read-modify-write of that bit alone; a sub-key or second step sets bit 10 too, as B did for bit 8. Bits 0–7 of `CLK_CON2` are never written.
- Undo: stop ALNK1 (`CON0` as read before) and put `CLK_CON2` back exactly as read before the first press.
- Log and show: ALNK1's `CON0` to `CON3` before and after, the half changes counted and halves a second (timed as audio1 times ALNK0's), `CLK_CON2` before and after, and core 1's count.
- No pin is routed for ALNK1 (HW-146); this asks only whether ALNK1 runs.

**Not included:** D (`JL_IOMAP->CON5`) gets its own prompt, and only if H shows an audio clock while ALNK0 stays dead. No PLL register, no `CLK_CON2` low byte, no `JL_IOMAP` write, no port C register.

Suggested order on the unit: H's counter check; H with bit 9 clear; bit 9 (audio3's key) then H; B then H; undo all; then I, and I with bit 10. Your key mapping is yours; say it on the screen.

## 2. fwtest
In fwtest the clock registers have no effect (HW-53) and the counter is whatever fwtest gives (if it gives nothing, say so and have the seams case check only that H reads, writes and undoes as it should, without a hang). ALNK1 in fwtest: say whether it plays; if it does, check its halves at 44 117.6 a second. Extend the seams case so H and I and their undos are pressed and every undo restores the values read before. The existing cases should pass unchanged.

## 3. For the owner
Tell the owner, in one list:
- the keys and the order to press them;
- that the log holds every reading, and how to read H's and I's entries from the flash image;
- what each outcome means:
  - H's check is not 7.5 × the gate: the counter isn't read as HW-151 says; stop there and report;
  - H shows an audio clock (with bit 9, near 11.29 or 12.31 MHz) and ALNK0 stays dead: the clock is there and something gates the link; D comes next (its own prompt);
  - H shows no audio clock in any state: the audio clock isn't running after m-bootloader's call; E and F are what remain, for the owner's ruling;
  - ALNK1 runs where ALNK0 doesn't: note its halves a second; the difference between the links is the next spec question;
  - ALNK1 is dead too: both links fail the same way.

Finish with "done, ready to clear", Questions, one merge order.
