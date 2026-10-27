>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are a spec-side session, working unattended overnight; the owner reviews in the morning. Read this whole message before starting.

Setup notes: you are in the spec folder (~/Development/<top>/spec). Privacy rule as always; never read or print tools/private-terms.local. This prompt is committed to docs/prompts/: no hardware facts in it, and nothing outside harness/ may contain emulator internals. Every PR targets main; dependent PRs are cumulative; ONE merge order at the end. Questions at the top of your final message; continue meanwhile. Stop all work if free disk drops below 2 GB. A clean session works at the same time (M9's app release, preset candidates); before you finish, merge its latest open PR branches into yours and resolve shared-file conflicts so yours merge cleanly after its.

## 0. Start
Run tools/spec-setup.sh, banner OK, terms file present (don't open it). Archive unarchived spec sessions, run tools/check-transcripts.py, EXPOSURE.md entry, save this prompt unedited as docs/prompts/spec-overnight-1025.md. The owner approved owner-answers-1025's ALLOWED_MISMATCH (by merging #127) and declined the clock BPM script event (not needed).

## 1. The app's USB patch note
The F-Emulator app found a USB register-access port whose "done" bit never sets in the emulator, so firmware waits for its own timeout; its behaviour-only note is ~/Development/<top>/drop/emulator-patches/usb-port-done.md (read only that file there). Confirm or refute the behaviour from allowed sources (the JieLi SDK's USB code and headers, FM-1-RE's documents). If confirmed: a patch under vendor/emulator/patches/ with a harness test that fails without it, a new fwtest image (publish, then a pin PR), the firmware suite run on it (report any change), docs/EMULATOR-PARITY.md and harness/upstream/ updated. If not confirmed, say what the sources show.

## 2. The single-file release format (M9)
Add to docs/M9-PLAN.md a precise definition of the app release's files: release.json's fields (names, types, required/optional), and a single-file .fm1img container (for example a zip with a fixed layout, or a simple header plus payload) that the F-Emulator app can open in one tap from Files or AirDrop; versioning of the format itself; how the app verifies it. A document change only, in its own PR, so the firmware side and the app can both build to it.

## 3. Watch
Until about 8 hours after you started: every 20 minutes, check docs/SPEC-REQUESTS.md on main and in clean's open PRs' branches (that file only) for new requests and answer them.

Finish with "done, ready to clear", Questions, and one merge order (clean's PRs first, then yours).
