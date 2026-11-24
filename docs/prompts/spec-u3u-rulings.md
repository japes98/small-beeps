U3-U rulings:
1. (a): USB starts only once the cable reading shows an awake computer, at the app's start and then about once a second.
2. (a): keep the spacing in its one place, start with a generous value (MIDI needs little speed), and log it.
3. Approved: on a give-up, log the stage and index, stop writing to USB until the next power-on, keep the instrument running.
4. (a): HW-172's order, with usb_slave_init's writes straight after the SIE's start, and SIEIE set last.
5. Approved, with the unit file's name marking it as owner-only with USB on (e.g. small-beeps-u3u-usb-owner-only-key-980f.fwsc).

No write to 0x16A00 or any clock register, as drafted. Update the draft's header: #245 was replaced by #247. Send U3-U to clean once #247 and #246 are on main.
