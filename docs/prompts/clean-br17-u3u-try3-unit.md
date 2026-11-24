Try 3, way 0 on the unit (fm1-20261123-194712). This is a regression: in try 2's first session the Mac's notes sounded (repeated and chording, but heard); in try 3 nothing from the Mac sounds. The cause: RXCOUNT1 isn't the length. It read 56, 12, 60, 16, 64, 20, 68, 48, stepping by 4, for 4-byte packets.
	•	In, for try 4: don't use RXCOUNT1 for the length. Since you clear the buffer after each read, parse 4-byte USB-MIDI events until the first all-zero one, at most 16, and drop events whose code index doesn't match their status byte. Log RXCOUNT1 alongside, still. No new register.
	•	Out: every message the Mac received was the first one again (90 3C 64, note-offs included), and packets of 64 and 28 bytes went out where 4 were written. That question is with the spec side; keep KEY8's ways.
	•	USB gone/back work, and the instrument played on.
	•	The owner can't use the test screen (no key is lit, and the step row is too small). Make the way of sending go to the next at each power-on (0, 1, 2, then 0), shown in large text at power-on, and logged.
	•	Give try 4 its own identity.
