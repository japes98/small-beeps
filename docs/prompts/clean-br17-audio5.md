>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

This adds to leds1, which you are finishing now (the key LEDs on top of report1). Build K and J into that same build and branch, so the owner flashes one file. If leds1 is already in an open PR, build on top of it, cumulatively.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio5.md.
- Read, on main (the spec side's #219 has merged):
  - HARDWARE-SPEC section 41: HW-153 (report1's log: the counter checked, input 5 at 48.00 MHz in every state, ALNK1 dead, `DAA_CON7` corrected) and HW-154 (what the 48 MHz says);
  - with them HW-43 to HW-45, HW-53, HW-140, HW-145, HW-146, HW-151, and the notes on Q-9.
- Take every fact from those.

## 1. Two more steps, each by key, each undoable, every reading in the log
The owner has allowed K and J, and nothing else new. Keep every earlier step (bit 9, A, B, H, I) as it is. As before, each step is taken only by a key, is undone by putting back exactly the values read before, shows its state and core 1's count, keeps its rows on screen as start3b does, and **writes every reading to report1's log as well as the screen**, in the order taken.

**Step K: what input 5 is (HW-154).** Same method and gate as H (the crystal oscillator as the gate, the same gate length, two readings a gate apart, a timeout, the pending flag not relied on). It writes only `CLK_CON1` bits 4–6 and bits 2–3, each by read-modify-write of those bits alone, and `JL_GPCNT->CON`.
1. Count each clock-system input in turn through `CLK_CON1` bits 4–6 (the counter set to count the clock system's input, as in H): 3 (the high-speed bus, as H's check), 1 (the sample-rate converter's clock), 5 (the audio clock), 6 (the wireless block's), 7 (the USB's).
2. Count the counter's own 480 MHz input directly (its counted-clock choice 6, HW-151), with the same gate.
3. Then the DAC's clock choice, `CLK_CON1` bits 2–3 (HW-53: 0 the PLL's 24 MHz, 1 the oscillator, 2 the low-speed bus, 3 off; it reads 0): with bits 4–6 = 5, set bits 2–3 to 1, measure input 5; to 2, measure; to 3, measure; then put bits 2–3 back as read and measure again. If input 5 follows the DAC choice (24 MHz, 60 MHz, 0), it is the audio block's clock; if it stays at 48 MHz, it is not.
- Undo: `CLK_CON1` and `JL_GPCNT->CON` back exactly as read before K's first press.
- Log and show: for every measurement, `CLK_CON1` and `JL_GPCNT->CON` as written, both `NUM` readings, the gate length and `CLK_CON2`.

**Step J: ALNK0's own `CON1` and `CON3`, one bit at a time.** ALNK0's `CON1` (16 bits) and `CON3` (8 bits) read 0, and no source gives their bits (HW-146). The owner allows trying each bit alone. J writes only ALNK0's `CON1` and `CON3`: no pins, no other register.
- With ALNK0 running (`CON0` bit 11, as now) and `CLK_CON2` in whatever state audio3's keys left it (log it; suggest the sweep with bit 9 set, then again with bit 9 clear if time allows), J's key tries the next bit: it puts back the previous try's register exactly as read before it, then sets the one new bit (`CON1` bits 0 to 15, then `CON3` bits 0 to 7) with every other bit as read, reads the register back, waits a fixed time (say 100 ms), and records the result. A second key undoes the try in progress (the register back as read) without moving on. Show which bit is being tried.
- For every try, log and show: the register and bit, the value written and the value read back (so bits that don't hold show themselves), `CON0` and `CON0` bit 15 changes counted, `CON2` (the pending flags), source 11's count, `CLK_CON2`, and core 1's count.
- If any try makes `CON0` bit 15 move or source 11 count, stop the sweep there, keep that bit set until the owner undoes it, and show that it moved.
- If a try hangs the unit, the log's last record says which bit; power it off.

**Not included:** D (`JL_IOMAP->CON5`), any PLL register, `CLK_CON2`'s low byte, `JL_IOMAP`, any port C register, ALNK1's `CON1`/`CON3`. E and F come up for the owner's ruling only after K and J have both been tried and failed.

Suggested order on the unit: K (all of it), then J with bit 9 set, then J with bit 9 clear. Your key mapping is yours; say it on the screen and in the log.

## 2. fwtest
In fwtest the clock registers have no effect (HW-53); say what the counter gives there. ALNK0's `CON1` and `CON3` have no effect in fwtest beyond being stored, if that is what fwtest does; say so. Extend the seams case: K and J are pressed (J through at least a few bits and an undo), every undo restores the values read before, and the tone keeps playing in `audio.wav` at 44 117.6 frames a second. The existing cases should pass unchanged.

## 3. For the owner
Tell the owner, in one list:
- the keys and the order to press them;
- how to read K's and J's entries from the flash image;
- what each outcome means:
  - K: input 5 stays 48 MHz whatever the DAC choice, and matches the USB's or another input's count: it is the shared PLL clock, which the owner has ruled counts as "no audio clock";
  - K: input 5 follows the DAC choice: it is the audio block's clock, and D (its own prompt) comes next;
  - J: a bit makes ALNK0 run: which bit, its readback, halves a second; routing is the next spec request;
  - J: no bit does: with K, that is the case for E and F, for the owner's ruling.

Finish with "done, ready to clear", Questions, one merge order.
