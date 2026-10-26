#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The reference reader of the app release's single file, the `.fm1img`
(docs/M9-PLAN.md, section 1, "The release format", format 1.0): the
app's checks, in the same order, so the tests and the app's author agree
on them (R-REL-2). Also writes one (pack).

  fm1img.py FILE.fm1img            runs the checks; prints the release or
                                   the first check that failed (exit 1)
  fm1img.py FILE.fm1img --unpack DIR
                                   ... and writes its release.json and image
"""

import argparse
import hashlib
import json
import os
import re
import struct
import sys

MAGIC = b"FM1IMG\r\n"
FORMAT_MAJOR, FORMAT_MINOR = 1, 0
HEADER = struct.Struct("<8sHHIIIII32s")      # format 1.0's 64 bytes
HEADER_SIZE = HEADER.size
ALIGN = 16
JSON_MAX = 65536
IMAGE_MAX = 1032192                          # docs/HARNESS.md, "The raw image"
LOAD_ADDRESS = ENTRY = 33554432              # 0x02000000, HW-1, HW-2
TARGET = "f-emulator-app"

# release.json's fields in format 1.0: (path, type, required).
FIELDS = [
    ("format", dict, True), ("format.major", int, True), ("format.minor", int, True),
    ("kind", str, True), ("name", str, True), ("version", str, True), ("tag", str, True),
    ("git_commit", str, True), ("targets", list, True),
    ("image", dict, True), ("image.file", str, True), ("image.size", int, True), ("image.sha256", str, True),
    ("image.load_address", int, True), ("image.entry", int, True),
    ("fwtest", dict, True), ("fwtest.version", str, True), ("fwtest.image", str, True),
    ("record", dict, True), ("record.tree_sha256", str, True), ("record.ci_run", str, False),
    ("build", dict, False), ("build.toolchain_sha256", str, False), ("build.container", str, False),
    ("build.ram_used", int, False),
    ("store", dict, False), ("store.format_version", int, False), ("store.offset", int, False),
    ("store.size", int, False),
]
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$")
HEX40, HEX64 = re.compile(r"^[0-9a-f]{40}$"), re.compile(r"^[0-9a-f]{64}$")
FILE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def dumps(obj):
    """release.json's exact bytes (format 1.0's rule)."""
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def pack(meta_bytes, image):
    """The .fm1img of release.json's bytes and the image."""
    image_offset = HEADER_SIZE + len(meta_bytes)
    image_offset += (-image_offset) % ALIGN
    body = meta_bytes + b"\0" * (image_offset - HEADER_SIZE - len(meta_bytes)) + image
    return HEADER.pack(MAGIC, FORMAT_MAJOR, FORMAT_MINOR, HEADER_SIZE, HEADER_SIZE, len(meta_bytes), image_offset,
                       len(image), hashlib.sha256(body).digest()) + body


def get(meta, path):
    v = meta
    for k in path.split("."):
        if not isinstance(v, dict) or k not in v:
            return None
        v = v[k]
    return v


def field_problems(meta, writer=False):
    """Missing required fields and fields of the wrong type (a reader's
    rule); with writer, also fields format 1.0 doesn't have and the
    values' forms (a writer writes only format 1.0's fields)."""
    p = []
    for path, t, required in FIELDS:
        v = get(meta, path)
        if v is None:
            if required:
                p.append("release.json: no %s" % path)
        elif not isinstance(v, t) or (t is int and isinstance(v, bool)):
            p.append("release.json: %s is not a%s %s" % (path, "n" if t is int else "", t.__name__))
    if writer and not p:
        known = {f for f, _, _ in FIELDS}

        def walk(d, pre):
            for k, v in d.items():
                path = pre + k
                if path not in known:
                    p.append("release.json: %s is not a format 1.0 field" % path)
                elif isinstance(v, dict) and path != "format":
                    walk(v, path + ".")
        walk(meta, "")
        for path, rx in (("version", SEMVER), ("git_commit", HEX40), ("image.sha256", HEX64),
                         ("record.tree_sha256", HEX64), ("image.file", FILE_NAME)):
            if not rx.match(get(meta, path)):
                p.append("release.json: %s %r is not of its form" % (path, get(meta, path)))
        if not all(isinstance(t, str) for t in meta["targets"]):
            p.append("release.json: targets holds a non-string")
    return p


def check(blob):
    """The app's checks in order (format 1.0, "How the app verifies it"):
    (release.json as an object, its bytes, the image), or ValueError
    naming the first that failed."""
    # 1. The magic.
    if len(blob) < 64 or blob[:8] != MAGIC:
        raise ValueError("1: not a small-beeps release (no FM1IMG magic)")
    magic, major, minor, hsize, joff, jsize, ioff, isize, digest = HEADER.unpack_from(blob)
    # 2. A major this reader knows.
    if major != FORMAT_MAJOR:
        raise ValueError("2: format %d.%d needs a newer app" % (major, minor))
    # 3. A consistent header (Python's integers don't overflow).
    if not (hsize >= 64 and joff >= hsize and 2 <= jsize <= JSON_MAX and ioff >= joff + jsize
            and 1 <= isize <= IMAGE_MAX and ioff + isize == len(blob)):
        raise ValueError("3: the header's offsets and sizes don't fit the file")
    # 4. The payload's SHA-256.
    if hashlib.sha256(blob[hsize:]).digest() != digest:
        raise ValueError("4: the payload's SHA-256 doesn't match the header's (damaged)")
    # 5. release.json.
    jb = blob[joff:joff + jsize]
    try:
        meta = json.loads(jb.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise ValueError("5: release.json doesn't parse: %s" % e)
    if not isinstance(meta, dict):
        raise ValueError("5: release.json is not one object")
    p = field_problems(meta)
    if p:
        raise ValueError("5: " + p[0])
    if (meta["format"]["major"], meta["format"]["minor"]) != (major, minor):
        raise ValueError("5: release.json's format %r is not the header's %d.%d" % (meta["format"], major, minor))
    if meta["kind"] != "app":
        raise ValueError("5: kind %r, not an app release" % meta["kind"])
    if TARGET not in meta["targets"]:
        raise ValueError("5: not a release for %s" % TARGET)
    # 6. The image.
    image = blob[ioff:ioff + isize]
    if meta["image"]["size"] != isize or hashlib.sha256(image).hexdigest() != meta["image"]["sha256"]:
        raise ValueError("6: the image's size or SHA-256 is not release.json's")
    # 7. Where it loads and starts.
    if meta["image"]["load_address"] != LOAD_ADDRESS or meta["image"]["entry"] != ENTRY:
        raise ValueError("7: load address or entry is not 0x02000000")
    return meta, jb, image


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--unpack")
    a = ap.parse_args()
    with open(a.file, "rb") as f:
        blob = f.read()
    try:
        meta, jb, image = check(blob)
    except ValueError as e:
        print("fm1img: FAIL at check %s" % e)
        return 1
    print("fm1img: OK: %s %s (%s), %d bytes, SHA-256 %s"
          % (meta["name"], meta["version"], meta["git_commit"][:12], len(image), meta["image"]["sha256"]))
    if a.unpack:
        os.makedirs(a.unpack, exist_ok=True)
        for n, b in (("release.json", jb), (meta["image"]["file"], image)):
            with open(os.path.join(a.unpack, n), "wb") as f:
                f.write(b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
