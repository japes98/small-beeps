New tool for unit runs (owner's request): photos are too slow and too
error-prone. From now on I'll read the whole 1 MiB flash back as an image
file after a run (in download mode), and the main session decodes it. So:

1. Add a report log to the hardware build:
   - A flash sector of its own for the log: outside the app image, outside
     the store, and never erased by installing a new build. Choose it from
     the spec's flash map; if the spec doesn't make one safe, file an SR
     rather than guess.
   - Fixed-format records, append-only, wrapping when the sector is full
     (erase once, then append; keep the newest). Each record: a magic word,
     a format version, a sequence number, the build identity, the beat
     count, a short label (what triggered it), then the values the screen
     would show (registers as 32-bit words, counters, step states), with a
     CRC.
   - Write a record automatically at the fixed points the screens already
     mark (end of boot, page start, after each step key and its undo), and
     on a dedicated key press ("save report"). Show "saved #n" on the step
     row so I know it worked.
2. A decoder in your repo (tools/, Python 3, no dependencies): takes the
   1 MiB image file, finds the log sector, checks each record's CRC and
   prints the records in order, with the register names. If no valid record
   is found, it should say so plainly (the first run will tell us whether
   what the firmware writes reads back as plain bytes in the image).
3. fwtest: a seams case that runs a build, triggers a few records, dumps
   the emulated flash and checks the decoder reads them back.
4. Keep the screens as they are; the log is in addition.

Build it on top of audio3 (same steps and keys) as a "report1" candidate,
so the first run repeats audio3 with the log, and we can compare against
the photos we already have. Finish with "done, ready to clear", Questions,
one merge order.
