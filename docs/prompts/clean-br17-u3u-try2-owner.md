U3-U try 2, the owner's runs (2026-11-23, spacing 10 µs). Backups fm1-20261123-162559 and fm1-20261123-180939; decoded with d20756e7's decoder (a70ad95a's can't name layout 14's fields; keep old layouts decodable).
- Every session reached configured with no give-up, stall or drop; polls at most 3; read back CON0 0002883D, CON1 00008000, IO CON0 0000164C.
- "out 1 packets 1 events" in all three sessions, though more messages went through: that endpoint looks never re-armed after its first packet.
- "in": 54 packets / 749 events, 19 / 195, 1 / 12, so about 10–16 events per packet: more is read than the packet holds.
- The unit to the Mac: two presses of C sent 90 3C 40, 90 3C 00, 90 3C 40, 90 48 00. 0x48 was the note the Mac had just sent, so outgoing bytes mix with incoming ones. The first run had a stray 90 35 64 between every two notes.
- The Mac to the unit: in the first session notes built up into a chord (G: 157 note-ons for 7 sent). After a reboot nothing from the Mac sounded, though small-beeps was still listed and the unit's notes still reached the Mac.
- Unplugging: 0 suspends logged in every session. Once, after unplugging, the unit's own keys went silent until a power-off. The instrument must play on whatever USB does.
- For try 3: separate receive and send buffers; each packet gives exactly its own events (by the received count); both endpoints re-armed after every packet; every release sends a note-off with its own note; unplug detected and logged, the instrument unaffected. Seams checks for each, with notes going both ways at once and several packets in a row.
