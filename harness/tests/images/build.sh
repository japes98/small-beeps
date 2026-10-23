#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Builds the harness's own test images with the pinned toolchain container
# (tools/build.sh image) and writes SHA256SUMS.
#
#   harness/tests/images/build.sh            build into this folder
#   harness/tests/images/build.sh --check    build into a temporary folder
#                                            and compare with the committed
#                                            images (C-HARNESS-IMAGES)
#   harness/tests/images/build.sh inside OUT (runs inside the container)
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
IMAGES="heartbeat halt wild hang console lcd leds keys pot midi audio flashrw spi1irq"

inside() {
    out=$1
    cd "$HERE"
    flags="-target pi32v2 -std=c11 -ffreestanding -nostdlib -Os -Wall -Wextra -Werror"
    clang -target pi32v2 -c start.S -o "$out/start.o"
    for n in $IMAGES; do
        # shellcheck disable=SC2086
        clang $flags -c "$n.c" -o "$out/$n.o"
        ld -nostdlib -T image.ld -o "$out/$n.elf" "$out/start.o" "$out/$n.o"
        objcopy -O binary -j .text "$out/$n.elf" "$out/$n.bin"
        rm "$out/$n.o" "$out/$n.elf"
    done
    rm "$out/start.o"
    (cd "$out" && for n in $IMAGES; do sha256sum "$n.bin"; done > SHA256SUMS)
}

build() {
    out=$1
    sh "$ROOT/tools/build.sh" image >/dev/null
    tag=$(sh "$ROOT/tools/build.sh" image-tag)
    docker run --rm --platform linux/amd64 --network none --user "$(id -u):$(id -g)" \
        -v "$ROOT:/src:ro" -v "$out:/out" "$tag" sh /src/harness/tests/images/build.sh inside /out
}

case "${1:-}" in
    inside) inside "$2" ;;
    --check)
        tmp=$(mktemp -d)
        trap 'rm -rf "$tmp"' EXIT
        build "$tmp"
        if diff "$tmp/SHA256SUMS" "$HERE/SHA256SUMS" && (cd "$HERE" && sha256sum -c --quiet SHA256SUMS 2>/dev/null || shasum -a 256 -c --quiet SHA256SUMS); then
            echo "test images: rebuilt images match the committed ones"
        else
            echo "test images: FAIL, the committed images differ from a rebuild" >&2
            exit 1
        fi ;;
    "")
        tmp=$(mktemp -d)
        trap 'rm -rf "$tmp"' EXIT
        build "$tmp"
        cp "$tmp"/*.bin "$tmp/SHA256SUMS" "$HERE/"
        cat "$HERE/SHA256SUMS" ;;
    *) sed -n '5,13p' "$0" >&2; exit 2 ;;
esac
