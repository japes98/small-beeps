<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# The similarity audit

This repository says its firmware was written clean-room, without the FM-1's
GPL community firmwares (CONTRIBUTING.md). The audit backs that up with a
measurement. On every push to main, a CI job compares our firmware with
every FM-1 firmware repository it can find, and with an unrelated control
project, and puts the scores in the commit's record. Requirements:
R-AUDIT-1 to R-AUDIT-6 (docs/REQUIREMENTS.md).

Nobody working on this repository reads the targets. The spec side found
them from repository metadata alone. The job fetches them only inside CI,
and its logs and outputs hold scores and file names, never code. When the
job flags a pair, only an **auditor** may look (below).

## What is compared

- **Ours:** the C files under `firmware/` (`.c`, `.h`, and C++ suffixes if
  we ever have any). Assembly (`.S`) and linker scripts (`.ld`) are not
  compared: JPlag's C front end doesn't read them. `vendor/` is not ours
  and is never compared. A file of ours that JPlag cannot score at all, or
  that it matches with nothing, is compared as text too (below, "Files JPlag
  cannot score").
- **Base code:** the vendored JieLi SDK headers
  (`vendor/jieli-sdk/include_lib`), for all our files; and (since SR-4) the
  vendored Plaits (`vendor/plaits/`), only for our files under
  `firmware/demos/plaits/` (below, "Base code"). JPlag drops matches with
  base code, and the text check leaves out what is in it, so code that both
  sides took from the SDK or Plaits doesn't count against us.
- **Targets:** the C and C++ files of every target (below), at its pinned
  commit. `audit/targets.json` lists the targets; `paths` limits a target
  to some of its folders.
- **The control:** the C files of `raspberrypi/pico-examples` at tag
  `sdk-2.2.0`, commit `4c3a3dc0196dd426fddd709616d0da984e027bab`
  (BSD-3-Clause; `audit/audit.json`).

## Base code

`audit/audit.json`'s `base_code` lists the trees (since SR-4, after
spec request SR-4). Each is given to JPlag as base code (`-bc`), and to
the text check, which leaves out every piece of our text found in a base
file and never counts a file of ours that is a base file's bytes as an
exact copy. Only files with the audit's suffixes are used.

- **The JieLi SDK** (`vendor/jieli-sdk/include_lib`): for all our files.
- **Plaits** (`vendor/plaits/`, MIT, pinned upstream, R-REPRO-7): only the
  files its `SHA256SUMS` lists, each checked against its hash; a changed,
  missing or unlisted file fails the audit. It is base code **only for our
  files under `firmware/demos/plaits/`** (`only_for`), which get a JPlag
  pass of their own: with the SDK and Plaits as base code, and the control
  scored again in that pass, so their threshold is the control's longest
  match under the same base code plus the margin. The report gives each
  pass's files, base code and threshold.

**Why not Plaits for every file.** Given as base code to all our files,
Plaits shortened the longest match the self-test found for core files that
don't use it, because short runs of their tokens also occur in Plaits'
code. On 2026-10-23, against copies of our files: `src/synth.c` 262 to
134 tokens, `src/panel.c` 230 to 145, `src/input.c` 383 to 335 and
`src/audio.c` 51 to 39, so 11 of 15 files were found instead of 15. A
target that copied those files would score lower in the gate by as much.
The owner chose to keep Plaits to the demo's files.

**A core file that uses Plaits** fails the audit (C-AUDIT-BASE), rather
than getting Plaits as base code silently: a file outside
`firmware/demos/plaits/` with an `#include` that names a Plaits file
(a path with a folder in it, matched against the end of a listed path).
The owner then decides: move the file, or change `only_for` by pull
request.

## The targets, from metadata only

`tools/audit-discover.py` builds `audit/targets.json` from
`audit/discover.json`. It asks GitHub's REST API, and `git ls-remote`, for
repository names, owners, descriptions, licences, languages, fork lists and
commit and tree SHAs. It never opens a target's files, README or web pages,
and never prints a description. A target is:

