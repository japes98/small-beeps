>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are a spec-side session. Task: fix the similarity audit's failing self-test. Read this whole message before starting.

Setup notes:
- You are in the spec folder (~/Development/<top>/spec). The owner drives this from a phone via Remote Control: short questions, one at a time. The owner merges PRs with GitHub's merge button.
- Privacy: this repository is public. Never write the owner's username, real name, email, hostname, local folder names or full local paths into any committed file, commit message or PR text; write paths relative to the repo, or as ~/... with the top folder shown as <top>. Never read or print tools/private-terms.local.
- This prompt is committed to docs/prompts/, which clean sessions read: it contains no hardware facts, and nothing you write outside harness/ may contain emulator internals.
- Never open any audit target's code; work only from our files, the audit's tools, its reports and its self-test.
- A clean session (M3) may be running; expect to update your branch if main moves.

## 0. Start

Update to main, run tools/spec-setup.sh, check the banner is OK and tools/private-terms.local exists (don't open it). Archive any spec session not yet archived, run tools/check-transcripts.py, add your EXPOSURE.md entry, and save this prompt unedited as docs/prompts/audit-selftest.md.

## 1. The task

The audit workflow on main has failed its self-test since #37 (M2): it finds 8 of our 9 firmware files. Find out which file isn't found and why.
- If it's a bug, fix it, with a test that fails without the fix.
- If the file can't be scored by JPlag at all (for example, too few tokens), don't just drop it. Make the audit report such files explicitly as "not scorable by JPlag", with the reason. Add a second check that suits them (for example, an exact and near-exact comparison of that file's content against every target file, reporting scores only), with its own threshold justified in docs/AUDIT.md, and make the self-test cover that check too.
- Re-run the audit on main and confirm it's green. The earlier red runs stay as they are; PLAN.md notes the gap (which merges ran without a passing self-test) and its fix.

## Done when

- The audit is green on main with a passing self-test that covers every firmware file, one way or the other; tests cover the change; docs/AUDIT.md explains it.
- Finish by committing everything and telling the owner "done, ready to clear". Give the merge order. Don't archive your own transcript.
