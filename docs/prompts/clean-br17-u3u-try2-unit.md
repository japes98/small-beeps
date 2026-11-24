U3-U try 2 on the unit (owner, 2026-11-23), spacing 10 µs, from power-on:
- "small-beeps" appeared in MIDI Studio. Notes went both ways. Unplugged, the instrument played on.
- Log (fm1-20261123-162559): every stage cable → set-up → reset → address → configured → first in → first out; interrupts 80, resets 1, setups 11, no give-up, no stalls, nothing dropped, polls at most 3. Read back: CON0 0002883D, CON1 00008000, IO CON0 0000164C.
- Bug 1, the unit's keys to the Mac (Pocket MIDI's monitor): note-ons only, no note-offs. Between each real note the Mac receives an extra 90 35 64. Sequence: 90 35 64, 90 35 64, 90 36 64, 90 35 64, 90 37 64, 90 35 64, 90 38 64 … 90 3B 64, 90 35 64. The log counts out 1 packet, 1 event.
- Bug 2, the Mac to the unit: Pocket MIDI sent 7 pairs (90 48 40 / 80 48 00 five times, then 4A, then 49). The owner heard each note double. The log: in 54 packets, 749 events; audio12's G counts 157 note-ons, the last 16 all note 72.
- Fix both in try 3. Add a seams check that each received packet gives exactly its own events, and that a key's release sends a note-off. Keep 10 µs as the default.
