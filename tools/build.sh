#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Builds everything inside the pinned build container (tools/Dockerfile).
#
#   tools/build.sh image                      build the container image
#   tools/build.sh image-tag                  print its tag
#   tools/build.sh build --out DIR [--src-mount PATH] [--define NAME]...
#                        [--demo plaits]
#                                             build in a fresh container,
#                                             outputs and SHA256SUMS in DIR;
#                                             --define adds -DNAME (test
#                                             builds only, tools/perf.py);
#                                             --demo builds a demo's own
#                                             image instead (M4b: the
#                                             Plaits load test), never the
#                                             firmware's
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
    out="" src_mount=/mnt/small-beeps-src defines="" demo=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --out) out=$2; shift 2 ;;
            --src-mount) src_mount=$2; shift 2 ;;
            --define)
                case "$2" in
                    ''|*[!A-Z0-9_]*) echo "build: --define takes a NAME of A-Z, 0-9 and _" >&2; exit 2 ;;
                esac
                defines="$defines $2"; shift 2 ;;
            --demo)
                case "$2" in
                    plaits) demo=$2 ;;
                    *) echo "build: --demo takes plaits" >&2; exit 2 ;;
                esac
                shift 2 ;;
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
        --user "$(id -u):$(id -g)" -e SB_DEFINES="$defines" -e SB_DEMO="$demo" \
        -v "$ROOT:$src_mount:ro" -v "$out:/out" -w "$src_mount" \
        "$tag" sh "$src_mount/tools/build.sh" inside "$src_mount" /out
    cat "$out/SHA256SUMS"
}

# The image's size in bytes, from the symbols firmware/app.ld defines:
# code (code and constants, in the image), data (initialised data: in the
# image and copied to RAM), bss (zeroed RAM, the beacon included), image
# (the raw image's length), stack (reserved at the top of RAM, both
# stacks) and irq_stack (the lower part of it: the interrupt stack).
write_size() {
    sym() { nm "$1" | awk -v s="$2" '$3 == s { print $1 }'; }
    hex() { printf '%d' "0x$1"; }
    origin=$(hex 02000000)
    data_load=$(hex "$(sym "$1" __data_load)")
    data=$(( $(hex "$(sym "$1" __data_end)") - $(hex "$(sym "$1" __data_start)") ))
    bss=$(( $(hex "$(sym "$1" __bss_end)") - $(hex "$(sym "$1" __bss_start)") ))
    stack=$(( $(hex "$(sym "$1" __stack_top)") - $(hex "$(sym "$1" __stack_limit)") ))
    irq=$(( $(hex "$(sym "$1" __irq_stack_top)") - $(hex "$(sym "$1" __stack_limit)") ))
    printf 'code %d\ndata %d\nbss %d\nimage %d\nstack %d\nirq_stack %d\n' \
        $((data_load - origin)) "$data" "$bss" $((data_load - origin + data)) "$stack" "$irq"
}

