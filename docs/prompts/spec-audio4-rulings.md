#215 is merging. Rulings (owner):
1. H and I allowed in the next build, each by key press and undoable,
   like A and B. For H, CLK_CON1 by read-modify-write of bits 4–6 only;
   the counter's own register as needed.
2. D allowed only after H, and only if H shows an audio clock while ALNK0
   stays dead. Not in this build; it gets its own prompt then.
3. E and F: not now. Revisit only if H shows no audio clock.

Clean is building report1 now: audio3 plus a report log written to a
flash sector of its own, which I read back as a full flash image after
each run (so every register value on the screens is also logged). Write
the clean prompt for H and I as additions to report1, in the same build,
and make sure every H and I reading (counter counts, CLK_CON1 before and
after, ALNK1's registers) goes into the log as well as on screen. End with
"done, ready to clear".
