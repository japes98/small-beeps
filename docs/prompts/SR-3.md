>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are a spec-side session. Task: answer spec request SR-3. Read this whole message before starting.

Setup notes:
- You are in the spec folder (~/Development/<top>/spec). The owner drives this from a phone via Remote Control: short questions, one at a time. The owner merges PRs with GitHub's merge button.
- Privacy: this repository is public. Never write the owner's username, real name, email, hostname, local folder names or full local paths into any committed file, commit message or PR text; write paths relative to the repo, or as ~/... with the top folder shown as <top>. Never read or print tools/private-terms.local.
- This prompt is committed to docs/prompts/, which clean sessions read: it contains no hardware facts, and nothing you write outside harness/ may contain emulator internals.
- A clean session (M3) may be running at the same time; expect to update your branch if main moves.

## 0. Start

Update to main, run tools/spec-setup.sh, check the banner is OK and tools/private-terms.local exists (don't open it). Archive any spec session not yet archived, run tools/check-transcripts.py, add your EXPOSURE.md entry, and save this prompt unedited as docs/prompts/SR-3.md.

## 1. Answer SR-3 (docs/SPEC-REQUESTS.md)

- Answer by adding sourced entries to docs/HARDWARE-SPEC.md (new HW IDs, standing confirmed or emulator-only), linked from the request. Facts, not code: requirements and register meanings, never a sequence transcribed from SDK driver code or the emulator. What the allowed sources don't establish becomes an open question.
- The firmware side observed that fwtest raises the panel transfer's interrupt even when the enable bit is clear, which disagrees with the spec. Decide which is right from the allowed sources. If fwtest is wrong, fix it in harness/ (harness tests first, a new pinned image, HARNESS.md updated as black-box behaviour) and say in the request what changed; if the spec is wrong, supersede the entry with a new one. Either way the firmware side must be told plainly in the request's answer.

## 2. Ahead of M3

Read HARDWARE-SPEC.md's panel section (keys, matrix, encoders, pot, LEDs) as the firmware side will for M3. Where a fact is emulator-only and a spec-side black-box experiment could confirm how fwtest behaves, add the experiment (CI reruns it) and update the standing. Don't add facts M3 hasn't asked for beyond that.

## Done when

- SR-3 is answered (fully or partly, with open questions), every new fact sourced; any fwtest change has tests and a new pinned image.
- Spec lint, separation checks, the records hygiene check and the audit pass; the record is PASS.
- Finish by committing everything and telling the owner "done, ready to clear". Give the merge order. Don't archive your own transcript.
