>>> FOR THE SPEC (DIRTY) SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "spec". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are a spec-side session. Short job. Setup notes as before: privacy rule; never read or print tools/private-terms.local; this prompt is committed to docs/prompts/; nothing outside harness/ may contain emulator internals; every PR targets main; stop below 2 GB free.

## 0. Start
Run tools/spec-setup.sh, banner OK. Archive spec-a1-fwsc's transcript, run tools/check-transcripts.py, add your EXPOSURE.md entry, save this prompt unedited as docs/prompts/spec-answers-a1.md. The owner merged #141 to #146.

## 1. Record the owner's answers to spec-a1-fwsc's questions (one PR)
1. R-HARN-9's narrowing (#143): approved explicitly by the owner. Packages only through the crates' package reader, never the stock-boot extras; test packages built only from HARDWARE-SPEC.
2. Loader files: yes, the JieLi SDK's own uboot.boot and ota.bin are the candidates, not FM1 Open's boot files.
3. The app's package path: asked of the app session; leave "to confirm" until its answer arrives.
4. .fwsc's document-type rank: Alternate, confirmed.
5. The 0.8.0 pin PR: the clean side opens it (it's in its current prompt).
6. FM-1-RE documents that quote disassembly: allowed on the spec side, facts only, with the SDK or another source confirming where possible (as you did for +0x120). The rule against stock firmware covers the files and any disassembly of them, not a reverse-engineering document that cites them. Clean-side limits stay as they are.
Also from the app session: it keeps LSSupportsOpeningDocumentsInPlace true (opened files stay where they are, so they don't pile up next to the user's recordings). Update M9-PLAN's iOS section to match.

## 2. Parity doc
The app session reports that it already has patches 0003, 0005, 0006 and 0009, and is now applying 0010 (its rules, timing off by default) and 0011. Don't change docs/EMULATOR-PARITY.md's table yet; add a dated note under it saying this and that the app's confirmation, with commits, is pending.

Finish with "done, ready to clear", Questions, and one merge order.
