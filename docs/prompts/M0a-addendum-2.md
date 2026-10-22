# Addendum 2 (part of M0a): record and verify the Claude Code configuration

The deny rules in .claude/settings.json were created by hand before this session started. Never remove or loosen any of them.
1. Record the hand-made file's SHA-256 in EXPOSURE.md, noting that it was made by the owner before the repo existed.
2. Commit config/claude/clean.json: the hand-made deny rules unchanged, plus the hook from step 4. Also commit config/claude/spec.json with these deny rules plus the same hook:
   ["Read(**/fm1-sid/**)","Read(**/probes/lcdtest.c)","WebFetch(domain:hugelton.github.io)","WebFetch(domain:thefirmwarehub.com)","Bash(git clone*Felucca*)","Bash(git clone*felucca*)","Bash(git clone*dinghy*)"]
   Add a test that fails if either config's deny list ever drops an entry.
3. Add .claude/settings.json and .claude/settings.local.json to .gitignore. tools/clean-setup.sh and a new tools/spec-setup.sh copy the matching config into .claude/settings.json. Run clean-setup.sh here once the hook script exists, so this folder's live settings become config/claude/clean.json.
4. The hook: SessionStart, on every source including startup, resume, clear and compact. It runs tools/session-banner.sh, which prints the role, `claude --version`, the SHA-256 of .claude/settings.json and of the committed config, and the UTC time. On a mismatch it prints CONFIG MISMATCH and exits non-zero.
5. Sessions: each milestone gets a fresh conversation (/clear or a new session). At the start of every session, before anything else, archive the previous session's transcript into sessions/ and run tools/check-transcripts.py. That script fails on any archived transcript without the banner, or with a mismatch. (This session is the first, so it has nothing to archive and no banner; record that in EXPOSURE.md.)
6. End every milestone by committing everything and telling the owner "done, ready to clear". Don't archive your own live transcript; the next session does that.
7. Commit using the What/Why/How/Result template, and save this text as docs/prompts/M0a-addendum-2.md.
