The owner's rulings on the audit (2026-11-24):
- (a), with changes. Run the random-bytes experiment on patches.c now. If it confirms that number tables are misread, change the audit so data-only tables are compared by value in the text check.
- Hold the auditor session until after the clean-up round, since hw_audio.c is mostly bring-up code that will move or go. Re-run the audit then, and the owner starts an auditor session for whatever is still flagged.
- Don't hold #253 for the audit: it already fails on main. Merge #253 when its other checks are green, after #250 and #251. The audit must pass before the release.
- This covers #252, #250, #251 and #253 only; if any fails on a real test, don't merge and tell me.
