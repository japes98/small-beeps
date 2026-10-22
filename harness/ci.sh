#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# The harness's CI steps (spec side). tools/record.py runs them as the
# C-HARNESS-* checks, and skips them where harness/ isn't on disk.
#
#   harness/ci.sh tag                print the local image tag
#   harness/ci.sh image              build the runtime image (and print the
#                                    fwtest binary's SHA-256)
#   harness/ci.sh test               build the test stage: cargo test
#   harness/ci.sh suite OUT MOUNT    run tests/harness.suite in a fresh
#                                    container, harness/tests mounted
#                                    read-only at MOUNT; outputs in OUT
#   harness/ci.sh scope              the harness never uses the vendored
#                                    crates' update-package or stock-boot paths
#   harness/ci.sh context            write the build context (a tar) to stdout
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PLATFORM=linux/amd64

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"
    else shasum -a 256 "$@"; fi
}

# The image tag: a hash of everything that goes into the build context.
tag() {
    h=$(cd "$ROOT" && context_files | LC_ALL=C sort | while read -r f; do sha256 "$f"; done | sha256 | cut -c1-16)
    echo "small-beeps-fwtest:$h"
}

# (The spec-side experiments are not part of fwtest: harness/spec-experiments/
# runs them against it.)
context_files() {
    git -C "$ROOT" ls-files vendor/emulator harness LICENSE NOTICE | grep -v '^harness/spec-experiments/'
}

# A tar of exactly the tracked context files (its owners and times don't
# matter: the build's outputs don't depend on them).
context() {
    cd "$ROOT"
    context_files | LC_ALL=C sort > "$tmp/files"
    tar --format=ustar -c -f - -T "$tmp/files" 2>/dev/null \
        || tar -c -f - $(cat "$tmp/files")
}

build() {
    target=$1 t=$2
    context | docker build --platform "$PLATFORM" --target "$target" -t "$t" -f harness/Dockerfile -
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

case "${1:-}" in
    tag) tag ;;
    context) context ;;
    image)
        t=$(tag)
        build runtime "$t"
        docker image inspect --format 'image {{.Id}}' "$t"
        docker run --rm --platform "$PLATFORM" --network none --entrypoint sha256sum "$t" /usr/local/bin/fwtest
        docker run --rm --platform "$PLATFORM" --network none "$t" version ;;
    test)
        build test "$(tag)-test" ;;
    suite)
        out=$2 mount=$3
        t=$(tag)
        docker image inspect "$t" >/dev/null 2>&1 || build runtime "$t"
        rm -rf "$out"
        mkdir -p "$out"
        out=$(cd "$out" && pwd)
        docker run --rm --platform "$PLATFORM" --network none --user "$(id -u):$(id -g)" \
            -v "$ROOT/harness/tests:$mount:ro" -v "$out:/out" "$t" \
            suite "$mount/harness.suite" --out /out/suite ;;
    scope)
        # file names and counts only: CI logs must not quote harness or emulator source
        if grep -c -E 'fwsc|stock_from_package|stock_boot|write_boot_info|smk|Smk37|flaky' "$ROOT"/harness/src/*.rs | grep -v ':0$'; then
            echo "scope: FAIL, the harness names the update-package, stock-boot or other-board paths" >&2
            exit 1
        fi
        echo "scope: PASS (harness/src uses none of them)" ;;
    *) sed -n '5,18p' "$0" >&2; exit 2 ;;
esac
