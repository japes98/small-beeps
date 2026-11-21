report1 (6628de27…, hw3k) ran on the unit, and the log works end to end:
23 records read back from a full flash image, all CRCs valid, decoded
with your report_decode.py. Results went to the spec side.
Two things:
1. Which PR do I merge, #217 or #218? Close the other.
2. Owner request for the next build: light each key's LED while it is
   held, and keep the step keys' LEDs (REC, SEQ, ARP, SAVE, ENV, FX, LFO,
   SEL, EDIT) lit while their step is taken, so the owner can see what
   they're pressing and what state each step is in. Nothing else changes.
