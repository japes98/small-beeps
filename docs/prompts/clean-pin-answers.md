>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Read this whole message before starting.

Setup notes: you are in the clean folder (~/Development/<top>/clean). Privacy rule as always; never read or print tools/private-terms.local. This prompt was written by the planning conversation (spec side): no hardware facts. Everything about the hardware comes from CONTRIBUTING.md's allowed sources, starting with docs/HARDWARE-SPEC.md and docs/HARNESS.md. Every PR targets main; dependent PRs are cumulative; ONE merge order at the end. Questions at the top of your final message. Stop all work if free disk drops below 2 GB. A spec session is working at the same time; never open its branches or anything under the spec-side folders.

## 0. Start
The owner merged #136, #135, #138, #139, #140, #134 and #137. #126 stays a draft. Run the clean setup checks, archive overnight-1025's transcript (clean role) and run tools/check-transcripts.py, add your EXPOSURE.md entry, and save this prompt unedited as docs/prompts/clean-pin-answers.md. In your entry, also add the line overnight-1025 noted it missed: late in that session it printed #137's changed-file list (names only).

## 1. Pin fwtest 0.7.0
The 0.7.0 image was published from main when #137 merged. Open the PR that updates config/fwtest-image to its digest. On that branch run the firmware suite, the store tests and the ARP suite, and report any change in outputs (spec expects none: 2202 identical files on its local build). Its own PR, first in your merge order.

## 2. The owner's answers to overnight-1025's questions
Record them in PLAN.md's open items, the timing policy and RELEASING.md as fits, and act on them:
1. Steam Pipes' breath (a full-level feedback modulator on a quiet second carrier, ~25 dB under): accepted for now. The owner decides by ear when he sends preset notes.
2. Tutti Swell: keep it a pad, the stab 15 dB under. Same: the owner may move it after listening.
3. The run-end check: keep it failing CI, since the fix is mechanical. Make the failure message print the exact replacement --ms, so whoever sees it can fix it in one step.
4. The four exceptions to "goldens re-recorded only by the tool" are accepted. List each one, with its reason, in the timing policy so they stay visible.
5. The 250 ms gap before our clock resumes after the sender stops: accepted. Document it in the ARP/MIDI notes.
6. Releases:
   - Don't give m2–m8 versions. Change the workflow so a tag not in config/releases.json is skipped with a clear notice and a success, not a failure.
   - record.tree_sha256: don't add the records branch to the clean folder's allowed fetches (it brought spec-side blobs in before). The workflow reads it in CI; by hand stays only for local dry runs. Say so in RELEASING.md.
   - build.container: in CI, the release must build in the build image pinned by registry digest and record that digest. A local image ID is acceptable only for local dry runs, and the release must mark that as such.
7. The stack: raise it when SEQ needs it, with a measured high-water mark in the record. The compiler crash: log the details if it recurs, nothing else.

## 3. Coming next (no work yet)
The spec side is writing the facts for packaging our firmware as a standard .fwsc package (Phase A1). When they're merged, you'll get a prompt to build a tools/ packager from those facts only and test it on three load paths. Don't start on it, guess at the format or look for it anywhere. M8b (#126) waits for the owner's preset notes.

Finish with "done, ready to clear", Questions, and one merge order.
