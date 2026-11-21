audio5 (6c3097a2…, hw3n) ran on the unit: 65 records read back. K and J
worked as designed (results to the spec side). Two things:
1. Three records in this run's log failed their CRC (decoder: "3 more
   with the magic but a failing CRC"; they fall at sequence gaps #34,
   #36 and #45, roughly 0x64800, 0x65800 and 0x6A000). Please find out
   why: a write interrupted, a page program crossing a boundary, the
   panel and flash sharing the bus, or something else. Fix it in the next
   build, and have the decoder print each failing record's offset and
   header.
2. Owner request: the keys can't be seen in low light. Light the LED of
   the key the owner should press next (slow blink), following that
   build's suggested order from one table in the code, and show
   "next: <KEY>" on the step row.
Put both in the next build, which will carry spec's step D once its
prompt is ready. Don't rebuild audio5 for these alone.

---

1. Three records in this run's log failed their CRC (#34 at 0x64800, #36
   at 0x65800, #45 at 0x6A000). I looked at the raw bytes: each is a
   record cut off partway. Its first pages are written correctly and its
   last 256-byte pages are still erased (FF): #34 is missing page 7, #36
   pages 3–7, #45 pages 6–7. Every good record has all 8 pages. All three
   came in fast bursts (end of sweep 1 into "J done", and mid-sweep 2).
   So a record write is being abandoned before its last pages are
   programmed: most likely a new record starting before the previous one
   has finished, or a page skipped on a busy timeout. Find which, fix it
   (finish each record's pages, waiting on busy, before the next starts),
   and have the decoder print each failing record's offset and which
   pages are blank.

---

Good find on sb_now(). Please also check every other caller that
subtracts two sb_now() readings (timeouts, the audio pages' rates and
frames per second, the store, the scan), say in your report whether any
could have been affected before the fix, and add a seams case that forces
the wrap/interrupt race so sb_now() going backwards can't come back.
