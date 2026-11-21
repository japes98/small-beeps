audio3 (b139e49d…, identity FM-1_0.10.0-hw3j) on the unit, 2026-11-21:
- Core 1 never froze in this build. Page 3/4 after boot: every mark from
  rel to now moved ("+"), "moved" = "now", r 32514. It kept counting
  through every step below (4/4 "n" row rising each time). So with its
  count in its own block it runs; that points to your B (core 0 not seeing
  core 1's stores through a shared line), not to ALNK0. Please say what
  that means for core 1's shared data from now on.
- REC (bit 9): CLK2 00000006 → 00000206. IRQ 0, fps 0.0.
- ARP (A) with bit 9: CON0 800 → 0 → 800 (A −11 00000000, +11
  00000800). IRQ 0, b15 0, fps 0.0. Undo: fine.
- SAVE (B): CLK2 00000206 → 00000306. IRQ 0, fps 0.0.
- ARP (A again, B taken): CON0 800, CLK2 00000306. IRQ 0, fps 0.0.
- Nothing heard on the speaker at any step. One ARP pressed before REC was
  refused as designed (refused 1). SEQ wasn't pressed.
#214 is merged. Nothing else for now; the next audio step waits on the
spec side and my rulings.
