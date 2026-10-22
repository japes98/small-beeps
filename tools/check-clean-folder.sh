#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# C-CLEAN-FOLDER (R-CLEAN-1, R-SEP-2): makes a fresh clean folder with
# tools/clean-setup.sh from this checkout's HEAD, and checks that
#   - vendor/emulator/, harness/ and sessions/spec/ are not on disk;
#   - none of their files' contents are in its .git (a blob-less clone that
#     never fetched them);
#   - its live settings are config/claude/clean.json, which denies reading
#     all three, and the session banner says OK;
#   - its .git/info/attributes marks all three -diff.
#   - the firmware side's own tools, run inside it with git's lazy fetching
#     off as clean sessions run (the tool tests, the transcript, term and spec
#     checks, the emulator pin check, and `git log -p` over this branch,
#     which must fail rather than fetch), fetch none of those contents;
#   - tools/clean-update.sh brings a clean folder made at HEAD's parent up to
#     HEAD with the same results.
# It never reads those folders' contents itself: only their file lists and
# object IDs, from this checkout's history. In a clean folder it says SKIP
# and does nothing: it needs the full history to serve the copy it checks.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
if [ ! -d "$ROOT/vendor/emulator" ] || [ "$(cat "$ROOT/.claude/small-beeps-role" 2>/dev/null)" = clean ]; then
    echo "SKIP: this is a clean folder (it can't serve the spec-side files a check would need)"
    exit 0
fi
EXCLUDED="vendor/emulator harness sessions/spec"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
fail=0
bad() { echo "FAIL: $*"; fail=1; }

head=$(git -C "$ROOT" rev-parse HEAD)
# A bare copy that serves partial clones (a plain local clone would copy every
# object and ignore --filter).
git clone -q --bare --no-local "$ROOT" "$work/src.git"
git -C "$work/src.git" config uploadpack.allowFilter true
git -C "$work/src.git" update-ref refs/heads/checked "$head"

SETUP_SOURCE="file://$work/src.git" SETUP_REF=checked \
    sh "$ROOT/tools/clean-setup.sh" "$work/clean" > "$work/setup.log" 2>&1 || {
    cat "$work/setup.log"; bad "tools/clean-setup.sh failed"; exit 1; }
clean="$work/clean"
[ "$(git -C "$clean" rev-parse HEAD)" = "$head" ] || bad "the clean folder is not at $head"

for p in $EXCLUDED; do
    if [ -e "$clean/$p" ]; then bad "$p is on disk"; else echo "absent:   $p"; fi
done

# Every blob under the excluded paths at HEAD must be missing from the clean
# folder's objects (checked without fetching: --missing=print lists them).
no_blobs() {
    missing=$(git -C "$clean" rev-list --objects --missing=print HEAD -- $EXCLUDED | sed -n 's/^?//p' | sort -u)
    for p in $EXCLUDED; do
        for oid in $(git -C "$ROOT" ls-tree -r HEAD -- "$p" | awk '$2 == "blob" { print $3 }' | sort -u); do
            if ! printf '%s\n' "$missing" | grep -qx "$oid"; then
                bad "$1: a blob under $p is in the clean folder's .git ($oid)"
            fi
        done
        n=$(git -C "$ROOT" ls-tree -r HEAD -- "$p" | grep -c . || true)
        echo "no blobs ($1): $p ($n files at HEAD)"
    done
}
no_blobs "after setup"

live="$clean/.claude/settings.json"
if cmp -s "$live" "$ROOT/config/claude/clean.json"; then echo "settings: config/claude/clean.json"
else bad "the live settings are not config/claude/clean.json"; fi
for rule in 'Read(./vendor/emulator/**)' 'Read(./harness/**)' 'Read(./sessions/spec/**)'; do
    if grep -qF "\"$rule\"" "$live"; then echo "denied:   $rule"; else bad "settings lack $rule"; fi
done
attrs="$(git -C "$clean" rev-parse --absolute-git-dir)/info/attributes"
for p in $EXCLUDED; do
    grep -qxF "/$p/** -diff" "$attrs" || bad "$attrs lacks /$p/** -diff"
done
grep -q '^status: OK' "$work/setup.log" || bad "the banner did not say status: OK"

# The firmware side's tools, run inside the clean folder, must not fetch them.
py=$(sh "$ROOT/tools/find-python.sh")
base=$(git -C "$ROOT" merge-base HEAD "$(git -C "$ROOT" rev-parse --verify -q origin/main || echo HEAD)")
(cd "$clean" && GIT_NO_LAZY_FETCH=1 COMMIT_RANGE="$base..HEAD" "$py" tools/record.py run --out "$work/inside" \
    --only C-UNIT,C-TRANSCRIPTS,C-SEP-TERMS,C-SPEC-LINT,C-EMU-PIN,C-CLEAN-FOLDER,C-FWTEST-PIN) > "$work/inside.log" 2>&1 \
    || { cat "$work/inside.log"; bad "the firmware side's checks failed inside the clean folder"; }
grep -E '^C-' "$work/inside.log" | sed 's/^/inside:   /'
if GIT_NO_LAZY_FETCH=1 git -C "$clean" log -p "$base..HEAD" > /dev/null 2>&1; then
    echo "git log -p: needed no excluded file"
else
    echo "git log -p: refused to fetch excluded files, as it should"
fi
no_blobs "after the tools and git log -p"

# An update from HEAD's parent to HEAD.
if parent=$(git -C "$ROOT" rev-parse -q --verify "HEAD~1"); then
    git -C "$work/src.git" update-ref refs/heads/old "$parent"
    git -C "$work/src.git" update-ref refs/heads/main "$head"
    SETUP_SOURCE="file://$work/src.git" SETUP_REF=old \
        sh "$ROOT/tools/clean-setup.sh" "$work/clean2" > /dev/null 2>&1 || bad "clean-setup.sh at HEAD's parent failed"
    if sh "$ROOT/tools/clean-update.sh" --dir "$work/clean2" main > "$work/update.log" 2>&1; then
        echo "update:   $(tail -1 "$work/update.log")"
    else
        cat "$work/update.log"; bad "tools/clean-update.sh failed"
    fi
    clean_saved=$clean; clean="$work/clean2"
    [ "$(git -C "$clean" rev-parse HEAD)" = "$head" ] || bad "the update did not reach HEAD"
    for p in $EXCLUDED; do [ ! -e "$clean/$p" ] || bad "$p is on disk after the update"; done
    no_blobs "after an update"
    clean=$clean_saved
fi

if [ $fail -eq 0 ]; then echo "clean folder: PASS"; else echo "clean folder: FAIL"; fi
exit $fail
