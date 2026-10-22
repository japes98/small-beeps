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
  search and shell command is listed in the check's log, and any that touches
  forbidden material fails.

Matching is on text, so it errs towards flagging: a shell command that only
*writes* a document naming a forbidden folder is flagged too. Such a hit can
be cleared only by an entry in `REVIEWED.json` naming that exact session and
tool call, the rule it matched and why it isn't a touch, added by pull
request so the owner's signed merge approves it. Agents avoid the problem by
writing prose with their file-writing tool, not with shell commands.
