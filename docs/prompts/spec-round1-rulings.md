The owner's rulings on round 1 (2026-11-24):
1. Keep 0004, 0007 and 0008. The owner is fine with them being public; the MIT grant (P-39) covers them. My earlier wording "nothing from the closed F-Emulator" was too strict; the rule is that the F-Emulator app stays closed. Record the grant per patch in NOTICE and PROVENANCE.
2. 0012 stays as our own code; note its origin in PROVENANCE.
3. The three transcripts stay as they are, with no redaction and no history rewrite.
4. Change the commit check so it no longer requires the Claude-Session link (keep Co-Authored-By), stop adding the links, and remove them from files at HEAD.
5. Fix NOTICE, the M0c.md path, and the audit failing on main.

Then round 1's PR. Later, not now: the owner may offer the emulator fixes (0004, 0007, 0008 and our own where useful) to fm1-emu as a pull request, so keep each patch self-contained and documented. Nothing goes to fm1-emu without the owner's go-ahead.

1. Keep 0004, 0007 and 0008. They're fixes to fm1-emu that were made for F-Emulator's copy of it, not app code, and the owner is fine with them being public. The MIT grant (P-39) covers them.
