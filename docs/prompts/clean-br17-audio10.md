>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

**Working (the owner's rule for every clean prompt):**
- While iterating, run only the seams cases the change touches.
- Open the PR once those pass and the .fwsc is packed. CI runs the full suite; don't do a full local run before the PR.
- The owner flashes once the file has been checked, without waiting for CI.
- Say how long the build took and where the time went: compiling, fwtest runs, container start-up, packing, other.

This is audio10, built on audio9 (#231). audio9 put the route up at start-up and the synth on it. The sound is quiet everywhere, and S2 showed why it may be: the same sample in both halves of a word nearly cancels, while either half alone is loud. audio10 changes only the samples and reads only what the build already reads: no new register is written. The owner has ruled (the spec side saves the rulings with the next round's PR): F with U at start-up; the mix M2 with M3 under it, no M1; V and C as written.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio10.md.
- Read, on main, once the spec side's #232 has merged (it also carries your #231). If it hasn't merged yet, build the parts that need no facts first and read section 46 when it lands; don't open the spec branch:
  - HARDWARE-SPEC section 46: HW-163 (audio9 on the unit) and HW-164 (what it settles: the mute is in the hardware, PB5 is 0 with headphones in, the halves of a word work against each other);
  - with them HW-129, HW-133, HW-136, HW-160, HW-161, HW-162 and the notes on Q-9.
- Take every fact from those.

## 1. F: the sample format, and a listening test
HW-164's reading, untested: the outside part's output is the difference of the two halves. If so, the sample in one half and its negative in the other is about 6 dB louder than one half alone, and twice as loud as anything heard so far but S2's single halves.
- **One key cycles the format** for everything the link plays (the tone and the synth), the screen naming each:
  1. **P:** the sample in both halves (audio9's form);
  2. **U:** the upper half alone, the lower 0;
  3. **L:** the lower half alone, the upper 0;
  4. **N:** the sample in the upper half and its negative in the lower (the most negative sample's negative clamped to the most positive);
  5. **N':** the negative in the upper half, the sample in the lower.
- **The format at start-up:** U (the owner's ruling).
- Log each change of format with its time.
- **Before plugging in headphones, `MASTER` down:** U and N are far louder than audio9's P.

## 2. M: headroom for 8 voices
Today the synth sits 12 dB below full scale, so four voices at full level reach it. Say whether the 16-bit packing wraps or saturates at full scale: a wrap is far worse to hear.
- **The owner's ruling: M2 with M3 under it.**
  - **M2:** the synth stays 12 dB below full scale, with a soft clip on the sum (a smooth curve that flattens toward full scale), so chords compress rather than distort.
  - **M3:** under it, saturate at full scale in the packing (a hard clip, never a wrap).
  - No M1 (no further cut per voice).
- Under N, the output's swing is twice a half's; the headroom above is per half.
- Log and show the longest fill time again, and separately the longest with 8 keys held during the chord test: audio9's was 297.4 µs of 2 902 µs, with how many voices sounding not known.

## 3. V: MASTER's coarse steps
Read only; the pot is SARADC channel 4 (HW-133, HW-136).
- Show and log `MASTER`'s raw reading beside the level the build applies to the samples, and say how the build turns one into the other (a shift, a multiply, a curve).
- The owner turns `MASTER` slowly from end to end in about eight steps, pausing at each; log every reading over the turn with its time.
- With F's N or U, the owner listens again for the steps.

## 4. C: the half-second clicks
- **Before the build:** list everything in the build that happens about twice a second (the LED guide's blink, screen redraws, the log writes, PB5's logging, the late-half check, anything else), and look in fwtest's `audio.wav` for a step or gap at that period in the tone. Say what you find.
- **On the unit, one key each** (all switched back by the same key), the owner listening for the clicks:
  1. **zero samples:** the route up, the link playing zeros. Clicks still heard: they don't come from the samples.
  2. **LED blink held** (the LEDs left as they stand);
  3. **screen redraws held** (the screen left as it stands);
  4. **log writes held** (records queued, written when released, or dropped and counted);
  5. **the matrix scan held**, with `0xFFFF` latched. No key works while it is held, so the hold ends by itself after a fixed time (say 5 s), with no key press needed to undo it, as in D. The screen counts it down.
- Say whether holding the LED blink also holds the scan in your build, and keep the holds apart if you can.
- Log each key's state with its time.

## 5. Not included
- No register written beyond audio9's: `JL_IOMAP` (`CON5` included), any PLL register, `CLK_CON1`, `CLK_CON2`'s low byte, the analogue registers (`DAA_CON7` included), ALNK1, `CON1` beyond `0x1000`, `CON3` beyond L2's.
- No pin driven beyond audio9's; no port B write.
- fwtest's own format and `LEN` unchanged (the spec side's `LEN` change comes later); the fill stays sized per target.

## 6. fwtest
- Extend the seams cases you touch:
  - F: each format's packed 16-bit words checked through the test seam, the clamp included (the formats apply to the unit's packing; fwtest's `audio.wav` plays its own layout, so it can't show them);
  - M: M2 and M3 with 8 voices held: the sum never wraps;
  - V: the raw reading and the applied level logged with the seam's pot moved;
  - C: each hold key switches and restores, the scan hold ending by itself; the zero-samples key gives zeros in `audio.wav`.

## 7. For the owner
In one list:
- how long the build took, and where the time went;
- the keys and order; `MASTER` down before headphones;
- what each outcome means:
  - **N (and N') louder than U, U and L alike, P near silent:** the outside part takes the difference of the halves. Next: N becomes the only format; S2's "which half is left" falls away (the output is mono).
  - **N as loud as U, or silent:** the difference reading is wrong. Next: the spec side reads the levels heard and sets out the next test.
  - **chords clean with 8 keys under M2 and M3:** the mix is done. **Still distorting:** the distortion isn't the sum's (it may be the outside part's input or the amplifier). Next: lower levels to find where it starts.
  - **`MASTER`'s raw reading smooth and the steps gone with N or U:** the steps were what was left after the halves cancelled. **Raw smooth, steps still heard:** the mapping. **Raw reading jumping:** the reading (the ADC's timing or set-up); the spec side looks at channel 4.
  - **clicks gone with zero samples:** they are in the samples (a step in the tone or a late refill). **Clicks with zero samples, gone with one hold key:** that activity couples into the sound electrically (the LEDs' current, the screen's bus, the flash). **With zero samples, no hold key ends them:** something else; note how regular they are.

Finish with "done, ready to clear", Questions, one merge order.
