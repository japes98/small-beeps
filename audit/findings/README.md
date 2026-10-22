<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Auditors' findings

One file per flagged pair an auditor compared (docs/AUDIT.md, "When the
audit fails"): `<date>-<n>.md`, by pull request, reviewed by the owner.

A finding says, in general terms only:

- which of our files, and the target's repository, pinned commit and path;
- the scores from the audit's report (longest match, max, avg) and the run;
- the auditor session (its docs/EXPOSURE.md entry);
- the conclusion: coincidence, a common source (the SDK, a datasheet's
  sequence, a standard idiom; named), or derived;
- what follows: an entry in `audit/accepted.json`, or the owner's decision
  on replacing our file.

It never quotes, paraphrases or describes the target's code or its
structure.

None yet.
