#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Builds everything inside the pinned build container (tools/Dockerfile).
#
#   tools/build.sh image                      build the container image
#   tools/build.sh image-tag                  print its tag
#   tools/build.sh build --out DIR [--src-mount PATH]
#                                             build in a fresh container,
#                                             outputs and SHA256SUMS in DIR
#   tools/build.sh inside SRC OUT             (runs inside the container)
#
# Builds are deterministic (R-REPRO-3): fixed SOURCE_DATE_EPOCH (set in the
# image), no network, relative source paths with -fdebug-prefix-map, sorted
# output lists, and a check that no output contains the source mount path.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PLATFORM=linux/amd64

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
    else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

image_tag() {
    echo "small-beeps-build:$(sha256 "$ROOT/tools/Dockerfile" | cut -c1-16)"
}

cmd_image() {
    # No build context: the Dockerfile fetches everything it needs.
    docker build --platform "$PLATFORM" -t "$(image_tag)" - < "$ROOT/tools/Dockerfile"
    docker image inspect --format 'image {{.Id}}' "$(image_tag)"
}

cmd_build() {
    out="" src_mount=/mnt/small-beeps-src
    while [ $# -gt 0 ]; do
        case "$1" in
            --out) out=$2; shift 2 ;;
            --src-mount) src_mount=$2; shift 2 ;;
            *) echo "unknown option $1" >&2; exit 2 ;;
        esac
    done
    [ -n "$out" ] || { echo "build: --out DIR is required" >&2; exit 2; }
    tag=$(image_tag)
    docker image inspect "$tag" >/dev/null 2>&1 || cmd_image
    rm -rf "$out"
    mkdir -p "$out"
    out=$(cd "$out" && pwd)
    docker run --rm --platform "$PLATFORM" --network none \
        --user "$(id -u):$(id -g)" \
        -v "$ROOT:$src_mount:ro" -v "$out:/out" -w "$src_mount" \
        "$tag" sh "$src_mount/tools/build.sh" inside "$src_mount" /out
    cat "$out/SHA256SUMS"
}

cmd_inside() {
    src=$1 out=$2
    cd "$src"
    CFLAGS="-target pi32v2 -std=c11 -ffreestanding -nostdlib -Os -g
            -Wall -Wextra -Werror -fdebug-prefix-map=$src=."
    clang --version | head -1
    ld --version | head -1
    echo "SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH"
    set -x
    # shellcheck disable=SC2086
    clang $CFLAGS -c firmware/src/placeholder.c -o "$out/placeholder.o"
    ld -nostdlib -e placeholder -o "$out/placeholder.elf" "$out/placeholder.o"
    set +x
    # No output may contain the absolute source path.
    for f in "$out"/placeholder.o "$out"/placeholder.elf; do
        if grep -q -F "$src" "$f"; then
            echo "FAIL: $f contains the source path $src" >&2; exit 1
        fi
    done
    (cd "$out" && find . -type f ! -name SHA256SUMS | sed 's|^\./||' \
        | LC_ALL=C sort | xargs sha256sum > SHA256SUMS)
}

case "${1:-}" in
    image) cmd_image ;;
    image-tag) image_tag ;;
    build) shift; cmd_build "$@" ;;
    inside) shift; cmd_inside "$@" ;;
    *) sed -n '5,12p' "$0" >&2; exit 2 ;;
esac
