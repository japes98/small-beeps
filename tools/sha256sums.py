# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""A vendored tree checked against its SHA256SUMS (since M4b): the files
listed there, each matching its hash, and nothing else in the tree but the
list itself and our own notes about it (OURS). Used where a vendored tree
counts as public or as base code only as pinned: tools/check-emulator-terms.py
(R-SEP-1) and tools/audit.py (R-AUDIT-4).
"""
import hashlib
import os

# files in a vendored tree that we write ourselves, not upstream's
OURS = ("SHA256SUMS", "SOURCE.md")


def verified(top):
    """{path in top: its bytes} for every file top/SHA256SUMS lists, in path
    order, each checked against its hash. ValueError names the first that is
    missing or doesn't match, or a file in top that isn't listed (other than
    OURS). Nothing else in top is read."""
    listed = {}
    with open(os.path.join(top, "SHA256SUMS"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                want, path = line.split()
                listed[path] = want
    on_disk = set()
    for dirpath, _, names in os.walk(top):
        for n in names:
            rel = os.path.relpath(os.path.join(dirpath, n), top).replace(os.sep, "/")
            if rel not in OURS:
                on_disk.add(rel)
    extra = sorted(on_disk - set(listed))
    if extra:
        raise ValueError("%s is not in SHA256SUMS" % extra[0])
    out = {}
    for path in sorted(listed):
        try:
            with open(os.path.join(top, path), "rb") as f:
                data = f.read()
        except OSError:
            raise ValueError("%s is missing" % path)
        if hashlib.sha256(data).hexdigest() != listed[path]:
            raise ValueError("%s does not match its SHA-256" % path)
        out[path] = data
    return out
