#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Prints the first Python 3 (3.9 or later) that actually runs here. Some
# hosts have a python3 on PATH built for another CPU, so we test each one.
# Override with PYTHON=/path/to/python3.
for p in "${PYTHON:-}" python3 /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    [ -n "$p" ] || continue
    if "$p" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
        command -v "$p"
        exit 0
    fi
done
echo "no working Python 3.9+ found (set PYTHON=...)" >&2
exit 1
