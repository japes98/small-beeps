>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are a spec-side session. Read this whole message before starting.

Setup notes:
- You are in the spec folder (~/Development/<top>/spec). The owner drives this from a phone via Remote Control: short questions, one at a time. The owner merges PRs with GitHub's merge button.
- Privacy: this repository is public. Never write the owner's username, real name, email, hostname, local folder names or full local paths into any committed file, commit message or PR text; write paths relative to the repo, or as ~/... with the top folder shown as <top>. Never read or print tools/private-terms.local.
- This prompt is committed to docs/prompts/, which clean sessions read: it contains no hardware facts, and nothing you write outside harness/ may contain emulator internals.
- Stop and tell the owner if free disk drops below 2 GB.
- A clean session (M6a, MIDI in) is running and waits on SR-8; answer SR-8 first and get it merged before the rest.

## 0. Start

Update to main, run tools/spec-setup.sh, check the banner is OK and tools/private-terms.local exists (don't open it). Archive any spec session not yet archived, run tools/check-transcripts.py, add your EXPOSURE.md entry, and save this prompt unedited as docs/prompts/midi-in-out.md.

## 1. MIDI in: answer SR-8 (first, its own PRs)

Answer SR-8 (docs/SPEC-REQUESTS.md) from allowed sources only (the vendored emulator, FM-1-RE's documents, the JieLi SDK, public product pages and manuals; never any firmware's source, FM1 Open included): sourced HW entries with their standing, open questions where the sources don't settle it. If fwtest's MIDI input model is incomplete or wrong against what the sources establish, fix it as a patch with harness tests and a new pinned image (the usual merge, publish, pin sequence), update HARNESS.md and docs/EMULATOR-PARITY.md, and write harness/upstream/ notes for the app.

## 2. MIDI out

The goal is MIDI out from firmware running in the emulator (fwtest and the F-Emulator app), using the real MIDI-out hardware of the FM-1's sibling, the M-VAVE SMK-37, which runs FM-1 firmwares through a board layer.
- a. From the same allowed sources, find how the SMK-37 sends MIDI out: transport (a UART's transmit side to a TRS/DIN socket, USB, or Bluetooth), peripheral and pins, speed and framing; and whether the FM-1's chip has the same peripheral, and how it relates to the MIDI input UART from SR-8. Record it in HARDWARE-SPEC.md, sourced, with its standing and open questions. Stop and report before (b) if the transport is USB or Bluetooth; the owner decides.
- b. If it's a UART: model its transmit side for the FM-1 board as a patch, with harness tests; fwtest gains a MIDI-out capture (raw bytes with timestamps, plus a decoded text log) with golden-file support. New pinned image; HARNESS.md documents it as black-box behaviour, including what happens on a real FM-1. Update docs/EMULATOR-PARITY.md and write harness/upstream/ notes for the app, where the bytes will go to CoreMIDI.

## 3. Housekeeping

- Audit: the self-test has found 25 of 30 files since #61. Fix it, keeping every file covered one way or another (JPlag, the text check, or an explicitly reported reason), with a test that fails without the fix; confirm green on main; PLAN.md notes which merges ran without a passing self-test.
- Disk: report docker system df and df -h, what belongs to this project, and what's safe to remove. Delete nothing without the owner's yes.
- FM1 Open (m-vave/fm1_open): read only its licence and terms files (LICENSE*, THIRD_PARTY*, any SDK terms file), never code or scripts, and record in docs/EXPOSURE.md and PLAN.md's risks what they allow, especially redistribution of the SDK and flashing. A third party summarised them as GPLv3 with a linking exception plus a proprietary binary SDK; confirm or correct that from the files.

Finish with "done, ready to clear" and the merge order.