# The Plaits demo's own sources and the vendored Plaits (M4b,
# docs/DESIGN-NOTES.md): our C glue and runtime with the firmware's flags;
# our C++ with the same warnings, as errors (Plaits' headers are system
# headers to it: their warnings are not ours to fix); the vendored files
# unmodified at upstream's -O2, with warnings off. All the C++ is built in
# upstream's portable configuration (-DTEST), with our standard headers
# and plaits_pre.h in place of a C library's. Objects are named after their
# paths, since vendored names repeat.
build_demo_plaits() {
    d=firmware/demos/plaits
    CXX="clang -target pi32v2 -x c++ -std=c++11 -ffreestanding -nostdlib -nostdinc -fno-exceptions
         -fno-rtti -fno-threadsafe-statics -fno-common -g -fdebug-prefix-map=$src=.
         -I$d/include -isystem vendor/plaits/eurorack -isystem vendor/plaits -I$d -Ifirmware/src
         -DTEST -include $d/include/plaits_pre.h"
    for d2 in ${SB_DEFINES:-}; do CXX="$CXX -D$d2"; done
    # PLAITS_HWFLOAT: the toolchain's hardware single-precision float
    # instructions (its fprev1 feature) instead of our soft-float, for the
    # C++ only: a measurement of what they would save, never the demo's
    # default, since whether the chip has them is open (SR-5).
    case " ${SB_DEFINES:-} " in
        *" PLAITS_HWFLOAT "*) CXX="$CXX -Xclang -target-feature -Xclang +fprev1" ;;
    esac
    defs=""
    for d2 in ${SB_DEFINES:-}; do defs="$defs -D$d2"; done
    for s in $(find "$d" -name '*.c' -o -name '*.S' | LC_ALL=C sort); do
        o="$obj/$(echo "$s" | tr / _ | sed 's/\.[cS]$/.o/')"
        case "$s" in
            # shellcheck disable=SC2086
            *.S) set -x; clang $ASFLAGS $defs -c "$s" -o "$o"; set +x ;;
            # shellcheck disable=SC2086,SC2046
            *) set -x; clang $(echo "$CFLAGS" | sed 's/ -mcpu=r3 -mfprev1//') -c "$s" -o "$o"; set +x ;;
        esac
        objs="$objs $o"
    done
    for s in $(find "$d" -name '*.cc' | LC_ALL=C sort); do
        o="$obj/$(echo "$s" | tr / _ | sed 's/\.cc$/.o/')"
        # shellcheck disable=SC2086
        set -x; $CXX -Os -Wall -Wextra -Werror -c "$s" -o "$o"; set +x
        objs="$objs $o"
    done
    for s in $(find vendor/plaits -name '*.cc' | LC_ALL=C sort); do
        o="$obj/$(echo "$s" | tr / _ | sed 's/\.cc$/.o/')"
        # shellcheck disable=SC2086
        $CXX -O2 -w -c "$s" -o "$o"
        objs="$objs $o"
    done
    echo "built $(find vendor/plaits -name '*.cc' | wc -l) vendored Plaits files"
}

cmd_inside() {
    src=$1 out=$2
    cd "$src"
    # The chip's CPU model and its single-precision float instructions, as
    # the SDK builds for it (HW-62, since M5). The Plaits demo's own C is
    # built without them, as before (build_demo_plaits): its soft-float
    # test must exercise the soft-float routines, and `-mcpu=r3` on its
    # own already makes the compiler use the instructions.
    CPU="-mcpu=r3 -mfprev1"
    # -nostdinc: no C library headers either; the SDK's register headers
    # are the only outside includes. -fno-common puts zeroed data in .bss.
    CFLAGS="-target pi32v2 $CPU -std=c11 -ffreestanding -nostdlib -nostdinc -Os -g
            -fno-common -Wall -Wextra -Werror -fdebug-prefix-map=$src=.
            -Ifirmware/src -Ivendor/jieli-sdk/include_lib/driver/cpu/wl82/asm"
    for d in ${SB_DEFINES:-}; do CFLAGS="$CFLAGS -D$d"; done
    # Assembly is built without -g, which would record the source path.
    ASFLAGS="-target pi32v2 $CPU -nostdinc -Werror"
    clang --version | head -1
    ld --version | head -1
    echo "SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH"
    # Objects are intermediate: kept out of the outputs.
    obj=/tmp/small-beeps-obj
    rm -rf "$obj" && mkdir -p "$obj"
    objs=""
    if [ -n "${SB_DEMO:-}" ]; then
        CFLAGS="$CFLAGS -DSB_DEMO_PLAITS -Ifirmware/demos/plaits"
    fi
    for s in $(find firmware/src -name '*.c' -o -name '*.S' | LC_ALL=C sort); do
        o="$obj/$(basename "$s" | sed 's/\.[cS]$/.o/')"
        case "$s" in
            *.S) set -x; clang $ASFLAGS -c "$s" -o "$o"; set +x ;;
            # shellcheck disable=SC2086
            *) set -x; clang $CFLAGS -c "$s" -o "$o"; set +x ;;
        esac
        objs="$objs $o"
    done
    if [ -n "${SB_DEMO:-}" ]; then
        build_demo_plaits
    fi
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
