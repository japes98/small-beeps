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
#   - tools/reproduce's export of a commit, even with lazy fetching on,
#     fetches none of those contents (since M2);
#   - tools/clean-update.sh stops when a spec-side output reaches .git
#     through another branch (as the records branch holds them);
#   - tools/clean-update.sh brings a clean folder made at HEAD's parent up to
#     HEAD with the same results, and updates one across a commit (made here)
#     that changes vendor/emulator/ and harness/ without fetching any of
#     their blobs, while a plain merge with its summary does fetch some.
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

# An update across a commit that changes vendor/emulator/ and harness/. The
# commit is made here, on top of HEAD: in each folder one existing file gets
# new contents and one file is added (made-up text; nothing is read from the
# folders but one file name each). tools/clean-update.sh must bring none of
# their blobs, old or new, into .git. As a control, a plain fast-forward,
# whose merge summary counts the changed files' lines, must fetch some in
# another copy; otherwise this test would prove nothing. The control's output
# goes to /dev/null, since it names the files.
src="$work/src.git"
idx="$work/probe.index"
GIT_INDEX_FILE=$idx git -C "$src" read-tree "$head"
for p in vendor/emulator harness; do
    set -- $(git -C "$ROOT" ls-tree -r HEAD -- "$p" | awk '$2 == "blob" { print $1, $4; exit }')
    changed=$(printf 'clean-update probe: %s, changed\n' "$p" | git -C "$src" hash-object -w --stdin)
    added=$(printf 'clean-update probe: %s, added\nsecond line\n' "$p" | git -C "$src" hash-object -w --stdin)
    GIT_INDEX_FILE=$idx git -C "$src" update-index --add --cacheinfo "$1,$changed,$2" \
        --cacheinfo "100644,$added,$p/clean-update-probe.txt"
done
probe=$(git -C "$src" -c user.name=probe -c user.email=probe@invalid commit-tree \
    "$(GIT_INDEX_FILE=$idx git -C "$src" write-tree)" -p "$head" -m "probe: change both folders")
git -C "$src" update-ref refs/heads/main "$probe"
# Every blob under the two folders at HEAD or at the probe commit.
probe_blobs=$( (git -C "$src" ls-tree -r "$head" -- vendor/emulator harness
                git -C "$src" ls-tree -r "$probe" -- vendor/emulator harness) | awk '$2 == "blob" { print $3 }' | sort -u)
present() {
    n=0
    for oid in $probe_blobs; do
        if GIT_NO_LAZY_FETCH=1 git -C "$1" cat-file -e "$oid" 2>/dev/null; then n=$((n + 1)); fi
    done
    echo $n
}
for c in probe-update probe-control; do
    SETUP_SOURCE="file://$src" SETUP_REF=checked \
        sh "$ROOT/tools/clean-setup.sh" "$work/$c" > /dev/null 2>&1 || bad "clean-setup.sh for $c failed"
done
if sh "$ROOT/tools/clean-update.sh" --dir "$work/probe-update" main > "$work/probe.log" 2>&1; then
    echo "update across a change to both folders: $(tail -1 "$work/probe.log")"
else
    cat "$work/probe.log"; bad "tools/clean-update.sh across a change to both folders failed"
fi
[ "$(git -C "$work/probe-update" rev-parse HEAD)" = "$probe" ] || bad "the update did not reach the probe commit"
n=$(present "$work/probe-update")
if [ "$n" = 0 ]; then echo "no blobs (update across a change to both folders): 0 present"
else bad "the update across a change to both folders brought $n of their blobs into .git"; fi
GIT_NO_LAZY_FETCH=1 git -C "$work/probe-control" fetch -q origin
env -u GIT_NO_LAZY_FETCH git -C "$work/probe-control" merge --ff-only origin/main > /dev/null 2>&1 || true
n=$(present "$work/probe-control")
if [ "$n" -gt 0 ]; then echo "control: a merge with its summary fetched $n of their blobs, as expected"
else bad "control: a merge with its summary fetched none of their blobs, so this test can't tell"; fi

# tools/reproduce's export of a commit, run in a clean folder with lazy
# fetching on (as a person might run it), must fetch no spec-side blob and
# export none of those folders. As a control, `git archive` with exclude
# pathspecs (its method before M2) fetches some in another copy.
head_blobs=$(git -C "$ROOT" ls-tree -r HEAD -- $EXCLUDED | awk '$2 == "blob" { print $3 }' | sort -u)
count_present() {
    n=0
    for oid in $head_blobs; do
        if GIT_NO_LAZY_FETCH=1 git -C "$1" cat-file -e "$oid" 2>/dev/null; then n=$((n + 1)); fi
    done
    echo $n
}
for c in export export-control; do
    SETUP_SOURCE="file://$src" SETUP_REF=checked \
        sh "$ROOT/tools/clean-setup.sh" "$work/$c" > /dev/null 2>&1 || bad "clean-setup.sh for $c failed"
done
mkdir "$work/exported"
if (cd "$work/export" && env -u GIT_NO_LAZY_FETCH sh tools/reproduce --export-only HEAD "$work/exported") > "$work/export.log" 2>&1; then
    n=$(count_present "$work/export")
    if [ "$n" = 0 ]; then echo "no blobs (tools/reproduce's export, lazy fetching on): 0 present"
    else bad "tools/reproduce's export brought $n spec-side blobs into .git"; fi
    for p in $EXCLUDED; do [ ! -e "$work/exported/$p" ] || bad "tools/reproduce exported $p"; done
    [ -f "$work/exported/tools/build.sh" ] || bad "tools/reproduce's export lacks tools/build.sh"
else
    cat "$work/export.log"; bad "tools/reproduce --export-only failed"
fi
env -u GIT_NO_LAZY_FETCH git -C "$work/export-control" archive HEAD -- . ':(exclude)vendor/emulator' \
    ':(exclude)harness' ':(exclude)sessions/spec' > /dev/null 2>&1 || true
n=$(count_present "$work/export-control")
if [ "$n" -gt 0 ]; then echo "control: git archive with exclude pathspecs fetched $n spec-side blobs, as expected"
else bad "control: git archive with exclude pathspecs fetched none, so this test can't tell"; fi

# A spec-side output reached through another branch (as a record on the
# records branch holds them): a made-up file under records/x/spec-experiments/
# on a local branch, with its blob present, must make clean-update.sh stop.
d="$work/probe-update"
oid=$(printf 'clean-update probe: a spec-side output in a record\n' | git -C "$d" hash-object -w --stdin)
t=$(printf '100644 blob %s\tprobe.txt\n' "$oid" | git -C "$d" mktree)
for name in spec-experiments x records; do t=$(printf '040000 tree %s\t%s\n' "$t" "$name" | git -C "$d" mktree); done
git -C "$d" update-ref refs/heads/planted "$(git -C "$d" -c user.name=probe -c user.email=probe@invalid commit-tree "$t" -m 'clean-update probe')"
if sh "$ROOT/tools/clean-update.sh" --dir "$d" main > "$work/planted.log" 2>&1; then
    cat "$work/planted.log"; bad "tools/clean-update.sh missed a spec-side output reached through another branch"
elif grep -q '^STOP: 1 spec-side' "$work/planted.log"; then
    echo "a spec-side output reached through another branch: clean-update.sh stopped, as it should"
else
    cat "$work/planted.log"; bad "tools/clean-update.sh failed, but not for the planted output"
fi
git -C "$d" update-ref -d refs/heads/planted

if [ $fail -eq 0 ]; then echo "clean folder: PASS"; else echo "clean folder: FAIL"; fi
exit $fail
