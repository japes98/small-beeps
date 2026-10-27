>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are a spec-side session. The owner may not be watching; take the most reasonable reading and say which you took. Read this whole message before starting.

Setup notes: you are in the spec folder (~/Development/<top>/spec). Privacy rule as always; never read or print tools/private-terms.local. This prompt is committed to docs/prompts/: no hardware facts in it, and nothing outside harness/ may contain emulator internals. Every PR targets main; dependent PRs are cumulative; ONE merge order at the end. Questions at the top of your final message; continue meanwhile. Stop all work if free disk drops below 2 GB. Never open, fetch or search M-VAVE's stock firmware files or any disassembly of them; the rules in CONTRIBUTING.md stand.

## 0. Start
Run tools/spec-setup.sh, banner OK, terms file present (don't open it). Archive unarchived spec sessions, run tools/check-transcripts.py, add your EXPOSURE.md entry, save this prompt unedited as docs/prompts/spec-a1-fwsc.md. The owner merged #135, #138, #139, #140, #134, #137 and #136.

## 1. The owner's answers to spec-overnight-1025's questions
Record these in the right documents (docs/M9-PLAN.md, PROVENANCE.md, harness/upstream/ as fits), in one small PR:
1. The fwtest 0.7.0 pin PR: the clean side opens it, once the 0.7.0 image has been published from main, and runs its store and firmware tests on that branch before the owner merges. Not you. (If the image has not been published, say why.)
2. The type identifiers. Our container's exported type is `io.github.japes98.fm1img`: the format is the open project's (MIT), not the app's, so any app or emulator may declare it. Replace #136's placeholder with it. Also define the stock firmware package (the `.fwsc` extension) as an IMPORTED type the app declares, identifier `io.github.japes98.fwsc`, conforming to public.data, with a one-line note that it is a declaration for opening the files, not a claim to own the format. Say in M9-PLAN that .fm1img is the release format for our firmware and .fwsc is accepted for compatibility (section 2 below).
3. The USB behaviour note: the owner confirms it is covered by MIT on the same terms as P-47. Record that against P-59 / patch 0012.
4. The "busy" bit: stays open, as recorded in harness/upstream/fm1-emu-usb-port.md. Add it to the list of things to confirm on a real FM-1 (Phase B), nothing else.

## 2. Phase A1: our firmware as a standard .fwsc package (spec side)
Goal: the clean side can build our firmware into a correct .fwsc package that loads in F-Emulator's package path, in fwtest through the standard loader chain, and in the upstream fm1-emu web build, the same way a stock package does.
- Write the package's facts into docs/HARDWARE-SPEC.md as new HW-n entries, each sourced, facts only: the package layout (headers, sections, checksums or CRCs, alignment), any encryption or scrambling and its key derivation, and the loader chain's steps and what each checks before running the next. Allowed sources only: the JieLi SDK and its packaging tools and docs, FM-1-RE's documents, datasheets, and the emulator's documented behaviour. If a fact can only be learned from a stock file, don't learn it: say so and leave it open.
- Which loaders a package needs and where they come from: if the chain needs JieLi's or M-VAVE's own loader binaries, say which, their licence (the SDK's boot/update files are Apache-2.0), and whether our package may include them. Don't put any M-VAVE binary in the repo.
- Add to docs/HARNESS.md whatever fwtest needs to boot a package through the loader chain (an option or a mode, as a black box). If the harness can't do it yet, build it: a harness change with its own test that fails without it, a new fwtest image, and a pin PR.
- A test-only package for the harness's own test, made by you under harness/tests/ from the facts above (not from any stock file).
- Open a docs/SPEC-REQUESTS.md-style note to the clean side, in docs/M9-PLAN.md or a new docs/A1-PLAN.md, saying what it should build (a tools/ packager, from the HW-n facts only) and how it will be tested (the three load paths above).

Finish with "done, ready to clear", Questions, and one merge order.
