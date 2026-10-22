#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Vendors the parts of JieLi's AC79 SDK we use, from a pinned commit, and
# checks every file against vendor/jieli-sdk/SHA256SUMS (PROVENANCE P-2).
#
#   tools/fetch-sdk.sh --verify   check the committed files (default, offline)
#   tools/fetch-sdk.sh --fetch    re-download them from the pinned commit into
#                                 vendor/jieli-sdk/, then verify
#
# To vendor another file: add its path to SDK_FILES, run --fetch, add its
# hash to SHA256SUMS in the same commit, and log it in PROVENANCE.md.
set -eu

SDK_URL=https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK.git
SDK_COMMIT=5fa84a9b2f723a5e9337ad79dc2ad741fc98fe2d
SDK_FILES="
LICENSE
include_lib/driver/cpu/wl82/asm/WL82.h
include_lib/driver/cpu/wl82/asm/csfr.h
"

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEST="$ROOT/vendor/jieli-sdk"
SUMS="$DEST/SHA256SUMS"

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
    else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

verify() {
    status=0
    # Every listed file must exist with the recorded hash...
    while read -r want path; do
        [ -n "$want" ] || continue
        if [ ! -f "$DEST/$path" ]; then
            echo "MISSING $path"; status=1; continue
        fi
        got=$(sha256 "$DEST/$path")
        if [ "$got" = "$want" ]; then echo "OK      $path"
        else echo "CHANGED $path ($got, want $want)"; status=1; fi
    done < "$SUMS"
    # ...and nothing else may be vendored under the SDK's paths.
    for f in $(cd "$DEST" && find . -type f ! -name SHA256SUMS ! -name SOURCE.md | sed 's|^\./||' | LC_ALL=C sort); do
        if ! awk -v p="$f" '$2 == p { found = 1 } END { exit !found }' "$SUMS"; then
            echo "UNLISTED $f"; status=1
        fi
    done
    for f in $SDK_FILES; do
        if ! awk -v p="$f" '$2 == p { found = 1 } END { exit !found }' "$SUMS"; then
            echo "NO HASH  $f (in SDK_FILES but not in SHA256SUMS)"; status=1
        fi
    done
    if [ $status -eq 0 ]; then echo "SDK files match commit $SDK_COMMIT"; fi
    return $status
}

fetch() {
    work=$(mktemp -d)
    trap 'rm -rf "$work"' EXIT
    git -C "$work" init -q
    git -C "$work" remote add origin "$SDK_URL"
    git -C "$work" fetch -q --depth 1 --filter=blob:none origin "$SDK_COMMIT"
    # shellcheck disable=SC2086
    git -C "$work" sparse-checkout set --no-cone $(for f in $SDK_FILES; do printf '/%s ' "$f"; done)
    git -C "$work" -c advice.detachedHead=false checkout -q FETCH_HEAD
    got=$(git -C "$work" rev-parse HEAD)
    [ "$got" = "$SDK_COMMIT" ] || { echo "fetched $got, want $SDK_COMMIT"; exit 1; }
    for f in $SDK_FILES; do
        mkdir -p "$DEST/$(dirname "$f")"
        cp "$work/$f" "$DEST/$f"
    done
    verify
}

case "${1:---verify}" in
    --verify) verify ;;
    --fetch) fetch ;;
    *) echo "usage: $0 [--verify|--fetch]" >&2; exit 2 ;;
esac
