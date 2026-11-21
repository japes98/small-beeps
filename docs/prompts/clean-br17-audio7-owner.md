Spec's audio7 prompt is ready: drop/prompts/clean-br17-audio7.md. The
owner has allowed it. Add set-ups L1 and L2 to the build you're
finishing (audio6 + the CRC/sb_now fix + the next-key LED guide), as one
file, with D held and out of the next-key order as the prompt says.
Also include, if not done already: check every other caller that
subtracts two sb_now() readings (timeouts, the audio pages' rates and
frames per second, the store, the scan), say whether any could have been
affected before the fix, and add a seams case that forces the
wrap/interrupt race.