- **a seed:** Felucca (`hugelton/Felucca`), dinghy (`zvenson/dinghy`), the
  `fm1-sid/` and `probes/` folders of fm1-emu
  (`joakimeriksson/fm1-emu`), M-VAVE's `m-vave/fm1_open`, and the other
  FM-1 repositories of Felucca's author (`felucca-bsp`,
  `Felucca-Engines`, `Felucca-WebApp`, `felucca-mirror`);
- **a search hit:** a repository that one of the search queries finds and
  whose description names the FM-1, Felucca, GHOULBOX or Hortator. A
  repository that only matches by name must also be written in C or C++.
  "M-VAVE" or "dinghy" alone don't count, because they also name other
  products, boats and tools. dinghy's own lineage is found through its
  fork tree, and through descriptions that name the FM-1;
- **any fork of a target, to any depth.** A fork inherits its parent's
  `paths` and licence override.

**As found on 2026-10-22:** 780 repositories, after two passes whose
search results differed a little. Of these, 516 are scored and 262 are
duplicates by tree. The other 2 are empty. Of the 516 scored, 381 are classed `gpl`, 47
`permissive`, 43 `other` and 45 `none`.

The owner chose this wide net on 2026-10-22: every FM-1 repository, not
only Felucca's and dinghy's lineage. A target that turns out to be
unrelated costs only CI minutes. A target that is missed weakens the
claim.

Each target is **pinned** at its default branch's head commit, together
with that commit's tree. The job checks both. Targets whose tree (and
`paths`) is already in the list are marked `duplicate` and not fetched
again. Seeds come first, then other repositories, then forks, so a fork
that changed nothing is covered by the repository it copies. Empty
repositories are listed as `empty`.

Each target's **licence** is classed from its metadata as `gpl` (GPL,
LGPL, AGPL), `permissive` (MIT, BSD, Apache-2.0, ISC, WTFPL, CC0 and
similar), `other` (MPL-2.0, NOASSERTION, anything else) or `none` (no
licence). fm1-emu's metadata says MIT, but `fm1-sid/` is a GPL firmware
(docs/EXPOSURE.md), so that seed is classed `gpl`. The report shows each
target's class beside its scores. A flagged pair fails the job whatever
the licence.

**Unresolved:** *Felucca Salt* and *Felucca 8 Patterns*, both named in
CONTRIBUTING.md's forbidden list. No repository for either was found from
metadata on 2026-10-22; they may be distributed only as binaries. They are
listed in `discover.json` and in every report, and the owner adds a URL if
one turns up.

**Limits:** only the default branch is pinned; work on other branches,
and code in git submodules, is not fetched. A repository that neither
search finds nor any target's fork tree reaches is missed. Repositories
deleted after pinning are reported as `not fetched`.

### Rediscovery

`.github/workflows/audit-discover.yml` runs on the first day of every month,
and on demand. It runs `tools/audit-discover.py --write`, which uses
metadata only, as above. If any target is new, gone or has moved to a new
commit, it opens an issue titled "audit: the targets have changed" that
lists those repositories by name, or updates that issue if one is still
open. The rewritten `audit/targets.json` is kept as the run's `targets`
artifact for 90 days. The job has read access to the code and write
access to issues only: it cannot push a branch or open a pull request. It
never fetches a target's code: only the audit job does that.

Search results vary from run to run, so a target already in
`targets.json` stays even when this month's searches miss it. It is
dropped only when `git ls-remote` can no longer reach its repository. A
run also reuses the stored tree of every target whose head hasn't moved, so
only new or moved repositories cost an API request for their tree. When
GitHub's rate limit runs out, it waits for the reset time GitHub gives.
Each run prints how many requests it made.

