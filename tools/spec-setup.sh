#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Creates (or sets up) a spec-side working folder:
#   tools/spec-setup.sh [DIR]
# A full clone plus the Claude Code settings in config/claude/spec.json.
# See tools/setup-folder.sh and CONTRIBUTING.md ("Barriers").
exec sh "$(dirname "$0")/setup-folder.sh" spec "$@"
