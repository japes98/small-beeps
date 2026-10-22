You are the spec-side session for milestone M0b of the small-beeps repository. Read this whole message before starting.

Setup notes for this session:
- You are running in ~/work/small-beeps/spec on the owner's Docker machine. The folder holds only .claude/settings.json, created by hand by the owner before this session started. Never edit, remove or loosen it.
- The owner is driving this from a phone via Remote Control: keep questions short and one at a time. The owner merges PRs with GitHub's merge button; you never merge, and never hold the owner's signing key.
- This prompt deliberately contains no hardware facts, because it will be committed to docs/prompts/, which firmware-side (clean) sessions read.

# M0b: the emulator harness (spec side)

## 0. Get the repo into this folder, and set it up

1. This folder isn't empty, so don't `git clone` into it. Instead: `git init`, add the remote https://github.com/japes98/small-beeps, fetch, and check out `main` (the hand-made .claude/settings.json is untracked and ignored, so it stays).
2. Read CONTRIBUTING.md, docs/PLAN.md (M0b and M0c), docs/EXPOSURE.md, docs/REQUIREMENTS.md and sessions/README.md. They are the rules; this prompt adds to them.
3. Record the hand-made file's SHA-256 in EXPOSURE.md as M0a did for the clean one, then run `tools/spec-setup.sh` (no argument: it sets up this checkout). It must accept the hand-made rules without dropping any. The banner hook takes effect from the next session; record that this session started without it.
4. Archive the previous session (M0a, clean side) with tools/archive-session.py and run tools/check-transcripts.py, as sessions/README.md says. Then add your own entry to docs/EXPOSURE.md: spec side, model ID and its training cutoff, and that you will read the F-Emulator / fm1-emu emulator source (crates fm1-isa, fm1-core, fm1-soc).
5. Save this prompt unedited as docs/prompts/M0b.md in your first commit.

## 1. Rules for the spec side

