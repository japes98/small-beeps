Spec's prompt for step D is ready: drop/prompts/clean-br17-audio6.md
(one key press runs the whole 32-bit CON5 sweep, each try self-checked
and self-undone by the firmware). The owner has allowed it. Build it on
top of the build you're finishing now (the CRC/sb_now fix and the
next-key LED guide), as one file, with D's two runs (bit 9 set, then
clear) in the next-key order table.

Also: good find on sb_now(). Please check every other caller that
subtracts two sb_now() readings (timeouts, the audio pages' rates and
frames per second, the store, the scan), say in your report whether any
could have been affected before the fix, and add a seams case that forces
the wrap/interrupt race so sb_now() going backwards can't come back.
