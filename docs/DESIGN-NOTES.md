<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Design notes

From M0d on, each firmware design choice is explained here: what was chosen,
the `HARDWARE-SPEC.md` facts (by their IDs) and first principles it follows
from, and the alternatives considered. A clean-room claim is stronger when
every choice can be traced to the spec and to reasoning, not to someone
else's code.

Format for each entry:

```
## <date> <milestone>: <the choice>
- Facts: HARDWARE-SPEC IDs (and PROVENANCE IDs) it relies on
- Reasoning: why, from first principles
- Alternatives: what else was considered, and why not
```

## Entries

### 2026-10-21 M0a: build flags only (no firmware yet)
- Facts: none from the hardware spec (it doesn't exist yet). PROVENANCE P-1
  (the toolchain).
- Reasoning: freestanding C11 (`-std=c11 -ffreestanding -nostdlib`) means
  the firmware brings everything it runs, so no toolchain or SDK library code
  of unknown licence ends up in our binaries. `-Os` because flash and RAM are
  small. `-g` with `-fdebug-prefix-map` keeps debug info useful without
  embedding absolute paths, so builds are reproducible.
- Alternatives: the toolchain's newlib C library (rejected: unknown terms in
  this distribution, and more than we need).
