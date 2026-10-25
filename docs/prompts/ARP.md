>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

Preface (the owner can't merge right now): #130 (fwtest 0.6.0 pin) and #126 (presets draft) are not merged yet. Base your work on #130: every PR you open targets main and includes #130's commits (cumulative), so each is green on its own. Before ARP itself, in its own PR (also on top of #130): make PRESETS stop at the ends instead of wrapping (and adjust the tests and goldens that depended on wrapping), and add R-PRESET-n requirements and a C-PRESETS check to #126's branch, keeping #126 a draft. ARP's per-patch settings must also migrate the draft presets' format, so #126 still merges cleanly after ARP.

You are the firmware-side (clean) session for the ARP milestone. Read this whole message before starting.

Setup notes:
- You are in the clean folder (~/Development/<top>/clean). Privacy rule as always; never read or print tools/private-terms.local. This prompt was written by the planning conversation (spec side): no hardware facts. Everything about the hardware comes from CONTRIBUTING.md's allowed sources, starting with docs/HARDWARE-SPEC.md and docs/HARNESS.md.
- Every PR targets main (never another branch); dependent PRs are cumulative, so each gets CI on its own and is green. Give ONE merge order at the end. List REVIEWED.json entries in the PR. Questions for the owner go at the top of your final message; take the most reasonable reading meanwhile. Stop all work if free disk drops below 2 GB. Don't wait on GitHub's run status more than 10 minutes at a time.
- A spec session may be adding MIDI clock or timing features to fwtest and answering spec requests; use a new fwtest only once its pin PR exists (read HARNESS.md from that PR's branch if needed, docs only, lazy fetching off).

# ARP

## 0. Start safely
Banner OK; tools/clean-update.sh ends with "no spec-side files on disk or in .git" (stop on STOP); terms file present (don't open it); lazy fetching off. Archive the clean sessions not yet archived; run tools/check-transcripts.py; never open anything under sessions/spec/. EXPOSURE.md entry; save this prompt unedited as docs/prompts/ARP.md.

## 1. Scope (docs/ARP-PROPOSAL.md, with the owner's answers recorded there)
- Modes UP, DOWN, UP/DOWN, ORDER, RANDOM (a fixed generator, so tests can predict it) and CHORD.
- Rates 1/2, dotted 1/4, 1/4, dotted 1/8, 1/8, 1/8T, dotted 1/16, 1/16, 1/16T, 1/32; tempo, gate length and octave range as the proposal gives them.
- The ARP button: short press toggles the arpeggiator, hold shows the ARP screen (with the usual knob strip).
- MIDI out sends the arpeggiated notes by default; a setting sends the held keys instead.
- ARP settings are saved per patch (extend the patch format with a version bump and migration; the store and the presets keep working).
- Clock: an internal tempo, and incoming MIDI clock (0xF8, start, stop, continue) followed automatically, falling back to the internal tempo when it stops; the arpeggiator's timing stays sample-accurate within audio blocks.
- MIDI in notes and panel keys both feed the arpeggiator; latch or hold behaviour as the proposal says.

## 2. Tests
fwtest captures with golden outputs for each mode and rate; timing against MIDI clock (including tempo changes, start/stop/continue and clock loss); MIDI out of the arpeggiated notes against a golden capture; per-patch saving and migration; no stuck notes when switching modes, patches or stopping; no underruns under the loaded input with the arpeggiator running. R-ARP-* requirements traced. Budgets raised in their own PR first if needed.

## Done when
CI, the record and the audit pass; PLAN.md records ARP's results and says M9 (the app release) is next, then SEQ, then FX. Drop a build at ~/Development/<top>/drop/small-beeps-<short commit>.bin with its SHA-256. Finish with "done, ready to clear", Questions, and one merge order.
