Two owner answers to spec's open questions:
1. The first app-area-only package leaves out blimit.bin, info.log, ota.bin, script.ver and tail.bin. The unit settles which of them an installer needs (Q-26), and R-REPRO holds.
2. Make the candidate in the .fwsc form, with only the app area in it: that's the form the owner's installer takes. Not the OTA form for now; if the unit refuses the .fwsc candidate, we'll ask for it then.
