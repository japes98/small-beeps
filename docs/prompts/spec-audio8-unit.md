audio8, second run (hw3r, flash log + owner's ears; source UNIT):
- Step 1 (R2 in place, CON5 0, CON0 bits 7 and 8 set: 0800/8800 > 0980/8980,
  read back the same) at MASTER 1023: the owner HEARD A BEEP on the speaker,
  in two runs, lasting the 100 ms watch until the firmware's own undo (it
  undid because port C IN can't show output pins). So ALNK0 reaches the
  speaker through port C with CON5 0, and the speaker needs no amplifier
  enable. In the first run, MASTER was 0 during step 1: silent.
- The CON5 sweep (bits 0-31, each with bits 7 and 8): clicks on the speaker
  only, no tone. CON5 isn't needed.
- Sense scan (19 980 readings) while the owner plugged headphones in and
  out 3 times: only PB5 changed (bit 0020 of port B), 12 events with
  contact bounce. PB5 looks like the headphone detect. PB's DIE is FFBD.
- DAA_CON7 read 00004901 at start-up, 0000C901 after step 1, and stayed
  so; in the first run, 00006901 from start-up.
- Headphones haven't been listened to with the route on yet.

Next, in one PR with the results: audio9 for the owner's rulings before
clean starts. Suggested: at start-up L2 + R2 + step 1's route kept (no
port C movement check, since IN can't see it; the matrix check and undo
by key stay), a steady quiet tone at MASTER, PB5 shown on screen as the
headphone state, listen on speaker and headphones. And, as a separate
option: the synth engine's output (fm_play) into this path, so the keys
play notes. Same rules: touched seams cases only, timing reported.
