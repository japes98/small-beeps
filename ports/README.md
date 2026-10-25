<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Porter reports

A porter (CONTRIBUTING.md, "Roles") ports a GPL FM-1 engine onto our base
in the separate port repository `small-beeps-ports`. What comes back to
this repository is only what is here: one report per port and session,
`ports/<date>-<short name>.md`, written by the porter. The firmware side
may read these (log what it uses in PROVENANCE.md, as for any source); a
report is the only way anything of a port reaches it.

A report holds:

- **Which port:** the port repository's commit, and the engine's name and
  licence as its repository states them.
- **Measurements on our base:** what fwtest showed for the port built on
  our base at a named commit of this repository: cycles per audio block
  and per voice (`ipb.csv`), memory used, voices held, any underruns or
  faults, with the fwtest version and the commands that reproduce them.
- **API requests:** what the port needed from the base and didn't find,
  each as a need in general terms ("a call each audio block with the
  block's length", "a way to keep 12 KiB in RAM across patch changes"),
  never how the engine does it.

A report never holds code, pseudo-code, code structure, names of the
engine's functions, variables or files, comments, or text copied from the
engine or its port, and never says how the engine computes anything. The
firmware side answers an API request with its own design, as it would a
spec request.
