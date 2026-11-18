Light probe result (light1, 74e19144…), on the unit, 2026-11-18:
- The backlight came on and PLAY's LED lit, for about 5 s; both went out.
- The recovery menu then said "APP EXITED".

So the entry is reached, the backlight (HW-116), the LED pins and the
shift-in (HW-117/HW-118) work as section 26 says, and the return to
m-bootloader works. The round-3 probe is no longer needed.

The chip key 0x980F is confirmed by the owner on the unit (m-flasher info,
2026-11-18); treat it as settled and don't ask again.

Next: the panel. Bring it up from HW-115 and show something unmistakable
(a solid colour or a simple pattern), with the backlight on, then return as
light1 does. Same rules as before: facts only from HARDWARE-SPEC; file an SR
for anything it doesn't give. Package with key 0x980F, flash 0x4000 up only.
End with "done, ready to clear", Questions, the merge order and the file to try.
