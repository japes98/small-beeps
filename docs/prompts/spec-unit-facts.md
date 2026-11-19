Rulings: (1) The give-back writes BAUD = 1 between CON = 0 and restoring
CON, as m-bootloader does; BAUD can't be read back, so follow its sequence.
(2) What I observe on the unit is a fact source: record MASTER on ADC
channel 4, KNOB1 at matrix columns 8 and 9, core 1 not running after
m-bootloader's call (C1_CON 0x01000002), the store's counter and the CON
reading as HW facts, source "the unit, relayed by the owner", with the date.
PRESETS through an ADC channel stays a note until a build names the channel.
Update the clean prompt to match. End with "done, ready to clear".
