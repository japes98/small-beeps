# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import argparse
import hashlib
import json
import os
import struct
import tempfile
import unittest

from tests.helpers import ROOT, load_tool

rel = load_tool("release.py")
fm = load_tool("fm1img.py")


def fake_build(d, image=b"\x01\x02\x03" * 1000):
    os.makedirs(d)
    for n, b in (("app.bin", image), ("app.elf", b"elf" + image)):
        with open(os.path.join(d, n), "wb") as f:
            f.write(b)
    with open(os.path.join(d, "app.size"), "w") as f:
        f.write("code 3000\ndata 80\nbss 1000\nimage 3000\nstack 4096\nirq_stack 2048\nram_code 3000\n")


def report_of(build, commit, overall="PASS"):
    sha = lambda n: hashlib.sha256(open(os.path.join(build, n), "rb").read()).hexdigest()
    return {"commit": commit, "overall": overall, "outputs": {"app.bin": sha("app.bin"), "app.elf": sha("app.elf")},
            "environment": {"build_image_id": "sha256:" + "b" * 64,
                            "github": {"GITHUB_REPOSITORY": "o/r", "GITHUB_RUN_ID": "42"}}}


class ReleaseTest(unittest.TestCase):
    """Requirements: R-REL-1, R-REL-2"""

    COMMIT = "1" * 40
    PINNED = ("build-identity:dockerfile-sha256=" + "5" * 64 + ",toolchain-sha256=" + "7" * 64
              + ",base=debian:bookworm-slim@sha256:" + "8" * 64)

    def make(self, d, name, report=None, version="0.9.0", container=PINNED):
        build = os.path.join(d, "build")
        if not os.path.exists(build):
            fake_build(build)
        rp = os.path.join(d, "report-%s.json" % name)
        with open(rp, "w") as f:
            json.dump(report or report_of(build, self.COMMIT), f)
        a = argparse.Namespace(tag="m9", version=version, commit=self.COMMIT, src=ROOT, build=build, report=rp,
                               record_sums_sha256="3" * 64, fwtest_version="fwtest 0.6.0 (emulator 43ed55800648)",
                               created="2026-10-26T00:00:00Z", build_container=container, out=os.path.join(d, name))
        return rel.build(a), a.out

    def test_reproducible_byte_for_byte_and_verified(self):
        with tempfile.TemporaryDirectory() as d:
            p1, o1 = self.make(d, "one")
            p2, o2 = self.make(d, "two")
            self.assertEqual((p1, p2), ([], []))
            self.assertEqual(rel.same_tree(o1, o2), [])
            self.assertEqual(rel.verify(o1), [])
            self.assertEqual(sorted(os.listdir(o1)), sorted(
                ["SHA256SUMS", "release.json", "LICENSE", "NOTICE", "small-beeps-0.9.0.bin",
                 "small-beeps-0.9.0.elf", "small-beeps-0.9.0.fm1img", "small-beeps-0.9.0.spdx.json"]))

    def test_hashes_match_and_the_format_holds(self):
        with tempfile.TemporaryDirectory() as d:
            _, o = self.make(d, "one")
            mb = open(os.path.join(o, "release.json"), "rb").read()
            meta = json.loads(mb)
            image = open(os.path.join(o, "small-beeps-0.9.0.bin"), "rb").read()
            self.assertEqual(image, open(os.path.join(d, "build", "app.bin"), "rb").read())
            self.assertEqual(meta["image"]["sha256"], hashlib.sha256(image).hexdigest())
            self.assertEqual(meta["image"]["size"], len(image))
            self.assertEqual(fm.field_problems(meta, writer=True), [])
            self.assertEqual(mb, (json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode())
            self.assertEqual((meta["format"], meta["kind"], meta["image"]["load_address"], meta["image"]["entry"]),
                             ({"major": 1, "minor": 0}, "app", 0x02000000, 0x02000000))
            self.assertEqual((meta["fwtest"]["version"], meta["record"]["ci_run"]),
                             ("0.6.0", "https://github.com/o/r/actions/runs/42"))
            self.assertEqual(meta["store"], {"format_version": 1, "offset": 0xFC000, "size": 0x3000})
            m2, jb, ib = fm.check(open(os.path.join(o, "small-beeps-0.9.0.fm1img"), "rb").read())
            self.assertEqual((jb, ib), (mb, image))
            sums = open(os.path.join(o, "SHA256SUMS")).read().splitlines()
            self.assertIn("%s  small-beeps-0.9.0.fm1img" % hashlib.sha256(
                open(os.path.join(o, "small-beeps-0.9.0.fm1img"), "rb").read()).hexdigest(), sums)

    def test_a_tampered_file_fails_verify(self):
        with tempfile.TemporaryDirectory() as d:
            _, o = self.make(d, "one")
            p = os.path.join(o, "small-beeps-0.9.0.bin")
            b = bytearray(open(p, "rb").read())
            b[10] ^= 1
            open(p, "wb").write(bytes(b))
            self.assertTrue(rel.verify(o))

    def test_refuses_a_failed_or_foreign_record_and_another_build(self):
        with tempfile.TemporaryDirectory() as d:
            fake_build(os.path.join(d, "build"))
            r = report_of(os.path.join(d, "build"), self.COMMIT, overall="FAIL")
            self.assertTrue(self.make(d, "a", r)[0])
            r = report_of(os.path.join(d, "build"), "4" * 40)
            self.assertTrue(self.make(d, "b", r)[0])
            r = report_of(os.path.join(d, "build"), self.COMMIT)
            r["outputs"]["app.bin"] = "0" * 64
            self.assertTrue(self.make(d, "c", r)[0])
            self.assertTrue(self.make(d, "e", version="0.9")[0])
            self.assertFalse(os.path.exists(os.path.join(d, "a")))

    def test_a_writer_writes_only_format_1_0s_fields(self):
        with tempfile.TemporaryDirectory() as d:
            _, o = self.make(d, "one")
            meta = json.load(open(os.path.join(o, "release.json")))
        for change in (lambda m: m.pop("git_commit"), lambda m: m.update(extra=1),
                       lambda m: m["image"].update(size="12"), lambda m: m["image"].update(load_address="0x2"),
                       lambda m: m.update(version="v0.9.0"), lambda m: m["record"].update(tree_sha256="x")):
            m = json.loads(json.dumps(meta))
            change(m)
            self.assertTrue(fm.field_problems(m, writer=True), m)
        m = json.loads(json.dumps(meta))
        m["later"] = 1                        # a reader ignores a field it doesn't know
        self.assertEqual(fm.field_problems(m), [])

    def test_the_build_image_a_ci_release_names_and_a_dry_runs_mark(self):
        # The owner's answers: in CI the build's identity, recorded
        # (2026-10-27); a local image's ID only in a local dry run, marked
        # as one, and never published (2026-10-26).
        with tempfile.TemporaryDirectory() as d:
            p, o = self.make(d, "ci")
            self.assertEqual(p, [])
            self.assertEqual(json.load(open(os.path.join(o, "release.json")))["build"]["container"], self.PINNED)
            self.assertEqual(rel.verify(o, publish=True), [])
            local = rel.DRY_RUN + "sha256:" + "6" * 64
            p, o = self.make(d, "local", container=local)
            self.assertEqual(p, [])
            self.assertEqual(json.load(open(os.path.join(o, "release.json")))["build"]["container"], local)
            self.assertEqual(rel.verify(o), [])
            self.assertIn("dry run", " ".join(rel.verify(o, publish=True)))
            for bad in ("sha256:" + "6" * 64, "small-beeps-build:2f1adc7009fddc03", "ghcr.io/o/r-build:latest",
                        "ghcr.io/o/r-build@sha256:" + "5" * 64, self.PINNED.replace(",base=", ",")):
                self.assertTrue(self.make(d, "bad", container=bad)[0], bad)
            self.assertFalse(os.path.exists(os.path.join(d, "bad")))

    def test_the_build_identity_is_this_trees_own(self):
        # config/build-image (the owner's answer, 2026-10-27): the base
        # image's digest, the Dockerfile's SHA-256 and the toolchain's, as
        # tools/Dockerfile and docs/TOOLCHAIN.md have them.
        with open(os.path.join(ROOT, "config", "build-image")) as f:
            pin = dict(l.split() for l in f if l.strip() and not l.startswith("#"))
        self.assertEqual(sorted(pin), ["base", "dockerfile", "toolchain"])
        df = open(os.path.join(ROOT, "tools", "Dockerfile"), "rb").read()
        self.assertEqual(pin["dockerfile"], hashlib.sha256(df).hexdigest())
        self.assertIn(("\nARG BASE=%s\n" % pin["base"]).encode(), df)
        self.assertIn(("\nARG TOOLCHAIN_SHA256=%s\n" % pin["toolchain"]).encode(), df)
        self.assertIn(pin["toolchain"], open(os.path.join(ROOT, "docs", "TOOLCHAIN.md")).read())
        self.assertTrue(rel.IDENTITY_REF.match("%sdockerfile-sha256=%s,toolchain-sha256=%s,base=%s" % (
            rel.IDENTITY, pin["dockerfile"], pin["toolchain"], pin["base"])))

    def test_releases_list_starts_at_0_9_0(self):
        v = json.load(open(os.path.join(ROOT, "config", "releases.json")))["versions"]
        self.assertEqual(v.get("m9"), "0.9.0")
        self.assertTrue(all(tuple(map(int, x.split("."))) >= (0, 9, 0) for x in v.values()))


class ReaderTest(unittest.TestCase):
    """The .fm1img reference reader: the app's checks, in order.
    Requirements: R-REL-2"""

    def release(self, **meta_changes):
        image = bytes(range(256)) * 4
        meta = {"format": {"major": 1, "minor": 0}, "kind": "app", "name": "small-beeps", "version": "0.9.0",
                "tag": "m9", "git_commit": "1" * 40, "targets": ["f-emulator-app"],
                "image": {"file": "small-beeps-0.9.0.bin", "size": len(image),
                          "sha256": hashlib.sha256(image).hexdigest(), "load_address": 33554432, "entry": 33554432},
                "fwtest": {"version": "0.6.0", "image": "x@sha256:" + "a" * 64}, "record": {"tree_sha256": "c" * 64}}
        for k, v in meta_changes.items():
            meta[k] = v
        return fm.pack(fm.dumps(meta), image), image

    def first_failure(self, blob):
        try:
            fm.check(blob)
            return None
        except ValueError as e:
            return str(e).split(":")[0]

    def test_a_good_one_and_its_layout(self):
        blob, image = self.release()
        meta, jb, ib = fm.check(blob)
        self.assertEqual(ib, image)
        magic, major, minor, hs, jo, js, io, isz, digest = struct.unpack_from("<8sHHIIIII32s", blob)
        self.assertEqual((magic, major, minor, hs, jo), (b"FM1IMG\r\n", 1, 0, 64, 64))
        self.assertEqual((io % 16, io >= jo + js, io + isz), (0, True, len(blob)))
        self.assertEqual(digest, hashlib.sha256(blob[64:]).digest())

    def test_each_check_in_its_order(self):
        blob, _ = self.release()
        self.assertEqual(self.first_failure(b"FM1IMG\r\n" + b"\0" * 50), "1")
        self.assertEqual(self.first_failure(b"NOTIMG\r\n" + blob[8:]), "1")
        self.assertEqual(self.first_failure(blob[:8] + struct.pack("<H", 2) + blob[10:]), "2")
        self.assertEqual(self.first_failure(blob + b"\0"), "3")
        self.assertEqual(self.first_failure(blob[:-1]), "3")
        damaged = bytearray(blob)
        damaged[-1] ^= 1
        self.assertEqual(self.first_failure(bytes(damaged)), "4")
        self.assertEqual(self.first_failure(self.release(kind="hardware")[0]), "5")
        self.assertEqual(self.first_failure(self.release(targets=["elsewhere"])[0]), "5")
        self.assertEqual(self.first_failure(self.release(format={"major": 1, "minor": 1})[0]), "5")
        good, image = self.release()
        meta = json.loads(fm.check(good)[1])
        meta["image"]["sha256"] = "0" * 64
        self.assertEqual(self.first_failure(fm.pack(fm.dumps(meta), image)), "6")
        meta = json.loads(fm.check(good)[1])
        meta["image"]["entry"] = 0
        self.assertEqual(self.first_failure(fm.pack(fm.dumps(meta), image)), "7")


class WorkflowTest(unittest.TestCase):
    """Requirements: R-REL-3"""

    def test_never_makes_a_tag_and_checks_the_signature(self):
        wf = open(os.path.join(ROOT, ".github", "workflows", "release.yml")).read()
        sh = open(os.path.join(ROOT, "tools", "release.sh")).read()
        self.assertIn("gh release create \"$TAG\" --verify-tag --draft", wf)
        self.assertNotIn("git tag ", wf + sh)
        self.assertNotIn("git push", wf + sh)
        self.assertNotIn("--clobber", wf)
        self.assertIn(".verification.verified", sh)

    def test_a_tag_not_listed_is_skipped_with_a_notice(self):
        # The owner's answer (2026-10-26): m2 to m8 get no versions; their
        # tags' runs succeed, saying why nothing was built.
        wf = open(os.path.join(ROOT, ".github", "workflows", "release.yml")).read()
        build = wf[wf.index("\n  build:"):wf.index("\n  publish:")]
        steps = build.split("\n      - ")[1:]
        tag = [i for i, st in enumerate(steps) if st.startswith("name: The tag")][0]
        self.assertIn("config/releases.json", steps[tag])
        self.assertIn("::notice::", steps[tag])
        self.assertIn('echo "skip=true" >> "$GITHUB_OUTPUT"\n            exit 0', steps[tag])
        self.assertLess(steps[tag].index("skip=true"), steps[tag].index("git fetch"))
        for st in steps[tag + 1:]:
            self.assertIn("if: steps.tag.outputs.skip == 'false'", st, st.splitlines()[0])
        self.assertIn("if: needs.build.outputs.skip == 'false' &&", wf[wf.index("\n  publish:"):])

    def test_ci_checks_the_build_identity_first_and_publishes_only_its_releases(self):
        wf = open(os.path.join(ROOT, ".github", "workflows", "release.yml")).read()
        sh = open(os.path.join(ROOT, "tools", "release.sh")).read()
        self.assertIn('"$ROOT/config/build-image"', sh)
        self.assertIn('if [ "${GITHUB_ACTIONS:-}" = true ]', sh)
        ci = sh[sh.index('if [ "${GITHUB_ACTIONS:-}" = true ]'):]
        for check in ("$dockerfile", "$base", "$toolchain"):
            self.assertLess(ci.index('fail "$tag\'s tools/Dockerfile'), ci.index('build.sh" image'), check)
            self.assertIn('= "%s" ] || fail' % check, ci)
        self.assertLess(ci.index('build.sh" image'), ci.index('build.sh" build'))
        self.assertNotIn("docker pull", sh)
        self.assertIn("container=build-identity:", sh)
        self.assertIn('--build-container "$container"', sh)
        self.assertIn("container=local-dry-run:", sh)
        pub = wf[wf.index("\n  publish:"):]
        self.assertLess(pub.index("build-identity:*) ;;"), pub.index("gh release upload"))


if __name__ == "__main__":
    unittest.main()
