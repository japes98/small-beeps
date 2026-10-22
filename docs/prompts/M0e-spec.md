>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the spec-side session for milestone M0e (spec part) of the small-beeps repository. Read this whole message before starting.

Setup notes:
- You are in the spec folder (~/Development/<top>/spec). The owner drives this from a phone via Remote Control: short questions, one at a time. The owner merges PRs with GitHub's merge button.
- Privacy: this repository is public. Never write the owner's username, real name, email, hostname, local folder names or full local paths into any committed file, commit message or PR text; write paths relative to the repo, or as ~/... with the top folder shown as <top>. If you see one of those terms anywhere in the repo, tell the owner rather than repeating it. Never read or print tools/private-terms.local; only the tools use it.
- This prompt is committed to docs/prompts/, which clean sessions read, so it contains no hardware facts, and nothing you write outside harness/ may contain emulator internals (CONTRIBUTING.md).
- A clean session (M0e, performance) may be running at the same time. Expect to update your branch if PLAN.md or EXPOSURE.md changed on main before your PR merges.

# M0e (spec part): the similarity audit, and harness follow-ups

## 0. Start

1. Update to main (a normal pull is fine on the spec side), run tools/spec-setup.sh, and check the banner says status OK.
2. Check that tools/private-terms.local exists (don't open it). If it doesn't, stop and ask the owner to copy it in.
3. Archive any spec session not yet in sessions/spec/ (at least M0c's), and run tools/check-transcripts.py. This time, archive only spec sessions; the clean side archives its own.
4. Add your entry to docs/EXPOSURE.md. Save this prompt unedited as docs/prompts/M0e-spec.md in your first commit.

## 1. The similarity audit

The evidence that our firmware isn't derived from the GPL firmwares, measured rather than asserted.

- **Targets:** Felucca and every firmware built on it, dinghy and anything built on it, and fm1-emu's fm1-sid. You may not read any of them, so identify them from repository metadata only: names, owners, URLs and commit SHAs (GitHub's repository search API, `git ls-remote`). Never open their files, READMEs or web pages. List each target with its URL and pinned commit in `audit/targets.json`; if you can't find a repository for a named firmware from metadata alone, list it as unresolved and tell the owner.
- **The job:** an isolated CI workflow (`audit.yml`) that runs on pushes to main and on demand, never on pull requests from forks. It fetches each target at its pinned commit into a temporary directory, runs JPlag (pinned version, checked by hash) on our `firmware/` against each target, and deletes the targets afterwards. The GPL sources are never committed, cached, uploaded as artifacts, or printed: the job's logs and outputs contain only scores and file names.
- **Fairness:** give JPlag the vendored JieLi SDK as base code, so code both sides took from the SDK doesn't count, and exclude `vendor/`. Score a **control**: an unrelated permissive embedded C project (pick one, pin it, say why in the audit doc). Our scores mean something only next to the control's.
- **Results:** each run writes scores (overall and the top file pairs, by name only) into the commit's record. `docs/AUDIT.md` explains the method, the targets, the control, and the threshold: a pair scoring above the control's highest score by a margin you choose and justify fails the job.
- **When it fails:** nobody on either side reads the matched code. Document the procedure: the owner is told; a separate **auditor** session (a third role, recorded in EXPOSURE.md, allowed to read the GPL target and our code, and never allowed to write firmware or spec afterwards) compares the flagged pair and writes a finding. Add the auditor role to CONTRIBUTING.md and to config/claude/ (its own settings), but don't start one now.
- Requirements: R-AUDIT-* in docs/REQUIREMENTS.md, traced to the job's checks.

## 2. Harness follow-ups

- **Timer polling:** the clean side observed that fwtest treats a loop that polls a timer as waiting even when it stores to RAM on every pass, and that captures can land late in such loops. Describe in docs/HARNESS.md, as black-box behaviour, exactly when fwtest treats code as waiting, what that does to capture timing, and how a test can get exact timing. If the behaviour is wrong rather than undocumented, fix it in harness/ (fwtest's own tests first), publish the new image, and update the pinned digest.
- **The two doors:** make the separation check (check-emulator-terms) accept, without per-term entries, any term that appears in docs/HARDWARE-SPEC.md or docs/HARNESS.md on main, since those passed review. Keep config/emulator-terms-reviewed.json for anything else, and drop entries the new rule now covers.
- **Spec requests:** answer any open ones in docs/SPEC-REQUESTS.md.

## Done when

- audit.yml runs on main with every target pinned (or listed as unresolved), the control scored, and scores only in the record; docs/AUDIT.md and the auditor role are documented.
- HARNESS.md covers the polling behaviour; any harness fix has its tests and a new pinned image.
- The separation check accepts terms from the two documents, with tests.
- PLAN.md records the results. Finish by committing everything and telling the owner "done, ready to clear". Don't archive your own transcript.
