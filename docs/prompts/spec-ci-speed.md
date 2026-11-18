#190 (start2) works on the unit: small-beeps' start-up, screen, timer, keys
and LEDs. To go faster from here, three things, in this order:

1. CI speed-up first (owner request): run the quick static checks first and
   stop on any failure; run C-HARNESS-ISA on PRs only when harness/, the
   toolchain pin, the CPU flags or the fwtest image change (always on main
   and before a release); and split the remaining checks into parallel jobs,
   with a final job that assembles the record exactly as now (a skipped
   check marked skipped, never passed). Show before and after times.

2. Numbering: from now on HW- numbers are the spec side's only, and P- rows
   are split by side (spec and clean each take their own range; say which),
   so parallel PRs stop conflicting. Record the rule where both sides
   read it.

3. SR-16 in full, in one answer: everything clean needs for the rest of the
   hardware: encoders, pot, the store on the chip, core 1's start, audio
   (clocks, output, DMA) and MIDI, from the sources my rulings allow, same
   guardrails as sections 25 and 26. Where the sources don't give a fact,
   say so per item, not as a new SR.
   Also, as an emulator request: fwtest doesn't model the panel's chip
   select (PC7, HW-115), so start1's bug passed CI and was only caught on
   the unit. Have fwtest's panel ignore bytes sent while it's high, with a
   case that fails start1's lcd.c.

Then write the next clean prompt: one hardware build that brings up the
encoders, pot, the store and core 1 together, each reporting on the test
screen, with what each outcome means; audio in the build after. End with
"done, ready to clear", Questions, merge order, the prompt's path.
