>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

**Working (the owner's rule for every clean prompt):**
- While iterating, run only the seams cases the change touches.
- Open the PR once those pass and the .fwsc is packed. CI runs the full suite; don't do a full local run before the PR.
- The owner flashes once the file has been checked, without waiting for CI.
- Say how long the build took and where the time went: compiling, fwtest runs, container start-up, packing, other.

This is audio8, built on audio7 (#227, on main through #228). It takes audio7's L2 as the running state, and adds the first routing steps and a headphone-sense scan. The owner has ruled on its parts (the spec side saves the rulings with the next round's PR): R0, R2, R3 step 1 and R5 allowed; R3 step 2 allowed only if step 1 shows no port C movement; R4 as written, no pin driven. R1 (the board photo) is the owner's, and nothing here waits for it.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio8.md.
- Read, on main (the spec side's #228 has merged):
  - HARDWARE-SPEC section 44: HW-159 (audio7 on the unit) and HW-160 (what it settles: `LEN` is frames a half, bit 9 stops the PLL's audio clock, the 16-bit buffer);
  - with them HW-56, HW-85, HW-117, HW-118, HW-119, HW-141, HW-146, HW-156, HW-157, HW-158, and the notes on Q-9.
- Take every fact from those.

## 1. The running state (R0)
- **L2 at start-up.** Once the test screen is up, set up L2 as audio7 did: `CON3` `0x83`, `CON1` `0x1000`, `CON0` `0x0800`, with `CLK_CON2` bit 9 left clear as read.
  - Use audio7's write order, logging and matrix check.
  - If the link doesn't move within one second, or the check fails, undo it as audio7 does, and log and show it. The rest of audio8 then doesn't run.
- **The tone in 16-bit form, on the unit only.** In 16-bit mode a half is `LEN` frames of four bytes (HW-160): each 32-bit word holds one frame's two 16-bit samples.
  - Which half of the word is left is not given, so write the same sample into both halves of each word; the order then doesn't matter.
  - The tone is quiet, at MASTER's level, as before.
  - fwtest keeps its own format (HW-44); the build picks the format by target. Say how.
- **The bit 9 key stays.** Setting bit 9 now stops the link (HW-160); the log should show that if it's pressed.
- **The LED guide:** D, J, K and L1 are out of its order, as D was in audio7.

## 2. Routing data 3 to port C (R2, R3)
ALNK0's port C pins are PC0 (master clock), PC1 (bit clock), PC2 (word select) and PC6 (data 3) (HW-141). Its other group, B1, is on port A: PA4 to PA10, the matrix's shift-register data, its rows PA5 to PA8 and the LED lines PA9 and PA10 (HW-156). Which `JL_IOMAP->CON5` value picks which group is not given (HW-146); it reads 0.

**Seeing a pin move with no instrument.** Sample port C's `IN` in a tight loop for a fixed time (say 10 ms), with the digital input on for the four pins (R2). Count each pin's changes, and do the same for PA4 to PA10.
- A routed word-select pin changes about 88 000 times a second.
- A bit-clock pin changes far more often; aliasing may undercount it, but never to 0.
- Log every count.
- If `IN` doesn't follow a pin the link drives, the counts stay 0. Say so: that is a result too.

**R2: PC0, PC1, PC2 and PC6 as outputs.** Set them as the AW30N's driver does for a master: `OUT` high, then `DIR` 0 (an output), then `DIE` on.
- Use read-modify-write of those four bits alone in port C's `OUT`, `DIR` and `DIE`. Leave the pulls and drive as read.
- PC7 to PC10 (the panel) and every other port C pin stay as read.
- Undo: port C's registers back as read.

**R3, step 1: no `CON5` write.**
1. **(a)** With R2 in place and `CON0` bits 7 and 8 clear, sample port C and port A.
2. **(b)** Then set `CON0` bits 7 and 8 (the clocks to the pins) and sample again.

`CON5`'s 0 may already be port C: the AC7911B calls port C's pins group "A" (HW-141, HW-156). Step (b) is where group B1's overlap matters. If 0 were B1, the link could drive PA4 (garbling the column word), PA5 and PA6 (rows) and the LED lines. So, for (b):
- **Before the write:** latch `0xFFFF` (no column) and hold the matrix and LED scan. With every column high, a key pressed against a row the link drives can't join a high output to a low one.
- **The owner touches no key during (b).** Show that on screen. The firmware checks the rows are idle before writing.
- **The watch** is 100 ms, then D's matrix check, its own undo of `CON0` bits 7 and 8 if port A moved or the check fails, and the re-check.
- **If port C moves and port A doesn't:** keep it running. The owner listens (section 6).

**R3, step 2: the `CON5` sweep, only if step 1 shows no port C movement.** D's single-bit sweep from audio6 (log before the write, the watch, matrix check, self-undo, re-check), with R2 in place, `CON0` bits 7 and 8 set and `0xFFFF` latched for each try.
- **Each try's watch** is the port C and port A sampling.
- **Stop** at the first bit that moves port C with port A unchanged: keep it, show it, and the owner listens. Also stop at the first failed check.
- **Stop at a bit that moves port A:** undo it, and log the bit and port A's counts.
- **One key press runs the sweep.**

## 3. Headphone sensing (R5)
A read-only scan:
- While the owner plugs headphones in and out (say three times over 20 seconds), read every port's `IN` (A to H) every millisecond.
- Log each bit that changes, with times.
- Write nothing to any port, `DIE` included: a pin whose digital input is off may read nothing. Log each port's `DIE` beside its result.
- Its key starts it; the screen counts down and shows the bits that changed.

## 4. Not included
- **The amplifier enable (R4):** no pin is driven to find it. The owner listens on the speaker and on headphones once port C moves.
- **The board photo (R1):** the owner's, not this build's.
- Not written:
  - any other `JL_IOMAP` word, ever (`CON0` bit 5 and `CON1` bit 1 select the flash's pins, HW-85);
  - port D, any PLL register, `CLK_CON1`, `CLK_CON2`'s low byte;
  - the analogue registers;
  - ALNK1;
  - `CON1` beyond `0x1000`.
- No key-matrix pin is written beyond leds1's scan and the `0xFFFF` latch.

## 5. fwtest
- Say what fwtest does with port C's `DIE` and `IN` while ALNK0 plays: it probably shows no pin movement.
- Say what it does with `CON5`.
- Extend the seams cases you touch:
  - L2 at start-up;
  - the 16-bit tone on the unit target (the image builds; fwtest plays its own format at 44 117.6);
  - R2's set and undo;
  - step 1 and the sweep (with the test seam forcing a failed check and a port A movement);
  - the sense scan running without a hang.

## 6. For the owner
In one list:
- how long the build took, and where the time went;
- the keys and order;
- **what to listen for:** the speaker, then headphones, while port C moves;
- what each outcome means:
  - **port C moves, and sound on both:** routing is done and the amplifier is on. Next: the synth's audio path.
  - **port C moves, sound only on headphones:** the speaker's amplifier needs an enable. Next: the board photo (R1), or the owner's plan to list the candidate pins.
  - **port C moves, silent on both:** no part outside the chip takes I2S on these pins, or it needs set-up. Next: R1.
  - **port C never moves (step 1 and the sweep):** `IN` doesn't show it, or no single `CON5` bit routes it. The spec side sets out what's next.
  - **port A moves at some bit:** that bit routes to B1. Note it; it is undone.
  - **the sense scan finds a bit that follows the plug:** note it. If nothing changes, the mute is in the jack's hardware, or the pin's input is off.

Finish with "done, ready to clear", Questions, one merge order.
