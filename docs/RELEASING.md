<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Releasing (M9: the app release)

How an app release is cut, checked and loaded into the F-Emulator app.
The format (`release.json` and the `.fm1img`, format 1.0): docs/M9-PLAN.md,
section 1, "The release format" (the spec side's, pull request #136).
The plan and the owner's answers: the same document. A hardware package
(`.fwsc`) is not this: it waits for M10.

## What a release holds

| File | What |
|------|------|
| `small-beeps-X.Y.Z.fm1img` | the one file a user needs: `release.json` and the raw image in one container (tools/fm1img.py reads and checks it as the app does) |
| `small-beeps-X.Y.Z.bin` | the raw image, byte for byte the build's `app.bin`, linked at `0x02000000` |
| `release.json` | the metadata, byte for byte the copy in the `.fm1img` |
| `small-beeps-X.Y.Z.elf` | the same build's ELF, for symbols |
| `small-beeps-X.Y.Z.spdx.json` | an SPDX 2.3 SBOM: the firmware, the SDK headers, the toolchain (a build tool), each source file of the image with its SHA-256 |
| `LICENSE`, `NOTICE` | as at the tag |
| `SHA256SUMS` | every file above, in `sha256sum`'s format |

Every file comes from the tag, its build and its test record only (no
time of day, no host, no path; the SBOM's one date is the tag's commit's),
so the same tag gives the same bytes (R-REL-1).

## Cutting one (the owner)

1. **The milestone is merged** and its merge commit's record on the
   `records` branch is written, overall PASS (records.yml, then the
   audit; `tools/reproduce <commit>` says REPRODUCED).
2. **Its version is listed.** A pull request adds the tag and its version
   to `config/releases.json` (`"m9": "0.9.0"` is there already). A tag not
   listed gets no release.
3. **Sign and push the tag** on that commit, as CONTRIBUTING.md says
   ("SSH signing for milestone tags"): `git tag -s m9 -m "m9"`, then
   `git push origin m9`. GitHub must show it as **Verified**.
4. **The release workflow** (`.github/workflows/release.yml`) runs on the
   tag's push. It:
   - checks the tag is annotated and that GitHub verifies its signature,
     and refuses it otherwise;
   - takes the version from `config/releases.json` (main's);
   - reads the record `records/<commit>/report.json` from the records
     branch, and the SHA-256 of the record's `SHA256SUMS`
     (`record.tree_sha256`; the audit adds files beside it later, never to
     it);
   - exports the tag's files (`tools/reproduce`'s way: never the
     spec-side folders) and builds them twice with the tag's own
     `tools/build.sh`, at two source paths: the same bytes, and the
     record's;
   - asks the record's fwtest image for its version;
   - runs `tools/release.py build` twice (the same bytes), then
     `tools/release.py verify` and `tools/fm1img.py` (the app's checks, in
     the app's order);
   - uploads the files as the run's artifact, then attaches them to the
     tag's GitHub release. If the release doesn't exist yet it makes it,
     as a **draft**, with `gh release create --verify-tag`, which refuses
     to make a tag. It never replaces a file a release already has.
5. **Publish the draft** after a look: its title, the notes (they list
   SHA256SUMS), the files. Add the milestone's own notes as for m0
   and m1 if wanted.

If the record wasn't written yet when the tag was pushed, the run fails
at "no record": run the workflow again by hand (Actions, "release",
"Run workflow", the tag, "publish" ticked) once the record is there. The
same by hand works for any listed, signed tag; with "publish" unticked
it only makes the artifact.

Tags m2 and later were not signed when this was written (2026-10-26),
and none is listed in `config/releases.json`, so none gets a release
until the owner signs it and lists it. The m0 and m1 releases were made
by hand and are left as they are.

## Checking one (anyone)

From a folder with the release's files:

```sh
sha256sum -c SHA256SUMS                         # every file as listed
python3 tools/fm1img.py small-beeps-0.9.0.fm1img  # the app's checks, in its order
python3 tools/release.py verify .               # release.json as format 1.0 writes it, the
                                                # .fm1img's parts the loose files, SHA256SUMS
```

Then check it is the tag's build:

- `release.json`'s `git_commit` is the tag's commit
  (`git rev-parse m9^{commit}`), and `git tag -v m9` shows the owner's
  good signature;
- `tools/reproduce <git_commit>` rebuilds it, and the image's SHA-256 is
  `image.sha256`;
- the record: the SHA-256 of `records/<git_commit>/SHA256SUMS` on the
  `records` branch is `record.tree_sha256`, and its `report.json` says
  PASS.

Or make the whole release again, byte for byte:
`tools/release.sh m9 --out DIR`, then compare the two folders. In a clean
folder, which never fetches the records branch and of a record fetches
only `report.json`, `report.md` and logs, give `--report` (that
`report.json`, fetched by name) and `--record-sums-sha256` (the
release's `record.tree_sha256`).

## Loading one into the app

The F-Emulator app boots a raw image (docs/EMULATOR-PARITY.md). Either:

- **The single file:** open `small-beeps-X.Y.Z.fm1img` (Files, AirDrop,
  Mail, a download: one tap, once the app declares the type,
  docs/M9-PLAN.md, "Opening it in one tap"). The app runs the format's
  seven checks in order ("How the app verifies it"; `tools/fm1img.py` is
  the reference), shows the name, the version and the commit's first 12
  digits, and boots the image at `0x02000000`.
- **The bare image**, as before: `small-beeps-X.Y.Z.bin` alone, unchecked,
  no version shown.

Reading the `.fm1img` is the app's change, the owner's to make
(docs/M9-PLAN.md, the owner's answer 1); until then the bare image works
as it always has.

Saved patches: `store.format_version`, `store.offset` and `store.size` say
where the release keeps them; a release with the same store format reads
the patches an earlier one saved.