New repository names can trip the separation check (C-SEP-TERMS), as
`audit/targets.json` already did once: a repository named after another
M-VAVE keyboard that the emulator also models. In principle they could
trip the privacy check (C-PRIVATE) too. A spec-side session reviews such a
hit. A separation hit gets an entry by hash in
`config/emulator-terms-reviewed.json`; a privacy hit goes to the owner.

A spec-side session turns the issue into a pull request:
1. Download the newest run's artifact, as the issue says
   (`gh run download <run> -n targets`), and replace `audit/targets.json`
   with it. Don't rerun the discovery locally: search results vary, and the
   artifact is what the issue lists.
2. Do the review just described for any separation or privacy hit.
3. Open the pull request with "Closes #<issue>". Because a person opens it,
   `ci` runs as usual, and the owner merges it with the button.

## The method

JPlag 6.3.0 (the jar with dependencies, checked against its SHA-256 in
`audit/audit.json`) runs in the Java 25 image `eclipse-temurin`, pinned by
digest, with no network. Its settings:
- the C language module, with JPlag's default minimum match of 12 tokens;
- **every file is its own submission**, because JPlag drops a whole
  submission when one of its files fails to parse;
- our files and the control's files are the "new" submissions, and the
  target files are the "old" ones. JPlag compares every new file with every
  old one, and never compares two old ones;
- each target file is scored **once per blob**: forks share most files, and
  a report lists every target and path that holds a flagged blob;
- comparisons with no match at all are not written (`-m 0.000001`), which
  loses no score.

Each file pair gets three numbers:
- the **longest match**: the longest run of tokens the two files share;
- **max**: the matched tokens over the smaller file's tokens;
- **avg**: the matched tokens over the mean of the two files' tokens.

JPlag compares token structure, not names, so renaming identifiers does
not hide a copy.

### Why the longest match, not the ratio

Before choosing, the spec side scored the control against an unrelated
permissive embedded project: TinyUSB's `src/` at commit
`3fa7b06d284c0ac1d1078a0a2d09dceb405499e7` (MIT), 244 control files against
190 TinyUSB files, 27,492 file pairs, with the same settings. Nothing
GPL was involved.

| Score | Median | 99th percentile | 99.9th percentile | Highest |
|-------|--------|-----------------|-------------------|---------|
| Longest match (tokens) | 0 | 13 | 17 | 33 |
| max (ratio) | 0 | 0.116 | 0.325 | 0.857 |

The ratio reaches 0.857 between two unrelated projects: a short file is
easily "mostly matched" by chance. The longest match stays short between
unrelated code, while a copied function gives one long run. So the gate
uses the longest match, and the report shows `max` and `avg` beside it.

### The threshold

The job **fails** when a pair of one of our files and a target file has a
longest match above the **threshold**:

> threshold = the control's longest match with any target it is not
> related to + 24 tokens

The control's highest score is what chance gives, in this run, against
these targets. That covers code idioms, common libraries and headers the
targets share with any embedded C. The margin of 24 tokens is twice
JPlag's minimum match: three or four C statements of identical structure,
beyond the longest run that unrelated embedded code shares with any
target. The calibration's highest chance run was 33 tokens, so the
threshold works out at about 55 to 60 tokens: six to eight lines of the
same code, which chance did not produce once in 27,492 pairs.

**Control-related targets.** A target that the control itself matches by
more than **100 tokens** is not unrelated to it. Some FM-1 repository might
carry Raspberry Pi code, for example a recovery tool for a Pico. Such a
target:
- is listed in the report as *control-related*;
- is left out of the baseline, so it doesn't raise the threshold for every
  other target;
- is judged against the control's own score there: a pair of ours fails
  above that score plus 24.

A file that several targets hold gets the strictest of their thresholds.
C-AUDIT-CONTROL fails if more than 10% of the scored targets are
control-related. The control would then be a poor yardstick for these
targets, and the owner chooses another, by pull request. A dry run showed
why this rule is needed. Against TinyUSB as a whole (not only its `src/`),
the control shares a 107-token run, because TinyUSB's own Raspberry Pi port
overlaps pico-examples' USB examples. One target like that would otherwise
have lifted the threshold for all of them.

