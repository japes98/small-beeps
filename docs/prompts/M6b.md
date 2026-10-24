>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session for milestone M6b of the small-beeps repository. Read this whole message before starting.

Setup notes:
- You are in the clean folder (~/Development/<top>/clean). The owner drives this from a phone via Remote Control: short questions, one at a time. The owner merges PRs with GitHub's merge button. Don't wait for merges: stack branches and give one merge order at the end. List any REVIEWED.json entries in the PR rather than stopping to ask; the owner's merge is the approval.
- Privacy: this repository is public. Never write the owner's username, real name, email, hostname, local folder names or full local paths into any committed file, commit message or PR text; write paths relative to the repo, or as ~/... with the top folder shown as <top>. Never read or print tools/private-terms.local.
- This prompt was written by the planning conversation, which is spec side, so it contains no hardware facts. Everything about the hardware comes from the allowed sources in CONTRIBUTING.md, starting with docs/HARDWARE-SPEC.md and docs/HARNESS.md.
- Don't wait on GitHub's run status for more than 10 minutes at a time. Stop and tell the owner if free disk drops below 2 GB.
- fwtest 0.5.0 (MIDI out) is being pinned by the spec side at the same time. Build the parts that don't need it first; use it as soon as its pin is on main (or read its HARNESS.md from the open pin PR's branch, docs only, if it isn't merged yet).
- The signed tags m2 to m6a don't exist yet; the owner signs them at the Mac. Don't create releases.

# M6b: MIDI out

## 0. Start safely

1. Banner OK; tools/clean-update.sh ends with "no spec-side files on disk or in .git" (stop on STOP); tools/private-terms.local exists (don't open it). Lazy fetching off for every git command.
2. Archive the clean sessions not yet archived and run tools/check-transcripts.py. Never open anything under sessions/spec/.
3. EXPOSURE.md entry; save this prompt unedited as docs/prompts/M6b.md.

## 1. Scope

MIDI out through the transmit side the spec describes (HARDWARE-SPEC.md, HARNESS.md's MIDI-out capture). On the FM-1 itself the bytes go nowhere; in the app they will reach other apps and DAWs, which is the point.
- **The sender:** a small `midi_out` API: a queue the engine and UI write messages to, drained by the transmitter without ever blocking audio or the main loop; a stated policy for when the queue is full (which messages are kept, which dropped, and a counter), respecting the wire's real bandwidth.
- **What is sent:**
  - notes played on the panel (keys, with velocity if available), on a transmit channel;
  - knob moves as control changes, using the inverse of M6a's CC map, so another FM-1 (or this one's own MIDI in) would respond the same way;
  - program change when a patch is selected;
  - pitch-related controls if the panel has them.
- **Thru:** an option to echo incoming MIDI to the out (soft thru), off by default, never echoing our own output back.
- **Local control:** an option to send the panel's notes and knobs to MIDI out without playing the engine (the FM-1 as a controller), off by default.
- **Settings:** transmit channel, thru and local control, stored where M7 can save them, and shown on the screen.

## 2. Tests

- fwtest MIDI-out captures with golden files (midi-out.csv and midi-out.txt): each kind of message, running-status choice (whatever you choose, state it), thru with mixed input, local control off, a burst that overfills the queue (the policy holds and nothing wedges), sent bytes respecting the wire's timing.
- A round trip: MIDI out from one run fed as MIDI in to another run plays the same notes.
- Latency from a panel key to its note-on's first byte on the wire.
- R-MIDIOUT-* requirements, traced. Budgets: if needed, raise to M6b budgets in their own PR first.

## Done when

- MIDI out sends correctly and never disturbs audio; thru and local control work; tests pass deterministically; CI, the record and the audit pass; budgets hold.
- PLAN.md records M6b's results and says M7 (flash storage) is next.
- Drop a build at ~/Development/<top>/drop/small-beeps-<short commit>.bin with its SHA-256.
- Finish by committing everything and telling the owner "done, ready to clear". Give one merge order, and remind the owner of the unsigned tags. Don't archive your own transcript.
