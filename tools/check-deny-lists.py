#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Deny lists never drop an entry (R-CLEAN-4, check C-DENY-LISTS).

Fails if config/claude/clean.json or spec.json lacks any deny rule that
  - config/claude/deny-baseline.json lists for it (entries may be added to
    the baseline, never removed), or
  - is in ORIGINAL below (the lists as first committed; a change to this
    file would show in review), or
  - (clean only) is in config/claude/handmade-settings.json, the owner's
    hand-made file, whose SHA-256 must stay the one in docs/EXPOSURE.md.
Also checks that both configs run tools/session-banner.sh on every
SessionStart.
"""
import hashlib
import json
import os
import sys

HANDMADE_SHA256 = "a557bd84008372ff9d3e24cd648df9986d76a05928d9f50b5d3e60975bf29b32"
BANNER = '"$CLAUDE_PROJECT_DIR"/tools/session-banner.sh'
ORIGINAL = {
    "clean": [
        "Read(./vendor/emulator/**)",
        "Read(./harness/**)",
        "Read(**/fm1-sid/**)",
        "WebFetch(domain:hugelton.github.io)",
        "WebFetch(domain:thefirmwarehub.com)",
        "Bash(git clone*Felucca*)",
        "Bash(git clone*felucca*)",
        "Bash(git clone*dinghy*)",
        "Bash(git clone*fm1-emu*)",
        "Bash(git clone*f-emulator*)",
    ],
    "spec": [
        "Read(**/fm1-sid/**)",
        "Read(**/probes/lcdtest.c)",
        "WebFetch(domain:hugelton.github.io)",
        "WebFetch(domain:thefirmwarehub.com)",
        "Bash(git clone*Felucca*)",
        "Bash(git clone*felucca*)",
        "Bash(git clone*dinghy*)",
    ],
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def deny_of(cfg):
    return cfg.get("permissions", {}).get("deny", [])


def has_banner_hook(cfg):
    for entry in cfg.get("hooks", {}).get("SessionStart", []):
        if entry.get("matcher", "*") not in ("*", ""):
            continue
        for h in entry.get("hooks", []):
            if h.get("type") == "command" and h.get("command") == BANNER:
                return True
    return False


def check(config_dir):
    problems = []
    baseline = load(os.path.join(config_dir, "deny-baseline.json"))
    handmade_path = os.path.join(config_dir, "handmade-settings.json")
    with open(handmade_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if digest != HANDMADE_SHA256:
        problems.append("handmade-settings.json changed (sha256 %s)" % digest)
    handmade = deny_of(load(handmade_path))

    for role in ("clean", "spec"):
        cfg = load(os.path.join(config_dir, role + ".json"))
        deny = deny_of(cfg)
        required = list(ORIGINAL[role]) + list(baseline.get(role, []))
        if role == "clean":
            required += handmade
        missing = sorted(set(r for r in required if r not in deny))
        for r in missing:
            problems.append("%s.json dropped deny rule %s" % (role, r))
        for r in ORIGINAL[role]:
            if r not in baseline.get(role, []):
                problems.append("deny-baseline.json dropped %s rule %s" % (role, r))
        if not has_banner_hook(cfg):
            problems.append("%s.json has no SessionStart hook running %s" % (role, BANNER))
        print("%s.json: %d deny rules, %d required, banner hook %s"
              % (role, len(deny), len(set(required)),
                 "present" if has_banner_hook(cfg) else "MISSING"))
    return problems


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "config", "claude")
    problems = check(config_dir)
    for p in problems:
        print("FAIL " + p)
    print("deny lists: %s" % ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
