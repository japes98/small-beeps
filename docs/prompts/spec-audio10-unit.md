audio10 on the unit (hw3t, flash log + owner's ears; source UNIT):
- Formats, by ear, after the run (headphones unplugged for the speaker):
  speaker: U silent; L, N, N' and P play.
  headphones: U, L, N' play; N slightly louder; P silent.
  So the speaker seems to play the lower half of each word, and the
  headphones the difference of the halves. N is the only format that
  plays on both. At start-up in U the speaker was silent, as that implies.
- Mix (M2 + M3): an 8-key chord sounded clean. Log: most voices 8, longest
  fill 312.2 us (8 voices 312.2 us) of a 2902 us half, soft clipped 0,
  saturated 0, late halves 0, underruns 0.
- MASTER: still stair steps by ear. The raw reading took only these values
  in 993 changes: 0, 3, 7, 15, 31, 63, 512, 768, 896, 960, 1008, 1023 (93
  raw jumps, largest raw step 449). Those are 2^k-1 below and 1024-2^k
  above: once the first decision is made, every later bit repeats it, as if
  the conversion doesn't settle per bit (the ADC clock or the sample time).
- PLAY (zeros): silence. The half-second clicks weren't checked against
  the holds this run; clicks were heard on LFO presses (format switches).
- PB5 and DAA_CON7 (0000C901) as before.

Next, in one PR with the results: audio11 options for the owner's rulings
before clean starts:
1. N as the only format, at start-up;
2. the SARADC fix for MASTER and every other knob on the converter: the
   clock divider or sample time, from what the spec has (JieLi's SDK
   included), with every knob's raw readings logged before and after;
3. the half-second clicks: the holds again, with the owner asked to listen
   in N;
4. what's left before the synth's audio path counts as done.
Same rules: touched seams cases only, timing reported.
