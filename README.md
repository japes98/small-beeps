Embedded audio experiments. Work in progress.

MIT licensed (see `LICENSE` and `NOTICE`). How changes are made and recorded:
`CONTRIBUTING.md`. What is planned: `docs/PLAN.md`.

## Build

Needs Docker (any host; builds run as `linux/amd64`, Apple Silicon included)
and Python 3.9 or later.

```sh
./tools/build.sh image            # build the pinned build container
./tools/build.sh build --out out/build
cat out/build/SHA256SUMS
```

The container fetches the compiler from its vendor and checks its SHA-256
(`docs/TOOLCHAIN.md`). The compiler is never stored in this repository.

## How to verify our work

Every commit on `main` has a permanent test record on the `records` branch,
at `records/<commit>/`: `report.md` and `report.json` (environment, every
check with its requirement IDs, results, output hashes), the full logs, and
an OpenTimestamps proof.

To rebuild a commit and compare its outputs with its record:

```sh
git clone <this repository> && cd <it>
./tools/reproduce <commit>
```

`tools/reproduce` checks out that commit in a temporary folder, builds its
pinned container, builds the outputs, and compares each output's SHA-256 with
the record. It prints `REPRODUCED` or lists every difference.

To check a record's timestamp, install `opentimestamps-client` and run
`ots verify records/<commit>/SHA256SUMS.ots` (or the later
`SHA256SUMS.upgraded.ots`) in a checkout of the `records` branch.

## Checks

`python3 tools/record.py run --out out/check` runs every check CI runs and
writes a report to `out/check/`.
