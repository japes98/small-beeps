From the owner, to cut the time per round:
1. Every clean prompt from now on says: while iterating, run only the seams
   cases the change touches; open the PR when those pass and the .fwsc is
   packed; CI runs the full suite. No full local run before the PR. The
   owner flashes once the file has been checked, without waiting for CI.
   Also ask clean to say how long the build took and where the time went.
2. Rulings ahead, not after. With each prompt, list the likely outcomes of
   the run and the next step each would lead to, for the owner to rule on
   before the run. Then put the unit results and the next prompt in one PR,
   with no separate rulings PR. Start now: for audio7 (L1, L2), set out what
   comes next if L1 runs (routing data 3 to the pins, the amplifier enable,
   headphone sensing), if only L2 runs, and if neither runs.
3. Local builds: today each seams case builds in a linux/amd64 container,
   which runs under emulation on the owner's Mac (a full run about 30 min).
   Propose how clean can build natively (arm64) while iterating, keeping the
   pinned amd64 build for CI, the records and releases. Say what the
   reproducibility requirements allow, as a requirement change for the
   owner to approve.
4. After audio7: propose a table-driven probe as a spec request for clean.
   That's a probe engine, built once, where each unit test is a table of steps
   (register, the bits allowed to change, the value, what to read back and
   log, the checks and the undo), within the owner's rulings. A new test
   is then a table edit plus one seams case, not new firmware code.
