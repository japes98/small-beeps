#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Checks on the files git tracks.

  check-tracked.py secrets       no tokens or private keys (R-PUB-2, C-SECRETS)
  check-tracked.py no-toolchain  nothing that looks like the toolchain or a
                                 build output (R-REPRO-1, C-NO-TOOLCHAIN)
"""
import os
import re
import subprocess
import sys

SECRETS = [
    ("private key", re.compile(rb"-----BEGIN[A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(rb"\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("Anthropic key", re.compile(rb"\bsk-ant-[A-Za-z0-9_-]{40,}")),
    ("AWS key ID", re.compile(rb"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(rb"\bxox[abpr]-[A-Za-z0-9-]{20,}")),
]
TOOLCHAIN_NAMES = re.compile(
    r"(\.tar\.xz|\.a|\.so(\.\d+)*|\.elf|\.o)$|LLVMgold|libcompiler-rt|jieli-linux-toolchains")
MAX_BYTES = 2 * 1024 * 1024          # outside sessions/
ELF_MAGIC = b"\x7fELF"


def tracked():
    out = subprocess.run(["git", "ls-files", "-z"], check=True, stdout=subprocess.PIPE).stdout
    return [p.decode("utf-8") for p in out.split(b"\0") if p]


def secrets(paths):
    problems = []
    for p in paths:
        if not os.path.isfile(p):
            continue
        with open(p, "rb") as f:
            data = f.read()
        for name, rx in SECRETS:
            for m in rx.finditer(data):
                line = data.count(b"\n", 0, m.start()) + 1
                problems.append("%s:%d: looks like a %s" % (p, line, name))
    print("%d tracked files scanned for secrets" % len(paths))
    return problems


def no_toolchain(paths):
    problems = []
    for p in paths:
        if TOOLCHAIN_NAMES.search(p):
            problems.append("%s: toolchain or build-output file name" % p)
        if not os.path.isfile(p):
            continue
        size = os.path.getsize(p)
        if size > MAX_BYTES and not p.startswith("sessions/"):
            problems.append("%s: %d bytes, larger than %d" % (p, size, MAX_BYTES))
        with open(p, "rb") as f:
            if f.read(4) == ELF_MAGIC:
                problems.append("%s: an ELF binary" % p)
    print("%d tracked files checked for toolchain parts and binaries" % len(paths))
    return problems


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("secrets", "no-toolchain"):
        print(__doc__, file=sys.stderr)
        return 2
    paths = tracked()
    problems = secrets(paths) if sys.argv[1] == "secrets" else no_toolchain(paths)
    for p in problems:
        print("FAIL " + p)
    print("%s: %s" % (sys.argv[1], "FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
