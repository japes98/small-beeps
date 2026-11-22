#235: option 2. No force-push. Pass the rename to clean-6b yourself:
rename adc_con in #236 (hw_audio.c and hw_fm1.h) to a name that isn't in
the emulator, run C-SEP-TERMS locally, push. Then merge that into #235.
Merge order: #235 alone, containing #236. In future, stop on a failed
check before pushing a merge.

audio11 on the unit (hw3u, flash log + owner's ears; source UNIT):
- N at start-up on speaker and headphones, as expected.
- SARADC: SDK set-up CON F44E F45E F45E (read after F41E), 1 596 248
  conversions, 0 timed out, conversion ~211 us (tight poll). Old set-up
  (0450): 0.4 us, 0 timed out. MASTER's raw reading now moves in small
  steps (e.g. 504, 508, 512, 516...); all 19 raw jumps over 32 fall in
  the old set-up's minute. The owner hears MASTER smooth in the SDK
  set-up. ch0 reads mostly 1020-1021.
- Clicks: none heard, with nothing held or with each hold (LED, screen,
  log, scan, zeros). So the half-second clicks came with MASTER's
  unsteady reading.
- Synth: 8 voices, longest fill 318.7 us (A8, 8 voices), soft clipped 0,
  saturated 0. The log shows algorithms A1-A10 all selected (single-voice
  fills 158-199 us); the 8-key chord was held in A8 only, since the owner
  can't hold 8 keys and turn ALGORITHM at once. The owner heard no change
  when turning ALGORITHM.
- Low notes are much quieter than high ones on the speaker; on headphones
  they're close to even (lows slightly softer, as expected for low sines).
  So it's the speaker's bass roll-off, not the engine.
- Large status text works.

Next, in one PR with the results: audio12 options for the owner's rulings:
1. a key that makes the firmware play an 8-voice chord in each algorithm
   in turn (a second or two each), logging each algorithm's fill, with
   nothing for the owner to hold;
2. why ALGORITHM sounds the same (the patch, or changes applying only to
   new notes);
3. D5 (the normal start brings the audio path up; test keys behind the
   test screen) and D6 (ARP timed in frames);
4. D8 (levels by ear), with a speaker-only bass/loudness option, as a
   later round unless cheap.
Then set out the plan for USB MIDI as the next big step. Same rules:
touched seams cases only, timing reported.
