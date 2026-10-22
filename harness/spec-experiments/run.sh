#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# C-SPEC-EXPERIMENTS: rebuilds the spec-side experiments and checks they
# match the committed images, then runs experiments.suite against this
# checkout's fwtest (harness/ci.sh's image, built if missing) in a fresh
# container with no network. Every case must have its expected outcome and
# match its golden files: the results docs/HARDWARE-SPEC.md cites.
#
#   harness/spec-experiments/run.sh OUT
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
out=${1:?usage: run.sh OUT}

sh "$HERE/build.sh" --check
t=$(sh "$ROOT/harness/ci.sh" tag)
docker image inspect "$t" >/dev/null 2>&1 || sh "$ROOT/harness/ci.sh" image >/dev/null
rm -rf "$out"
mkdir -p "$out"
out=$(cd "$out" && pwd)
docker run --rm --platform linux/amd64 --network none --user "$(id -u):$(id -g)" \
    -v "$HERE:/experiments:ro" -v "$out:/out" "$t" \
    suite /experiments/experiments.suite --out /out/suite
echo "spec experiments: every case matched its golden files"
