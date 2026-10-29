>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are a spec-side session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before: privacy rule; never read or print tools/private-terms.local; this prompt is committed to docs/prompts/; nothing outside harness/ may contain emulator internals; every PR targets main, cumulative, ONE merge order at the end; stop below 2 GB free. A clean session may work at the same time: before you finish, merge its latest open PR branches into yours and resolve shared-file conflicts (keep both EXPOSURE entries).

## 0. Start
tools/spec-setup.sh, banner OK, terms file present (not opened). Archive the last spec session's transcript, run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/spec-isa-audit.md.

## 1. Does fwtest run every instruction the toolchain can emit?
Firmwares built on small-beeps (ours and other people's, with other compiler flags and C++ code) may use instruction forms our own firmware never has. If fwtest lacks one, a firmware faults in fwtest for reasons that have nothing to do with it. Make the coverage complete, from the toolchain alone.
- Sources: only the pinned JieLi toolchain (P-1): its assembler, disassembler and compiler, and their own tables, help and documentation (for example the target description and instruction definitions the LLVM-based tools expose, `-mattr` variants such as +fprev1, and the assembler's accepted mnemonics), plus the JieLi SDK. Nothing else: no firmware of anyone else's, no other emulator, nothing the owner's other projects learned.
- Enumerate every instruction form the toolchain's assembler and disassembler know for this target, with each `-mcpu`/`-mattr` variant the SDK builds use. For each, check whether fwtest decodes and executes it; list the gaps.
- For each gap: establish its behaviour from the toolchain (its documentation and instruction definitions, and the compiler's own use of it: compile C that should produce it, at the flags the SDK uses, and read what the code expects of the result). Where the toolchain leaves a detail open (for example a rounding or tie rule), say so plainly, pick the behaviour the compiler's code relies on, and record it as a Q-n for the hardware phase.
- Implement the gaps in fwtest, each with a crate test and a harness test that fails without it, as patches under vendor/emulator/patches/, then a new fwtest image and a pin PR as usual. Facts go in HARDWARE-SPEC.md, sourced to the toolchain.
- Add a CI check that fails if the toolchain knows an instruction form fwtest doesn't decode, so future toolchain pins can't open a gap silently.
- Report: the count of forms, the gaps found, which were implemented, and which stay open and why.

Finish with "done, ready to clear", Questions, and one merge order.
