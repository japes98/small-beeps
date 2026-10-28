>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes: you are in the clean folder (~/Development/<top>/clean). Privacy rule; never read or print tools/private-terms.local. This prompt was written by the planning conversation (spec side): no hardware facts; everything about the hardware comes from CONTRIBUTING.md's allowed sources. Every PR targets main; dependent PRs cumulative; ONE merge order at the end. Questions at the top of your final message. Stop below 2 GB free. A spec session works at the same time; never open its branches.

## 0. Start
The owner merged #150 to #153. Clean setup checks, archive clean-a1-packager's transcript, run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-1027.md.

## 1. The owner's answers to clean-a1-packager's questions
1. The blocked `ls`: record it as a reviewed entry that says exactly what happened: an attempt, denied by the settings, never ran, nothing listed. Approved.
2. M9-PLAN's build.container wording: the spec side updates it.
3. The second 0.7.0 image: the spec side investigates.
4. The .fwsc for the app: yes. Copy the CI-built package from #153's tree (or a fresh one from main) to ~/Development/<top>/drop/releases/small-beeps-dev.fwsc, with its SHA-256 next to it in a .sha256 file. The pair from one tag comes with m9.

## 2. Seams for firmwares built on small-beeps
small-beeps is meant to be a base other people build their own firmwares on. A downstream firmware (the owner's; don't name or describe it anywhere) asked for these, in general terms. Build them so any downstream firmware can use them, with base/ used unmodified. Each with tests and DESIGN-NOTES entries, and requirements where they fit:
- BR-1, a neutral engine seam: a build switch (e.g. SB_ENGINE_EXTERNAL) under which main() skips the base's FM engine and store start-up and calls functions a downstream firmware defines: an init (before interrupts, where fm_init() is called today), the block callback for audio_start(), and a main-loop hook called on each wake with work. Keep SB_DEMO_PLAITS working (it can become a user of the new seam).
- BR-2, the platform linkable without the instrument: a set of platform files (boot, interrupts, input, audio, LCD and screen, MIDI in and out, the store) that links without fm.c, fm_play.c, patches.c, arp.c, views.c, saving.c and spectrum.c, and a linker script whose assertions cover only the platform's records, with a documented place for a downstream engine's record. Today app.ld asserts sb_fm, sb_ui and sb_arp, and main.c and the main loop call the instrument.
- BR-3, core 1's start as a platform function: release core 1 into a given entry with a given stack and return once it runs, plus the lock and shared load the engine uses to hand work over, moved out of fm_play.c and core1.S into the platform with neutral names.
- BR-4, the C++ runtime and mem* in the platform: memcpy, memmove, memset, __cxa_pure_virtual, operator delete and the freestanding C++ headers as a platform part, not inside demos/plaits/.
- BR-5, building with outside sources: tools/build.sh options to add source folders outside firmware/ and to leave chosen base files out, with the same flags and deterministic outputs, and a documented way for a downstream repository to call the build image.
- BR-7, SysEx bytes from MIDI in: a byte tap called for every SysEx byte the parser reads (or midi_read handing on SysEx data in pieces), for dumps up to at least 4 104 bytes; work on them runs from BR-1's main-loop hook.
- BR-8, raw bytes to MIDI out: a call that takes a buffer and its length and streams it through the transmitter in chunks, holding queued channel messages until it ends (only realtime bytes may go inside SysEx).
- BR-9, storage for large records: store records for a 4 096-byte payload (or a kind whose payload spans records), a kind or id range reserved for downstream firmwares, and a factory reset that voids those too. Where a larger region goes is a later owner decision; keep today's region and say how much it holds.
Also: a build check in small-beeps' own build that refuses an image containing a store with write-back whose stored register is its own base register (the forms `[++rN=k] = rN` and post-increment ones); the spec side is answering what the chip does (SR-10). Report whether today's firmware contains any.
Then write docs/BUILDING-ON-SMALL-BEEPS.md: a guide for someone making their own firmware: clone, use the seams, build with the build image, test with fwtest, run it in the F-Emulator app, and MIDI out (what the base sends for you and how to send your own). Plain and practical.
Order the PRs so each seam can be merged on its own where possible.

## 3. M8b
The owner doesn't need preset notes: this is a sample firmware. Finish #126 with all 70 presets as they are (64 plus P65–P70), take main into it, resolve the DESIGN-NOTES conflict you predicted, make it ready for review (not a draft), and put it in the merge order.

Finish with "done, ready to clear", Questions, and one merge order.
