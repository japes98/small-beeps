>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

This is audio6: audio5 (your #222, merged on main) plus one step, D. Build it on main as audio5 left it, so the owner flashes one file. If you have audio5 follow-ups in an open PR, build on top of it, cumulatively.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio6.md.
- Read, on main once the spec side's #223 has merged:
  - HARDWARE-SPEC section 42: HW-155 (audio5: input 5 is the DAC clock; no single bit of ALNK0's `CON1` or `CON3` starts it) and HW-156 (what that says, and ALNK0's port A pin group);
  - with them HW-45, HW-85, HW-117, HW-118, HW-138, HW-141, HW-146, HW-148, HW-153, and the notes on Q-9.
- Take every fact from those.

## 1. Step D: `JL_IOMAP->CON5`, one bit at a time, each try checked and undone by the firmware itself
The owner has allowed D, and nothing else new. Keep every earlier step (bit 9, A, B, H, I, K, J) and leds1 as they are. No source gives any value for `CON5` (HW-146): D is a blind try, allowed under these limits.

**Why the firmware checks and undoes each try itself.** If `CON5` picks ALNK0's pin group and a value picks group B1, the link may take over PA4 to PA10: the matrix's shift-register data, its rows PA5 to PA8 and the LED lines PA9 and PA10 (HW-156). Then no key may work, so **no undo may depend on a key press.**

**Pacing: one key press runs the whole sweep (the owner's ruling).** D's key starts an automatic sweep of 32 tries, in this order: `CON5` as read with bit 0 alone set, then bit 1 alone, up to bit 31, each with every other bit as read. The firmware does each try, its checks and its undo by itself, exactly as below. The firmware's own matrix check stands in for a key press between tries. Show which bit is being tried.

**Where the sweep stops.** It stops at the first try whose matrix check fails (step 4 or step 6) or whose link moves (step 3), and shows that try. It takes no further try. Otherwise it runs to bit 31 and shows that it finished with no stop. A press of D's key while it runs stops it after the try in progress, which the firmware undoes as usual.

**Each try, in this order:**
1. **Log before the write.** Write a log record naming the bit about to be tried. Log the values read before it:
   - `CON5`;
   - `JL_IOMAP` `CON0` to `CON8`;
   - port A's registers (`DIR`, `OUT`, `IN`, `PU`, `PD`, `DIE`, `HD0`, `HD`);
   - `CLK_CON2`;
   - ALNK0's `CON0` to `CON3`;
   - source 11's count;
   - core 1's count.
   The record must be complete in the flash before step 2, so if the unit hangs, the log's last record names the bit.
2. **The write.**
   - Pause the matrix and LED scan with port A as it stands.
   - Write `CON5` with the one new bit set and every other bit as read.
   - Read `CON5` back.
   - Write nothing to the flash until step 5 has restored `CON5` or kept the bit.
3. **The watch.** For a fixed time (say 100 ms):
   - count `CON0` bit 15's changes, `CON2`'s pending flags and source 11's interrupts;
   - read port A's `IN` at the start and the end.
4. **The matrix check, with the bit still set.**
   - Latch `0xFFFF` (no column) and read rows PA0 and PA5 to PA8: all must read high.
   - Then scan every column once as leds1 does: with no key held, no key may read closed. (Your scan's port A writes are leds1's own. D adds no new port A write.)
   - Then read port A's registers again and compare them with step 1's.
   - The check fails if any of these differs: the idle rows, the scan, or `DIR`, `PU`, `PD` or `DIE` against step 1.
5. **The undo.**
   - **If the link moved** (bit 15 changed or source 11 counted) **and the matrix check passed:** keep the bit set and stop the sweep. Show and log that it moved. The owner's undo key puts `CON5` back as read.
   - **In every other case,** the firmware puts `CON5` back exactly as read before the try, and reads it back. That includes "the link moved, but the check failed": log the movement and the failure, then undo. If the check failed or the link moved, the sweep stops here, after steps 6 and 7.
6. **The check after the undo.**
   - Read port A's registers and `JL_IOMAP` `CON0` to `CON8` again, and repeat step 4's matrix check.
   - If `CON5` didn't go back as read, or port A or the matrix doesn't match step 1, stop D: take no further try, and show and log which.
   - Resume the scan.
7. **Log after.** Write the try's record:
   - the bit, the value written and the value read back (bits that don't hold show themselves);
   - every count from step 3;
   - port A's `IN` readings;
   - the matrix check's result with the bit set and after the undo;
   - `CLK_CON2`, ALNK0's `CON0` to `CON3`, core 1's count;
   - whether the firmware undid the try, or kept the bit set because the link moved.

**On screen.** For the try in progress, and for the try the sweep stopped at, show on screen, keeping the rows as start3b does:
- port A's registers and the row readings, before and after;
- the bit, and the value written and read back;
- the counts and the matrix check's result;
- core 1's count.

Every try's readings are in the log; the screen shows port A before and after the try in progress and the one the sweep stopped at.

**States.** The owner runs the sweep twice:
- once with `CLK_CON2` bit 9 set (audio2's key);
- once with bit 9 clear;
- the DAC clock's choice (`CLK_CON1` bits 2 and 3) left as read.

Log `CLK_CON2` at each try. If the log sector can't hold every record, say how many tries fit, and have the screen and the log say where it filled.

**Writes.** D writes only `JL_IOMAP->CON5`.
- No other `JL_IOMAP` word, ever: `CON0` bit 5 and `CON1` bit 1 select the flash's pins (HW-85).
- No port A write beyond leds1's own scan, and no port C register.
- No PLL register, no `CLK_CON2` low byte.
- No ALNK0 `CON1` or `CON3` bit beyond what J leaves (put J's register back as read before D, and log it).

**If the unit hangs:** the log's last record names the bit. Power it off. m-bootloader sets the clocks again at each start. `CON5` has read 0 after m-bootloader on every run so far, which is a past reading, not a source.

**Not included:** E and F (PLL2, the system clock), any other `JL_IOMAP` word, combinations of bits, ALNK1 (D watches ALNK0 only).

## 2. fwtest
Say what fwtest does with `JL_IOMAP->CON5` (stored only, or ignored). Extend the seams case:
- press D's key and run the whole sweep with no hang, checking that each try puts `CON5` back as read and that the matrix check passes;
- through a test seam, force one failed matrix check, and see the firmware undo that try by itself and stop the sweep there; likewise force a link movement and see the bit kept and the sweep stopped;
- check that the tone keeps playing in `audio.wav` at 44 117.6 frames a second.
The existing cases should pass unchanged.

## 3. For the owner
Tell the owner, in one list:
- the keys and the order to press them (D's key once with bit 9 set, once clear), how to stop a sweep, and how to undo a kept bit;
- how to read D's records from the flash image;
- what each outcome means:
  - **a bit makes ALNK0 run and the matrix still works:** note which bit, its readback and the halves a second. The group's value, the pins' set-up and whether anything is heard come next, in a spec request.
  - **a bit makes ALNK0 run but breaks the matrix:** the firmware undid it. That bit likely moves the link to port A's group B1. Note the bit and what port A read.
  - **a bit breaks the matrix, and ALNK0 stays dead:** the firmware undid it. Note the bit and what port A read.
  - **the unit hangs:** power it off. Report the last record's bit.
  - **no bit moves ALNK0:** with K and J, D has failed. E and F come up for the owner's ruling.

Finish with "done, ready to clear", Questions, one merge order.
