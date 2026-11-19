>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio1.md.
- Wait until the spec side's #206 has merged. Then read:
  - HARDWARE-SPEC section 36: HW-140 (the audio blocks and their interrupts), HW-141 (the two possible output paths, the pins, the speaker and headphones), HW-142 (clocks, rate, DMA and the analogue side, known and open);
  - with them HW-43 to HW-46, HW-56, HW-119, HW-129, HW-130 and HW-139, and the notes on Q-9;
  - your own `firmware/src/audio.c`, which drives ALNK0 in fwtest.
- Take every fact from those.

## 1. audio1: a first audio probe for the unit
A hardware build, like start3 and encoders1, that tells the next unit run whether ALNK0 runs on the chip and whether any sound comes out. It is a probe, not the synth.
- **The output.** ALNK0 set up as `audio.c` does in fwtest (HW-43 to HW-45), playing from data 3, on the port C pins HW-141 names. Use their audio link function as HW-56 describes pin mapping; if the spec doesn't say how to select ALNK0's pin group, say so and file a spec request rather than guessing a register.
- **The sound.** A quiet tone, a few hundred Hz, the same in both channels, with a soft start and stop. Use MASTER (ADC channel 4, HW-133) as its level if that is easy; otherwise a fixed low level. Start it after the test screen is up, and let a key stop and start it.
- **Read, never write.** Show these on the screen as read after m-bootloader's call and again once the tone runs, as observed values only:
  - `PLL2_CON0` and `CLK_CON2` (HW-142);
  - `JL_ANA`'s `DAA_CON0` to `DAA_CON3`, `DAA_CON7` and `ADA_CON0` to `ADA_CON2` (HW-140);
  - `JL_AUDIO`'s `DAC_CON`;
  - ALNK0's `CON0` to `CON3`, and the pin-map register you used.

  Write nothing to the analogue block, PLL2, the clock registers or `JL_AUDIO`: no source gives their values yet.
- **Whether ALNK0 runs.** Count source 11's interrupts. Show `CON0` bit 15 changing, and the halves per second, timed against a timer whose clock HW-119 gives, as frames per second. That settles the rate on the unit without a scope.
- **Pins.** Drive only the four pins HW-141 names, and only through the audio link. Drive no other unknown pin while looking for an amplifier enable (PD6, for one, is the flash's power gate, HW-56).
- **The rest.** Everything start3 and encoders1 show stays as it is: core 1, the keys and encoders, MASTER, the store.

## 2. fwtest
In fwtest, ALNK0 plays as before (HW-44 to HW-46), and the register reads show fwtest's values. Add a seams case that runs audio1 and checks that the tone plays in `audio.wav` and that its frames per second are fwtest's 44 117.6 (HW-45). The existing cases should pass unchanged.

## 3. For the owner
Tell the owner:
- what to listen for, on the speaker and then on headphones;
- what to photograph: the rows and what each value means;
- what each outcome means for the next step:
  - the tone sounds;
  - ALNK0 runs (the count and frames per second move) but it is silent;
  - ALNK0 doesn't run.

Finish with "done, ready to clear", Questions, one merge order.
