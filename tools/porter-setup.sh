#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Creates (or sets up) a porter's working folder:
#   tools/porter-setup.sh [DIR]
# A full clone plus the Claude Code settings in config/claude/porter.json.
# Only for a porter session the owner starts (CONTRIBUTING.md, "Roles"):
# it clones the port repository into DIR/port-work/ (gitignored here) and
# writes the GPL ports only there; see tools/setup-folder.sh.
exec sh "$(dirname "$0")/setup-folder.sh" porter "$@"
