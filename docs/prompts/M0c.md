You are the spec-side session for milestone M0c of the small-beeps repository. Read this whole message before starting.

Setup notes for this session:
- You are in /Users/smallsignals/Development/F-Irmware/spec, set up by M0b with the spec config and banner. The owner drives this from a phone via Remote Control: short questions, one at a time. The owner merges PRs with GitHub's merge button.
- This prompt deliberately contains no hardware facts, because it is committed to docs/prompts/, which firmware-side sessions read.

# M0c: HARDWARE-SPEC.md (spec side)

## 0. Start

1. Update to main. Archive the previous spec session (M0b) into sessions/spec/ with tools/archive-session.py, and run tools/check-transcripts.py, as sessions/README.md says. Also archive any clean session that ended since the last archive (a short clean maintenance session that updated the clean folder).
2. Add your entry to docs/EXPOSURE.md (spec side, model ID and cutoff, what you will read).
3. Save this prompt unedited as docs/prompts/M0c.md in your first commit.

## 1. What HARDWARE-SPEC.md is

The firmware side's only window onto what the spec side knows. It holds facts about the hardware and about how fwtest presents it, never code and never how any firmware or the emulator is written. It is read by people and agents who must stay clean, so treat every line as if it will be read in court.

Every fact is an entry:
- an ID (HW-1, HW-2, ...; never reused or renumbered; a corrected fact gets a new ID and the old one is marked superseded, not deleted);
- the fact, stated as a property of the hardware or a requirement it imposes ("bit N of register R enables X"; "after reset, the LCD needs at least T ms before the first command"), never as a procedure copied from code;
- its sources, as precisely as possible (file and line or section of the JieLi SDK at the vendored commit, FM-1-RE document and section, datasheet and page, or "black-box experiment E-n");
- its standing: **confirmed** (an independent non-GPL source, or a spec-side black-box experiment in fwtest, agrees), or **emulator-only** (the only source is the emulator model, which was partly written from GPL code; the firmware side may rely on it but should prefer to confirm it by its own black-box test).

## 2. Rules for writing it

- Names: use the JieLi SDK's names for registers, bits and peripherals wherever they exist. Otherwise use plain descriptive names. Never use identifiers that occur only in vendor/emulator/ (CI's separation check will catch them).
- Facts, not code: no code, pseudo-code, struct layouts, tables copied from source, or comments copied from anywhere. No initialisation sequences transcribed from the emulator or the SDK's driver code: state the requirements (what must be set, what order is required by the hardware, timing limits) and let the firmware side design its own sequence.
- Minimal: include what the firmware side needs for M0d through M4 (below), and the answers to any open spec requests. Don't dump everything the emulator models. More can be added later through spec requests.
- Never derive a fact from forbidden material (Felucca and its descendants, dinghy, fm1-sid, probes/lcdtest.c, stock firmware or its disassembly), even indirectly. If the only way to learn something would be from those, record it as an open question, not a fact.
- Black-box experiments: you may confirm facts by writing small spec-side test images that you run in fwtest. They live under harness/spec-experiments/ (excluded from clean folders; add that path to the separation checks if needed). In the spec, cite them only by ID (E-n) and result ("E-4: writing X made Y happen within T"); their code never leaves harness/.

## 3. What it must cover

Organised by subsystem, each section saying which milestone needs it:
- the raw image and boot as fwtest presents them (consistent with docs/HARNESS.md, which defers some of this to the spec): load address, entry, the memories and their sizes, what state the core is in at entry, and how the second core is released;
- clocks and timers, and interrupts (enough for M1);
- the debug/marker channel fwtest observes;
- the LCD and its interface (M2);
- keys, the key matrix, encoders, the pot and LEDs, including the mapping from fwtest's key, LED and encoder numbers to the panel (M3);
- audio output: format, rate, how samples reach the output, and the timing fwtest measures (M4);
- flash storage, only as far as M7 will need; mark it later if it isn't ready;
- open questions: what isn't known, or is known only from forbidden material.

## 4. Review before the firmware side reads it

- When the draft is complete, start a fresh subagent with no context except docs/HARDWARE-SPEC.md, CONTRIBUTING.md and sections 1 and 2 of this prompt, and have it review every entry for: code or procedure-from-code, emulator-only identifiers, missing or vague sources, facts that seem to come from forbidden material, and anything the firmware side couldn't act on. Fix what it finds; commit its report as docs/reviews/M0c-spec-review.md.
- Run the separation checks over the spec. Add HARDWARE-SPEC.md to any check that should cover it.
- Add R-SPEC-* requirements (every entry has a source and a standing; no emulator-only identifiers; reviewed before release to the clean side) with tests where they can be automated, e.g. a lint that parses entries and fails on a missing ID, source or standing.

## Done when

- HARDWARE-SPEC.md covers section 3, every entry sourced with a standing, open questions listed.
- The review report is committed and its findings fixed; the separation checks and spec lint pass in CI; the record is PASS.
- docs/PLAN.md has M0c's results and says M0d (clean side) is next.
- PRs are small, follow the commit template, and say nothing about emulator internals outside harness/.
- Finish by committing everything and telling the owner "done, ready to clear". Don't archive your own transcript.

# Addendum (part of M0c)

1. When you archive the clean maintenance session, redact the merge summary's lines that list paths under vendor/emulator/ and harness/ (replace them with a note), and say so in its REDACTIONS.md. The owner keeps the original.
2. Fix the cause: in tools/clean-update.sh and the steps in docs/PLAN.md, the merge must run with --no-stat (and -q), because a diffstat lazily fetches the blobs it counts. Add a CI test that updates a blob-less sparse clean clone across a commit that changes vendor/emulator/ and harness/, and checks that none of their blobs reach .git.