### Files JPlag cannot score: the text check

JPlag drops a submission it cannot score: one with fewer tokens than its
minimum match (`TOO_SMALL`), or one it cannot parse (`CANNOT_PARSE`). A
file of ours dropped like that is never compared by the gate above. Since
M2 one is: `src/font.c`, our font, is a single constant table whose rows
are macro calls on string literals, and JPlag's C front end makes 5 tokens
of its 116 lines. Such a file is not left out:

(Since session midi-in-out, a file JPlag scores but matches with nothing,
which it leaves out of its index, goes to the text check the same way, and
the report marks it so; "The second self-test gap" below.)

- the report lists it under "Our files" as **not scorable by JPlag**, with
  JPlag's reason;
- the **text check** (C-AUDIT-TEXT) compares it with every target file, one
  copy per blob, and reports two scores per pair:
  - **exact:** the same bytes;
  - **containment:** the share of our file's distinct 24-character pieces
    that occur in the target file, both sides normalised first: comments
    removed (the SPDX header included), then all whitespace. String and
    character literals are kept. Containment, not a symmetric ratio,
    because a copy may sit inside a larger target file.
- The check **fails** on an exact copy, or at a containment of **0.5** or
  more. Like the gate, it fails whatever the target's licence, and only
  an auditor looks at a flagged pair.

Only files JPlag dropped go to the text check. A file JPlag scored that
matched nothing (`no match`) was compared by the gate; it is not sent
here. Which files go is decided by each run's JPlag output, so a new file
that JPlag cannot score is covered without a change here. Its rows hold
names and numbers only, and the leak check reads them like the rest of the
report.

**Why 24 characters and 0.5.** Before choosing, the spec side ran the
check on the same calibration pair as the gate: every pico-examples file
against every TinyUSB `src/` file (the commits above; 244 × 190 = 46,170
pairs, all permissive).

| Piece length | Median | 99th percentile | 99.9th percentile | Highest |
|--------------|--------|-----------------|-------------------|---------|
| 16 characters | 0 | 0.020 | 0.091 | 0.376 |
| **24 characters** | 0 | 0.005 | 0.053 | 0.286 |
| 32 characters | 0 | 0 | 0.018 | 0.247 |
| 48 characters | 0 | 0 | 0 | 0.219 |

- The highest pairs are not chance: a pico-examples USB example's
  configuration header against TinyUSB's options header, and USB
  descriptor types against TinyUSB's own. Both follow the USB standard and
  TinyUSB's conventions, a common source.
- Even that stays below 0.3 at 24 characters, while a copy, verbatim or
  reformatted, scores 1.0. A threshold of 0.5 lies well above the common
  source and well below a copy: half of our file found in one target
  file.
- For `src/font.c` that is about 1,770 of its 3,540 pieces, roughly half
  its glyphs' rows. Against the same 434 files it scored 0 at every piece
  length. That only shows that neither project holds a font like it: the
  calibration has no font drawn as text. The first run on main, whose
  report shows `src/font.c`'s best containment, is the first measurement
  against files of its kind. A font drawn the same way with common glyph
  shapes could share pieces with ours without copying, a common source
  like the USB headers. If the check flags such a pair, it goes to an
  auditor like any flagged pair. The threshold is never moved after
  seeing the targets' scores.
- 24 characters is also the leak check's line length: a piece about as
  long as one C statement, or three rows of a glyph.

Its limits:
- **Re-encoded data.** It compares text, so the same glyphs stored another
  way (hex bytes, or by column) would not be found. That is a rewrite, as
  with reordered code below.
- **Tiny files.** A file whose normalised text is shorter than 24
  characters is one piece; any target file holding it scores 1.0. No such
  file exists today. If one fails the check, the auditor's finding says
  so.
- **No acceptance yet.** `audit/accepted.json` accepts gate pairs only. If
  the text check ever flags a pair, the pull request with the auditor's
  finding also adds acceptance for it.

