>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

**Working (the owner's rule for every clean prompt):**
- While iterating, run only the seams cases the change touches.
- Run tools/check-emulator-terms.py with COMMIT_RANGE=origin/main..HEAD before every push, and don't push while it fails.
- Open the PR once those pass and the .fwsc is packed. CI runs the full suite; don't do a full local run before the PR.
- The owner flashes once the file has been checked, without waiting for CI.
- Say how long the build took and where the time went: compiling, fwtest runs, container start-up, packing, other.

This is audio12, built on audio11 (#236, on main with #235). audio11 settled the SARADC, the clicks and the format. audio12 measures the engine in every algorithm without the owner holding keys, finds why `ALGORITHM` sounds the same, moves the audio path into the normal start and counts time in frames. The owner has ruled (saved on main as docs/prompts/spec-audio12-rulings.md, #238): S yes; G yes; G2 only if G finds the start-up patch is the cause, clean deciding from its fwtest check and saying which it did; D5 now; D6 now; D8 later, in the level round.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-audio12.md.
- Read, on main (the spec side's audio11 PR, #237, has merged):
  - HARDWARE-SPEC section 48: HW-169 (audio11 on the unit) and HW-170 (the SARADC settles; the clicks came with `MASTER`'s reading; the speaker rolls off the bass);
  - with them HW-165 to HW-168 and the notes on Q-8 and Q-9.
- Take every fact from those.

## 1. S: an automatic chord in each algorithm
- **One key starts a sweep:** for each algorithm 1 to 10 in turn, the firmware selects it, plays an 8-voice chord (fixed notes, say a spread over three octaves, the same in each) for about 1.5 s, releases it, and waits for the release to end before the next.
- **Log per algorithm:** the longest fill, with the voices sounding then; soft-clip and saturation counts; late halves and underruns.
- **On screen, in the large status area:** the algorithm being played and its longest fill so far.
- The same key during a sweep stops it after the chord in progress, with every voice released.
- The owner touches nothing during the sweep, and listens: whether the algorithms sound different (section 2).

## 2. G: why `ALGORITHM` sounds the same
Two causes are likely: the patch (if the modulators' levels are 0, every algorithm sounds the same), or a change of algorithm reaching only notes started after it.
- **Before the build, in fwtest:** play the same note under each algorithm with the patch the unit starts with, and say whether `audio.wav` differs between algorithms. Say what that patch's operator levels are, and whether the engine applies a change of algorithm to sounding voices or only to new notes.
- **On the unit:** log `ALGORITHM`'s value as the engine reads it at each note-on, beside the algorithm the voice then uses.
- **G2 (the owner's ruling: only if G finds the start-up patch is the cause):** start in a patch whose modulators sound (say which), so the sweep in S is heard to change. Decide from the fwtest check, and say whether you did G2 and why.

## 3. D5: the normal start brings the audio path up (the owner's ruling: now)
- The instrument's own start runs L2, the four port C pins, the route and N, with the matrix check and its self-undo, as the test screen's start does now; then the instrument runs with sound and no test screen.
- The test screen and its keys stay reachable (say how: a key held at power-on, say), and do nothing in normal running.
- If the start's self-undo fires, the instrument still runs, silent, and shows why.

## 4. D6: timing in frames (the owner's ruling: now)
- Whatever counts audio interrupts to keep time (ARP, which runs at half speed on the unit, and anything else) counts frames instead, so it is right on the unit (128 frames a half) and in fwtest (its own layout), with no rate change.
- Say what else counted audio interrupts.

## 5. D8: not in audio12
The owner's ruling: D8 (levels, the speaker's bass) comes later, in the level round. No boost and no level change here.

## 6. Not included
- No register written beyond audio11's.
- No pin driven beyond audio11's; no port B write.
- Nothing on the USB block: no USB register read or written (the USB plan's unit checks come in a later round).
- fwtest 0.13.0 (`--audio-chip`) is published from main at `bb0a8815` (#235's merge) as `ghcr.io/japes98/small-beeps@sha256:b2a1e76379509f13ef7c43b12442b4c48ad349248f7ef0b2ad3053e0e74e936b`. Pin it if you adopt `--audio-chip` (only where the build fills the chip's layout in fwtest too), and say whether you do.

## 7. fwtest
- Extend the seams cases you touch: the sweep (every algorithm, the stop key, the log); G's per-algorithm comparison; D5's start and its self-undo (forced through the test seam); D6's timing on both targets.

## 8. For the owner
In one list:
- how long the build took, and where the time went;
- the keys and order;
- what each outcome means:
  - **S: every algorithm's longest fill well under 2 902 µs:** the engine fits on core 0 at 8 voices. **One near or over:** that algorithm needs work, or core 1.
  - **G: algorithms differ in fwtest and on the unit with the new patch:** it was the patch. **Differ in fwtest, not on the unit:** `ALGORITHM` doesn't reach the engine on the unit; the log's values say where. **Same in fwtest too:** the engine or the patch; clean says which.
  - **D5: sound at power-on with no test screen:** the audio path is the instrument's.
  - **D6: ARP at the right speed on the unit:** done.

Finish with "done, ready to clear", Questions, one merge order.
