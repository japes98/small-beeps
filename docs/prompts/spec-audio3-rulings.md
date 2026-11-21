Rulings (owner):
1. A and B allowed in the next build, each by key press, each undoable,
   with the core-1 count shown alongside.
2. C: only in this narrower form. FM-1-RE's description of CON3's fields
   (which bit enables which data channel) is a hardware fact and may be
   used to enable data 3's channel, the one HW-141 names. The values the
   stock firmware writes may not be used. If FM-1-RE doesn't say which bit
   is data 3 without relying on the stock firmware's writes, drop C.
3. D, E, F: no, until A and B have been tried.

New unit facts (source UNIT, from a boot video of audio2, no key
pressed): core 1 started (count 6742150 at boot step 16), was at ~36586082
when the test screen came up, then froze at 419825784 from about 21 s
after power-on while the main loop kept running. So core 1 runs until
ALNK0 is started and then stops; it doesn't fail to start. Clean's
working explanation: ALNK0 told to run with no clock stalls core 1's
memory access, and bit 9 releases it. Record it as clean's hypothesis.

Clean is already building a core-1 probe (count at fixed points, a key
that stops and restarts ALNK0 without the clock step, core 1's data in its
own block, the 0x80–0x8F words). Write the clean prompt for A, B (and C as
ruled) as additions to that same build, so it comes as one file. End with
"done, ready to clear".
