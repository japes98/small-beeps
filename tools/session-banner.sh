#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# SessionStart hook (config/claude/clean.json, spec.json and auditor.json), run on every
# session source: startup, resume, clear, compact. It prints the session's
# role, the Claude Code version, the SHA-256 of the live settings and of the
# committed config for that role, and the UTC time. If the live settings
# aren't byte-identical to the committed config, it prints CONFIG MISMATCH
# and exits non-zero. The output lands in the session transcript, where
# tools/check-transcripts.py looks for it (R-CLEAN-5).
set -u

ROOT=${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}
SETTINGS="$ROOT/.claude/settings.json"
ROLE_FILE="$ROOT/.claude/small-beeps-role"

sha256() {
    [ -f "$1" ] || { echo "absent"; return; }
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
    else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

# Read the hook's JSON input (it names the source) without needing jq.
input=$(cat 2>/dev/null || true)
source=$(printf '%s' "$input" | sed -n 's/.*"source"[[:space:]]*:[[:space:]]*"\([a-z]*\)".*/\1/p')

role=unknown
[ -f "$ROLE_FILE" ] && role=$(tr -cd 'a-z' < "$ROLE_FILE")
config="$ROOT/config/claude/$role.json"

live=$(sha256 "$SETTINGS")
committed=$(sha256 "$config")
# `claude` is often a shell alias, so also try its usual install places.
version=unavailable
for c in claude "$HOME/.claude/local/claude" "$HOME/.local/bin/claude" \
         /opt/homebrew/bin/claude /usr/local/bin/claude; do
    if v=$("$c" --version 2>/dev/null) && [ -n "$v" ]; then version=$v; break; fi
done

status=OK
case "$role" in clean|spec|auditor) ;; *) status="CONFIG MISMATCH" ;; esac
if [ "$live" = absent ] || [ "$live" != "$committed" ]; then status="CONFIG MISMATCH"; fi

cat <<EOF
=== small-beeps session banner v1 ===
role: $role
source: ${source:-unknown}
claude: $version
settings: .claude/settings.json sha256=$live
config: config/claude/$role.json sha256=$committed
utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)
status: $status
=== end of banner ===
EOF

if [ "$status" != OK ]; then
    echo "CONFIG MISMATCH: .claude/settings.json does not match config/claude/$role.json. Stop and tell the owner." >&2
    exit 1
fi
