audio9 on the unit (hw3s, flash log + owner's ears; source UNIT):
- Start-up: L2 kept, R2 set, route kept; tone heard on the speaker. MASTER
  works on the speaker but in 3-4 coarse steps, roughly powers of two;
  the owner saw MASTER jump from about 63 to about 512, with a noisy
  in-between state that a nudge can reach.
- Headphones: the tone is there but very quiet. Plugging in mutes the
  speaker, so the mute is in the hardware.
- PB5 reads 1 unplugged, 0 plugged (settled values, with contact bounce;
  50 changes logged over the run). DAA_CON7 0000C901 throughout (10 reads).
- S2 (LFO), owner fairly sure: upper half only = much louder than both;
  lower half only = the same as upper only; then both halves again =
  silent or near silent. Both ears in every state. So the same sample in
  both halves of a word is quiet or cancels, and either half alone is
  loud: the outside part may take the difference of the halves, or one
  half inverted.
- Occasional clicks on the speaker, about every half second.
- Synth (FX): plays, quiet. 0 late halves, 0 underruns, longest fill
  297.4 us of a 2902 us half, on core 0 alone. Distortion starts with 4
  keys held at once (synth at -12 dB, so 4 voices reach full scale).

Next, in one PR with the results: audio10 options for the owner's rulings
before clean starts:
1. the sample format: what S2's result says about how the outside part
   reads each word, and the fix for the low level (e.g. one half only,
   or the second half inverted), with a listening test to confirm;
2. the mix: headroom for 8 voices (scaling or a soft clip) so chords
   don't distort;
3. MASTER's coarse steps: whether the reading or the mapping is wrong;
4. the half-second clicks: their source (LED blink, screen, scan).
Same rules: touched seams cases only, timing reported.