- **You may read** the emulator source in the public upstream `joakimeriksson/fm1-emu` (MIT), the JieLi SDK, FM-1-RE, datasheets and anything the firmware side may use.
- **You never open, fetch, search or quote** Felucca and anything built on it, dinghy and anything built on it, fm1-emu's `fm1-sid/` and `probes/lcdtest.c`, or M-VAVE's stock firmware and its disassembly. Even exposed, we don't copy from GPL code: the spec carries facts, never code.
- **Nothing you learn from emulator source leaves `vendor/emulator/` and `harness/`, except through two doors:** `HARDWARE-SPEC.md` (M0c, facts only, each sourced) and `docs/HARNESS.md` (this milestone: the harness's interface, below). The firmware side reads everything else in the repo, so:
  - **commit messages, PR titles and descriptions** from the spec side describe *what changed in the harness* in general terms, never emulator internals (no register names, addresses, struct names, code excerpts). Put that detail in comments inside `harness/` instead;
  - nothing under `docs/`, `tests/` (outside harness), `tools/`, records or release notes may contain emulator internals;
  - CI logs and records from harness runs may show results (pass/fail, hashes, images, numbers), not emulator source.
- **Spec-side transcripts contain emulator source**, so they must never reach a clean folder. Archive them under `sessions/spec/` (move the scheme in tools/archive-session.py, check-transcripts.py and sessions/README.md to `sessions/clean/` and `sessions/spec/`). Add `/sessions/spec/` to the clean sparse-checkout excludes in tools/setup-folder.sh, and add `Read(./sessions/spec/**)` to config/claude/clean.json's deny list (adding a rule is allowed; the deny-list test must keep passing). Make check-transcripts.py skip, not read, spec transcripts that aren't on disk, so it still works in a clean folder.
- **Who archives whom:** a spec session may archive the previous session of either role. A clean session archives only clean sessions and never opens anything under `sessions/spec/`. Write this into sessions/README.md and CONTRIBUTING.md.

## 2. Vendor the emulator

- Copy `crates/fm1-isa`, `crates/fm1-core` and `crates/fm1-soc` from the public upstream at a pinned commit (the current main, recorded by hash) into `vendor/emulator/`, with the upstream LICENSE and a `vendor/emulator/UPSTREAM.md` saying where and which commit. Never bring in anything else from that repo (no `fm1-sid/`, no probes, no other crates, no firmware files).
- A fetch script (`tools/fetch-emulator.sh`) reproduces the copy from the pinned commit and checks a tree hash, like tools/fetch-sdk.sh does for the SDK.
- Keep upstream code unmodified. If the harness needs a change in it, make the smallest patch, keep it as a separate file under `vendor/emulator/patches/`, apply it in the fetch script, and say why in UPSTREAM.md.
- REUSE: vendored files keep upstream's licence (add REUSE.toml entries as needed). PROVENANCE.md logs the vendoring.

## 3. The harness

`harness/`: a Rust workspace (Rust toolchain pinned in rust-toolchain.toml; Cargo.lock committed; third-party crates checked by the lockfile's hashes), a library plus the `fwtest` CLI. It must:
- boot a raw firmware image (no M-VAVE loaders, nothing M-VAVE's), with the image format and load rules written down in docs/HARNESS.md as the firmware side will need them;
- run N emulated milliseconds, driving inputs from a timed script (keys, encoders, the pot, MIDI in) in a simple text format;
- capture, as asked: RAM regions, the LCD as PNG, LED states, flash contents, audio as WAV, and instructions executed per audio block;
- detect halts, faults and hangs, and say which with a clear exit code;
- compare outputs with golden files (exact for deterministic outputs; documented tolerances where an output is meant to be approximate);
- emit JUnit XML and JSON results that tools/record.py can include in the commit's record.

Determinism: the same image, script and fwtest build give byte-identical outputs on every run and every machine. Test that in CI by running twice.

Harness tests: tiny test images for the harness's own tests live in `harness/tests/` (spec side, excluded from clean). Write them from the emulator's documented behaviour, not from any probe or firmware in fm1-emu.

## 4. How the firmware side uses it without seeing it

The clean side never has harness or emulator source on disk, so it uses a prebuilt fwtest:
- CI builds a container image with fwtest from `main` (base image pinned by digest, deterministic build) and publishes it to GHCR under the repo's name, low profile (no quiet words in the image name, labels or description).
- `tools/fwtest` (outside harness/, so the clean side has it) runs that image **pinned by digest**. The digest lives in a small committed file updated by a PR whenever the harness changes.
- docs/HARNESS.md is the clean side's whole manual: the CLI, the input-script format, outputs, exit codes, golden-file rules and the raw-image format. It describes behaviour as a black box; it doesn't explain how the emulator works inside. Review it against the rules in section 1 before committing.
- Records: when firmware tests run fwtest, the record notes the image digest used.

## 5. The spec-request channel

Create `docs/SPEC-REQUESTS.md`: how the firmware side asks for a hardware fact (a numbered question, why it's needed, the date), and how the spec side answers (by adding a sourced fact to HARDWARE-SPEC.md and linking it, never with code or explanations of other firmwares). Empty for now apart from the instructions and a template.

## 6. Requirements and plan

- Add R-HARN-* requirements (boot, inputs, each capture, halts, golden files, determinism, results format, the clean-side wrapper) to docs/REQUIREMENTS.md, each traced to tests.
- Add requirements for the separation itself: spec-side text discipline (section 1), sessions/spec exclusion, and that tools/fwtest uses a pinned image digest. Add CI checks where they can be automated (e.g. a check that commit messages and docs outside harness/ contain no identifiers that appear only in vendor/emulator/: build the list of such identifiers automatically and report hits without printing surrounding source).
- Update docs/PLAN.md: M0b's actual results; M0c next (spec side).

## Done when

- The repo is set up in this folder with the spec config and banner hook; the M0a transcript is archived and checked; EXPOSURE.md has this session's entry.
- `vendor/emulator/` is reproducible from the pinned upstream commit by script and hash.
- `fwtest` builds in the pinned container; its own tests pass in CI and run twice with identical outputs; JUnit/JSON results land in the commit's record.
- The fwtest image is published by digest, and `tools/fwtest` runs it.
- A fresh clean folder made with `tools/clean-setup.sh <new dir>` contains no `vendor/emulator/`, `harness/` or `sessions/spec/`, and its settings deny them. Test this in CI.
- docs/HARNESS.md and docs/SPEC-REQUESTS.md exist and pass review against section 1.
- Work arrives as small commits in one or more PRs, each with the What/Why/How/Result template; the owner merges them with the button.
- Finish by committing everything and telling the owner "done, ready to clear". Don't archive your own transcript; the next session does.
