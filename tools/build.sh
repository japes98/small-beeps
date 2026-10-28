#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Builds everything inside the pinned build container (tools/Dockerfile).
#
#   tools/build.sh image                      build the container image
#   tools/build.sh image-tag                  print its tag
#   tools/build.sh build --out DIR [--src-mount PATH] [--define NAME]...
#                        [--demo plaits] [--src DIR]... [--leave-out FILE]...
#                                             build in a fresh container,
#                                             outputs and SHA256SUMS in DIR;
#                                             --define adds -DNAME (test
#                                             builds, tools/perf.py; and a
#                                             firmware built on the base,
#                                             e.g. SB_ENGINE_EXTERNAL);
#                                             --demo builds a demo's own
#                                             image instead (M4b: the
#                                             Plaits load test), never the
#                                             firmware's; --src adds the
#                                             sources in a folder outside
#                                             firmware/, --leave-out
#                                             leaves a base source out
#                                             (since clean-1027, BR-5;
#                                             docs/BUILDING-ON-SMALL-BEEPS.md)
#   tools/build.sh inside SRC OUT             (runs inside the container)
#
# The outputs: app.elf and app.bin (the raw image, linked at 0x02000000),
# app.size, and since A1 (not for --demo) app-pkg.elf and app-pkg.bin, the
# same objects linked at 0x02000120 for a .fwsc (tools/fwsc.py; HW-91).
#
# Builds are deterministic (R-REPRO-3): fixed SOURCE_DATE_EPOCH (set in the
# image), no network, relative source paths with -fdebug-prefix-map, sorted
# output lists, and a check that no output contains the source mount path.
#
# Sources from outside (--src DIR, BR-5): each folder is mounted read-only
# beside the source mount, at sb-src-N for the Nth (/mnt/sb-src-1 for
# build A), and built by its path from there (../sb-src-1/...), as the
# base's files are by theirs, so where it sits on the host never reaches
# an output. Every .c, .S and .cc under it is built, sorted
# by path, with the firmware's flags plus -I for the folder (C++ with the
# same CPU, warnings and freestanding flags, as C++14 without exceptions
# or RTTI), and named by its path (src<N>_<path>.o), so a name the base
# also uses is never mixed up with the base's. --leave-out FILE takes a
# base source (a path from the repository's root, under firmware/) out
# of the build, so a firmware can replace it or do without it. A
# firmware built on the base calls this script from the base's folder
# (docs/BUILDING-ON-SMALL-BEEPS.md).
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
    out="" src_mount=/mnt/small-beeps-src defines="" demo="" mounts="" srcs="" leave="" n=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --out) out=$2; shift 2 ;;
            --src)
                [ -d "$2" ] || { echo "build: --src $2 is not a folder" >&2; exit 2; }
                d=$(cd "$2" && pwd)
                case "$ROOT/" in
                    "$d"/*) echo "build: --src $2 holds the base itself; give the folders of your own sources" >&2; exit 2 ;;
                esac
                case "$d/" in
                    "$ROOT/firmware/"*) echo "build: --src $2 is inside firmware/, which is built already" >&2; exit 2 ;;
                    *" "*) echo "build: --src $2: a path with a space is not supported" >&2; exit 2 ;;
                esac
                n=$((n + 1))
                srcs="$srcs $d"
                shift 2 ;;
            --leave-out)
                case "$2" in
                    firmware/*) [ -f "$ROOT/$2" ] || { echo "build: --leave-out $2: no such base file" >&2; exit 2; } ;;
                    *) echo "build: --leave-out takes a base source's path from the repository's root (firmware/...)" >&2; exit 2 ;;
                esac
                leave="$leave $2"; shift 2 ;;
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
    # The outside folders, beside the source mount (above).
    n=0 outside=""
    for d in $srcs; do
        n=$((n + 1))
        mounts="$mounts -v $d:$(dirname "$src_mount")/sb-src-$n:ro"
        outside="$outside $(dirname "$src_mount")/sb-src-$n"
    done
    tag=$(image_tag)
    docker image inspect "$tag" >/dev/null 2>&1 || cmd_image
    rm -rf "$out"
    mkdir -p "$out"
    out=$(cd "$out" && pwd)
    # shellcheck disable=SC2086
    docker run --rm --platform "$PLATFORM" --network none \
        --user "$(id -u):$(id -g)" -e SB_DEFINES="$defines" -e SB_DEMO="$demo" \
        -e SB_SRCS="$outside" -e SB_LEAVE_OUT="$leave" \
        -v "$ROOT:$src_mount:ro" $mounts -v "$out:/out" -w "$src_mount" \
        "$tag" sh "$src_mount/tools/build.sh" inside "$src_mount" /out
    cat "$out/SHA256SUMS"
}

# The image's size in bytes, from the symbols firmware/app.ld defines:
# code (code and constants, in the image, wherever they run), data
# (initialised data: in the image and copied to RAM), bss (zeroed RAM, the
# beacon included), image (the raw image's length), stack (reserved at the
# top of RAM, both stacks), irq_stack (the lower part of it: the interrupt
# stack) and, since M7, ram_code (the part of code copied to RAM and run
# there, which takes RAM as data does).
write_size() {
    sym() { nm "$1" | awk -v s="$2" '$3 == s { print $1 }'; }
    hex() { printf '%d' "0x$1"; }
    origin=$(hex 02000000)
    data_load=$(hex "$(sym "$1" __data_load)")
    data=$(( $(hex "$(sym "$1" __data_end)") - $(hex "$(sym "$1" __data_start)") ))
    bss=$(( $(hex "$(sym "$1" __bss_end)") - $(hex "$(sym "$1" __bss_start)") ))
    stack=$(( $(hex "$(sym "$1" __stack_top)") - $(hex "$(sym "$1" __stack_limit)") ))
    irq=$(( $(hex "$(sym "$1" __irq_stack_top)") - $(hex "$(sym "$1" __stack_limit)") ))
    ram_code=$(( $(hex "$(sym "$1" __ram_code_end)") - $(hex "$(sym "$1" __ram_code_start)") ))
    printf 'code %d\ndata %d\nbss %d\nimage %d\nstack %d\nirq_stack %d\nram_code %d\n' \
        $((data_load - origin + ram_code)) $((data - ram_code)) "$bss" $((data_load - origin + data)) \
        "$stack" "$irq" "$ram_code"
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

# The sources of the folders given with --src (BR-5), mounted beside the
# source mount as sb-src-N: every .c, .S and .cc, sorted by path, named
# by it, and built by its path from the source mount.
build_outside() {
    k=0
    for m in ${SB_SRCS:-}; do
        k=$((k + 1))
        r=../sb-src-$k
        # shellcheck disable=SC2086
        for s in $(cd "$m" && find . -name '*.c' -o -name '*.S' -o -name '*.cc' | sed 's|^\./||' | LC_ALL=C sort); do
            o="$obj/src${k}_$(echo "$s" | tr / _ | sed 's/\.[cS]$/.o/; s/\.cc$/.o/')"
            case "$s" in
                *.S) set -x; clang $ASFLAGS -I"$r" -c "$r/$s" -o "$o"; set +x ;;
                *.cc) set -x; clang $CXXFLAGS -I"$r" -c "$r/$s" -o "$o"; set +x ;;
                *) set -x; clang $CFLAGS -I"$r" -c "$r/$s" -o "$o"; set +x ;;
            esac
            objs="$objs $o"
        done
    done
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
    for d in ${SB_DEFINES:-}; do ASFLAGS="$ASFLAGS -D$d"; done
    # C++ from outside folders (BR-5): the C flags' CPU, warnings and
    # freestanding build, C++14 without exceptions, RTTI or guarded
    # statics.
    CXXFLAGS="-target pi32v2 $CPU -x c++ -std=c++14 -ffreestanding -nostdlib -nostdinc -Os -g
              -fno-common -fno-exceptions -fno-rtti -fno-threadsafe-statics -Wall -Wextra -Werror
              -fdebug-prefix-map=$src=. -Ifirmware/src"
    for d in ${SB_DEFINES:-}; do CXXFLAGS="$CXXFLAGS -D$d"; done
    clang --version | head -1
    ld --version | head -1
    echo "SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH"
    # Objects are intermediate: kept out of the outputs.
    obj=/tmp/small-beeps-obj
    rm -rf "$obj" && mkdir -p "$obj"
    objs=""
    # The demo is an engine on the engine seam (firmware/src/engine.h).
    if [ -n "${SB_DEMO:-}" ]; then
        CFLAGS="$CFLAGS -DSB_DEMO_PLAITS -DSB_ENGINE_EXTERNAL -Ifirmware/demos/plaits"
    fi
    for s in $(find firmware/src -name '*.c' -o -name '*.S' | LC_ALL=C sort); do
        case " ${SB_LEAVE_OUT:-} " in
            *" $s "*) echo "left out: $s"; continue ;;
        esac
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
    build_outside
    # No store that writes back into the register it stores (since
    # clean-1027; tools/ownbase.pl, R-BUILD-3): every object's code is
    # checked before anything is linked, so no image holds one. One
    # exception: the Plaits demo's measurement builds with the hardware
    # float instructions (PLAITS_HWFLOAT, which only fwtest ever runs),
    # where the compiler puts such stores in the vendored Plaits; there
    # they are listed and counted, not refused.
    wb=0
    for o in $objs; do
        objdump -d "$o" | perl tools/ownbase.pl "$(basename "$o")" || wb=$((wb + 1))
    done
    if [ "$wb" -ne 0 ]; then
        case " ${SB_DEMO:-}:${SB_DEFINES:-} " in
            *plaits:*" PLAITS_HWFLOAT "*)
                echo "ownbase check: $wb objects with such stores (above), allowed in a PLAITS_HWFLOAT measurement build" ;;
            *)
                echo "FAIL: a store writes back into the register it stores (above; tools/ownbase.pl)" >&2
                exit 1 ;;
        esac
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
    # The package link (Phase A1, HW-91): the same objects, linked where a
    # package's app.bin runs, 0x120 past the window's start; its raw image
    # is what tools/fwsc.py packs into a .fwsc. Not for a demo.
    if [ -z "${SB_DEMO:-}" ]; then
        ld -nostdlib --no-undefined --orphan-handling=error --defsym=IMAGE_ORIGIN=0x02000120 \
            -T firmware/app.ld -o "$out/app-pkg.elf" $objs
        objcopy -O binary -j .text "$out/app-pkg.elf" "$obj/pkg-text.bin"
        objcopy -O binary -j .data "$out/app-pkg.elf" "$obj/pkg-data.bin"
        cat "$obj/pkg-text.bin" "$obj/pkg-data.bin" > "$out/app-pkg.bin"
    fi
    set +x
    write_size "$out/app.elf" > "$out/app.size"
    cat "$out/app.size"
    image=$(awk '$1 == "image" { print $2 }' "$out/app.size")
    if [ "$(wc -c < "$out/app.bin")" -ne "$image" ]; then
        echo "FAIL: app.bin is not the $image bytes app.ld lays out" >&2; exit 1
    fi
    # Nothing in the firmware may depend on which link it is (A1-1): what
    # runs from RAM is byte for byte the same in both, the boot code (run
    # from the window) is as long, and the package's starts at 0x02000120.
    # The RAM check is the firmware's, not a test build's: the store's wipe
    # test (SB_TEST_STORE_WIPE) turns a link symbol into a chip offset.
    if [ -z "${SB_DEMO:-}" ]; then
        [ -n "${SB_DEFINES:-}" ] || cmp "$obj/data.bin" "$obj/pkg-data.bin" \
            || { echo "FAIL: the package link's RAM code and data differ from the raw image's" >&2; exit 1; }
        [ "$(wc -c < "$obj/pkg-text.bin")" -eq "$(wc -c < "$obj/text.bin")" ] \
            || { echo "FAIL: the package link's boot code is not as long as the raw image's" >&2; exit 1; }
        [ "$(nm "$out/app-pkg.elf" | awk '$3 == "_start" { print $1 }')" = 02000120 ] \
            || { echo "FAIL: the package link's _start is not at 0x02000120" >&2; exit 1; }
        rm "$obj/pkg-text.bin" "$obj/pkg-data.bin"
    fi
    rm "$obj/text.bin" "$obj/data.bin"
    # No output may contain the absolute source path, or an outside
    # folder's mount path.
    for f in $(find "$out" -type f | LC_ALL=C sort); do
        for p in "$src" ${SB_SRCS:-}; do
            if grep -q -F "$p" "$f"; then
                echo "FAIL: $f contains the source path $p" >&2; exit 1
            fi
        done
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
