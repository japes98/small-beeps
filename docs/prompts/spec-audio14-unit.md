audio14 on the unit (backup ~/Documents/M-Flasher/backups/fm1-20261123-070223.bin):
- ARP (R): done. 123 gaps of 5514–5515 frames, 124.7–127.6 ms; REC's save worked ("ARP saved"), and the ARP-off record was written too. audio13's missing save was REC not being pressed.
- P: 0x16A00–0x16A0C read 00000000 008881C3 00000000 00000000, the same from power-off and after m-bootloader's MIDI mode, a second later too. Bit 1 of 0x16A00 is clear in both.
- U2-A: repeats audio13's values for both starts.

Record these in the next round's PR. Then draft U3-U from HW-178, with no write to 0x16A00 or any clock register: MIDI mode ran USB with that block reading off, so try without it first. List the outcomes ahead for my ruling, including recovery through m-bootloader's PLAY menu. Plan the run as: plug into the Mac, see whether "small-beeps" appears in Audio MIDI Setup, then notes both ways.

#245's C-SEP-TERMS failure: still to fix, as asked. Find the identifier for clean.
