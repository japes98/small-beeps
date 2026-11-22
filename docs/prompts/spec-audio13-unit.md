audio13 on the unit (backup ~/Documents/M-Flasher/backups/fm1-20261122-181335.bin):
- D5: power-on into the instrument worked with sound, every Inst stage logged in order.
- ARP: sounded even and right to the owner, but no ARP record reached the log (the panel's REC save after ARP didn't produce one); clean to fix.
- U2-A: no hang.
  - From power-off: CON0 00008001 (00038001 a second later), CON1 0, IO_CON0 00000E0C, IO_CON1 0 (3 a second later), IO_CON2 00000E0C.
  - After m-bootloader's MIDI mode: CON0 00008000, CON1 00008000, IO_CON0 0000000C. So MIDI mode leaves bit 0 of CON0 clear, CON1 bit 15 set and IO_CON0 bits 9–11 clear.
- U2-B: run 1's states were out of order; use run 2.
  - CON0 bits 16–17 and IO_CON1 bits 0–1 flicker with no cable, with a charger and with the computer asleep.
  - They read steadily 0 with an awake computer.
  - VBUS (bit 5) never set. CHKDPO (bit 15) always set.
- U2-C: ch12/ch13 always 0 on the awake computer; 0 to about 940 in the other states.
- Conclusion: a host can be detected by reading alone (both lines held low); VBUS isn't readable with USB off.

Put these in the next round's PR, and set out U3 (enumeration as 1209:0001, "small-beeps") with rulings ahead. Also include the clean fix: the panel's REC save must write the ARP gaps to the log.
