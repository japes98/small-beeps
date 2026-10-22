#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Shared by tools/clean-setup.sh, tools/spec-setup.sh and tools/auditor-setup.sh.
#
#   tools/setup-folder.sh ROLE [DIR]
#
# ROLE is clean, spec or auditor. With a DIR that doesn't exist yet, clones
# this repository into it first (clean: blob-less clone with a sparse checkout
# that leaves out vendor/emulator/, harness/ and sessions/spec/, so their
# contents never reach the disk; spec and auditor: a full clone). Without DIR, sets up
# this checkout. SETUP_SOURCE (a URL, default this checkout's origin) and
# SETUP_REF (default main) choose what a new folder is cloned from; CI uses
# them to test a pull request's own tree.
#
# A clean folder also gets .git/info/attributes marking those paths -diff,
# so history commands (git log -p, git show) don't print their contents.
# Then it installs config/claude/ROLE.json as .claude/settings.json (a
# byte-for-byte copy), records the role, turns on the commit-msg hook and
# commit template, and prints the session banner.
#
# It never loosens settings: it refuses to replace a .claude/settings.json
# whose deny rules aren't all in the new config.
set -eu

ROLE=${1:-}
DIR=${2:-}
case "$ROLE" in clean|spec|auditor) ;; *) echo "usage: $0 clean|spec|auditor [DIR]" >&2; exit 2 ;; esac

HERE=$(cd "$(dirname "$0")/.." && pwd)
CLEAN_EXCLUDES="/vendor/emulator/ /harness/ /sessions/spec/"

if [ -n "$DIR" ] && [ ! -e "$DIR" ]; then
    url=${SETUP_SOURCE:-$(git -C "$HERE" remote get-url origin 2>/dev/null || echo "file://$HERE")}
    ref=${SETUP_REF:-main}
    if [ "$ROLE" = clean ]; then
        git clone --filter=blob:none --no-checkout "$url" "$DIR"
        # shellcheck disable=SC2086
        git -C "$DIR" sparse-checkout set --no-cone '/*' $(for p in $CLEAN_EXCLUDES; do printf '!%s ' "$p"; done)
        git -C "$DIR" checkout "$ref"
    else
        git clone "$url" "$DIR"
        git -C "$DIR" checkout "$ref"
    fi
    TARGET=$(cd "$DIR" && pwd)
elif [ -n "$DIR" ]; then
    TARGET=$(cd "$DIR" && pwd)
else
    TARGET=$HERE
fi

if [ "$ROLE" = clean ] && git -C "$TARGET" rev-parse --verify -q HEAD >/dev/null; then
    # Apply (or re-apply) the sparse checkout to an existing clean folder.
    # shellcheck disable=SC2086
    git -C "$TARGET" sparse-checkout set --no-cone '/*' $(for p in $CLEAN_EXCLUDES; do printf '!%s ' "$p"; done)
fi
if [ "$ROLE" = clean ]; then
    attrs="$(git -C "$TARGET" rev-parse --absolute-git-dir)/info/attributes"
    mkdir -p "$(dirname "$attrs")"
    for p in $CLEAN_EXCLUDES; do
        line="${p}** -diff"
        grep -qxF "$line" "$attrs" 2>/dev/null || printf '%s\n' "$line" >> "$attrs"
    done
    for p in $CLEAN_EXCLUDES; do
        if [ -e "$TARGET$p" ]; then
            echo "STOP: $TARGET$p exists in a clean folder. Tell the owner." >&2
            exit 1
        fi
    done
fi

NEW="$TARGET/config/claude/$ROLE.json"
LIVE="$TARGET/.claude/settings.json"
[ -f "$NEW" ] || { echo "missing $NEW" >&2; exit 1; }
mkdir -p "$TARGET/.claude"

if [ -f "$LIVE" ]; then
    "$(sh "$HERE/tools/find-python.sh")" -I - "$LIVE" "$NEW" <<'EOF'
import json, sys
old = json.load(open(sys.argv[1])).get("permissions", {}).get("deny", [])
new = json.load(open(sys.argv[2])).get("permissions", {}).get("deny", [])
dropped = [r for r in old if r not in new]
if dropped:
    print("REFUSED: the new config would drop these deny rules:", file=sys.stderr)
    for r in dropped:
        print("  " + r, file=sys.stderr)
    sys.exit(1)
EOF
fi
if [ -f "$TARGET/.claude/settings.local.json" ]; then
    echo "NOTE: $TARGET/.claude/settings.local.json exists; check that it allows nothing forbidden:"
    cat "$TARGET/.claude/settings.local.json"
fi

cp "$NEW" "$LIVE"
printf '%s\n' "$ROLE" > "$TARGET/.claude/small-beeps-role"
git -C "$TARGET" config core.hooksPath tools/hooks
git -C "$TARGET" config commit.template .gitmessage

echo "Installed config/claude/$ROLE.json as $LIVE"
CLAUDE_PROJECT_DIR=$TARGET sh "$TARGET/tools/session-banner.sh" < /dev/null