### What the gate cannot see

- **Small files.** A pair can fail only if its longest match is above the
  threshold. A verbatim copy of a file that JPlag scores but that is
  shorter than the threshold therefore can't fail the job. On 2026-10-23,
  `src/start.c` (20 tokens) was such a file. An exact copy of it would show
  as a top pair with `max` 1.0, but would not fail the job. The report
  lists each of our files' token counts, and its top pairs with `max`, so
  a reader can see this. The gate gets stronger as the firmware grows. A
  file too small for JPlag to score at all goes to the text check
  (above).
- **Drift.** The control is fixed and the firmware grows. Larger files have
  more chances to share a run by accident. The control's score, measured
  against the same targets in the same run, is the yardstick. If the
  firmware ever dwarfs the control, a larger control is chosen, by pull
  request.
- **Reordered or rewritten code** splits a copied run into shorter ones.
  Clean-room work is meant to prevent that kind of derivation, and the audit
  is evidence for it, not proof.

### Why this control

`raspberrypi/pico-examples` is:
- permissive (BSD-3-Clause);
- pinned at a release tag;
- embedded C of the same kind as ours: startup and clocks, timers,
  interrupts, UART, GPIO, DMA, audio and display examples;
- mostly small files, as ours are.

It is written for a different chip family (RP2040 and RP2350) and has
nothing to do with the FM-1, so its similarity to the targets is chance
and shared idiom, not copying. Its scores measure the noise floor that ours
are judged against. TinyUSB, used for the calibration above, was not chosen
as the control: an FM-1 firmware could reasonably vendor TinyUSB for USB
MIDI, which would raise the baseline.

## Running it

`.github/workflows/audit.yml`:
- runs on every push to main, and on demand (`workflow_dispatch`, with a
  choice of set);
- never runs for pull requests: there is no such trigger, and both jobs
  also require main.

GitHub offers the on-demand run only once the workflow file is on main, so
its first run is the push that merges it.

- **Sets.** `full` scores every target that isn't a duplicate. `fast`
  scores the four seeds Felucca, dinghy, fm1-emu's `fm1-sid/` (with
  `probes/`) and `fm1_open`. Pushes to main run `full`: the first run
  (below) took under 4 minutes. If a full run ever takes more than about 30
  minutes, push runs switch to `fast` and a nightly schedule runs `full`.
  That is one change to `audit.yml`'s triggers, by pull request, and this
  page then says so.
- **Self-test first.** Each run starts with `tools/audit.py selftest`. It
  builds a made-up local target that holds a verbatim copy of each of our
  files and a reformatted one (comments removed, lines re-indented). It
  runs the whole pipeline on that target and checks that every one of our
  files is found, and that the leak check passes (C-AUDIT-SELFTEST):
  - a file JPlag scores, by a match covering at least 90% of its tokens;
  - a file JPlag cannot score, by the text check: as an exact copy (the
    verbatim one), and at or above its threshold without being exact (the
    reformatted one);
  - a file JPlag scored that matched nothing fails it.

  No GPL code is involved. If the self-test fails, the audit still runs
  and is recorded, and the job fails at the end.
- **Job `audit`** has read-only permissions, no environment and no
  secrets. For each target in turn it:
  1. fetches the pinned commit into a temporary folder: depth 1, blob-less,
     with a sparse checkout of the C and C++ files only;
  2. checks the commit's tree against the pin;
  3. copies each file it hasn't seen before into the pool;
  4. deletes the checkout.

  The fetches run eight at a time (`fetch_workers`), but files join the
  pool in the list's order, so the report is the same from run to run.
  Then it runs JPlag once over the whole pool. JPlag's console output goes
  to a log in the temporary folder that is never shown, because a parse
  error quotes source. Its report archive embeds the files it compared, so
  the tool reads only three JSON members of it (comparisons, failed files,
  token counts: names and numbers), then deletes it. The temporary folder
  is removed whatever happens, and the job says so. Nothing is cached. The
  only artifact is `report.json` and `report.md`.
