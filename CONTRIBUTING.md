<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Contributing

This repository is a clean-room, MIT-licensed base firmware for the M-VAVE
FM-1 pocket synthesizer (JieLi AC791N). The FM-1's existing community
firmwares are GPL-licensed; ours must be provably independent of them. The
rules below make that provable. Everyone follows them, people and agents
alike. If you are unsure whether something is allowed, **stop and ask the
owner** before you open it.

## Roles

Clean-room work separates the people who have seen the protected code from
the people who write ours.

- **Spec side (exposed).** May read the F-Emulator emulator's source, whose
  chip model was partly written from the GPL Felucca firmware's hardware
  layer. Builds the test harness and writes `HARDWARE-SPEC.md`: facts only
  (addresses, bits, pins, timings, protocols), never code or code structure,
  each fact citing a non-GPL source where one exists. Never writes firmware.
- **Firmware side (clean).** Writes the firmware. Reads only
  `HARDWARE-SPEC.md`, the JieLi SDK (Apache-2.0), FM-1-RE's hardware
  documents (WTFPL), public datasheets, and results of its own black-box
  experiments. Uses the harness only as a command-line tool, and never opens
  `vendor/emulator/` or `harness/` source.

- **Auditor (exposed to the GPL firmwares).** A third role, only for a
  failed similarity audit (docs/AUDIT.md, "When the audit fails"). The owner
  starts one; it works in a folder of its own set up with
  `tools/auditor-setup.sh` (settings `config/claude/auditor.json`), and may
  read the flagged GPL target files and our code. It writes only a finding
  in `audit/findings/`, in general terms (which of our files, the scores,
  the conclusion; never target code). It never writes firmware, the spec or
  the harness, then or in any later session. Its transcript holds GPL
  source, so it is **never archived in this repository**: it goes to the
  owner's private repository `small-beeps-audit` (created, with the
  owner's approval, when the first auditor session runs), committed there
  with an OpenTimestamps proof, and docs/EXPOSURE.md records the session's
  ID, the transcript's SHA-256 and that repository's commit.

Every person and every session is recorded in docs/EXPOSURE.md with its role
and exposure, before it does any work. A firmware-side person or session that
sees forbidden material becomes spec side from that moment: record it in
EXPOSURE.md at once, and stop writing firmware.

## Clean-room rules

### Firmware side never opens, fetches, searches or quotes

- hugelton/Felucca and every fork or firmware built on it (Felucca Salt,
  Felucca 8 Patterns, Hortator, GHOULBOX, Melodee, Skiff, ...);
- zvenson/dinghy and anything built on it;
- the F-Emulator / fm1-emu repository's `fm1-sid/` directory, its
  `probes/lcdtest.c`, and its emulator source (`crates/`);
