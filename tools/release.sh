#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Makes the app release of a signed milestone tag (docs/RELEASING.md;
# R-REL-1 to R-REL-3), the way .github/workflows/release.yml does:
#
#   tools/release.sh TAG --out DIR [--version X.Y.Z]
#                    [--records-ref REF | --report FILE --record-sums-sha256 HEX]
#
# 1. TAG must be an annotated tag that GitHub shows as Verified (signed by
#    a key of its tagger's account; the GitHub API, through gh). It never
#    makes a tag.
# 2. The version comes from config/releases.json (this folder's), unless
#    --version is given (a dry run for a tag that has none yet).
# 3. The tag's commit's test record: records/<commit>/report.json on REF
#    (by default origin/records), and the SHA-256 of that record's
#    SHA256SUMS (release.json's record.tree_sha256, docs/M9-PLAN.md); or,
#    in a clean folder (which never fetches the records branch, and of a
#    record fetches only report.json, report.md and logs), the report
#    fetched by name and that hash given (a milestone's release notes
#    state it).
# 4. The tag's files, exported as tools/reproduce does (never the
#    spec-side folders), built twice by their own tools/build.sh at two
#    source paths: the same bytes both times, and the record's. In CI
#    (GITHUB_ACTIONS) the build's identity comes first (config/build-image,
#    main's; the owner's answer, 2026-10-27): the tag's tools/Dockerfile
#    must have the SHA-256, the base image digest and the toolchain
#    SHA-256 it names, or the release stops; the image is then built fresh
#    from that Dockerfile (it is never published), and release.json's
#    build.container records the identity (`build-identity:...`). Run by
#    hand it is a local dry run: the local image, its ID in
#    build.container behind `local-dry-run:` (the owner's answer,
#    2026-10-26; docs/RELEASING.md, "The build image").
# 5. fwtest's version: the record's fwtest image, asked (tools/fwtest).
# 6. tools/release.py build, twice: the same bytes; then verify.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PY=$(sh "$ROOT/tools/find-python.sh")
tag="" out="" version="" ref=origin/records report="" sums=""
while [ $# -gt 0 ]; do
    case "$1" in
        --out) out=$2; shift 2 ;;
        --version) version=$2; shift 2 ;;
        --records-ref) ref=$2; shift 2 ;;
        --report) report=$2; shift 2 ;;
        --record-sums-sha256) sums=$2; shift 2 ;;
        -*) echo "unknown option $1" >&2; exit 2 ;;
        *) tag=$1; shift ;;
    esac
done
[ -n "$tag" ] && [ -n "$out" ] || { echo "usage: $0 TAG --out DIR [...]" >&2; exit 2; }
fail() { echo "release: $*" >&2; exit 1; }

# 1. A signed tag, verified by GitHub.
[ "$(git -C "$ROOT" cat-file -t "refs/tags/$tag" 2>/dev/null)" = tag ] || fail "$tag is not an annotated tag here"
commit=$(git -C "$ROOT" rev-parse --verify "refs/tags/$tag^{commit}")
repo=${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}
tag_sha=$(gh api "repos/$repo/git/ref/tags/$tag" --jq '.object.sha')
[ "$tag_sha" = "$(git -C "$ROOT" rev-parse "refs/tags/$tag")" ] || fail "$tag here is not GitHub's $tag"
verified=$(gh api "repos/$repo/git/tags/$tag_sha" --jq '.verification.verified')
[ "$verified" = true ] || fail "$tag is not signed and verified on GitHub ($(gh api "repos/$repo/git/tags/$tag_sha" --jq '.verification.reason'))"
echo "tag:     $tag ($tag_sha), verified; commit $commit"

# 2. Its version.
if [ -z "$version" ]; then
    version=$("$PY" -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["versions"].get(sys.argv[2], ""))' \
        "$ROOT/config/releases.json" "$tag")
    [ -n "$version" ] || fail "config/releases.json gives $tag no version"
