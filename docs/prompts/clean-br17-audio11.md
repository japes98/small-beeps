>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

**Working (the owner's rule for every clean prompt):**
- While iterating, run only the seams cases the change touches.
- Open the PR once those pass and the .fwsc is packed. CI runs the full suite; don't do a full local run before the PR.
- The owner flashes once the file has been checked, without waiting for CI.
- Say how long the build took and where the time went: compiling, fwtest runs, container start-up, packing, other.

This is audio11, built on audio10 (#233, on main). audio10 and the owner's listening found how the outputs read a word: the two halves are the two channels, one inverted on the board, and the speaker plays the lower half alone; so N is in-phase mono on both. It also showed that the SARADC's readings don't settle. audio11 fixes the format, sets the SARADC up as the chip's SDK does, and hunts the clicks in N. The owner has ruled (the spec side saves the rulings with the next round's PR): A, N as the only format from start-up; B2, `CON` bit 3 set as the SDK does; B3, `MASTER` by a curve with ramped level changes; C as written; D items 1 to 4 in audio11, 5, 6 and 8 in a later round, 7 as the spec side's own PR in parallel; E, the key status in large text.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio11.md.
- Read, on main, once the spec side's #234 has merged. If it hasn't merged yet, build the parts that need no facts first and read section 47 when it lands; don't open the spec branch:
  - HARDWARE-SPEC section 47: HW-165 (audio10 on the unit), HW-166 (the speaker takes the lower half; the SARADC doesn't settle), HW-167 (the SARADC's divider and start delay in the chip's SDK), HW-168 (the halves are two channels, one inverted on the board);
  - with them HW-40, HW-60, HW-129, HW-133, HW-163 and the notes on Q-8 and Q-9.
- Take every fact from those.

## 1. A: N as the only format (the owner's ruling)
- Everything the link plays (the tone and the synth) goes out as N: the sample in the upper half, its negative in the lower, the most negative sample's negative clamped to the most positive. From start-up.
- The format key goes; give its key back to the engine or leave it unused, and say which.
- N is mono and in phase on the headphones, since one channel is inverted on the board (HW-168). True stereo, later, would invert one channel to match; not in audio11.
- **`MASTER` down before plugging in headphones:** N is far louder there than audio9's P.

## 2. B: the SARADC set up as the chip's SDK does (HW-167)
For every conversion the build starts (`MASTER`'s reads and the test screen's sweep):
- **`CON`, in the SDK's three writes:**
  1. the channel in bits 8-11, bits 0-2 = `0b110` (the SDK's divide by 96), bits 12-15 = `0xF` (the start delay), bit 3 as ruled below, bit 6 set and bit 4 clear (in fwtest that clears the pending flag, HW-60);
  2. the same with bit 4 (enable) added;
  3. the same with bit 6 (start) set again.
  - Bit 5 (the interrupt enable): as the build uses it now. The SDK sets it; say so where the build differs.
- **Bit 3:** set, as the SDK does (B2, the owner's ruling); its meaning is not given.
- **A conversion will now take far longer.** The divider's input clock is not given; if it is the low-speed bus (60 MHz) the converter's clock is 625 kHz, and a conversion with the delay may take about a quarter of a millisecond. Every wait for bit 7 must allow that: measure the conversion time against the timer audio1 uses, log it, and make no wait end early or block the audio fill.
- **One key cycles the set-up** for comparison: the SDK's (at start-up), then the old one (fields 0), then back. The screen names it.
- **The sweep:** leave out every channel whose pin the build drives as an output: channels 6 and 7 (PC0 and PC1, the link's master and bit clocks) while the route is up, channel 2 (PA10, an LED line) and channels 8 and 9 (PC9 and PC10, the panel) (HW-129). The start delay holds each pin on the converter far longer than before. Say what the sweep reads on the others.
- **The sweep's cost:** at about a quarter of a millisecond a conversion, the sweep takes a few milliseconds of every 100 ms, against a half of 2.9 ms. Run it so it never delays the audio fill (one channel a pass, say), and log its time.
- **Knobs on the converter:** as far as is known, channels 3 (PB1) and 4 (PB6, `MASTER`); log both, and the others the sweep reads.
- **Log:** every channel's raw readings in each set-up (the distinct values seen, with counts), and a turn of `MASTER` from end to end in about eight steps in each set-up, as in audio10.
- **`MASTER`'s mapping (B3, the owner's ruling):** `MASTER` sets the level by a curve (say the square of the reading, so equal turns sound like equal steps), 0 silent. Level changes ramp over a half instead of jumping, so a change can't click. Say which curve.

## 3. C: the half-second clicks, in N
Before the build, from audio10's PR: the LED guide's blink is the only activity at half a second; the test screen's 100 ms refresh (the matrix sweep, the SARADC sweep, three rows) and the once-a-second rows are the other periodic ones. Zero samples were silent, so the clicks may come with the samples: a `MASTER` reading that flips between 63 and 512 makes the level jump.
- Keep audio10's hold keys: zero samples, the LED blink held, screen redraws held, log writes held, the scan held (ending by itself).
- **The owner listens in N, with `MASTER` still,** for about ten seconds in each: none held; each hold alone; zero samples.
- Log `MASTER`'s raw reading and applied level over each, so a level jump shows beside a click.

## 4. D: what's left before the synth's audio path counts as done
The owner's ruling: items 1 to 4 are in audio11; 5, 6 and 8 come in a later round; 7 is the spec side's own PR, in parallel.
1. **N fixed on both outputs** at full level (A).
2. **`MASTER` smooth and steady:** every raw value reachable, monotonic, 0 silent, no zipper noise (B).
3. **No periodic clicks** in N, with the instrument running normally (C).
4. **8-voice chords clean,** with the fill under budget for the heaviest patch, not only the one tried (audio10's 312.2 µs of 2 902 µs): log the longest fill per algorithm while the owner plays an 8-key chord in each. In audio11.
5. **The normal start brings the path up:** L2, the four port C pins, the route and N as the instrument's own start, not the test screen's; the test keys behind the test screen. [later round]
6. **Timing that counts audio interrupts** (ARP, which runs at half speed on the unit) counted in frames, so it is right on both targets. [later round]
7. **fwtest plays what the unit plays:** the spec side's harness change (`LEN` as frames a half, the 16-bit N word) so `audio.wav` matches. The spec side does it now, as its own PR in parallel. audio11 keeps fwtest's format and the per-target fill; adapt to the harness change once it is on main, in a later round.
8. **Levels:** the speaker against the headphones at `MASTER`'s top, and the soft clip's threshold, settled by ear. [later round]
- Not part of "done": the chip's own DAC; stereo (later, inverting one channel to match); `DAA_CON7`.

## 4b. E: the key status in large text (the owner's request)
The owner can't read the small text. Give the key status its own area of the screen, in large text:
- the format (N, while the format is fixed, still shown);
- `MASTER`: its raw reading and the level applied;
- the mode (the tone or the synth, and any hold or set-up key's state: which SARADC set-up, which hold).
Keep the rest of the screen as it is, smaller if it must be; everything also goes in the log. Say what the large area shows and how big the characters are.

## 5. Not included
- No register written beyond audio10's, but the SARADC's `CON` as in B: `JL_IOMAP`, any PLL register, `CLK_CON1`, `CLK_CON2`'s low byte, the analogue registers (`WLA_CON0`, `PLL_CON1` and `DAA_CON7` included; the SDK's set-up writes the first two for its internal channels only), ALNK1, `CON1` beyond `0x1000`, `CON3` beyond L2's.
- No pin driven beyond audio10's; no port B write.
- fwtest's own format and `LEN` unchanged; the fill stays sized per target.

## 6. fwtest
- Say what fwtest does with `CON` bits 0-3 and 12-15: stored, ignored, or used.
- Extend the seams cases you touch:
  - A: N's packed words through the test seam, from start-up;
  - B: each set-up's `CON` value and write order, the waits allowing a slow conversion (the seam delaying bit 7), the sweep leaving out channels 6 and 7 while the route is up, the mapping and the ramp;
  - C: the hold keys as in audio10;
  - E: the large area's contents for each state, through the screen seam.

## 7. For the owner
In one list:
- how long the build took, and where the time went;
- the keys and order; `MASTER` down before headphones;
- what each outcome means:
  - **N heard on the speaker, and full and centred in the headphones, at start-up:** the format is done.
  - **`MASTER`'s raw reading smooth in the SDK's set-up, and stepped in the old one:** the divider and delay were the fault; the knob is fixed (whether bit 3 alone matters is not tested). **Still stepped in both:** the converter needs more than `CON` (the analogue set-up, or the pin's set-up); the options go back to the owner, since the analogue registers are not allowed now.
  - **Conversions time out:** the conversion is slower than the waits allow; the log's measured time says by how much.
  - **No clicks with `MASTER` still and the reading smooth:** the clicks were level jumps from the unsettled reading. **Clicks gone with one hold:** that activity couples in (the LEDs' current, the screen's bus, the flash). **Clicks with zero samples:** they don't come with the samples after all.
  - **D item 4: every algorithm's longest fill under a half with 8 keys:** the engine fits on core 0. **One near or over:** that algorithm needs work, or core 1.

Finish with "done, ready to clear", Questions, one merge order.
