>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session, working unattended overnight; the owner reviews in the morning. Read this whole message before starting.

Setup notes:
- You are in the clean folder (~/Development/<top>/clean). Privacy rule as always; never read or print tools/private-terms.local. This prompt was written by the planning conversation (spec side): no hardware facts.
- Every PR targets main (never another branch); dependent PRs are cumulative, so each is green on its own. ONE merge order at the end. REVIEWED.json entries listed in the PR. Questions for the owner go at the top of your final message; take the most reasonable reading meanwhile. Stop all work if free disk drops below 2 GB. Don't wait on GitHub's run status more than 10 minutes at a time.
- A spec session works at the same time (it may change docs/M9-PLAN.md to define a single-file release format; read it from its open PR's branch, docs only, if you need it before it merges).

## 0. Start
Run tools/clean-setup.sh, banner OK, tools/clean-update.sh ends with "no spec-side files on disk or in .git", terms file present (don't open it), lazy fetching off. Archive unarchived clean sessions, run tools/check-transcripts.py, EXPOSURE.md entry, save this prompt unedited as docs/prompts/overnight-1025.md. Record the owner's answers to ARP's questions in PLAN.md's open items: ARP on/off stays per patch; tempo and the notes-or-keys choice are instrument-wide; the clock-stop definition stands; while following an external clock, our own clock out is suppressed (implement this, with a test); keys.txt tapping ARP is fine; force-pushing your own unmerged branches is acceptable if recorded in EXPOSURE.md.

## 1. Timing goldens policy (small PR)
Runs end at least 1 ms clear of audio-block boundaries; MIDI captures are compared with a small stated timing tolerance; goldens are re-recorded only by a tool that proves the change is a pure time shift (same notes, bytes and sound). Apply it to the existing cases.

## 2. M9: the app release (per docs/M9-PLAN.md and the owner's answers)
- A release build: the raw image plus release.json (name, version starting 0.9.0, image file name, size, SHA-256, the commit, the fwtest version it passed on, the record's tree hash), and a single-file .fm1img holding both (if the spec side's format PR exists, follow it; otherwise propose the format in your PR and say so).
- A workflow that builds these deterministically from a tag and attaches them to the GitHub release; it never creates a tag. Releases for already-signed tags only; tags m2 and later aren't signed yet, so don't create those releases tonight.
- docs/RELEASING.md: how a release is cut, verified and loaded into the app.
- Tests: the release is reproducible byte for byte, its hashes match, and release.json validates against the format.

## 3. M8b preset candidates (draft #126 stays a draft)
The owner wants variants covering the classic FM sounds, built from known recipes, never copied: design six NEW candidates from these recipes, with your own numbers, checked with your measurement tools: an orchestral swell/stab (detuned near-1:1 carriers, slow attack, plus a brass-like layer with fast decay); a round sequenced synth bass (feedback 1:1 stack, short filter-like modulator envelope); a punchy 80s riff lead; a calliope (near-pure carrier, breath from a low-level, feedback-heavy modulator, slow attack, gentle vibrato); an FM acoustic piano (two or three slightly detuned pairs, velocity to brightness, decaying index, slight inharmonicity in the upper pair); a wiry, biting bass (few operators, strong feedback, fast-closing modulator). Never open any voice bank or SysEx, never use factory names. Add them to #126 as candidates 65–70 (don't remove any preset; the owner will choose replacements), passing the preset tests, and render their WAVs into ~/Development/<top>/drop/presets/ with INDEX.md updated.

Finish with "done, ready to clear", Questions, and one merge order (#126 listed as draft, not for merging).
