>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are a spec-side session, working largely unattended (the owner checks in occasionally and may be asleep). Read this whole message before starting.

Setup notes:
- You are in the spec folder (~/Development/<top>/spec). Privacy rule as always: never write the owner's username, real name, email, hostname, local folder names or full local paths into anything committed; ~/... with <top>. Never read or print tools/private-terms.local.
- This prompt is committed to docs/prompts/, which clean sessions read: no hardware facts in it, and nothing you write outside harness/ may contain emulator internals.
- Unattended mode: don't wait for merges. Every PR targets main (never another branch); a PR that depends on an earlier one includes its commits (cumulative), so each gets CI on its own and is green when the owner wakes. Give ONE merge order at the end. Questions for the owner go at the top of your final message; continue meanwhile. Stop all work if free disk drops below 2 GB. Don't wait on GitHub's run status more than 10 minutes at a time.
- A clean session is working at the same time (moving M7's store, then M8).

## 0. Start
Update to main, tools/spec-setup.sh, banner OK, terms file present (don't open it). Archive any spec session not yet archived, run tools/check-transcripts.py, EXPOSURE.md entry, save this prompt unedited as docs/prompts/evening-1024.md. Then, as the owner decided (record these as the owner's answers to day-1024's questions):
- EXPOSURE.md: a Claude session was run in the porter folder for an unrelated project (not small-beeps; no FM-1 firmware, emulator or small-beeps material). No porter session has run. Don't record the other project's details.
- config/claude/clean.json and spec.json: add a deny for cloning small-beeps-ports (Bash(git clone*small-beeps-ports*)), with the deny-list test updated. Running sessions will see a config mismatch until they restart; say so in the PR.
- CONTRIBUTING.md: FM-1-RE's docs/io/09-storage.md is no longer allowed for the firmware side (most of it describes the stock firmware's own code); keep it allowed for the spec side, cite only its hardware facts.

## 1. Pin fwtest 0.6.0
Open the pin PR for the 0.6.0 image published from #99's merge, run the firmware suite on it, and report any change. Tell the owner in your final message that the clean side should run its store tests on the pin PR's branch before it merges.

## 2. Q-22 and the flash pins
From allowed sources (the JieLi SDK, FM-1-RE's hardware documents, datasheets), settle as far as possible which pins the FM-1's flash uses (clock, chip select, data) and what the firmware must avoid touching at start-up; Q-21/Q-23 where the sources allow. If fwtest's flash wiring disagrees with the sources, fix it as a patch with tests and a new image (publish, then a pin PR), and update docs/EMULATOR-PARITY.md and harness/upstream/.

## 3. Audit targets
Run the discovery tool once and add any new FM-1 firmware repositories (for example a recent internet-radio firmware by a known FM-1 developer) to audit/targets.json, from metadata only.

## 4. M9 groundwork (between request checks)
A document only, docs/M9-PLAN.md: how a release would be packaged for the app (raw image, metadata, checksums) and for real hardware (.fwsc structure from FM-1-RE's documents; which of FM1 Open's Apache-2.0 boot/update files would be vendored, from licence headers and file names only, never their code; what the firmware side would need), the risks, and the questions for the owner. Don't build anything for M9.

## 5. Spec requests
Then, until about 10 hours after you started: every 20 minutes, check docs/SPEC-REQUESTS.md on main and in clean's open PRs' branches (that file only) for new open requests, and answer each in its own PR.

## 6. Before you finish (end of your watch)
Merge the clean side's latest open PR branches into your own branches (allowed in this direction; never push to theirs), resolving conflicts in shared files (EXPOSURE.md, PROVENANCE.md, REQUIREMENTS.md, PLAN.md) so your PRs merge cleanly AFTER all of clean's. Re-run CI and confirm every one of your PRs is green and mergeable.

Finish with "done, ready to clear", the Questions list, and: "merge all of clean's PRs in clean's order, then mine in this order: ...".
