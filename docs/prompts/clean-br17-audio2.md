>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio2.md.
- Wait until the spec side's #211 has merged. Then read:
  - HARDWARE-SPEC section 38: HW-144 (audio1 on the unit, and what PLL2 and `CLK_CON2` hold after m-bootloader's call), HW-145 (what ALNK0's clock needs: known and open), HW-146 (routing, pins and mode: your SR-20, answered);
  - with them HW-140 to HW-142, HW-45, HW-53, HW-56, HW-85, HW-119, and the notes on Q-9;
  - docs/SPEC-REQUESTS.md, SR-20;
  - your own `firmware/src/hw_audio.c` (audio1).
- Take every fact from those.

## 1. audio2: audio1 plus one clock step, taken by hand
audio1 showed ALNK0 does not run after m-bootloader's call. audio2 is audio1 with more read back and one clock step the owner takes with a key. It is still a probe.
- **Keep audio1 as it is:** ALNK0 set up as in fwtest, the quiet tone, MASTER as its level, the key that stops and starts it, the interrupt count, `CON0` bit 15 and frames per second, and every register audio1 shows.
- **Read more, never write them:** add `CLK_CON0`, `CLK_CON1`, `SYS_DIV`, `PLL_CON0`, `PLL_CON1`, `PLL2_CON1`, and `JL_IOMAP`'s `CON2` to `CON8` (HW-146: the group select's reset value is unread). Show them after m-bootloader's call, and again after each step below.
- **The clock step (HW-145).** The only clock write any source gives is `CLK_CON2` bit 9 (the SDK's switched-off definitions, as ALNK0's clock enable; FM-1-RE's account runs against it). So:
  - Don't take it at start-up. A key takes it: read `CLK_CON2`, set bit 9 only, write it back, then read it back and show it. A second press puts back exactly the value read before the first, so the step can be undone.
  - Leave bit 8 as read (0, the 192 MHz / 17 choice, HW-145), and bits 10 and 11 as read.
  - Never write `CLK_CON2`'s low byte. Never write `PLL_CON0`, `PLL_CON1`, `PLL2_CON0` or `PLL2_CON1`: PLL2 clocks the processor after m-bootloader's call (HW-144).
  - After the step, show the interrupt count, `CON0` bit 15 and frames per second moving or not, as for audio1. Show which state the step is in (not taken, taken, undone).
  - Keep the rows on screen as start3b does, so a hang shows where.
- **No routing write.** HW-146 gives no register value for ALNK0's pin group, the pins' `DIR`, `DIE` or drive for the link, or `CON0` to `CON3`'s mode bits. Write none of them, and touch no port C register. If ALNK0 runs after the step, the next spec request is the routing; say so, don't guess.
- **Pins.** Drive no unknown pin. PC0 has a clock output of its own (`CLK_CON0` bits 10 to 12, HW-145); leave them as read.
- **The rest.** Everything presets1 and audio1 show stays as it is: core 1, the keys and encoders (all seven), MASTER, the store.

## 2. fwtest
In fwtest, ALNK0 plays as before (HW-44 to HW-46); `CLK_CON2` has no effect there (HW-53), so the step changes nothing. Add a seams case that runs audio2, presses the step's key and checks that the tone still plays in `audio.wav` at fwtest's 44 117.6 frames a second, and that a second press restores `CLK_CON2` exactly. The existing cases should pass unchanged.

## 3. For the owner
Tell the owner:
- what to photograph: the readback rows before the step, then after, and what each value means;
- when to press the step's key (after the tone has been started, so audio1's state is seen first), and how to undo it;
- what each outcome means for the next step:
  - after the step, the count and frames per second move: ALNK0 had no clock; note the frames per second (44 117.6 would fit 192 MHz / 17 with a 256-clock frame) and whether anything is heard; routing comes next;
  - they still don't move: bit 9 alone is not ALNK0's clock, or a source PLL output is off; the readback (`PLL_CON1`, `JL_IOMAP` `CON2` to `CON8`) is what the spec side needs next;
  - the unit hangs or the screen stops after the step: power it off; the step's row shows it was the cause.

Finish with "done, ready to clear", Questions, one merge order.