- **The leak check (C-AUDIT-LEAK).** Before the report is written, every
  line of every target file that is 24 characters or longer (after
  trimming) is looked for in it. On a hit the report is cut down to its
  checks, saying the leak check failed.
- **Job `record`** never sees a target. It:
  1. downloads the artifact;
  2. checks that it holds only that report (`tools/audit.py
     check-artifact`);
  3. appends it to the commit's record on the `records` branch, at
     `records/<sha>/audit/<run>-<attempt>/`, with the `records`
     environment's deploy key.

  If the records workflow is pushing at the same moment, it starts again
  from the branch's tip.

### The report

`report.json` and `report.md` hold:
- the pinned JPlag, Java image and control, the control's highest longest
  match with an unrelated target, the threshold and the margin, and the
  control-related targets;
- the base code, and each JPlag pass's files, base code and threshold
  (since SR-4);
- the checks (C-AUDIT-JPLAG, -PIN, -BASE, -CONTROL, -SCORE, -TEXT, -LEAK)
  and their traceability to R-AUDIT-*;
- **our top 20 file pairs**: our file, the target repositories and paths
  holding the matched file (the first ten of them, and how many there are),
  each with its licence class, and the longest match, max and avg;
- the control's top five pairs, and its best pair with our own files;
- each of our files' token counts. A file that matched nothing anywhere
  (no run of 12 tokens) shows `no match` with no count: JPlag leaves such a
  file out of its index. It was still parsed and compared; the self-test,
  which fails unless JPlag finds every such file in its copy, shows that it
  parses. A file JPlag could not score shows **not scorable by JPlag**,
  with the reason;
- the text check for those files: their pairs' containment and whether
  each is exact, the best per file, and any flagged pair, every place
  listed;
- every target: its pinned commit, licence class, files fetched (and how
  many were new to the pool), our longest and the control's longest match
  with it, and how many of its files JPlag could not parse or found too
  small;
- the flagged pairs, every place listed; pairs accepted by an auditor's
  finding; how many targets were skipped as duplicates or empty; and the
  unresolved names.

### The first run

The push that merged the audit (`362480c8`, run 39814921515) ran the full
set. Its report is in `records/362480c8…/audit/39814921515-1/`.
- The audit job took 3 minutes 44 seconds, the self-test included. That is
  why pushes run `full`.
- 516 targets were fetched at their pins, none unavailable; 18,498 target
  files were scored, one per blob.
- The control's longest match with an unrelated target was 35 tokens, so
  the threshold was 59. No target was control-related.
- Our best pair: `src/probe.c`, a 12-token match (JPlag's minimum) with
  several targets. `src/main.c`, `src/start.c` and `src/sb.h` matched
  nothing.
- Every check passed: C-AUDIT-JPLAG, -PIN, -CONTROL, -SCORE, -LEAK and
  -SELFTEST.

### The self-test gap (M2 to the text check)

From the merge of #35 (M2's firmware, which added `src/font.c`) until the
text check, every push's self-test failed: "8 of our 9 files found". The
file not found was `src/font.c`, which JPlag drops as `TOO_SMALL` (above).
The gate's own checks passed in each of those runs, but `src/font.c` was
compared with nothing. Those runs stay red in the records; docs/PLAN.md
lists them.

### The second self-test gap (#61 to the similarity rule)

From the merge of #61 (M4b's Plaits demo) the self-test failed again: "23
of our 27 files found", then "25 of our 30" from #70 on (session
midi-in-out, 2026-10-24, found why by running it locally):

