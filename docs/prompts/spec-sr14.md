Owner ruling for SR-14 (from clean's #185, now merged): spec may read
m-bootloader's sources for board facts, under the same guardrails as section 25.

Source: github.com/jvitkauskas/m-bootloader at 3ac7651a019f (MIT). Read
src/board.c, src/display.c, src/platform.c, src/boot.c, src/startup.S and the
matching sections of docs/SPEC.md, as far as SR-14 needs. Leave src/usb_midi.c
out (its notice says it draws on felucca-bsp, MPL-2.0); SR-14 needs no USB.

Take only hardware facts: the panel's pins and how it's brought up, the
backlight, the LEDs and the keys (PLAY, REC and the rest), and the state the
bootloader leaves when it starts the app (clocks, voltages, pins, what's
already on). Record them in HARDWARE-SPEC with provenance (source MB, the
commit), and log what you read in EXPOSURE. No stock-firmware details (016's
configuration and the like), no GPL firmware, no stock package; no code
copied, only facts in your own words.

Then answer SR-14, and write the next clean prompt so clean's next candidate
lights the backlight or one LED from those facts. End by naming the prompt's
path.

For your information: Phase B round 3 (clean's entry-return probe, 1b61609e...)
is pending on the unit; I'll pass its result on when I have it.
