>>> FOR THE CLEAN SESSION ONLY (check .claude/small-beeps-role says "clean"; if not, stop and tell the owner). <<< Fix needed: C-SEAMS fails on #243's own CI run and on #244, which contains it, in seams case report1.

From the CI log:
- `FAIL report1: report1: the build's identity isn't in app.bin`
- `FAIL report1: report1 first: a record of an unknown layout or another build: [(9, 980, '0.12.1-hw3w'), …]`

audio13 moved the identity to hw3x, and report1 still expects or finds hw3w. Every other case passed, audio13 and audio12 included.

The owner closed #243 unmerged; #244 (spec/audio13-rulings) carries it and merges only when CI is green. Please:
1. Fix report1 on `hw/audio13`, as a new commit with no force-push.
2. Run seams case report1, and the cases the fix touches.
3. Run check-emulator-terms with COMMIT_RANGE=origin/main..HEAD.
4. Push, and reply with the commit's hash. Don't open a new PR.

The spec side will merge it into #244. audio14 (the ARP save fix, plus U3's device in fwtest only) follows once #244 is on main.
