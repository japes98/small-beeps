Start3b on the unit gets through to the main loop. Fold into the clean
prompt and HW-132:
- CON reads back 0x009803B5 (clear photo), not 0x00980381: it reads back,
  but not as the mode word m-bootloader writes. Record it as read, relayed.
  The give-back should restore CON as read, as I said.
- The flash round trip works; the store's counter goes up one per power-on.
- Core 1 doesn't run after m-bootloader's call (counter 0, c1con 01000002).
- MASTER is ADC channel 4; PRESETS looks like an encoder read through an ADC
  channel; KNOB1 is in the matrix at columns 8 and 9.
Then finish: #196 can merge once #195's new head is in it and CI passes.
