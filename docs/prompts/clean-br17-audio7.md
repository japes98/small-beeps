>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

This is audio7. It adds to the build you are finishing now: audio6 with the CRC/sb_now fix and the next-key LED guide. Build it into that same build and branch, so the owner flashes one file. If audio6 is already in an open PR, build on top of it, cumulatively.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio7.md.
- Read, on main (the spec side's #225 has merged):
  - HARDWARE-SPEC section 43:
    - HW-157: the audio link's fields on the AW30N's chip, another chip;
    - HW-158: those fields set against ALNK0 here. It explains why `CON1` and `CON3` at 0 would leave the link with no channel and no clock.
  - with them HW-43 to HW-45, HW-53, HW-145, HW-146, HW-153, HW-155, HW-156, and the notes on Q-9.
- Take every fact from those.

## 1. Two set-ups, L1 and L2, in the next-key order; D held
The owner has allowed writing HW-157's fields to ALNK0's `CON0`, `CON1` and `CON3`, as below, and nothing else new. These values come from another chip's SDK: this is a probe of whether the FM-1's chip uses the same fields.

**D is held.**
- Take D out of the next-key order and out of the LED guide. D's code can stay in the build, but nothing leads the owner to it.
- Show D as "held" on its screen row.
- A D result in this run counts for nothing toward E and F.

Keep every other earlier step (bit 9, A, B, H, I, K, J) and leds1's keys as they are.

**The two set-ups.** Each is one key press. Each is undone by the firmware itself, with D's safety machinery (below).
- **L1, the oscillator (no clock register touched):**
  - `CON3` = `0xC2`: the master clock from the oscillator, divided by 1, 512 master clocks a frame;
  - `CON1` = `0x1000`: data 3 as I2S output, 16-bit;
  - then `CON0` with bit 11 set and bits 7 and 8 clear, every other bit as read.
  - Expected, if HW-157's fields hold here: 24 MHz / 512 = 46 875 frames a second.
- **L2, the PLL's audio clock:**
  - `CON3` = `0x83`: the PLL's audio clock, divided by 1, 256 a frame;
  - `CON1` = `0x1000`;
  - then `CON0` as for L1.
  - Taken twice: once with `CLK_CON2` bit 9 set (by audio2's own key, before L2's press), and once with bit 9 clear. `CLK_CON2` bit 8 is left as read.
  - Expected, if bit 9 enables the links' 192 MHz / 17 clock: 44 117.6 frames a second with bit 9 set. Any other rate, or none, is the result.

**Write order in each set-up** (HW-157's driver order, limited to the allowed registers):
1. Stop the link: `CON0` as read with bit 11 clear.
2. Write `CON3`.
3. Write `CON1`.
4. Write `CON0` with bit 11 set and bits 7 and 8 clear.
5. Read back each register after its write.

Leave `ADR3`, `LEN` and the buffer as audio1 set them, and write `CON2` only as audio1 already does.

**Each set-up, with D's safety machinery:**
1. **Log before the write.** Log the set-up's name and the values read before it:
   - `CON0` to `CON3`, `LEN` and `ADR3`;
   - `CLK_CON1` and `CLK_CON2`;
   - port A's registers;
   - source 11's count and core 1's count.

   Log the expected halves a second under both readings of `LEN`, computed from the `LEN` you read:
   - **(a) HW-157's:** a half holds `LEN` frames, so halves a second = frames a second / `LEN`;
   - **(b) fwtest's (HW-44):** a half holds `LEN` / 2 frames, so halves a second = 2 × frames a second / `LEN`.

   The record must be complete in the flash before step 2. As in D, write nothing to the flash until step 5 has undone the set-up or kept it.
2. **The writes,** in the order above, each read back.
3. **The watch: 1 second.**
   - Count `CON0` bit 15's changes, `CON2`'s pending flags and source 11's interrupts.
   - Time the halves against the timer audio1 uses, as halves a second and as frames a second under each `LEN` reading.
   - Take one second rather than D's 100 ms, so the rate can be read.
4. **The matrix check, with the set-up in place.** This is D's check: rows high with no column, one full scan with no key closed, and port A's registers against step 1's.
5. **The undo.**
   - **If the link moved and the check passed:** keep the set-up running, so the owner can see the rate. Show and log that it moved. The owner's undo key, or the next set-up's key, puts `CON0`, `CON1` and `CON3` back as read before the press, in that order.
   - **In every other case:** the firmware puts them back itself, in that order, and reads them back.
6. **The re-check after the undo,** as in D. If anything doesn't match step 1, stop: take no further set-up, and show and log which.
7. **Log after.** Record:
   - every value written and read back;
   - the counts, and the halves and frames a second (with both `LEN` readings beside the expected values);
   - the matrix check's results;
   - `CLK_CON2` and core 1's count;
   - whether the set-up was kept or undone.

**On screen:** for the set-up in progress, and for one kept or stopped at, show its rows as start3b does: the values before and after, the counts, the rates, the matrix check's result and core 1's count. Everything also goes in the log.

**Next-key order (the LED guide):**
1. L1;
2. undo L1, if it was kept;
3. bit 9 (audio2's key);
4. L2;
5. undo L2, if it was kept;
6. bit 9 again (back to clear);
7. L2;
8. undo L2, if it was kept.

The key mapping is yours; say it on the screen and in the log.

**Writes.** L1 and L2 write only ALNK0's `CON0`, `CON1` and `CON3`. `CLK_CON2` bit 9 is written only by audio2's existing key.
- Clock pins: none. `CON0` bits 7 and 8 stay clear, so no clock goes to a pin.
- Not written: `JL_IOMAP`, any port A write beyond leds1's scan, any port C register, any PLL register, `CLK_CON1`, or `CLK_CON2`'s low byte.
- Not included: D (held), E and F, `CON1` = `0x5000`, ALNK1, routing to any pin.
- Nothing will be heard: data 3 routes to no pin. That is expected.

## 2. fwtest
Say what fwtest does with `CON1` and `CON3`: stored only, or used. Extend the seams case:
- press L1 and L2 (with bit 9 set, then clear), each with no hang;
- check that each undo, the firmware's own or by key, restores `CON0`, `CON1` and `CON3` as read before;
- check that the matrix check passes;
- check that the log holds both `LEN` readings;
- check that the tone keeps playing in `audio.wav` at 44 117.6 frames a second;
- through the test seam, force one failed matrix check, and see the firmware undo that set-up and stop.

The existing cases should pass unchanged.

## 3. For the owner
Tell the owner, in one list:
- the keys and the order (the LED guide's), and how to undo a kept set-up;
- how to read L1's and L2's records from the flash image;
- what each outcome means:
  - **L1 runs, near 46 875 frames a second under one of the `LEN` readings:**
    - HW-157's `CON1` and `CON3` fields hold here, and the link runs from the oscillator with no PLL write;
    - that reading of `LEN` is the chip's;
    - routing to the pins comes next, as a spec request.
  - **L1 runs at another rate:** note the rate. The fields partly hold; the spec side reads it.
  - **L1 stays dead:** HW-157's fields are not this chip's, or something else gates both links. The options go back to the owner for a ruling.
  - **L2 runs with bit 9 set (near 44 117.6) and not with it clear:** bit 9 enables the links' PLL clock, and 44.1 kHz is reachable with no PLL write.
  - **L2 runs either way:** the PLL's audio clock doesn't need bit 9. Note both rates.
  - **L2 dead both ways while L1 runs:** the PLL's audio clock doesn't reach the link with bit 9 alone. The oscillator path remains.
  - **A matrix check fails:** unexpected, since no pin is routed. Note the set-up and what port A read.
  - **The unit hangs:** power it off, and report the last record.

Finish with "done, ready to clear", Questions, one merge order.
