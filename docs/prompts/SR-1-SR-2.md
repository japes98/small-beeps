>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are a spec-side session. Task: answer spec requests SR-1 and SR-2, and follow up on M1's observations. Read this whole message before starting.

Setup notes:
- You are in the spec folder (~/Development/<top>/spec). The owner drives this from a phone via Remote Control: short questions, one at a time. The owner merges PRs with GitHub's merge button.
- Privacy: this repository is public. Never write the owner's username, real name, email, hostname, local folder names or full local paths into any committed file, commit message or PR text; write paths relative to the repo, or as ~/... with the top folder shown as <top>. Never read or print tools/private-terms.local.
- This prompt is committed to docs/prompts/, which clean sessions read: it contains no hardware facts, and nothing you write outside harness/ may contain emulator internals.

## 0. Start

Update to main, run tools/spec-setup.sh, check the banner is OK and tools/private-terms.local exists (don't open it). Archive any spec session not yet archived, run tools/check-transcripts.py, add your EXPOSURE.md entry, and save this prompt unedited as docs/prompts/SR-1-SR-2.md.

## 1. Answer SR-1 and SR-2 (docs/SPEC-REQUESTS.md)

- Answer each by adding sourced entries to docs/HARDWARE-SPEC.md (new HW IDs, standing confirmed or emulator-only) and linking them from the request, as SPEC-REQUESTS.md describes. Facts, not code: requirements and register meanings, never a sequence transcribed from SDK driver code or the emulator.
- What the allowed sources don't establish becomes an open question (Q-n), stated plainly, and the request says which parts are answered and which stay open.
- SR-1 part (b), fwtest: say exactly what fwtest does today for each condition listed. If the allowed sources establish that the chip raises the exception for a condition, you may extend fwtest to model it (harness tests first, a new pinned image, HARNESS.md updated as black-box behaviour), labelled with its source. Never model behaviour the sources don't establish; say so instead.
- SR-2: real-hardware clock set-up is needed later (real hardware is Level 2), so a well-sourced partial answer plus open questions is fine.

## 2. M1's observations

- M1 measured fwtest's TIMER0 1 ms period as 24 000.7 to 24 001 time-base ticks rather than exactly 24 000. Find out whether that is how the chip behaves, an artefact of fwtest, or a firmware setting, and record the answer: as a spec fact, a HARNESS.md note, or a reply to the firmware side in the request log. Fix fwtest only if it is wrong.

## 3. Records hygiene

Records must not copy spec-experiment output files (memory dumps, captures, audio) into records/<sha>/; keep only their names and SHA-256 there. Existing records stay as they are. Add a test.

## Done when

- SR-1 and SR-2 are answered (fully or partly, with open questions), every new fact sourced; any fwtest change has tests and a new pinned image; the timer observation is explained in writing.
- Spec lint, separation checks and the audit pass; the record is PASS.
- Finish by committing everything and telling the owner "done, ready to clear". Don't archive your own transcript.
