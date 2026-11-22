Rulings for audio12: S yes. G yes. G2 only if G finds the start-up patch is the cause; clean decides from its fwtest check and says which it did. D5 now. D6 now. D8 later, in the level round.

USB MIDI: U0–U3 approved, with the sources as listed. From FM-1-RE's 06-usb.md, take only what isn't drawn from the stock firmware (the same rule as the note on Q-9). MIDI only, no USB audio. Device identity: pid.codes' vendor ID 0x1209 with its test product ID 0x0001 during development; apply for our own product ID before release. Check both against pid.codes' current rules first. Product and manufacturer strings say "small-beeps", never FM1, FM-1 or M-VAVE. Put the USB plan's facts (U0) and the fwtest host model (U1) in their own PRs, in parallel with audio12; no unit write for USB until U2's read-only checks are reported.

Save these rulings with audio12's prompt and send it to clean once #237 is merged. Merge order: #237 alone.
