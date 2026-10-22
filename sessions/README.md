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

## Files

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
    --archived-by "<this session's id>"
python3 tools/check-transcripts.py
```

and commits the result.

## What is checked

`tools/check-transcripts.py` (C-TRANSCRIPTS in every test record):

- every transcript must show the SessionStart banner from
  `tools/session-banner.sh` with `status: OK`. Any `CONFIG MISMATCH` fails.
  The only exemption is the first session (M0a,
  `36860ab8-77fd-4fd6-aa1d-2063c15a5548`), which began before the banner
  existed (docs/EXPOSURE.md);
- for clean-side transcripts, every file read, write, search, web fetch, web
  search and shell command is listed in the check's log, and any that touches
  forbidden material fails.

Matching is on text, so it errs towards flagging: a shell command that only
*writes* a document naming a forbidden folder is flagged too. Such a hit can
be cleared only by an entry in `REVIEWED.json` naming that exact session and
tool call, the rule it matched and why it isn't a touch, added by pull
request so the owner's signed merge approves it. Agents avoid the problem by
writing prose with their file-writing tool, not with shell commands.
