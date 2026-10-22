#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""tools/fwtest runs an image pinned by digest (R-SEP-3, R-HARN-10; check
C-FWTEST-PIN).

  check-fwtest-pin.py

config/fwtest-image must hold one image reference of the form
`ghcr.io/<owner>/<repository>@sha256:<64 hex digits>`, with no quiet words
in it (CONTRIBUTING.md, "Low profile"), or `unpublished` until the first
image is published (tools/fwtest then refuses to run). tools/fwtest must
take the image from that file, check for the digest form, and run it with
no network, as linux/amd64, with the working folder mounted read-only.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = re.compile(r"^ghcr\.io/[a-z0-9-]+/[a-z0-9._-]+@sha256:[0-9a-f]{64}$")
QUIET = re.compile(r"fm-?1|m-?vave|jie-?li|synth|firmware", re.I)
WRAPPER_MUST = [
    'PIN_FILE="$ROOT/config/fwtest-image"',
    "*@sha256:" + "?" * 64 + ")",
    "--network none",
    "--platform linux/amd64",
    ':/work:ro"',
]


def pinned(text):
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
    return lines[0] if len(lines) == 1 else None


def check(root=ROOT):
    problems = []
    with open(os.path.join(root, "config", "fwtest-image"), encoding="utf-8") as f:
        ref = pinned(f.read())
    if ref is None:
        problems.append("config/fwtest-image must hold exactly one reference")
    elif ref == "unpublished":
        print("config/fwtest-image: unpublished (no image yet; tools/fwtest refuses to run)")
    elif not REF.match(ref):
        problems.append("config/fwtest-image is not ghcr.io/<owner>/<repo>@sha256:<digest>: %s" % ref)
    elif QUIET.search(ref):
        problems.append("config/fwtest-image names a quiet word")
    else:
        print("config/fwtest-image: %s" % ref)
    with open(os.path.join(root, "tools", "fwtest"), encoding="utf-8") as f:
        wrapper = f.read()
    for must in WRAPPER_MUST:
        if must not in wrapper:
            problems.append("tools/fwtest lacks %r" % must)
    return problems


def main():
    problems = check()
    for p in problems:
        print("FAIL " + p)
    print("fwtest pin: %s" % ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
