# M0a addendum: evidence that the clean side stayed clean (add this before finishing M0a)

1. Session transcripts are evidence. Before each session ends, copy its full Claude Code
   transcript (the session's .jsonl under ~/.claude/projects/) into `sessions/<date>-<role>-<id>.jsonl`,
   after checking it for secrets (tokens, keys, private paths: redact them and say so in a note
   beside it). Add a `sessions/README.md` explaining what they are.
2. `tools/check-transcripts.py`: for every clean-side transcript, list every file read, search
   and web fetch, and fail if any touches a forbidden path or site (the list in
   CONTRIBUTING.md, plus `vendor/emulator/` and `harness/` source). Run it in CI and put its
   result in the record.
3. Barriers: `tools/clean-setup.sh` creates the clean working folder: a clone (a sparse
   checkout without `vendor/emulator/` and `harness/` once they exist) plus Claude Code
   settings that deny reading those paths and deny fetching the forbidden repos' domains and
   paths. Commit the script and the settings file it installs; record in EXPOSURE.md that
   this session ran under them from now on.
4. Each session's entry in EXPOSURE.md and each commit's trailers record the exact model ID
   used, and docs/EXPOSURE.md notes that model's published training cutoff and that the FM-1
   and its community firmwares postdate it. A session on a model with a later cutoff is
   flagged.
5. Add `docs/DESIGN-NOTES.md`: from M0d on, each design choice explained from the spec's facts
   and first principles.
Include this addendum in docs/prompts/ as M0a-addendum.md.
