#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Turns on the pre-commit and commit-msg hooks and the commit template for this checkout.
# (tools/clean-setup.sh and tools/spec-setup.sh do this too.)
set -eu
cd "$(dirname "$0")/.."
git config core.hooksPath tools/hooks
git config commit.template .gitmessage
echo "pre-commit and commit-msg hooks and .gitmessage template turned on"
