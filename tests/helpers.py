# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Loads the tools (whose file names have hyphens) as modules for tests."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_tool(filename):
    path = os.path.join(ROOT, "tools", filename)
    name = filename.replace("-", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Made-up spec-side folders for the barrier tools' tests (since M3): the
# same kinds and rule IDs as config/spec-side-folders, so the tests run the
# tools' real code without spelling the real folders out. Scratch test
# repositories made by hand use these names too.
PLACEHOLDER_FOLDERS = [
    ("spa/one", "source", "F-VENDOR-EMU", "spa/one/ (spec side)"),
    ("sptwo", "source", "F-HARNESS", "sptwo/ source (spec side)"),
    ("spl/three", "transcripts", "F-SPEC-SESSIONS", "spec-side session transcripts"),
]
PLACEHOLDER_DIRS = tuple(f + "/" for f, _, _, _ in PLACEHOLDER_FOLDERS)
