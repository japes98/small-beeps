>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session for milestone M6a of the small-beeps repository. Read this whole message before starting.

Setup notes:
- You are in the clean folder (~/Development/<top>/clean). The owner drives this from a phone via Remote Control: short questions, one at a time. The owner merges PRs with GitHub's merge button. List any REVIEWED.json entries in the PR rather than stopping to ask; the owner's merge is the approval.
- Privacy: this repository is public. Never write the owner's username, real name, email, hostname, local folder names or full local paths into any committed file, commit message or PR text; write paths relative to the repo, or as ~/... with the top folder shown as <top>. Never read or print tools/private-terms.local.
- This prompt was written by the planning conversation, which is spec side, so it contains no hardware facts. Everything about the hardware comes from the allowed sources in CONTRIBUTING.md, starting with docs/HARDWARE-SPEC.md and docs/HARNESS.md.
- Don't wait on GitHub's run status for more than 10 minutes at a time. Disk is low: check free space before large builds, clean up only your own outputs, and tell the owner below 3 GB.
- A spec session is working on emulator parity at the same time and will publish new fwtest images; expect to update your branch and re-run when the pinned image changes.
- The signed tags m2 to m5 don't exist yet; the owner signs them at the Mac. Don't create releases.
- MIDI out is not part of this milestone: the spec side is still working out which port it uses. It will come as M6b.

# M6a: MIDI in

## 0. Start safely

1. Banner OK; tools/clean-update.sh ends with "no spec-side files on disk or in .git" (stop on STOP); tools/private-terms.local exists (don't open it). Lazy fetching off for every git command.
2. Archive the clean sessions not yet archived and run tools/check-transcripts.py. Never open anything under sessions/spec/.
3. EXPOSURE.md entry; save this prompt unedited as docs/prompts/M6a.md.
4. fwtest 0.3.0 is pinned and runs SR-7's instruction forms (see SR-7's answer: note its correction about the base register). Remove the copy_words workaround and build.sh's check for the form, in a small PR with the suite passing.

## 1. Scope

MIDI in, from what docs/HARDWARE-SPEC.md and docs/HARNESS.md say about how MIDI reaches the firmware (in fwtest and on the chip). If they don't say enough, file a spec request and tell the owner before building on a guess.
- **Parser:** a robust MIDI 1.0 byte parser of our own: running status, realtime messages anywhere (including inside other messages), System Exclusive skipped safely with a length limit, malformed input never wedging it.
- **Messages to the engine:** note on/off with velocity (note on at velocity 0 is a note off), pitch bend (range as a patch or global setting), modulation wheel, sustain pedal (held notes, and notes that end under the pedal), all notes off and all sound off, program change selecting a patch.
- **Channel:** a receive channel setting, with omni as the default, stored where M7 can save it later.
- **Control changes:** a small, documented default map from CC numbers to engine parameters (and the four macro-style knobs, if they exist yet), designed so M8 can extend it; no MIDI learn yet.
- **Mixing with the panel:** MIDI notes and panel keys play together without stuck notes; the panel's display shows incoming notes.

## 2. Tests

- fwtest MIDI input scripts with golden outputs: every message type above, running status, realtime bytes interleaved, a SysEx flood, truncated and garbage input, a dense stream (for example, all 16 voices retriggered every block) with no dropped or stuck notes, sustain pedal cases, channel filtering.
- Latency from a MIDI note's last byte to sound, timed exactly per HARNESS.md's rules.
- R-MIDI-* requirements, traced in the record. Budgets: if the parser and dense MIDI input push the loaded measure past the M5 budgets, raise them to M6 budgets in their own PR first.

## Done when

- MIDI in plays the engine correctly and robustly; tests pass deterministically; CI, the record and the audit pass; budgets hold.
- PLAN.md records M6a's results and says M6b (MIDI out) is next, waiting on the spec side.
- Drop a build at ~/Development/<top>/drop/small-beeps-<short commit>.bin with its SHA-256.
- Finish by committing everything and telling the owner "done, ready to clear". Give the merge order, and remind the owner of the unsigned tags. Don't archive your own transcript.
