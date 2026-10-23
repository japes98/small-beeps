>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are a spec-side session. Task: two small corrections to the record. Read this whole message before starting.

Setup notes:
- You are in the spec folder (~/Development/<top>/spec). The owner drives this from a phone via Remote Control: short questions, one at a time. The owner merges PRs with GitHub's merge button.
- Privacy: this repository is public. Never write the owner's username, real name, email, hostname, local folder names or full local paths into any committed file, commit message or PR text; write paths relative to the repo, or as ~/... with the top folder shown as <top>. Never read or print tools/private-terms.local.
- This prompt is committed to docs/prompts/, which clean sessions read: it contains no hardware facts, and nothing you write outside harness/ may contain emulator internals.
- A clean session may be resolving M3's PRs at the same time; expect to update your branch if main moves.

## 0. Start

Update to main, run tools/spec-setup.sh, check the banner is OK and tools/private-terms.local exists (don't open it). Archive any spec session not yet archived, run tools/check-transcripts.py, add your EXPOSURE.md entry, and save this prompt unedited as docs/prompts/record-fixes-1.md.

## 1. The SR-3 session's missing entry

The SR-3 session has a barrier-log row in docs/EXPOSURE.md but no session entry. Add it, from its archived transcript: role, model ID and cutoff, what it read, its exposure. Mark it as added afterwards, with today's date.

## 2. Which hardware layer, under which licence

docs/EXPOSURE.md, CONTRIBUTING.md and earlier prompts say the emulator's chip model was partly written from "Felucca's GPL hardware layer". Repository metadata in audit/targets.json shows Felucca's board support package (hugelton/felucca-bsp) licensed MPL-2.0, while Felucca itself may be GPL. Find out which repository, at which licence, the emulator's chip model actually names or credits, using only:
- the vendored emulator's own comments, docs and licence files (vendor/emulator/);
- the public upstream fm1-emu repository's README and docs (not fm1-sid/ or probes/);
- repository metadata (names, licences, descriptions) through GitHub's API.
Never open Felucca's, felucca-bsp's or any other target's files, READMEs or web pages.

Write the answer, with sources, in docs/EXPOSURE.md as a dated correction note (never edit older entries' substance; say what was stated, what the sources show, and what that means). Update CONTRIBUTING.md's wording to match. If the sources don't settle it, say so plainly and leave the wording as it is, marked "unverified".

## Done when

- Both corrections are committed through a PR with the usual template; CI and the record pass.
- Finish by committing everything and telling the owner "done, ready to clear". Don't archive your own transcript.
