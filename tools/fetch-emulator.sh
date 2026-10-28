#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Vendors three crates of the public emulator upstream, at a pinned commit,
# into vendor/emulator/, applies the patches in vendor/emulator/patches/, and
# checks every file against vendor/emulator/SHA256SUMS, whose own SHA-256 is
# the tree hash below (PROVENANCE P-7). Spec side only: vendor/emulator/ is
# left out of clean folders, and --fetch refuses to run in one.
#
#   tools/fetch-emulator.sh --verify   check the committed files (default,
#                                      offline; SKIP when vendor/emulator/
#                                      isn't on disk, as in a clean folder)
#   tools/fetch-emulator.sh --fetch    re-download them from the pinned commit,
#                                      apply the patches, then verify
#
# The fetch is a blob-less clone with a sparse checkout of exactly the paths
# in UPSTREAM_PATHS, so nothing else in that repository reaches the disk.
# To move to another commit: change UPSTREAM_COMMIT, run --fetch in a spec
# folder, rewrite SHA256SUMS (--sums), update TREE_SHA256 and UPSTREAM.md,
# and log it in PROVENANCE.md, all in one pull request.
set -eu

UPSTREAM_URL=https://github.com/joakimeriksson/fm1-emu.git
UPSTREAM_COMMIT=43ed5580064885e93bc8d20be931ae950d10cd4f
UPSTREAM_PATHS="
/LICENSE
/Cargo.toml
/crates/fm1-isa/
/crates/fm1-core/
/crates/fm1-soc/
"
# SHA-256 of vendor/emulator/SHA256SUMS: one hash for the whole tree.
TREE_SHA256=f1ecfd168321d4ebde080de4eaffc2c3f77da858d5ace9cb25be67ca70940675

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEST="$ROOT/vendor/emulator"
SUMS="$DEST/SHA256SUMS"
# Ours, not upstream's: not listed in SHA256SUMS.
OURS="SHA256SUMS UPSTREAM.md"

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
    else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

listed_files() {
    (cd "$DEST" && find . -type f | sed 's|^\./||' | LC_ALL=C sort) | while read -r f; do
        case " $OURS " in *" $f "*) continue ;; esac
        printf '%s\n' "$f"
    done
}

verify() {
    if [ ! -d "$DEST" ]; then
        echo "SKIP: vendor/emulator/ is not on disk (a clean folder leaves it out)"
        return 0
    fi
    status=0
    got=$(sha256 "$SUMS")
    if [ "$got" = "$TREE_SHA256" ]; then echo "OK      SHA256SUMS (tree hash $TREE_SHA256)"
    else echo "CHANGED SHA256SUMS ($got, want $TREE_SHA256)"; status=1; fi
    while read -r want path; do
        [ -n "$want" ] || continue
        if [ ! -f "$DEST/$path" ]; then
            echo "MISSING $path"; status=1; continue
        fi
        [ "$(sha256 "$DEST/$path")" = "$want" ] || { echo "CHANGED $path"; status=1; }
    done < "$SUMS"
    for f in $(listed_files); do
        if ! awk -v p="$f" '$2 == p { found = 1 } END { exit !found }' "$SUMS"; then
            echo "UNLISTED $f"; status=1
        fi
    done
    n=$(grep -c . "$SUMS")
    if [ $status -eq 0 ]; then echo "$n emulator files match commit $UPSTREAM_COMMIT plus patches"; fi
    return $status
}

sums() {
    (cd "$DEST" && for f in $(listed_files); do printf '%s  %s\n' "$(sha256 "$f")" "$f"; done) > "$SUMS"
    echo "wrote SHA256SUMS: tree hash $(sha256 "$SUMS")"
}

refuse_in_clean_folder() {
    role=$(cat "$ROOT/.claude/small-beeps-role" 2>/dev/null || true)
    if [ "$role" = clean ] || git -C "$ROOT" sparse-checkout list 2>/dev/null | grep -q '^!/vendor/emulator/'; then
        echo "REFUSED: this is a clean folder; emulator source must never reach it." >&2
        exit 1
    fi
}

fetch() {
    refuse_in_clean_folder
    work=$(mktemp -d)
    trap 'rm -rf "$work"' EXIT
    git -C "$work" init -q
    git -C "$work" remote add origin "$UPSTREAM_URL"
    git -C "$work" fetch -q --depth 1 --filter=blob:none origin "$UPSTREAM_COMMIT"
    # shellcheck disable=SC2086
    git -C "$work" sparse-checkout set --no-cone $UPSTREAM_PATHS
    git -C "$work" -c advice.detachedHead=false checkout -q FETCH_HEAD
    got=$(git -C "$work" rev-parse HEAD)
    [ "$got" = "$UPSTREAM_COMMIT" ] || { echo "fetched $got, want $UPSTREAM_COMMIT"; exit 1; }
    for p in $(ls "$DEST/patches"/*.patch 2>/dev/null | LC_ALL=C sort); do
        git -C "$work" apply --whitespace=nowarn "$p"
        echo "applied $(basename "$p")"
    done
    keep=$(mktemp -d)
    for f in $OURS patches; do [ -e "$DEST/$f" ] && cp -R "$DEST/$f" "$keep/"; done
    rm -rf "$DEST"
    mkdir -p "$DEST/crates"
    cp "$work/LICENSE" "$work/Cargo.toml" "$DEST/"
    for c in fm1-isa fm1-core fm1-soc; do cp -R "$work/crates/$c" "$DEST/crates/"; done
    for f in $OURS patches; do [ -e "$keep/$f" ] && cp -R "$keep/$f" "$DEST/"; done
    rm -rf "$keep"
    verify
}

case "${1:---verify}" in
    --verify) verify ;;
    --fetch) fetch ;;
    --sums) sums ;;
    *) echo "usage: $0 [--verify|--fetch|--sums]" >&2; exit 2 ;;
esac
