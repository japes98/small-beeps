#223 is merging. Two things:
1. Change D's pacing: one key press runs the whole 32-bit sweep
   automatically, with every per-try step exactly as you wrote it (log
   before the write, the watch, the firmware's own matrix check, its own
   undo, the re-check). Stop the sweep at the first try whose check fails
   or whose link moves, and show it. The firmware's matrix check makes
   per-press pacing unnecessary, and 64 presses in low light is what I
   want to avoid. The owner runs it once with bit 9 set and once clear.
   Update the prompt in place.
2. Your question 1: the cut-off "To clean" part was meant for clean and
   got into your message by mistake. Ignore it; nothing for you there.
End with "done, ready to clear".
