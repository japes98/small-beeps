Unit facts, 2026-11-21 (source UNIT, relayed by the owner), from audio3
(b139e49d…):
- Outcome "neither": with CLK_CON2 bit 9 set, step A (CON0 bit 11
  cleared and set again) and step B (bit 8 set, CLK_CON2 00000306), alone
  and together, leave ALNK0 dead: no source-11 interrupts, CON0 bit 15
  never changes, fps 0, nothing heard. All steps read back as intended and
  undo cleanly; no hang.
- Core 1 never stopped in this build, with or without bit 9 and through
  every step. The only change from audio2 was core 1's count moving to its
  own 32-byte block. So audio2's "core 1 stops / runs only with bit 9" was
  core 0 not seeing core 1's stores, not the clock or ALNK0. Replace the
  HW-149 hypothesis with this, and add it to Q-18 (core 1 reliability).
Record them. Then set out D, E and F (and anything new) for my ruling,
each with its source, what it would tell us, its risk and how it would be
undone or recovered from (a power cycle, or REC-at-power-on download
mode). Rank them. Also say plainly whether there is any route to sound
left that doesn't touch PLL2 or the system clock. Don't write a clean
prompt yet. End with "done, ready to clear".

---
Follow-up from the owner, same day:

Also, from clean (SR-21, please answer with the rest): the data cache's
line size; whether main RAM is cached, and whether the two cores' caches
stay in step; and which flush or invalidate a hand-off between the cores
needs (Q-18). Clean's working rule meanwhile: anything one core writes
and the other reads sits in its own 64-byte aligned, padded block. Clean
still can't explain why bit 9 made the count move in audio2; record that
as open.
