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
IMAGES="heartbeat halt wild hang console lcd leds keys pot midi midiout audio spi1irq"
# C with code in RAM (image-ram.ld, flash.h)
RAM_IMAGES="flashrw flashcall flashload flashirq flashkeep"
# built with the firmware's CPU flags (tools/build.sh, CPU), as the firmware is
FW_IMAGES="blockc rotc"
# assembly, linked after start.S like the C images
ASM_IMAGES="blockmv pairhead rotr pushpop ramcode pairwaw"
# assembly with its own _start, linked alone
RAW_IMAGES="sr7"
ALL="$IMAGES $RAM_IMAGES $FW_IMAGES $ASM_IMAGES $RAW_IMAGES"

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
    for n in $RAM_IMAGES; do
        # shellcheck disable=SC2086
        clang $flags -c "$n.c" -o "$out/$n.o"
        ld -nostdlib -T image-ram.ld -o "$out/$n.elf" "$out/start.o" "$out/$n.o"
        # this objcopy takes one -j: the RAM code goes right after .text,
        # where image-ram.ld puts its load address
        objcopy -O binary -j .text "$out/$n.elf" "$out/$n.text"
        objcopy -O binary -j .ramtext "$out/$n.elf" "$out/$n.ram"
        objdump -d "$out/$n.elf" > "$out/$n.dis"
        cat "$out/$n.text" "$out/$n.ram" > "$out/$n.bin"
        rm "$out/$n.text" "$out/$n.ram"
        rm "$out/$n.o" "$out/$n.elf"
    done
    for n in $FW_IMAGES; do
        # shellcheck disable=SC2086
        clang $flags -mcpu=r3 -mfprev1 -c "$n.c" -o "$out/$n.o"
        ld -nostdlib -T image.ld -o "$out/$n.elf" "$out/start.o" "$out/$n.o"
        objcopy -O binary -j .text "$out/$n.elf" "$out/$n.bin"
        objdump -d "$out/$n.elf" > "$out/$n.dis"
        rm "$out/$n.o" "$out/$n.elf"
    done
    # blockc exists for the two forms below a base the compiler emits (SR-7)
    if ! grep -q '} = \[-r[0-9]*\]' "$out/blockc.dis" || ! grep -q '\[-r[0-9]*\] = {' "$out/blockc.dis"; then
        echo "blockc: the compiler no longer emits {..} = [-rN] and [-rN] = {..}" >&2
        exit 1
    fi
    # rotc exists for the rotate by a register the compiler emits
    if ! grep -q 'r[0-9]* = r[0-9]* <> r[0-9]*$' "$out/rotc.dis"; then
        echo "rotc: the compiler no longer emits rD = rS <> rT" >&2
        exit 1
    fi
    # pairwaw.S stands for a pair whose halves write one register, which the
    # compiler emits in flashkeep.c (a head, then a load into the same register)
    if ! awk -F '\t' '$NF ~ /^r[0-9]+ = .*# *$/ { h = $NF; sub(/ .*/, "", h); next }
              h != "" { t = $NF; sub(/^ */, "", t); if (index(t, h " = [") == 1) found = 1; h = "" }
              END { exit !found }' "$out/flashkeep.dis"; then
        echo "flashkeep: the compiler no longer pairs a head and a load into one register" >&2
        exit 1
    fi
    for n in $FW_IMAGES $RAM_IMAGES; do rm "$out/$n.dis"; done
    for n in $ASM_IMAGES; do
        clang -target pi32v2 -mcpu=r3 -c "$n.S" -o "$out/$n.o"
        ld -nostdlib -T image.ld -o "$out/$n.elf" "$out/start.o" "$out/$n.o"
        objcopy -O binary -j .text "$out/$n.elf" "$out/$n.bin"
        rm "$out/$n.o" "$out/$n.elf"
    done
    for n in $RAW_IMAGES; do
        clang -target pi32v2 -mcpu=r3 -c "$n.S" -o "$out/$n.o"
        ld -nostdlib -T image.ld -o "$out/$n.elf" "$out/$n.o"
        objcopy -O binary -j .text "$out/$n.elf" "$out/$n.bin"
        rm "$out/$n.o" "$out/$n.elf"
    done
    rm "$out/start.o"
    (cd "$out" && for n in $ALL; do sha256sum "$n.bin"; done > SHA256SUMS)
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
