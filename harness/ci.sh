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
#   harness/ci.sh repro              build the runtime image twice from
#                                    scratch, the second time at another
#                                    time and from a context whose file
#                                    times and owners differ: the same
#                                    image ID, or a failure
#   harness/ci.sh suite OUT MOUNT    run tests/harness.suite in a fresh
#                                    container, harness/tests mounted
#                                    read-only at MOUNT; outputs in OUT
#   harness/ci.sh scope              the harness never uses the vendored
#                                    crates' stock-boot path or other boards
#                                    (packages only through their reader)
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
# matter: the build's outputs don't depend on them, and the Dockerfile sets
# the image's own files' owners and times).
tracked_context() {
    cd "$ROOT"
    context_files | LC_ALL=C sort > "$tmp/files"
    tar --format=ustar -c -f - -T "$tmp/files" 2>/dev/null \
        || tar -c -f - $(cat "$tmp/files")
}
context() { tracked_context; }

# The image's one time, the Dockerfile's SOURCE_DATE_EPOCH. Passed as a build
# argument, BuildKit gives it to the image's config and history, and the
# Dockerfile's files stage gives it to every file it adds, so neither the
# build's time nor the checkout's file times reach the image. No provenance
# attestation: it records the build's own times. (Before this, two builds of
# the same source gave the same files under other times, so another digest:
# session spec-1027.)
epoch() {
    sed -n 's/^.*SOURCE_DATE_EPOCH=\([0-9][0-9]*\).*$/\1/p' "$ROOT/harness/Dockerfile" | head -n 1
}

build() {
    build_target=$1 build_tag=$2
    shift 2
    e=$(epoch)
    [ -n "$e" ] || { echo "no SOURCE_DATE_EPOCH in harness/Dockerfile" >&2; exit 1; }
    context | docker build --platform "$PLATFORM" --target "$build_target" --provenance=false \
        --build-arg SOURCE_DATE_EPOCH="$e" -t "$build_tag" "$@" -f harness/Dockerfile -
}

# The context again, as the file $tmp/shifted.tar: every file an hour newer
# and owned by another user.
shifted_context() {
    tracked_context > "$tmp/context.tar"
    "$(sh "$ROOT/tools/find-python.sh")" -I -c '
import sys, tarfile
src = tarfile.open(sys.argv[1], mode="r:")
dst = tarfile.open(sys.argv[2], mode="w", format=tarfile.USTAR_FORMAT)
for m in src:
    data = src.extractfile(m) if m.isfile() else None
    m.mtime += 3600
    m.uid, m.gid, m.uname, m.gname = 4321, 4321, "", ""
    dst.addfile(m, data)
dst.close()' "$tmp/context.tar" "$tmp/shifted.tar"
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
    repro)
        t=$(tag)
        build runtime "$t-repro-a" --no-cache
        a=$(docker image inspect --format '{{.Id}}' "$t-repro-a")
        sleep 2
        shifted_context
        context() { cat "$tmp/shifted.tar"; }
        build runtime "$t-repro-b" --no-cache
        b=$(docker image inspect --format '{{.Id}}' "$t-repro-b")
        docker image rm "$t-repro-a" "$t-repro-b" >/dev/null 2>&1 || true
        echo "image A $a"
        echo "image B $b"
        if [ "$a" != "$b" ]; then
            echo "repro: FAIL, the same source gave two images" >&2
            exit 1
        fi
        echo "repro: PASS (the same image ID from both builds)" ;;
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
        # since A1 a package goes through the reader (fwsc::unpack) and the boot
        # block (write_boot_info) only, never the stock path's extras
        if grep -c -E 'stock_from_package|stock_boot|usr_fill_defaults|usr_load_syx|usr_offset|smk|Smk37|flaky' "$ROOT"/harness/src/*.rs | grep -v ':0$'; then
            echo "scope: FAIL, the harness names the stock-boot or other-board paths" >&2
            exit 1
        fi
        if grep -o -h -E 'fwsc::[a-z_]+' "$ROOT"/harness/src/*.rs | sort -u | grep -v -x -E 'fwsc::unpack'; then
            echo "scope: FAIL, the harness uses more of the package module than its reader" >&2
            exit 1
        fi
        echo "scope: PASS (harness/src uses none of them)" ;;
    *) sed -n '5,23p' "$0" >&2; exit 2 ;;
esac
