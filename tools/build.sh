#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Builds everything inside the pinned build container (tools/Dockerfile).
#
#   tools/build.sh image                      build the container image
#   tools/build.sh image-tag                  print its tag
#   tools/build.sh build --out DIR [--src-mount PATH] [--define NAME]...
#                                             build in a fresh container,
#                                             outputs and SHA256SUMS in DIR;
#                                             --define adds -DNAME (test
#                                             builds only, tools/perf.py)
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
    out="" src_mount=/mnt/small-beeps-src defines=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --out) out=$2; shift 2 ;;
            --src-mount) src_mount=$2; shift 2 ;;
            --define)
                case "$2" in
                    ''|*[!A-Z0-9_]*) echo "build: --define takes a NAME of A-Z, 0-9 and _" >&2; exit 2 ;;
                esac
                defines="$defines $2"; shift 2 ;;
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
        --user "$(id -u):$(id -g)" -e SB_DEFINES="$defines" \
        -v "$ROOT:$src_mount:ro" -v "$out:/out" -w "$src_mount" \
        "$tag" sh "$src_mount/tools/build.sh" inside "$src_mount" /out
    cat "$out/SHA256SUMS"
}

# The image's size in bytes, from the symbols firmware/app.ld defines:
# code (code and constants, in the image), data (initialised data: in the
# image and copied to RAM), bss (zeroed RAM, the beacon included), image
# (the raw image's length) and stack (reserved at the top of RAM).
write_size() {
    sym() { nm "$1" | awk -v s="$2" '$3 == s { print $1 }'; }
    hex() { printf '%d' "0x$1"; }
    origin=$(hex 02000000)
    data_load=$(hex "$(sym "$1" __data_load)")
    data=$(( $(hex "$(sym "$1" __data_end)") - $(hex "$(sym "$1" __data_start)") ))
    bss=$(( $(hex "$(sym "$1" __bss_end)") - $(hex "$(sym "$1" __bss_start)") ))
    stack=$(( $(hex "$(sym "$1" __stack_top)") - $(hex "$(sym "$1" __stack_limit)") ))
    printf 'code %d\ndata %d\nbss %d\nimage %d\nstack %d\n' \
        $((data_load - origin)) "$data" "$bss" $((data_load - origin + data)) "$stack"
}

cmd_inside() {
    src=$1 out=$2
    cd "$src"
    # -nostdinc: no C library headers either; the SDK's register headers
    # are the only outside includes. -fno-common puts zeroed data in .bss.
    CFLAGS="-target pi32v2 -std=c11 -ffreestanding -nostdlib -nostdinc -Os -g
            -fno-common -Wall -Wextra -Werror -fdebug-prefix-map=$src=.
            -Ifirmware/src -Ivendor/jieli-sdk/include_lib/driver/cpu/wl82/asm"
    for d in ${SB_DEFINES:-}; do CFLAGS="$CFLAGS -D$d"; done
    # Assembly is built without -g, which would record the source path.
    ASFLAGS="-target pi32v2 -nostdinc -Werror"
    clang --version | head -1
    ld --version | head -1
    echo "SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH"
    # Objects are intermediate: kept out of the outputs.
    obj=/tmp/small-beeps-obj
    rm -rf "$obj" && mkdir -p "$obj"
    objs=""
    for s in $(find firmware/src -name '*.c' -o -name '*.S' | LC_ALL=C sort); do
        o="$obj/$(basename "$s" | sed 's/\.[cS]$/.o/')"
        case "$s" in
            *.S) set -x; clang $ASFLAGS -c "$s" -o "$o"; set +x ;;
            # shellcheck disable=SC2086
            *) set -x; clang $CFLAGS -c "$s" -o "$o"; set +x ;;
        esac
        objs="$objs $o"
    done
    set -x
    # shellcheck disable=SC2086
    ld -nostdlib --no-undefined --orphan-handling=error -T firmware/app.ld \
        -o "$out/app.elf" $objs
    # The raw image is the code, then the initial data, which app.ld loads
    # right after it. This objcopy takes one section at a time, and ld's
    # own binary output gets data addresses wrong, so the two are joined.
    objcopy -O binary -j .text "$out/app.elf" "$obj/text.bin"
    objcopy -O binary -j .data "$out/app.elf" "$obj/data.bin"
    cat "$obj/text.bin" "$obj/data.bin" > "$out/app.bin"
    rm "$obj/text.bin" "$obj/data.bin"
    set +x
    write_size "$out/app.elf" > "$out/app.size"
    cat "$out/app.size"
    image=$(awk '$1 == "image" { print $2 }' "$out/app.size")
    if [ "$(wc -c < "$out/app.bin")" -ne "$image" ]; then
        echo "FAIL: app.bin is not the $image bytes app.ld lays out" >&2; exit 1
    fi
    # No output may contain the absolute source path.
    for f in $(find "$out" -type f | LC_ALL=C sort); do
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
