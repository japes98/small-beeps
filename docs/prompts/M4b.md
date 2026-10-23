>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session for milestone M4b of the small-beeps repository. Read this whole message before starting.

Setup notes:
- You are in the clean folder (~/Development/<top>/clean). The owner drives this from a phone via Remote Control: short questions, one at a time. The owner merges PRs with GitHub's merge button.
- Privacy: this repository is public. Never write the owner's username, real name, email, hostname, local folder names or full local paths into any committed file, commit message or PR text; write paths relative to the repo, or as ~/... with the top folder shown as <top>. Never read or print tools/private-terms.local.
- This prompt was written by the planning conversation, which is spec side, so it contains no hardware facts. Everything about the hardware comes from the allowed sources in CONTRIBUTING.md, starting with docs/HARDWARE-SPEC.md.
- Don't wait on GitHub's run status for more than 10 minutes at a time; if it looks stuck, say so and move on.
- The signed tags m2, m3 and m4 don't exist yet; the owner signs them at the Mac. Don't create releases; remind the owner at the end.

# M4b: platform load test, and the loaded-case budget

## 0. Start safely

1. Banner OK; tools/clean-update.sh ends with "no spec-side files on disk or in .git" (stop on STOP); tools/private-terms.local exists (don't open it). Lazy fetching off for every git command here, as the tools do.
2. Archive the clean sessions not yet archived and run tools/check-transcripts.py; list any REVIEWED.json entries needed, one line each in the PR. Never open anything under sessions/spec/.
3. EXPOSURE.md entry; save this prompt unedited as docs/prompts/M4b.md.

## 1. The loaded-case budget (first, its own PRs)

M4's speed budget measures the firmware at rest (about 1 800 instructions per block), while five voices playing cost about 9 900, and nothing gates that. For an instrument the worst case matters. Add a **loaded** measurement: a fixed input script that drives the firmware to its heaviest steady load (every voice sounding, every control moving), measured the same deterministic way as steady state, recorded in every record and in the history file. Give it a per-milestone budget and the same +3% gate within a budget, with the baseline rule from #48. Amend R-PERF-1/R-PERF-2 with tests, in its own PR; set the M4 loaded budget in a separate budgets PR.

## 2. The platform load test

Port **Mutable Instruments' Plaits** to our base as a **separate demo build**, to learn what this chip can afford before M5's engine is designed.
- **Source:** only the original upstream, github.com/pichenettes/eurorack (plaits/ and whatever of stmlib/ it needs), at a pinned commit. Check the licence of every file you take at that commit (it should be MIT; stop and tell the owner if anything isn't permissive). Never take it from any FM-1 firmware or fork that may have ported it.
- **Vendoring:** like the JieLi SDK: a fetch script with a checksum, under vendor/plaits/ with its licence files, NOTICE updated, PROVENANCE.md logged, REUSE entries. Keep upstream code unmodified; any change is a separate patch file with its reason.
- **The audit:** give the vendored Plaits to the similarity audit as base code (vendor/ is already excluded from comparison), so our glue code is scored but Plaits isn't, and so FM-1 firmwares that ported Plaits don't flag us for sharing it. Ask the owner to have the spec side make that audit change if it's in spec-side tooling; file it in SPEC-REQUESTS.md as a harness/audit request, not a hardware one.
- **The demo:** firmware/demos/plaits/, built by tools/build.sh as its own image, never part of the base image. It uses our audio and input APIs only: a key plays a note, ALGORITHM selects the engine, KNOB1–4 drive Plaits' main parameters, MASTER is volume. Whatever the toolchain or the chip lacks for Plaits (language features, maths), solve it in our runtime or as a documented patch, and record what it took.
- **Measure** in fwtest, deterministically: for each Plaits engine, instructions per audio block at its heaviest; how many voices of each would fit in core 0's time; what using core 1 would add (only if the spec makes starting core 1 possible; otherwise say what's missing, and file a spec request if needed). Check its audio is clean (no underruns, no NaNs or overflows) with fwtest captures.

## 3. Results

- docs/DESIGN-NOTES.md (M4b): what the port needed, the per-engine table, the headroom it implies for M5 (operators × voices at a target sample rate, on one core and on two), and anything about the API that felt wrong and should change before M5.
- PLAN.md records M4b's results and says M5 (the FM engine) is next.
- The demo is not shipped in releases unless the owner asks.

## Done when

- The loaded-case measure and budget are in and gating; the Plaits demo builds deterministically from a pinned, checksummed upstream; its measurements are in the record and the design notes; CI, the record and the audit pass.
- Finish by committing everything and telling the owner "done, ready to clear". Give the merge order, and remind the owner of the unsigned tags. Don't archive your own transcript.
