Answers from the unit (audio2, fresh power-on, no REC pressed; read from
a video of the boot):
- Core 1 started: at boot step 16 ("tick after core 1") c1 read 6742150.
  The exact "sign seen" line wasn't caught on video.
- At the first test screen (step 25, audio page next) core1 read
  ~36586082; from about 21 s after power-on onward it read 419825784 and
  stayed there, while beat kept counting. c1con 01000000.
So core 1 counted from its release, then froze: a large frozen number,
not 0. That fits your A (ALNK0 told to run with no clock stalls core 1).
Your plan for the next build (count at fixed points, a key that stops and
restarts ALNK0 without the clock step, core 1's flag and count in their
own block, the 0x80–0x8F words) is approved. Build it now as its own
probe unless it needs something from the spec side; say which you took.
