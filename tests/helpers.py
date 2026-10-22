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
