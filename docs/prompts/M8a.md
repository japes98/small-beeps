>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session, working largely unattended (the owner checks in occasionally and may be asleep). Read this whole message before starting.

Setup notes:
- You are in the clean folder (~/Development/<top>/clean). Privacy rule as always; never read or print tools/private-terms.local.
- This prompt was written by the planning conversation (spec side): no hardware facts. Everything about the hardware comes from the allowed sources in CONTRIBUTING.md, starting with docs/HARDWARE-SPEC.md and docs/HARNESS.md. Note the change the spec side is making today: FM-1-RE's docs/io/09-storage.md is no longer allowed for the firmware side.
- Unattended mode: don't wait for merges. Every PR targets main (never another branch); a PR that depends on an earlier one includes its commits (cumulative), so each gets CI on its own and is green when the owner wakes. Give ONE merge order at the end, every PR in it green and mergeable into main as it stands. List REVIEWED.json entries in the PR; the owner's merge approves them. Questions for the owner go at the top of your final message; take the most reasonable reading meanwhile and say which. Stop all work if free disk drops below 2 GB. Don't wait on GitHub's run status more than 10 minutes at a time.
- The spec side is pinning fwtest 0.6.0 at the same time: when its pin PR exists, run the store's tests on that PR's branch (docs and config only; fetch with lazy fetching off) and report; build on 0.6.0 once the pin is on main.
- Signed tags don't exist yet; don't create releases.

## 0. Start safely
Banner OK (if it reports a config mismatch because the spec side changed clean.json, run tools/clean-setup.sh once the change is on main, and say so); tools/clean-update.sh ends with "no spec-side files on disk or in .git" (stop on STOP); terms file present (don't open it). Lazy fetching off for every git command. Archive the clean sessions not yet archived, run tools/check-transcripts.py; never open anything under sessions/spec/. EXPOSURE.md entry; save this prompt unedited as docs/prompts/M8a.md.

## 1. The store's region (small PR first)
The owner prefers that our firmware never erases the stock firmware's saved patches: move the store to the unused region the spec names (12 KiB, never the last 4 KiB) IF it meets 16 user slots, the selection and the settings with a stated wear life; otherwise keep the current region and explain why with numbers. Tests updated either way.

## 2. M8a: the instrument's interface (per docs/M8-PROPOSAL.md, with the owner's answers)
Owner's answers to the proposal's questions: 14 buttons (OCT- and OCT+ included); SEL is the shift key; macros stay offsets (not written into the patch on save) for now; 64 presets and 16 user slots; the spectrum is on the patch view by default, with log frequency; factory reset moves into Settings with a confirmation (replacing the SAVE+HOME hold); after M8, ARP then SEQ.
Build, in this order, each in its own PR:
1. The screen framework: one screen at a time, HOME back to the patch view, the bottom strip naming KNOB1–KNOB4 and their values on every screen, fixed meanings for MASTER, PRESETS, OCT- and OCT+, partial redraws within the drawing budget.
2. The patch view with the four macros (BRIGHT, COLOR, SHAPE, MOTION) as specified, sent and received as CC 16–19, and the old direct controls behind a "Knobs: direct" setting.
3. The operator and algorithm view (EDIT) with the live operator levels, and operator editing.
4. The envelope view (ENV) with the live position dot.
5. The live spectrum on the patch view (our own FFT; RAM and CPU within the proposal's figures).
6. Settings (GLO): MIDI channels, thru, local control, knob mode, factory reset with confirmation.
Not in M8a: the preset bank (M8b: the owner listens before it merges).
Tests: golden screens for each view, each control's effect in each view, the macros' effect on the sound (objective measures: brightness raises upper partials, COLOR moves partials off harmonics, SHAPE changes attack and release, MOTION adds modulation), drawing never making audio late, budgets (raise in their own PR first if needed). R-UI-* requirements traced. PLAN.md records M8a and names M8b (presets) next. Drop a build at ~/Development/<top>/drop/small-beeps-<short commit>.bin with its SHA-256.

## 3. After M8a, if time allows
- M8b candidates: build the 64-preset bank as the proposal describes, each preset passing its automatic tests, in a DRAFT PR (not for merging yet). Render each preset's reference note and a short phrase as WAVs into ~/Development/<top>/drop/presets/ with an index (number, name, category, one line on what it's for), so the owner can listen in the morning and say which to keep or change.
- Then a short ARP proposal, docs/ARP-PROPOSAL.md, like the M8 one: modes, controls, MIDI out behaviour, costs, questions for the owner. A document only.

Finish with "done, ready to clear", the Questions list, and one merge order (every PR green and mergeable into main; the draft preset PR listed separately as not for merging).
