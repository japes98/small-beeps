You are the clean session for small-beeps (~/Development/<top>/clean). Same rules as always: the clean room, your role file, no spec-side folders, no stock or GPL firmware, the privacy rule for the public repo. Save this prompt unedited as docs/prompts/clean-pin-flags.md, archive the previous session's transcript, write this session's EXPOSURE entry.

0. Answers to your store-region questions (record them where the decisions live: DESIGN-NOTES / the guide / R-STORE-12):
   1. Yes. Moving on until there is room (at most once round) and 128 record parts are accepted. Every save the old code accepted writes the same bytes, and the power-cut runs cover the new path. Say plainly in STORE-FORMAT that only previously refused saves behave differently.
   2. Keep every extra refusal. The VM region stays refused: it holds the stock firmware's settings and is where an update stages its loader, so a store there could be lost or break an update. The refusal message should say why.
   3. Good. SR-11 waits for spec. Until it is answered, the guide's wording stands (survives fwtest and the app, not yet a real unit's update).
   4. Good.
   5. Fine: the golden is unchanged and the cause was a block edge. Add a note in the fmgold script saying key events must sit well clear of audio block edges, and why.
   6. 18 ms once at init is acceptable. Don't optimise it; record the figures in the guide's sizing section.

1. Pin fwtest 0.10.0. small-beeps #175 has merged and published it. Pin it the same way 0.7.0 to 0.9.0 were pinned: one pull request on the clean side, the digest from the published image, C-HARNESS-IMAGE-REPRO and C-HARNESS-ISA green. Run the firmware suite on it. A case may now end as trap (exit code 6); if any of ours does, that's a finding, report it.

2. Refuse per-folder CPU and feature flags (amends BR-11). A firmware folder may still set its own -m flags for anything else, but its objects must be compiled for the SDK's CPU and float features: target CPU r3, and float features either +fprev1 or none. Use BR-13's own reading (note_cpu, clang -### for each compile line) rather than matching flag spellings, so -mcpu, -mfprev2, -msimd, -Xclang -target-feature and anything new are all caught the same way. The Plaits demo's +fprev1 stays allowed because it equals the SDK's set. Refuse at build time with a message that names the folder, the flag's effect (e.g. "double-precision float, which the SDK's flags exclude and fwtest doesn't run") and the fix. Add a seams test per refusal kind (another CPU, double precision, SIMD) and one that the allowed set passes. Update BUILDING-ON-SMALL-BEEPS.md (BR-11's section) and the requirements.

Separate pull requests for 1 and 2, each with CI green. Give me the merge order (after #173). Report briefly, then you're done.