- **Four of the demo's files** (`plaits_demo.c`, `plaits_voice.cc`,
  `sftest.c`, `runtime/softfloat.c`) were matched in full by their copies
  (JPlag's similarity 1.0), but in pieces: JPlag leaves out what matches
  the Plaits base code, which splits a verbatim copy's match, so the
  longest piece stayed under 90% of the file's tokens.
- **`src/audio.h`** matched nothing, not even its own verbatim copy
  (state "no match"), and such a file went nowhere: JPlag doesn't cover
  it, and the text check took only files JPlag could not score.

**The fix:** a file JPlag scored is found by a match covering 90% of its
tokens, or by a similarity of at least 0.9 with a copy of itself (the
report now names each pair's target file, so another file's copy doesn't
count). A file JPlag matched with nothing goes to the text check too, in
the real audit as well, so every file is covered by JPlag or by the text
check; the report says which, and why. The self-test then finds 30 of 30
(26 by JPlag, 4 by the text check). On the real audit at `1537391`, five
of our files matched nothing (three headers, `src/start.c`, the demo's
`plaits_voice.h`); they are now compared as text too. The gate and the
text check passed in every one of these runs; the runs stay red in the
records, and docs/PLAN.md lists them.

## When the audit fails

Nobody on the spec side or the firmware side opens the matched code, or the
target, to see what matched.

1. **The owner is told.** The failed `audit` run and its report say which
   of our files, which target files (by name) and what scores. Whoever
   sees it first tells the owner, and repeats nothing beyond those names
   and numbers.
2. **The owner starts an auditor session** (CONTRIBUTING.md, "Roles"):
   - in a folder of its own, set up with `tools/auditor-setup.sh
     ~/<top>/auditor`, which installs `config/claude/auditor.json`;
   - it adds its entry to docs/EXPOSURE.md before anything else;
   - the auditor reads only the flagged pairs: our file, and the target
     file at its pinned commit.
3. **The auditor writes a finding** in `audit/findings/`, in general terms
   only: which of our files, the target's repository and path, the scores,
   and the conclusion. Possible conclusions are coincidence, a common
   source (the SDK, a datasheet's sequence, a standard idiom), or derived.
   It contains no target code and no description of the target's
   structure. The finding comes by pull request, reviewed by the owner.
4. **Then:**
   - *Coincidence or a common source:* the pair goes in
     `audit/accepted.json`, with our file, the target's repository and path,
     the accepted longest match and the finding. A higher score later fails
     again.
   - *Derived:* the owner decides how the firmware side replaces our file
     clean-room, from HARDWARE-SPEC.md, without the finding's details.
5. **The auditor is done for good.** It never writes firmware or spec
   afterwards, in any session.

**Auditor transcripts are never archived in this repository**, because they
hold GPL source. The owner's decision of 2026-10-22:
- each one goes to a separate private repository owned by the owner
  (`small-beeps-audit`), committed there with an OpenTimestamps proof;
- that repository is created only when the first auditor session runs, and
  only with the owner's approval;
- here, docs/EXPOSURE.md records the auditor session's ID, the transcript's
  SHA-256 and the private repository's commit;
- `tools/check-transcripts.py` fails on any transcript outside
  `sessions/clean/` and `sessions/spec/`, so an auditor transcript put here
  by mistake fails CI.

## Files

| File | What it is |
|------|------------|
| `audit/discover.json` | Seeds, search queries, the mention rule, unresolved names. |
| `audit/targets.json` | Every target, pinned: commit, tree, licence class, status. Written by `tools/audit-discover.py`. |
| `audit/audit.json` | JPlag and the Java image (pinned), the control (pinned), base code (and which of our files each tree is for), the margin, the ceiling, the text check's piece length and threshold, the fast set. |
| `audit/accepted.json` | Pairs accepted by an auditor's finding. |
| `audit/findings/` | Auditors' findings (none yet). |
| `tools/audit.py` | The audit, its self-test, and the artifact check. |
| `tools/audit-discover.py` | Finds the targets from metadata. |
| `.github/workflows/audit.yml` | The audit and its record. |
| `.github/workflows/audit-discover.yml` | The monthly rediscovery. |
| `config/claude/auditor.json` | The auditor's Claude Code settings. |
