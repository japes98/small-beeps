#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Creates (or sets up) a clean, firmware-side working folder:
#   tools/clean-setup.sh [DIR]
# A blob-less clone with a sparse checkout without the spec-side folders
# (config/spec-side-folders), plus the Claude Code settings in
# config/claude/clean.json.
# See tools/setup-folder.sh and CONTRIBUTING.md ("Barriers").
exec sh "$(dirname "$0")/setup-folder.sh" clean "$@"
