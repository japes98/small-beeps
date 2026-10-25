>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are a spec-side session. Read this whole message before starting.

Setup notes: you are in the spec folder (~/Development/<top>/spec). Privacy rule as always; never read or print tools/private-terms.local. This prompt is committed to docs/prompts/: no hardware facts in it, and nothing outside harness/ may contain emulator internals. Every PR targets main; give one merge order. Stop all work if free disk drops below 2 GB. A clean session is working at the same time.

## 0. Start
Run tools/spec-setup.sh first (#110 changed spec.json, so the banner may report a mismatch until you do), then update to main, banner OK, terms file present (don't open it). Archive any spec session not yet archived, run tools/check-transcripts.py, EXPOSURE.md entry, save this prompt unedited as docs/prompts/owner-answers-1025.md.

## 1. Record the owner's answers (one small docs PR)
- docs/ARP-PROPOSAL.md: all six modes (UP, DOWN, UP/DOWN, ORDER, RANDOM, CHORD); rates 1/2, dotted 1/4, 1/4, dotted 1/8, 1/8, 1/8T, dotted 1/16, 1/16, 1/16T, 1/32 (no whole notes); ARP button: short press toggles on/off, hold shows the ARP screen; MIDI out sends the arpeggiated notes by default, with a setting to send the held keys instead; ARP settings saved per patch; follow incoming MIDI clock automatically, falling back to the internal tempo when it stops.
- docs/M9-PLAN.md: the app should read release.json (show the version, check the image's hash); M9 covers the app release only, the hardware package waits for M10; boot area, packaging tool and version scheme for hardware are decided at M10 (leaning towards our own packer); a hardware package keeps the stock user-patch region untouched; app releases start at 0.9.0.
- PLAN.md: the order after M8 is ARP, then SEQ, then FX; M9 (app release) fits after ARP. FX v1: a small 4-line feedback delay network reverb (Hadamard matrix, size and decay), a stereo chorus (one modulated delay per side, opposite LFO phases), and a stereo or ping-pong delay synced to the ARP/SEQ clock; designed from published literature only.
- docs/HARDWARE-SPEC.md, HW-85: note the owner accepts the AC7911B datasheet (served publicly, marked confidential) as a source for its three facts, which stay marked for confirmation on real hardware.

## 2. Ahead of ARP
Check that docs/HARNESS.md documents what the firmware side needs to test MIDI clock in (0xF8 timing, start/stop/continue) and MIDI out timing for arpeggiated notes; if fwtest lacks anything, add it as a harness feature with tests and a new image (publish, then a pin PR).

## 3. Then
Every 20 minutes for about 8 hours, check docs/SPEC-REQUESTS.md on main and in clean's open PRs' branches (that file only) for new requests and answer them.

Finish with "done, ready to clear", Questions, and one merge order.
