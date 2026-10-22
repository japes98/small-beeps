#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Creates (or sets up) an auditor's working folder:
#   tools/auditor-setup.sh [DIR]
# A full clone plus the Claude Code settings in config/claude/auditor.json.
# Only for an auditor session the owner starts after a failed audit
# (docs/AUDIT.md, "When the audit fails"); see tools/setup-folder.sh and
# CONTRIBUTING.md ("Roles").
exec sh "$(dirname "$0")/setup-folder.sh" auditor "$@"