fi
echo "version: $version"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# 3. The record.
if [ -z "$report" ]; then
    git -C "$ROOT" show "$ref:records/$commit/report.json" > "$work/report.json" \
        || fail "no record of $commit on $ref"
    git -C "$ROOT" show "$ref:records/$commit/SHA256SUMS" > "$work/record.sums" \
        || fail "the record of $commit on $ref has no SHA256SUMS"
    sums=$("$PY" -I -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' \
        "$work/record.sums")
    report=$work/report.json
fi
[ -n "$sums" ] || fail "--report needs --record-sums-sha256"
echo "record:  records/$commit/, its SHA256SUMS $sums"

# 4. The tag's files, built twice; in CI from the build's identity.
sh "$ROOT/tools/reproduce" --export-only "$commit" "$work/src"
itag=$(sh "$work/src/tools/build.sh" image-tag)
if [ "${GITHUB_ACTIONS:-}" = true ]; then
    # The build's identity (config/build-image, main's; the owner's answer,
    # 2026-10-27): the tag's Dockerfile must be the one it names, with its
    # base image and toolchain, before anything is built. The image is then
    # built fresh from it, never pulled.
    ident() { awk -v k="$1" '$1 == k { print $2 }' "$ROOT/config/build-image"; }
    base=$(ident base) dockerfile=$(ident dockerfile) toolchain=$(ident toolchain)
    [ -n "$base" ] && [ -n "$dockerfile" ] && [ -n "$toolchain" ] \
        || fail "config/build-image gives no build identity (base, dockerfile, toolchain)"
    have=$("$PY" -I -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' \
        "$work/src/tools/Dockerfile")
    [ "$have" = "$dockerfile" ] || fail "$tag's tools/Dockerfile has SHA-256 $have, not the build identity's $dockerfile"
    have=$(sed -n 's/^ARG BASE=//p' "$work/src/tools/Dockerfile" | head -1)
    [ "$have" = "$base" ] || fail "$tag's tools/Dockerfile builds on ${have:-(none)}, not the build identity's $base"
    have=$(sed -n 's/^ARG TOOLCHAIN_SHA256=//p' "$work/src/tools/Dockerfile" | head -1)
    [ "$have" = "$toolchain" ] || fail "$tag's tools/Dockerfile checks the toolchain against ${have:-(none)}, not the build identity's $toolchain"
    echo "identity: base $base, Dockerfile $dockerfile, toolchain $toolchain: $tag's"
    sh "$work/src/tools/build.sh" image
    container=build-identity:dockerfile-sha256=$dockerfile,toolchain-sha256=$toolchain,base=$base
fi
sh "$work/src/tools/build.sh" build --out "$work/b1"
sh "$work/src/tools/build.sh" build --out "$work/b2" --src-mount /tmp/elsewhere/small-beeps-src-b
if [ "${GITHUB_ACTIONS:-}" != true ]; then
    container=local-dry-run:$(docker image inspect --format '{{.Id}}' "$itag")
    echo "DRY RUN: built in the local image $itag; release.json's build.container says so, and it is never published"
fi
echo "build:   $container"
cmp "$work/b1/app.bin" "$work/b2/app.bin" || fail "the two builds differ"

# 5. fwtest's version, of the image the record names.
fwimage=$("$PY" -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["environment"]["fwtest_image"])' "$report")
fwver=$(FWTEST_IMAGE=$fwimage sh "$ROOT/tools/fwtest" version)
echo "fwtest:  $fwver ($fwimage)"

# 6. The release, twice.
created=$(TZ=UTC git -C "$ROOT" log -1 --date=format-local:%Y-%m-%dT%H:%M:%SZ --format=%cd "$commit")
for d in r1 r2; do
    "$PY" -I "$ROOT/tools/release.py" build --tag "$tag" --version "$version" --commit "$commit" \
        --src "$work/src" --build "$work/b1" --report "$report" --record-sums-sha256 "$sums" \
        --fwtest-version "$fwver" --created "$created" --build-container "$container" --out "$work/$d"
done
diff -r "$work/r1" "$work/r2" >/dev/null || fail "the two releases differ"
"$PY" -I "$ROOT/tools/release.py" verify "$work/r1"
"$PY" -I "$ROOT/tools/fm1img.py" "$work/r1/small-beeps-$version.fm1img"
mkdir -p "$out"
cp "$work/r1/"* "$out/"
echo "release: $out"
cat "$out/SHA256SUMS"
