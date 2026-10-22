#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Updates a clean folder to its remote's main (or REF), the safe way.
#
#   tools/clean-update.sh [--dir DIR] [REF]      (default: this folder, main)
#
# Clean sessions run with git's lazy fetching off (GIT_NO_LAZY_FETCH=1, set
# by config/claude/clean.json), so no command can download a file the clean
# folder leaves out. A checkout of new commits needs lazy fetching for the
# files it does check out, so this script allows it for exactly one
# fast-forward, then re-applies the sparse checkout and checks that no file
# under vendor/emulator/, harness/ or sessions/spec/ reached the disk or the
# folder's .git. Stop and tell the owner if it fails.
#
# The fast-forward runs with --no-stat and -q: a merge summary (diffstat)
# counts the lines of every changed file, and with lazy fetching allowed git
# downloads the excluded files' contents to count them.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
if [ "${1:-}" = "--dir" ]; then ROOT=$(cd "$2" && pwd); shift 2; fi
ref=${1:-main}
role=$(cat "$ROOT/.claude/small-beeps-role" 2>/dev/null || true)
[ "$role" = clean ] || { echo "clean-update.sh is for clean folders (role here: ${role:-none})" >&2; exit 2; }

GIT_NO_LAZY_FETCH=1 git -C "$ROOT" fetch -q origin
env -u GIT_NO_LAZY_FETCH git -C "$ROOT" merge -q --no-stat --ff-only "origin/$ref"
GIT_NO_LAZY_FETCH=1 sh "$ROOT/tools/clean-setup.sh" > /dev/null

fail=0
for p in vendor/emulator harness sessions/spec; do
    [ ! -e "$ROOT/$p" ] || { echo "STOP: $p is on disk"; fail=1; }
    have=$(GIT_NO_LAZY_FETCH=1 git -C "$ROOT" ls-tree -r HEAD -- "$p" | awk '$2 == "blob" { print $3 }' \
        | GIT_NO_LAZY_FETCH=1 git -C "$ROOT" cat-file --batch-check='%(objectname)' 2>/dev/null | grep -vc missing || true)
    [ "$have" = 0 ] || { echo "STOP: $have file(s) under $p are in .git"; fail=1; }
done
if [ $fail -ne 0 ]; then echo "Tell the owner before doing anything else." >&2; exit 1; fi
echo "clean folder at $(git -C "$ROOT" rev-parse --short HEAD); no spec-side files on disk or in .git"
