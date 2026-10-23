#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Builds the spec-side experiments (README.md) with the pinned toolchain
# container (tools/build.sh image) and writes SHA256SUMS.
#
#   harness/spec-experiments/build.sh            build into this folder
#   harness/spec-experiments/build.sh --check    build into a temporary folder
#                                                and compare with the committed
#                                                images (C-SPEC-EXPERIMENTS)
#   harness/spec-experiments/build.sh inside OUT (runs inside the container)
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
IMAGES="e2-console e3-timers e4-core1 e5-lcd e6-matrix e7-leds e8-adc e9-audio e10-faults e11-undefined e12-badjump e13-timer-ack e14-undefined-inline e15-spi1-irq e16-lcd-frame e17-adc-irq"

inside() {
    out=$1
    cd "$HERE"
    flags="-target pi32v2 -std=c11 -ffreestanding -nostdlib -Os -Wall -Wextra -Werror"
    clang -target pi32v2 -c start.S -o "$out/start.o"
    clang -target pi32v2 -c boot.S -o "$out/boot.o"
    # shellcheck disable=SC2086
    clang $flags -c e1-boot.c -o "$out/e1-boot.o"
    ld -nostdlib -T image.ld -o "$out/e1-boot.elf" "$out/boot.o" "$out/e1-boot.o"
    objcopy -O binary -j .text "$out/e1-boot.elf" "$out/e1-boot.bin"
    for n in $IMAGES; do
        # shellcheck disable=SC2086
        clang $flags -c "$n.c" -o "$out/$n.o"
        ld -nostdlib -T image.ld -o "$out/$n.elf" "$out/start.o" "$out/$n.o"
        objcopy -O binary -j .text "$out/$n.elf" "$out/$n.bin"
    done
    rm -f "$out"/*.o "$out"/*.elf
    (cd "$out" && for n in e1-boot $IMAGES; do sha256sum "$n.bin"; done > SHA256SUMS)
}

build() {
    out=$1
    sh "$ROOT/tools/build.sh" image >/dev/null
    tag=$(sh "$ROOT/tools/build.sh" image-tag)
    docker run --rm --platform linux/amd64 --network none --user "$(id -u):$(id -g)" \
        -v "$ROOT:/src:ro" -v "$out:/out" "$tag" sh /src/harness/spec-experiments/build.sh inside /out
}

case "${1:-}" in
    inside) inside "$2" ;;
    --check)
        tmp=$(mktemp -d)
        trap 'rm -rf "$tmp"' EXIT
        build "$tmp"
        if diff "$tmp/SHA256SUMS" "$HERE/images/SHA256SUMS" && (cd "$HERE/images" && sha256sum -c --quiet SHA256SUMS 2>/dev/null || shasum -a 256 -c --quiet SHA256SUMS); then
            echo "spec experiments: rebuilt images match the committed ones"
        else
            echo "spec experiments: FAIL, the committed images differ from a rebuild" >&2
            exit 1
        fi ;;
    "")
        tmp=$(mktemp -d)
        trap 'rm -rf "$tmp"' EXIT
        build "$tmp"
        mkdir -p "$HERE/images"
        cp "$tmp"/*.bin "$tmp/SHA256SUMS" "$HERE/images/"
        cat "$HERE/images/SHA256SUMS" ;;
    *) sed -n '5,13p' "$0" >&2; exit 2 ;;
esac
