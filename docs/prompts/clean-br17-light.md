>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

## 0. Start
Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-light.md.

## 1. BR-17, the light probe: the backlight and PLAY's LED (after round 3)
Round 2: the unit's installer took the hardware package, m-bootloader says "app OK" and starts it, and the unit shows nothing (SR-14). The round-3 entry-return probe (`1b61609e…`) is waiting on the unit. The owner will pass on its result.

The spec side has answered SR-14 in HARDWARE-SPEC section 26 (HW-115 to HW-119): the panel's pins and bring-up, the backlight, the key matrix, the LEDs, and the state m-bootloader leaves when it calls the app. It is in the spec side's pull request #186, which also carries your #185 and merges before this work starts (check that it has). Read section 26, with HW-56, HW-91 and HW-112. Take every fact from there, and don't learn any from a tool's source. If you need a fact section 26 doesn't give, file a spec request (SR) that names it exactly.

**(a) A light probe.** Add a probe build (a define like `SB_PROBE_LIGHT`, beside R-PROBE-1's) whose entry, before anything else:
1. Lights the backlight: PA2 an output driven low (HW-116).
2. Lights PLAY's LED (HW-117, HW-118):
   - PA1, PA3 and PA4 are outputs driven low, and the four LED lines (PA9, PA10, PH6, PH9) are outputs driven low.
   - Shift in the column word `0xFBFF` as HW-117 says, then latch it. Make each clock and latch edge its own read-modify-write of `OUT`, with a barrier (`csync`) between high and low. HW-117 says edges that are too short select the neighbouring column.
   - Drive PA10 high.
3. Holds both for about 5 s. HW-119 gives the clocks the app starts with. Busy-wait or use a timer, as you judge; HW-119 says TIMER0 is stopped and interrupts are off.
4. Puts them out again: PA10 low, the word `0xFFFF` shifted in and latched, and PA2 an input. Then returns to m-bootloader as HW-119 describes: the saved registers and the stack pointer as it got them, and nothing written in the bootloader's RAM or the retained area. Use only registers, and the stack below the stack pointer it got, as any called function does. If you use anything else, say what and why it is safe.

On the unit this should show: the screen's backlight on (the panel itself is not set up, so expect a lit black or blank screen) and PLAY's LED lit, for about 5 s. Then both go out and m-bootloader's recovery menu says "APP EXITED". If nothing lights but the menu says "APP EXITED", the entry ran and the pins are the question. If neither happens, the entry wasn't reached.

**(b) Its tests.**
- Without the define, the image is build A's, byte for byte.
- With it, in fwtest, the probe writes the port registers it should (the run's unmodelled-access record or a capture shows them) and returns.
- Its hardware package, made with key `0x980F`, passes `fwsc.py check`. That key is the one the owner's installer showed in round 2, relayed and not a fact on this side. The owner confirms it with `m-flasher info`.
- Add a requirement next to R-PROBE-1.

**Not in this change:** no panel set-up yet. HW-115 gives it, and it is the next round's if this one lights.

Finish with "done, ready to clear", Questions, one merge order, and the exact file to try: its path, its SHA-256, the flash range m-flasher's plan should show (from `0x4000` up, no lower), and the three outcomes above.
