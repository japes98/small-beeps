>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session for milestone M0d of the small-beeps repository. Read this whole message before starting.

Setup notes for this session:
- You are in ~/<top>/clean. The owner drives this from a phone via Remote Control: short questions, one at a time. The owner merges PRs with GitHub's merge button.
- This prompt was written by the planning conversation, which is spec side, so it deliberately contains no hardware facts. Everything you know about the hardware must come from the allowed sources in CONTRIBUTING.md, starting with docs/HARDWARE-SPEC.md.

# M0d: the smallest firmware (firmware side)

## 0. Start safely

1. Check the session banner says status OK. If it says CONFIG MISMATCH, stop and tell the owner.
2. Bring the folder up to date without fetching anything it leaves out. It is on the branch clean/maintenance-1, which is already merged. Do exactly this, and stop and tell the owner if anything fails or prints STOP:
   GIT_NO_LAZY_FETCH=1 git fetch -q origin
   GIT_NO_LAZY_FETCH=1 git switch -q main
   env -u GIT_NO_LAZY_FETCH git merge --ff-only --no-stat -q origin/main
   GIT_NO_LAZY_FETCH=1 sh tools/clean-setup.sh
   sh tools/clean-update.sh
   The last command must end with "no spec-side files on disk or in .git". Then delete the merged local branch clean/maintenance-1.
3. Archive any clean session not yet in sessions/clean/ (at least b7ed6c1a, which holds only a /clear), as sessions/README.md says, and run tools/check-transcripts.py. Never open anything under sessions/spec/.
4. Add your entry to docs/EXPOSURE.md (firmware side, model ID and its training cutoff, no exposure).
5. Save this prompt unedited as docs/prompts/M0d.md in your first commit.

## 1. What to read

- CONTRIBUTING.md (the rules), docs/PLAN.md (M0d), docs/REQUIREMENTS.md, docs/TOOLCHAIN.md.
- docs/HARNESS.md in full, including its notes on capture timing.
- docs/HARDWARE-SPEC.md: the sections M0d needs. Note each fact's standing. Where you rely on an emulator-only fact, add your own black-box test that confirms it in fwtest, and say so in the design notes.
- The vendored JieLi SDK headers and the allowed FM-1-RE documents, as needed. Log every source you use in PROVENANCE.md.
- Never anything on the forbidden list, nothing under vendor/emulator/, harness/ or sessions/spec/, and no other firmware's source.

If you need a hardware fact the allowed sources don't give, don't guess and don't look elsewhere: add a request to docs/SPEC-REQUESTS.md (by PR), tell the owner, and work around that part or wait.

## 2. The firmware

The smallest firmware that proves our own code boots and runs in fwtest:
- our own startup code and linker script, written from the spec, the SDK headers and first principles;
- `main` that writes a marker, then a heartbeat that fwtest can observe over time;
- freestanding C11 plus whatever assembly startup needs; no toolchain C library, nothing prebuilt from the SDK; our own minimal runtime (only what this needs);
- built by tools/build.sh in the pinned toolchain container, deterministic (the CI double build must stay byte-identical);
- every file with SPDX headers; small commits, each with the What/Why/How/Result/Sources/Exposure template.

Write docs/DESIGN-NOTES.md entries for each real choice (memory layout, stack, startup order, how the heartbeat is timed), each citing the HW IDs, SDK files or experiments it rests on. Choose your own designs; where the spec gives requirements, meet them in your own way.

## 3. Tests

- Tests run the built image through tools/fwtest (the pinned image digest) with suites and golden files as docs/HARNESS.md describes: it boots, the marker appears, the heartbeat keeps its timing within a stated tolerance, there are no faults or halts.
- Black-box tests for any emulator-only facts you rely on.
- Each test names the requirements it checks (add R-BOOT-* and any others to docs/REQUIREMENTS.md), and the record's traceability table shows them.
- Record the image's size (code, data, bss) in the record; budgets start in M0e.
- Replace firmware/src/placeholder.c, or keep it only if something still needs it, and say which.

## Done when

- The folder is updated safely and the earlier sessions are archived and checked.
- The firmware builds deterministically in CI, its fwtest suite passes, and the record is PASS with traceability.
- DESIGN-NOTES.md and PROVENANCE.md cover everything used; EXPOSURE.md has this session's entry.
- docs/PLAN.md records M0d's results and says M0e is next.
- Finish by committing everything and telling the owner "done, ready to clear". Don't archive your own transcript.

<!-- Saved by session M0d with one change, under the owner's privacy rule (docs/prompts/M0d-addendum.md): the local path in the setup notes is written as ~/<top>/clean. -->
