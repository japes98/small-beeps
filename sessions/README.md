<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Session transcripts

Every agent session that works on this repository is kept here as evidence.
A session's transcript is the full record of what it read, searched,
fetched, ran and wrote, so anyone can check that a firmware-side (clean)
session never touched forbidden material (CONTRIBUTING.md, "Clean-room
rules"; R-CLEAN-1, R-CLEAN-3).

## Folders, and who archives whom

- `clean/`: firmware-side (clean) sessions.
- `spec/`: spec-side sessions. Their transcripts contain emulator source,
  so `tools/clean-setup.sh` leaves this folder out of clean folders, and the
  clean settings deny reading it.

A **spec** session may archive the previous session of either role. A
**clean** session archives only clean sessions, and never opens, lists or
searches anything under `spec/`. When the previous session was spec side
and the next is clean, the clean session leaves it for the next spec
session to archive.

An **auditor** session (CONTRIBUTING.md, "Roles") is never archived here:
its transcript holds GPL source, so it goes to the owner's private
repository, and docs/EXPOSURE.md records its ID, SHA-256 and that
repository's commit. `tools/check-transcripts.py` fails on any transcript
outside `clean/` and `spec/`.

## Files

Each role folder holds:

- `<date>-<role>-<id>.jsonl`: the session's Claude Code transcript, one JSON
  entry per line, as Claude Code wrote it under `~/.claude/projects/`, with
  secrets and private details redacted. `<date>` is the UTC date of its first
  entry, `<role>` is `clean` or `spec`, and `<id>` is the Claude Code session
  ID.
- `<same name>.REDACTIONS.md`: what was redacted (kind and count), with the
  SHA-256 of the original and of the redacted copy. The owner keeps the
  originals, so a redacted copy can be matched to its original if that is
  ever challenged.
- `<same name>.subagents/`: transcripts of subagents the session started, if
  any.

## How they get here

A session never archives itself, because its transcript is still being
written. The **next** session, before doing anything else, runs:

```sh
python3 tools/archive-session.py ~/.claude/projects/<project>/<id>.jsonl --role <role> \
    --archived-by "<this session's id>"        # writes to sessions/<role>/
python3 tools/check-transcripts.py
```

and commits the result.

## What is checked

`tools/check-transcripts.py` (C-TRANSCRIPTS in every test record):

- every transcript must be in the folder of its role (a file outside
  `clean/` and `spec/` fails). When `spec/` isn't on disk (a clean folder),
  spec transcripts are skipped, not read, and the output says so;
- every transcript must show the SessionStart banner from
  `tools/session-banner.sh` with `status: OK`. Any `CONFIG MISMATCH` fails.
  The exemptions are listed by session ID in the check's `EXEMPT_NO_BANNER`,
  each with its reason (docs/EXPOSURE.md): the first session (M0a), M0a's
  one-prompt hook test, and the first spec session (M0b), each of which
  began before its folder had the banner hook;
- for clean-side transcripts, every file read, write, search, web fetch, web
  search and shell command is listed in the check's log by entry (the
  transcript's line number), tool and tool-call ID, and any that touches
  forbidden material fails, named by rule ID (`F-...`, the check's
  `FORBIDDEN` table). The log never quotes a transcript: it goes into every
  test record, and the oldest archived transcripts still hold text that the
  archiver now redacts.

Since M4 (the owner's request) the check tells an access from a mention.
It fails a call only when what is left of it, once the spans it can
prove are mentions are taken out, still names forbidden material: a pull
request's title or body, a commit message, a heredoc written into one of
our own files, Python fed to `python3 -` that provably opens only our own
files, a grep pattern or a substituting sed script over our own files.
Anything it can't parse or doesn't know stays flagged, and it never flags
what plain text matching would not, except a later command that runs a
file such a heredoc wrote. Text matching still runs, report only: every
mention it finds is logged as `MENTION` with its rule ID, so nothing goes
unseen. `tools/check-transcripts.py`'s docstring lists the spans.

A flagged call can be cleared only by an entry in `REVIEWED.json` naming
that exact session and tool call, the rule it matched and why it isn't a
touch, added by pull request so the owner's signed merge approves it. An
entry names its rule by the rule's label (older entries) or by its ID
(new entries, since M4b: some labels match their own rules).

### Rule IDs

Since M4b (the owner's request) the rule IDs are neutral numbers, so a
command that only names a rule, such as one adding a `REVIEWED.json`
entry, no longer matches it. Logs and records before M4b show the old
IDs:

| Old ID | New ID |
|--------|--------|
| `F-FELUCCA` | `F-1` |
| `F-HUGELTON` | `F-2` |
| `F-DINGHY` | `F-3` |
| `F-FM1-SID` | `F-4` |
| `F-PROBE` | `F-5` |
| `F-EMU-REPO` | `F-6` |
| `F-EMU-CRATES` | `F-7` |
| `F-VENDOR-EMU` | `F-8` |
| `F-HARNESS` | `F-9` |
| `F-FWHUB` | `F-10` |
| `F-SPEC-SESSIONS` | `F-11` |
| `F-RE-FIRMWARE` | `F-12` |
| `F-STOCK` | `F-13` |

The check's `OLD_IDS` holds the same table; the labels and patterns are
unchanged.
Agents still do best writing prose with their file-writing tool, not with
shell commands.

One kind of command is cleared by the check itself (since M1, at the
owner's request): a quoted heredoc fed to `python3 -` whose code provably
opens nothing but `sessions/REVIEWED.json` and files under `sessions/clean/`
(only `json` and `re` imported, no other file, process or `exec`-like call,
every `open()` path a literal under those two places). Its body is then left
out of the three spec-side folder rules only; every other rule, and the rest
of the command, is still matched as text. (Since M4 this is the text
rule's exception; the access rule's, above, is wider.) A `REVIEWED.json`
entry a rule made unnecessary may be marked `superseded` rather than
deleted; it clears nothing, and the check fails if the access rule ever
flags its call again.
