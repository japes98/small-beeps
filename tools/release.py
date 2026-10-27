#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""M9's app release (docs/RELEASING.md; docs/M9-PLAN.md, section 1, "The
release format", format 1.0; R-REL-1 to R-REL-3): the files a release of
a signed milestone tag carries, for the F-Emulator app.

  release.py build --tag TAG --version X.Y.Z --commit SHA --src DIR
                   --build DIR --report REPORT.json --record-sums-sha256 HEX
                   --fwtest-version "fwtest 0.6.0 (...)" --created TIME
                   --build-container REF --out DIR
      DIR gets the release's files (files() below): the raw image (the
      build's app.bin, byte for byte), its ELF, release.json, the
      .fm1img holding both (tools/fm1img.py), an SPDX 2.3 SBOM, the
      licence and notices as at the tag, and SHA256SUMS. SRC is the tag's
      files (tools/reproduce --export-only), BUILD its tools/build.sh
      output, REPORT the tag's commit's test record
      (records/<commit>/report.json), RECORD-SUMS-SHA256 the SHA-256 of
      that record's SHA256SUMS (the format's record.tree_sha256), TIME the
      tag's commit's time (the SBOM's only date), REF the build image
      the image was built in (build.container): in CI the one pinned by
      registry digest (`ghcr.io/...@sha256:<64 hex>`), in a local dry run
      `local-dry-run:` and the local image's ID (the owner's answer,
      2026-10-26). Stops if the record is not PASS, is another commit's,
      or names other outputs than the build's.
  release.py verify [--publish] DIR
      Checks a release folder: release.json (format 1.0's fields, as a
      writer must write them, and its exact bytes), the .fm1img by the
      app's checks in order (tools/fm1img.py), its release.json and image
      byte for byte the loose files, and SHA256SUMS. With --publish also
      that it was built in a build image pinned by registry digest (a
      local dry run is never published).
  release.py selftest --build DIR --out DIR
      C-RELEASE: a release made twice from build DIR with a stand-in
      record (this tree's own files), byte for byte the same, verified.

Everything in it comes from its inputs: no clock, no host, no path. The
same tag, build and record give the same bytes (R-REL-1).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fm1img  # noqa: E402  (tools/, our own)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "small-beeps"
REPO = "https://github.com/japes98/small-beeps"


# build.container (the owner's answer, 2026-10-26): a release built in CI
# names the build image pinned by registry digest; one built locally names
# the local image's ID behind DRY_RUN, a dry run's mark, and is never
# published (verify(publish=True)). Format 1.0 lets a writer add no field,
# so the mark is in the value.
REGISTRY_REF = re.compile(r"^[a-z0-9.-]+(/[a-z0-9._-]+)+@sha256:[0-9a-f]{64}$")
DRY_RUN = "local-dry-run:"
LOCAL_ID = re.compile(r"^" + DRY_RUN + r"sha256:[0-9a-f]{64}$")


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def read(path):
    with open(path, "rb") as f:
        return f.read()


def files(version):
    """The release's files, by kind."""
    return {"bin": "%s-%s.bin" % (NAME, version), "elf": "%s-%s.elf" % (NAME, version),
            "fm1img": "%s-%s.fm1img" % (NAME, version), "sbom": "%s-%s.spdx.json" % (NAME, version),
            "json": "release.json", "license": "LICENSE", "notice": "NOTICE"}


def sizes(build):
    with open(os.path.join(build, "app.size")) as f:
        return {k: int(v) for k, v in (l.split() for l in f if l.strip())}


def store_format(src):
    """The store's format version and region, from the tag's
    docs/STORE-FORMAT.md (its title and its region's line), or None for a
    tag before M7."""
    path = os.path.join(src, "docs", "STORE-FORMAT.md")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        text = f.read()
    v = re.search(r"^# The store's format, version (\d+)", text, re.M)
    r = re.search(r"Chip offsets `(0x[0-9A-Fa-f]+)` to `(0x[0-9A-Fa-f]+)`", text)
    if not v or not r:
        raise ValueError("docs/STORE-FORMAT.md: no version or region found")
    first, last = int(r.group(1), 16), int(r.group(2), 16)
    return {"format_version": int(v.group(1)), "offset": first, "size": last + 1 - first}


def fwtest_image(src):
    with open(os.path.join(src, "config", "fwtest-image")) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")][0]


def toolchain_sha256(src):
    with open(os.path.join(src, "tools", "Dockerfile")) as f:
        m = re.search(r"TOOLCHAIN_SHA256=([0-9a-f]{64})", f.read())
    return m.group(1) if m else None


def check_record(report, commit, outputs):
    """Problems of a test record against the build it is to vouch for."""
    p = []
    if report.get("commit") != commit:
        p.append("the record is of %s, not %s" % (report.get("commit"), commit))
    if report.get("overall") != "PASS":
        p.append("the record's overall result is %s, not PASS" % report.get("overall"))
    for name in ("app.bin", "app.elf"):
        if report.get("outputs", {}).get(name) != outputs.get(name):
            p.append("%s: the build's SHA-256 %s, the record's %s (not reproduced)"
                     % (name, outputs.get(name), report.get("outputs", {}).get(name)))
    return p


def metadata(a, image, report, src, size):
    """release.json, format 1.0."""
    env = report.get("environment", {})
    gh = env.get("github", {})
    fw = re.match(r"fwtest (\S+)", a.fwtest_version)
    meta = {
        "format": {"major": fm1img.FORMAT_MAJOR, "minor": fm1img.FORMAT_MINOR},
        "kind": "app",
        "name": NAME,
        "version": a.version,
        "tag": a.tag,
        "git_commit": a.commit,
        "targets": [fm1img.TARGET],
        "image": {"file": files(a.version)["bin"], "size": len(image), "sha256": sha256(image),
                  "load_address": fm1img.LOAD_ADDRESS, "entry": fm1img.ENTRY},
        "fwtest": {"version": fw.group(1) if fw else a.fwtest_version, "image": fwtest_image(src)},
        "record": {"tree_sha256": a.record_sums_sha256},
        "build": {"ram_used": size["data"] + size["bss"] + size["stack"] + size["irq_stack"]},
    }
    if gh.get("GITHUB_RUN_ID") and gh.get("GITHUB_REPOSITORY"):
        meta["record"]["ci_run"] = "https://github.com/%s/actions/runs/%s" % (gh["GITHUB_REPOSITORY"],
                                                                            gh["GITHUB_RUN_ID"])
    if toolchain_sha256(src):
        meta["build"]["toolchain_sha256"] = toolchain_sha256(src)
    meta["build"]["container"] = a.build_container
    store = store_format(src)
    if store:
        meta["store"] = store
    return meta


def sbom(meta, src, created):
    """An SPDX 2.3 SBOM: the firmware, the SDK headers it is built with,
    the toolchain (a build tool), and every source file of the image.
    Its one date is the tag's commit's (created), so it is reproducible."""
    names = ["firmware/app.ld"] + sorted("firmware/src/" + n for n in os.listdir(os.path.join(src, "firmware", "src")))
    names = [n for n in names if os.path.isfile(os.path.join(src, n))]
    sdk = None
    srcmd = os.path.join(src, "vendor", "jieli-sdk", "SOURCE.md")
    if os.path.exists(srcmd):
        with open(srcmd) as f:
            m = re.search(r"Commit: `([0-9a-f]{40})`", f.read())
        sdk = m.group(1) if m else None
    commit = meta["git_commit"]
    pk = [{
        "SPDXID": "SPDXRef-small-beeps", "name": NAME,
        "versionInfo": "%s (%s, %s)" % (meta["version"], meta["tag"], commit),
        "downloadLocation": "git+%s@%s" % (REPO, commit), "filesAnalyzed": False,
        "licenseConcluded": "MIT", "licenseDeclared": "MIT", "copyrightText": "Copyright (c) 2026 japes98",
        "primaryPackagePurpose": "FIRMWARE",
        "checksums": [{"algorithm": "SHA256", "checksumValue": meta["image"]["sha256"]}],
    }]
    if sdk:
        pk.append({
            "SPDXID": "SPDXRef-ac79-sdk", "name": "fw-AC79_AIoT_SDK (register-definition headers)",
            "versionInfo": sdk, "downloadLocation": "git+https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK@" + sdk,
            "filesAnalyzed": False, "licenseConcluded": "Apache-2.0", "licenseDeclared": "Apache-2.0",
            "copyrightText": "Copyright JIELI (as stated in the files' headers)", "primaryPackagePurpose": "SOURCE"})
    tc = meta.get("build", {}).get("toolchain_sha256")
    if tc:
        pk.append({
            "SPDXID": "SPDXRef-toolchain", "name": "jieli-linux-toolchains", "filesAnalyzed": False,
            "downloadLocation": "NOASSERTION", "checksums": [{"algorithm": "SHA256", "checksumValue": tc}],
            "licenseConcluded": "NOASSERTION", "licenseDeclared": "NOASSERTION", "copyrightText": "NOASSERTION",
            "comment": "Build tool only; not in the image (docs/TOOLCHAIN.md).", "primaryPackagePurpose": "APPLICATION"})
    fl = [{"SPDXID": "SPDXRef-src-%d" % i, "fileName": "./" + n,
           "checksums": [{"algorithm": "SHA256", "checksumValue": sha256(read(os.path.join(src, n)))}],
           "licenseConcluded": "MIT", "licenseInfoInFiles": ["MIT"], "copyrightText": "Copyright (c) 2026 japes98"}
          for i, n in enumerate(names)]
    rel = [{"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES",
            "relatedSpdxElement": "SPDXRef-small-beeps"}]
    rel += [{"spdxElementId": "SPDXRef-small-beeps", "relationshipType": "CONTAINS",
             "relatedSpdxElement": f["SPDXID"]} for f in fl]
    if sdk:
        rel.append({"spdxElementId": "SPDXRef-small-beeps", "relationshipType": "DEPENDS_ON",
                    "relatedSpdxElement": "SPDXRef-ac79-sdk"})
    return {
        "spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0", "SPDXID": "SPDXRef-DOCUMENT",
        "name": "%s %s" % (NAME, meta["version"]),
        "documentNamespace": "%s/releases/%s/sbom/%s" % (REPO, meta["tag"], commit),
        "creationInfo": {"created": created, "creators": ["Tool: tools/release.py"]},
        "packages": pk, "files": fl, "relationships": rel,
    }


def sums(named):
    return "".join("%s  %s\n" % (sha256(b), n) for n, b in sorted(named.items())).encode("ascii")


def build(a):
    image = read(os.path.join(a.build, "app.bin"))
    outputs = {n: sha256(read(os.path.join(a.build, n))) for n in ("app.bin", "app.elf")}
    with open(a.report) as f:
        report = json.load(f)
    problems = check_record(report, a.commit, outputs)
    if not (REGISTRY_REF.match(a.build_container) or LOCAL_ID.match(a.build_container)):
        problems.append("--build-container %s: neither a registry digest (host/name@sha256:<64 hex>) nor %s"
                        "sha256:<64 hex>" % (a.build_container, DRY_RUN))
    if problems:
        return problems
    meta = metadata(a, image, report, a.src, sizes(a.build))
    problems = fm1img.field_problems(meta, writer=True)
    if problems:
        return problems
    mb = fm1img.dumps(meta)
    fn = files(a.version)
    out = {fn["bin"]: image, fn["elf"]: read(os.path.join(a.build, "app.elf")), fn["json"]: mb,
           fn["fm1img"]: fm1img.pack(mb, image), fn["sbom"]: fm1img.dumps(sbom(meta, a.src, a.created))}
    for k in ("license", "notice"):
        if os.path.exists(os.path.join(a.src, fn[k])):
            out[fn[k]] = read(os.path.join(a.src, fn[k]))
    os.makedirs(a.out, exist_ok=True)
    out["SHA256SUMS"] = sums(out)
    for n, b in out.items():
        with open(os.path.join(a.out, n), "wb") as f:
            f.write(b)
    return []


def verify(d, publish=False):
    """Problems of a release folder (R-REL-1, R-REL-2); with publish, also
    one not built in a build image pinned by registry digest."""
    try:
        mb = read(os.path.join(d, "release.json"))
        meta = json.loads(mb)
    except (OSError, ValueError) as e:
        return ["release.json: %s" % e]
    p = fm1img.field_problems(meta, writer=True)
    if mb != fm1img.dumps(meta):
        p.append("release.json: not format 1.0's exact bytes")
    container = meta.get("build", {}).get("container", "") if isinstance(meta.get("build"), dict) else ""
    if publish and not REGISTRY_REF.match(container):
        p.append("build.container %r: %s" % (container, "a local dry run, never published" if LOCAL_ID.match(container)
                                             else "not a build image pinned by registry digest"))
    if p:
        return p
    fn = files(meta["version"])
    try:
        image = read(os.path.join(d, meta["image"]["file"]))
    except OSError:
        return ["no %s" % meta["image"]["file"]]
    try:
        _, jb, ib = fm1img.check(read(os.path.join(d, fn["fm1img"])))
        if jb != mb or ib != image:
            p.append("%s: its release.json or image is not the loose file's" % fn["fm1img"])
    except OSError:
        p.append("no %s" % fn["fm1img"])
    except ValueError as e:
        p.append("%s: check %s" % (fn["fm1img"], e))
    try:
        listed = {}
        for line in read(os.path.join(d, "SHA256SUMS")).decode("ascii").splitlines():
            h, n = line.split("  ", 1)
            listed[n] = h
    except (OSError, ValueError) as e:
        return p + ["SHA256SUMS: %s" % e]
    present = sorted(n for n in os.listdir(d) if n != "SHA256SUMS")
    if sorted(listed) != present:
        p.append("SHA256SUMS lists %s; the folder holds %s" % (sorted(listed), present))
    for n, h in listed.items():
        if os.path.exists(os.path.join(d, n)) and sha256(read(os.path.join(d, n))) != h:
            p.append("SHA256SUMS: %s does not match" % n)
    return p


def same_tree(a, b):
    na, nb = sorted(os.listdir(a)), sorted(os.listdir(b))
    if na != nb:
        return ["the two releases hold %s and %s" % (na, nb)]
    return ["%s differs between the two" % n for n in na if read(os.path.join(a, n)) != read(os.path.join(b, n))]


def selftest(a):
    """C-RELEASE: from build A, with a stand-in record of its outputs."""
    out = os.path.abspath(a.out)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    report = {"commit": "0" * 40, "overall": "PASS",
              "outputs": {n: sha256(read(os.path.join(a.build, n))) for n in ("app.bin", "app.elf")},
              "environment": {}}
    rp = os.path.join(out, "report.json")
    with open(rp, "wb") as f:
        f.write(fm1img.dumps(report))
    p = []
    for k in ("a", "b"):
        ns = argparse.Namespace(tag="m0", version="0.0.0-selftest", commit="0" * 40, src=ROOT, build=a.build,
                                report=rp, record_sums_sha256="0" * 64, fwtest_version="fwtest 0.0.0 (selftest)",
                                created="1970-01-01T00:00:00Z", build_container=DRY_RUN + "sha256:" + "0" * 64,
                                out=os.path.join(out, k))
        p += ["build %s: %s" % (k, q) for q in build(ns)]
    if not p:
        p += same_tree(os.path.join(out, "a"), os.path.join(out, "b"))
        p += verify(os.path.join(out, "a"))
        if read(os.path.join(out, "a", files("0.0.0-selftest")["bin"])) != read(os.path.join(a.build, "app.bin")):
            p.append("the release's image is not build A's app.bin")
    for q in p:
        print("FAIL: " + q)
    print("release selftest: %s" % ("FAIL" if p else "PASS (built twice, byte for byte the same; verified)"))
    return 1 if p else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    for k in ("tag", "version", "commit", "src", "build", "report", "record-sums-sha256", "fwtest-version",
              "created", "build-container", "out"):
        b.add_argument("--" + k, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--publish", action="store_true")
    v.add_argument("dir")
    s = sub.add_parser("selftest")
    s.add_argument("--build", required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest(a)
    p = build(a) if a.cmd == "build" else verify(a.dir, a.publish)
    for q in p:
        print("FAIL: " + q)
    print("release %s: %s" % (a.cmd, "FAIL" if p else "OK"))
    return 1 if p else 0


if __name__ == "__main__":
    sys.exit(main())
