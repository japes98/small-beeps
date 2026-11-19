>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-start3.md.
- Wait until the spec side's #192 has merged (it carries #191 and #189; check that all three have). Then read:
  - HARDWARE-SPEC sections 27 (HW-120 to HW-124) and 28 (HW-125 to HW-130), with HW-9, HW-18, HW-40, HW-56, HW-85, HW-115 to HW-119;
  - docs/SPEC-REQUESTS.md, SR-15 and SR-16;
  - CONTRIBUTING.md, "Numbering" (new): HW- numbers are the spec side's only; your P- rows are P-74 to P-499.
- Take every fact from those. Where section 28 says a fact is open, this build finds it out on the unit. Don't take it from anywhere else.
- **This prompt replaces clean-sr15-flash.md.** Its store changes are part (c) below.
- **fwtest 0.11.0** (HARNESS.md, "The LCD", "Versions"): the panel ignores bytes while PC7 is an output driven high. Once its image is published from main, open the pull request that moves `config/fwtest-image` to it. Show that the seams suite's hw case still passes on main's hardware build, and say what it reports for start1's build (`58c87df3`), whose panel now shows the bands but not the pattern.

## 1. BR-17, start3: the encoders, the pot, the store and core 1 in one hardware build
#190 (start2) works on the unit: start-up, the screen, TIMER0, the keys and the LEDs. Add one hardware build (`SB_HW_FM1`, as R-HW-1's) that brings up the four parts below together. Each reports on the test screen in rows of its own, and each row says what it is. Keep start2's bands and its key and LED test as they are.

Two things section 28 changes for every part:
- Set both `ssp` and `sp` before interrupts go on (HW-126).
- The vector table at `0x01C7FE00` may be written only after the boot block r0 points at has been read (the chip key at +12). Never write `0x01C7FD80` to `0x01C7FDD7`.

TIMER4 at 24 MHz needs `CON` bit 3 on the chip (HW-125). If you use it as the time base, set it, and show its count against TIMER0's on the screen once.

**(a) The encoders and the rest of the matrix (HW-117, HW-129).** No source gives the encoders' pins.
- The screen shows the matrix: for each of the 16 single-zero column words, rows PA5 to PA8 (pull-ups on, closed reads low, HW-117), as a 16 × 4 grid of open and closed.
- Below it, the live input registers of ports A, B, C and H, in hex. Mask out the pins this build drives itself and say which.
- Outcomes:
  - A key press closing exactly one cell gives that key's column and row.
  - An encoder turned one detent that toggles two cells in turn gives that encoder's two contacts in the matrix, as fwtest's are (HW-38).
  - An encoder that changes no cell but flips a bit in the port registers is wired outside the matrix: that bit is its pin.
  - Nothing changing at all means a pin set-up is missing: say which pins have pull-ups.
- The owner turns each encoder both ways and presses each key once, and reads you the screen.

**(b) The pot (HW-40, HW-129).** SARADC channels 0 to 11, each converted in turn as HW-40 gives it, with their values on the screen, refreshed about 10 times a second.
- Set channels 3 (PB1) and 4 (PB6) as analogue inputs: direction input, digital input off, no pulls. That set-up is this build's choice; section 28 doesn't give it, so say so.
- Outcomes:
  - The channel that follows the pot from end to end is the pot.
  - If none follows it, the set-up is wrong, or the pot is on a channel this build doesn't set up. The values of the others still say which pins are driven.

**(c) The store on the chip (HW-120 to HW-124, HW-128).** In two steps, the second only if the first worked.
1. **The round trip, read-only.** From code and data in RAM, with interrupts off:
   - take SPI0 from the window as HW-128 says;
   - read the JEDEC ID and status registers 1 and 2 (`0x9F`, `0x05`, `0x35`);
   - give the window back exactly as HW-128 lists it (the mode word, the base, the key, the cache invalidation, the cipher on);
   - return to code in the window.

   Show the ID and both status bytes. Light one LED from RAM code before giving the window back, and a second after the first instruction back in the window, so a hang shows where it stopped. Outcomes:
   - The ID shows (`856014` or `B36014`) and the build runs on: the round trip works.
   - The first LED lights but the screen freezes: the give-back fails. Report the LEDs, and stop there: no writes.
   - No LED lights: taking SPI0 fails.
2. **The store.** Only if step 1 worked:
   - The store accepts both IDs (HW-124 item 1). It refuses any other ID, and any set protection bit (BP0 to BP4 in status 1, CMP in status 2), with results of their own. It reads each erase back as all `0xFF` (item 4). It keeps the busy-bit wait after every erase and page program.
   - Add the tests clean-sr15-flash.md asked for: a test build that gives the store an ID and status bytes in place of what it read, and the cases with each part, an unknown ID and each protection bit, in its region and in one at `0x80000`.
   - On the unit, the build keeps a start-up counter in its default region at `0xFC000` (`store_put` and `store_get`) and shows it.
   - Outcomes: the counter goes up by one at each power-on, so the store works on this unit. A refusal shows its reason (the ID, or protection set). A failed read-back shows which.

**(d) Core 1 (HW-9).** Release core 1 as HW-9 says, running a loop from RAM that increments a counter in RAM. Show the counter on the screen, sampled once a second.
- Outcomes:
  - It rises steadily: core 1 runs after m-bootloader's call.
  - It stays 0: core 1 never started. Show `C1_CON` as read back.
  - It rises and then stops: say when.
- Start nothing else on core 1 yet.

**Tests.**
- Without `SB_HW_FM1` the image is build A's, byte for byte.
- In fwtest the build runs: the matrix grid follows an input script's keys and encoders, channel 4 follows the pot, the store's counter goes up across `--flash-out` and `--flash` runs, and core 1's counter rises.
- Its hardware package, key `0x980F`, passes `fwsc.py check`.
- R-HW-1 gains the four parts.

**Not in this build: audio.** The build after this one brings up the audio link and the DAC (HW-43 to HW-45, HW-130). It will play a tone after HW-43 to HW-45's set-up alone, to show what more the output needs on the chip.

Finish with "done, ready to clear", Questions, one merge order, and the exact file to try: its path, its SHA-256, the flash range m-flasher's plan should show, and for each of (a) to (d) what the owner should do and read back to you.