- any other FM-1 firmware source;
- M-VAVE's stock firmware and any disassembly or function database of it
  (including AL-255/FM-1-RE's `firmware-images/` and disassembly material);
- in this repository: `vendor/emulator/` and `harness/` source (spec side's
  work), and spec-side session transcripts (`sessions/spec/`), which
  contain emulator source. A clean folder never has their contents, not
  even in `.git`: clean sessions run with git's lazy fetching off
  (`GIT_NO_LAZY_FETCH=1`, from `config/claude/clean.json`), so a history
  command that would need them (`git log -p`, `git show`, `git diff`
  across commits) fails instead of downloading them. Give such commands a
  pathspec that leaves the three folders out, and update the folder only
  with `tools/clean-update.sh`. People working in a clean folder by hand
  set `GIT_NO_LAZY_FETCH=1` in their shell too;
- the sites hugelton.github.io and thefirmwarehub.com.

`tools/check-transcripts.py` checks every archived clean-side session against
this list (its `FORBIDDEN` table mirrors it; change both together).

### Firmware side may use

Log every use in PROVENANCE.md (an ID, the source, what was learned, where it
was used) and name the ID in the commit's `Sources:` field:

- `HARDWARE-SPEC.md`, once it exists (each fact there already cites its own
  source);
- JieLi's AC79 SDK, `Jieli-Tech/fw-AC79_AIoT_SDK` (Gitee), Apache-2.0:
  headers, register definitions, drivers. Not its prebuilt libraries;
- AL-255/FM-1-RE (GitHub, WTFPL): its hardware, memory-map, boot-chain and
  update-protocol documents only. Fetch single documents by URL; never clone
  it (a clone puts its firmware images and disassembly material on disk);
- public datasheets;
- our own experiments: test programs run in the emulator, observed only
  through the harness: `tools/fwtest`, whose manual is docs/HARNESS.md;
- answers to spec requests (docs/SPEC-REQUESTS.md), which arrive as facts
  in `HARDWARE-SPEC.md`.

### Barriers

- **Clean folder.** `tools/clean-setup.sh [DIR]` creates the clean working
  folder: a blob-less clone with a sparse checkout that leaves out
  `vendor/emulator/`, `harness/` and `sessions/spec/` (and marks them
  `-diff` for history commands), plus the Claude Code settings in
  `config/claude/clean.json`, which deny reading those paths, fetching the
  forbidden sites and cloning the forbidden repositories, and turn git's
  lazy fetching off. `tools/clean-update.sh` updates a clean folder and
  checks nothing excluded arrived; C-CLEAN-FOLDER tests all of this in CI.
- **Records in a clean folder.** Each record on the `records` branch also
  keeps the harness's and the spec experiments' outputs. Clean sessions
  never fetch the records branch wholesale (no `git archive`, checkout or
  lazy fetch of a whole record or of the branch): they fetch only named
  files of the firmware's own records, `report.json`, `report.md` and
  named logs under `logs/`, one path at a time. `tools/clean-update.sh`
  also stops if a file under a `harness/` or `spec-experiments/` folder,
  or under the excluded folders, is in `.git` through any branch, the
  records branch included (since M1, after a wholesale fetch brought 17
  such outputs into a clean folder; docs/EXPOSURE.md).
  `tools/spec-setup.sh [DIR]` does the same for spec side with
  `config/claude/spec.json`.
- **Deny lists only grow.** Never remove or loosen an entry in
  `config/claude/*.json`. Check C-DENY-LISTS fails if one is dropped.
- **Session banner.** Both configs run `tools/session-banner.sh` on every
  SessionStart (startup, resume, clear, compact). It prints the role,
  `claude --version`, the SHA-256 of `.claude/settings.json` and of the
  committed config, and the UTC time, and prints `CONFIG MISMATCH` and exits
  non-zero if they differ.
- **Session transcripts.** Each milestone gets a fresh session. At the start
  of every session, before anything else:
  1. archive the previous session's transcript with
     `python3 tools/archive-session.py <transcript.jsonl> --role <role>`
     (it redacts secrets and private paths, writes the copy to
     `sessions/<role>/` and a note beside it). A spec session may archive
     the previous session of either role; a clean session archives only
     clean sessions and never opens `sessions/spec/` (sessions/README.md);
  2. run `python3 tools/check-transcripts.py`;
  3. add this session's entry to docs/EXPOSURE.md.
  A session never archives its own live transcript; the next one does.

### Spec-side text discipline

What the spec side learns from emulator source leaves `vendor/emulator/`
and `harness/` only through two doors: `HARDWARE-SPEC.md` (facts only, each
sourced) and `docs/HARNESS.md` (the harness as a black box). Everything else
the firmware side can read, so spec-side commit messages, pull request
titles and descriptions, and every file outside those two folders and
`sessions/spec/` (docs, tools, tests, records, release notes) describe what
changed in general terms, never emulator internals: no register names,
addresses, struct or function names, or code excerpts. Such detail goes in
comments inside `harness/`. CI logs and records from harness runs show
results (pass/fail, hashes, images, numbers), never emulator source.
`tools/check-emulator-terms.py` (C-SEP-TERMS) looks for identifiers that
occur only in `vendor/emulator/` in all of those places and reports a hit
by place and hash, never the word; run it (with `--show`, in a spec folder)
on your commit messages before you push. People review the two doors, so a
term that occurs in either of them as merged on main is accepted everywhere
(read from main's commit, never the working tree: a term a branch adds to a
door is still a hit until that change has merged). Other reviewed false
positives are listed by hash in `config/emulator-terms-reviewed.json`.

## Commit messages

Every commit follows `.gitmessage` (run `tools/install-hooks.sh` once to make
it git's template and turn on the commit-msg hook):

```
<area>: <what changed, one line>

What:    what this commit does
Why:     the reason (the milestone and requirement IDs it serves)
How:     the approach, and anything tried and rejected
Result:  what the author saw when testing (the CI record is the authoritative result)
Sources: PROVENANCE IDs used (or "none")
Exposure: the author's role and exposure (e.g. "firmware side, none")
```

- `<area>` is lower-case: `docs`, `tools`, `ci`, `firmware`, `vendor`,
  `config`, `sessions`, and so on.
- A field may continue on following lines, indented.
- Agent-written commits end with the trailers `Model: <exact model ID>` and
  `Claude-Session: <session URL>` (and `Co-Authored-By:`). Their author is
  the agent; the owner is the committer.
- Small commits: one idea each.
- Merge commits are exempt from the template; the pull request they merge
  carries the sections.

`tools/check-commit-msg.py` enforces this in the hook and in CI (C-COMMIT-MSG).

## Pull requests and merging

- Agents and contributors commit **unsigned** on branches and open a pull
  request using `.github/pull_request_template.md` (the same sections, plus
  links to the CI run and the record).
- CI (`.github/workflows/ci.yml`) must pass.
- The **owner merges with GitHub's merge button** ("Create a merge commit").
  GitHub commits and signs the merge commit as `web-flow` (shown as
  Verified) and records the owner as the pull request's `merged_by`. No
  squash or rebase merges, and nobody bypasses the rules.
- Records (`records/<sha>/` on the `records` branch) are written only by
  `.github/workflows/records.yml`, for pushes to main, and the similarity
  audit's report beside it (`records/<sha>/audit/`) only by
  `.github/workflows/audit.yml`'s record job (docs/AUDIT.md). Both use the
  `records` environment's deploy key.
- **Performance budgets** (`config/budgets.json`, R-PERF-1) are raised, or
  moved to the next milestone's, only by a pull request of their own that
  says why in the What/Why/How/Result sections and changes nothing else.
  When CI's performance summary shows an improvement of more than 3%
  (R-PERF-2), say so in the pull request's Result.
- Milestones end with a tag `mN`, signed by the owner with their SSH key
  (below), and a GitHub release with the build outputs, the record and an
  SBOM.

### Merge policy and its history

- **2026-10-21:** the owner first chose to sign every merge with their own
  SSH key, as the ruleset's only bypass actor, because GitHub's button signs
  with GitHub's key instead.
- **2026-10-22:** pull request #1 was merged with the button. Its merge
  commit `2fd28219` is signed by GitHub (`web-flow`, verified), and its
  record shows C-MERGE **FAIL** under the old rule ("committer is web-flow,
  not the owner"). The record stays as it is, and history is not rewritten.
- **2026-10-22:** the owner then chose button merges for good. The bypass
  was removed from the main ruleset, so the rules now apply to everyone.

What a merge on main proves: GitHub's signature shows the commit was made
by GitHub on the owner's merge. `merged_by` shows the owner pressed the
button. The required `ci` check shows CI passed on exactly the merged head.
The records workflow re-checks all of this for every push to main
(C-MERGE): a merge commit, a verified signature, committer `web-flow` with
the pull request's `merged_by` the owner (or, for older merges, the owner
as committer), and its second parent the head of a pull request whose `ci`
run passed. Otherwise the record says **FAIL** for C-MERGE, and the record
is still written.

## Rulesets

Repository rulesets (Settings → Rules → Rulesets):

- **main**: restrict deletions; block force pushes; require a pull request
  before merging (allowed merge method: merge only); require status checks to
  pass (the `ci` job); no bypass (until 2026-10-22: the repository admin
  role).
- **records-history** (branch `records`): restrict deletions; block force
  pushes; no bypass.
- **records-writer** (branch `records`): restrict creations; restrict
  updates; bypass list: deploy keys only. Together these make the records
  workflow's deploy key the only writer, and it can only add commits.
- **milestone-tags** (tags `m*`): restrict deletions; restrict updates; no
  bypass.

Repository settings: allow merge commits only (squash and rebase merging
off).

Set up on 2026-10-22 by session M0a, with the owner's approval, through the
GitHub API:

| What | ID or fingerprint |
|------|-------------------|
| Ruleset `main` | 25612787 (required check `ci` from GitHub Actions; no bypass since 2026-10-22, before that the repository admin role) |
| Ruleset `records-history` | 25612788 |
| Ruleset `records-writer` | 25612790 (bypass: deploy keys) |
| Ruleset `milestone-tags` | 25612791 |
| Environment `records` | deployments from `main` only; secret `RECORDS_DEPLOY_KEY` |
| Deploy key "records workflow (records branch writer)" | 167260041, write access, ED25519 `SHA256:Od9RfSkzLwqLYSZRf1X7jEdcLhty0n1ISgQ+ec43Dkk` |

The deploy key's private half was generated in the session's scratch
folder, piped into the environment secret without being printed, and
deleted. To rotate it: make a new pair, replace the secret, add the new
public key, delete the old key.

## SSH signing for milestone tags (one-time setup, owner)

1. Create a signing key (or reuse an SSH key you already have):
   `ssh-keygen -t ed25519 -C "small-beeps signing" -f ~/.ssh/id_ed25519_signing`
2. Tell git to sign with it:
   ```sh
   git config --global gpg.format ssh
   git config --global user.signingkey ~/.ssh/id_ed25519_signing.pub
   git config --global tag.gpgSign true
   ```
   Leave `commit.gpgSign` off: merges are signed by GitHub's button.
3. Let git verify signatures locally: add a line
   `<your git email> <contents of id_ed25519_signing.pub>` to
   `~/.ssh/allowed_signers`, then
   `git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers`.
4. On GitHub: Settings → SSH and GPG keys → New SSH key → Key type
   **Signing Key**, and paste the `.pub` contents.
5. Tag a milestone: `git tag -s mN -m "mN"`, then `git push origin mN`.
6. Check: `git tag -v mN` shows "Good "git" signature", and GitHub shows the
   tag as **Verified**.

## Licences

- Every file we write starts with an SPDX header:
  `SPDX-License-Identifier: MIT` and `SPDX-FileCopyrightText: 2026 japes98`.
  Files that can't carry one are covered in `REUSE.toml`.
- Vendored files keep their own licences (`vendor/*/LICENSE`, `NOTICE`).
- CI runs `reuse lint` and fails on any gap (C-REUSE).
- Never commit the toolchain or anything containing it (docs/TOOLCHAIN.md).
- Nothing secret ever goes in: no keys, tokens or private notes. The
  repository is public and history is never rewritten.

## Privacy

The repository is public. No committed file, commit message or pull request
text names the owner's username, real name, e-mail address, hostname or
local folder names, or a full local path: write paths relative to the
repository, or as `~/...` with the top folder shown as `<top>`. Anyone who
finds such a term in the repository tells the owner instead of repeating it.

- **The terms** are kept by the owner, never in the repository: in the
  gitignored `tools/private-terms.local` (one per line, `#` comments,
  matched ignoring case) and in the repository secret `PRIVATE_TERMS`, which
  CI passes to the check.
- **The check** `tools/check-private.py` (C-PRIVATE, R-PUB-3) scans every
  tracked file and every commit message, and the pre-commit and commit-msg
  hooks scan staged files and the message (`tools/install-hooks.sh` turns
  them on). A hit is reported by file and line only, never the term. CI
  fails when the secret is missing.
- **Records are scanned too** (since M1). Before a test record, an audit
  report or a C-MERGE re-check is hashed, uploaded or pushed, any file in
  it holding a term is withheld: deleted, and listed with the SHA-256 of
  the original in `WITHHELD.json`, which the record keeps (C-RECORD-PRIVATE).
  The original is not kept anywhere; the checks are deterministic, so it
  can be regenerated and matched to its hash. CI artifacts are kept 14 days.
- **Older records stay as they are.** A file under `sessions/` or
  `docs/prompts/` whose blob is identical to the same path at the base
  commit in `config/private-base` (the last main commit before the check)
  is exempt. This is decided from git's object hashes alone, so no session
  opens or lists the spec side's transcripts for it, and the check prints
  only how many files it exempted per folder. Every file added or changed
  after the base is checked in full. Files that sessions keep editing get no
  exemption: their current text is redacted instead (`docs/EXPOSURE.md` was,
  on 2026-10-22), and git history keeps the originals.
- **Archived transcripts** are redacted by `tools/archive-session.py`: the
  username anywhere it appears, the local top-level folder as `<top>`, and
  every private term.

## Low profile (for now)

The repository is public but unpromoted. In its name, description and topics,
and in README.md, never use these quiet words: **FM-1, M-VAVE, JieLi, synth,
firmware** (any spelling or case; `tools/check-low-profile.py` has the
patterns). Don't link the repository from anywhere, star it, fork it or
announce it. Everything else in the repository stays complete and truthful.
docs/GOING-PUBLIC.md says how this ends.
