<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Spec requests

How the firmware side (clean) asks the spec side (exposed) for a hardware
fact it needs, and how the answer comes back, without anything else passing
between them (CONTRIBUTING.md, "Roles").

## Asking (firmware side)

Add a request at the end of "Requests" below, by pull request:

- a number (`SR-1`, `SR-2`, ...; never reused);
- the date asked;
- the question: one fact about the hardware (an address, a bit, a pin, a
  timing, a protocol step, a limit), asked as narrowly as you can;
- why it is needed: what the firmware is trying to do, the milestone, and
  what you already tried or read (HARDWARE-SPEC.md sections, the JieLi SDK,
  FM-1-RE's documents, datasheets, your own black-box runs in fwtest);
- the status `open`.

Don't ask how another firmware does something, and don't paste or describe
any material you aren't allowed to read. A question about fwtest's
behaviour (a capture, an exit code, an option) is not a spec request: open
an issue or a pull request against docs/HARNESS.md.

## Answering (spec side)

- Answer by adding the fact to `HARDWARE-SPEC.md`, with its source, as
  every fact there has (M0c's rules: facts only, never code or code
  structure; a fact whose only source is the emulator is marked so).
- Then set the request's status to `answered`, with a link to the section,
  in the same pull request. Nothing else goes in the request: no code, no
  explanation of how any other firmware or the emulator does it, no
  excerpts.
- If the fact isn't known, say so (`unknown`), with what would settle it
  (a probe on real hardware, a datasheet). If answering would take
  something the spec side may not pass on, say `declined` and why, in
  general terms.
- The spec side's text discipline applies to the whole exchange
  (CONTRIBUTING.md, "Spec-side text discipline"; C-SEP-TERMS checks it).

## Template

```markdown
### SR-<n>: <the question, in a few words>
- Asked: <YYYY-MM-DD>, <who or which session>
- Question: <one fact, asked narrowly>
- Why: <what the firmware needs it for; what was tried or read>
- Status: open | answered (HARDWARE-SPEC.md, "<section>") | unknown | declined
- Answered: <YYYY-MM-DD>, <who or which session>
```

## Requests

None yet.
