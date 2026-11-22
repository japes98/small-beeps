Keep the instrument start behind SEL for now. If it works on the unit in this run, the next round makes power-on go straight to the instrument again, with HOME for the test screen. 

audio12b worked on the unit. SEL's start: every Inst record in order, sound on. The sweep: A1–A10 each have a longest fill of 982–1 018 µs with 8 voices, nothing clipped, no late halves (fwtest said 142–146 µs, so fwtest's fill time doesn't predict the unit's). Both stops worked. MASTER smooth, no jumps. Backup: ~/Documents/M-Flasher/backups/fm1-20261122-150817.bin.

#241's CI: C-UNIT and C-CLEAN-FOLDER fail (run 45062300075). Fix both on #241 with no new firmware. Run those two checks locally first; if the .fwsc changes, say so.

Next round (audio13), as ruled: power-on goes straight to the instrument, with HOME held at power-on for the test screen. Fold in the U2 read-only USB checks (U2-A, U2-B, and U2-C on its own key), from spec's draft as the owner ruled it.
