Try 5 works on the unit (owner, 2026-11-24, backup fm1-20261124-065615). Way 0, the SDK's steps: the Mac's notes play once each at the right pitch, the unit's keys send one note-on and one note-off each, and the instrument plays on after unplugging. The log: in 8 packets, 18 events (RXCOUNT1 4 each, one of 44 at connect: 11 events); out 7 packets of 4 bytes; no stalls, drops or give-ups; "USB gone" at unplug.
The loop is done. For the final build:
- Keep only way 0. Remove ways 1 and 2, the power-on cycling and its large text, and KEY7's and KEY8's test keys if nothing else needs them. Keep the port's spacing at 10 µs and the log records.
- Its own identity (0.15.0-u3u, or what you'd call the release of U3).
- The published build is still USB-off (R-USB-1), and the owner-only file is still marked so.
- Then mark #249 ready for review, so it gets full CI. Pack the final owner-only file for the owner's backtest: power-on sound, keys, ARP with its save, USB both ways, unplug.
