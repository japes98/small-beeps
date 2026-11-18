#190 (start2) works on the unit: small-beeps' start-up, screen, timer, keys
and LEDs. Answer clean's SR-16 (what the encoders, pot, audio, MIDI, the store
and core 1 need on the chip), from the sources my rulings allow, same
guardrails as sections 25 and 26.

Also, as an emulator request: fwtest doesn't model the panel's chip select
(PC7, HW-115), so start1's bug, the panel ignoring every byte with PC7 high,
passed CI and was only caught on the unit. Have fwtest's panel ignore bytes
sent while its chip select is high, and add a case that fails start1's
lcd.c.

Then write the next clean prompt. End with "done, ready to clear",
Questions, merge order, the prompt's path.
