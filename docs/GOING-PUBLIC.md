<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Going public

For now the repository `japes98/small-beeps` is public but low profile
(CONTRIBUTING.md, "Low profile"). When the owner decides to announce it,
follow these steps in order. Each step that changes files is a normal pull
request with the usual commit template.

## 1. Transfer to the organisation and rename

1. Create the organisation (if needed) and make the owner an owner of it.
2. In the repository: Settings → General → Danger Zone → **Transfer**, to the
   organisation. Then Settings → General → **Repository name**, to the final
   name.
3. What carries over: every commit, branch (including `records`), tag,
   release and release asset, with their original timestamps and signatures.
   Rulesets, issues and pull requests move with the repository. GitHub
   redirects the old URLs (web and git) to the new ones, as long as nobody
   creates a new repository under the old name.
4. What doesn't carry over automatically, so redo it:
   - **The records deploy key** (Settings → Deploy keys) and the `records`
     environment's secret `RECORDS_DEPLOY_KEY`: check both are still there
     after the transfer; if not, make a new key pair, add the public half as
     a deploy key with write access and the private half as the environment
     secret, and delete the old key.
   - **The ruleset bypass actor**: re-add the owner (or the organisation's
     maintainers team) as the only bypass actor on main.
   - **Actions settings** (Settings → Actions): workflow permissions stay
     read-only by default; check that the records environment is still
     limited to `main`.
5. Never rewrite history and never delete the old records. The OpenTimestamps
   proofs commit to file contents, not to URLs, so they stay valid.

## 2. Description, topics and README front page

1. Description: replace "Embedded audio experiments." with a full
   description (an original MIT-licensed firmware for the M-VAVE FM-1, JieLi
   AC791N).
2. Topics: add the relevant ones (e.g. `fm-synthesis`, `embedded`,
   `firmware`, `clean-room`).
3. README.md: replace the low-profile front page with a full introduction:
   what the project is, the clean-room process (link CONTRIBUTING.md,
   docs/EXPOSURE.md, PROVENANCE.md), how to verify our work, and the licence.
4. Retire the low-profile check in the same pull request: remove C-LOW-PROFILE
   from `tools/record.py`, mark R-PUB-1 in docs/REQUIREMENTS.md as retired
   with the date (don't delete the row), and say why in the commit.

## 3. Update pinned URLs

Search the repository for the old owner and name and update them, each in a
reviewed pull request:

- `japes98/small-beeps` in docs, `tools/reproduce` (the default records
  remote is `origin`, so nothing is pinned there unless added later), and
  release notes;
- the SPDX copyright lines stay as they are (`2026 japes98`); new files may
  name the organisation;
- `.github/workflows/*`: no repository names are pinned; check anyway;
- the private preservation repository `japes98/small-beeps-toolchain` stays
  private. Transfer it too if the organisation should hold it, and update
  docs/TOOLCHAIN.md.

Then announce it.
