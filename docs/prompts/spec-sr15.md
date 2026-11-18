Owner request, SR-15: the FM-1's two flash chips.

Units sold since autumn 2026 carry a different flash chip. The owner's unit
reports 0x856014 (relayed: m-flasher info and m-bootloader's recovery menu,
"flash 856014 1024K"). Other units report 0xB36014. small-beeps (and
RevoiceDX's saves at 0x80000) must work on both.

Sources you may read, same guardrails as section 25 and 26: the two chips'
public datasheets (Puya P25Q80H, UCUN UC25HQ80), and m-bootloader at
3ac7651a019f (MIT): the SPI flash code in src/platform.c, src/board.c,
src/loader.c and src/load15 needs. Leave
src/usb_midi.c out. No GPL firmware, no stock package, no stock-firmware
details; facts only, in yance and EXPOSURE.

Answer in HARDWARE-SPEC: the commands and status
bits small-beeps uses (regram, sector erase, the
busy bit), with each one'imum), and every
difference between the twall-beeps, or that there
is none. Say what small-bmage works on both.

Then write the clean promst case if the emulator
can model the second chip if not). End by naming
the prompt's path.
