# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import json
import os
import shutil
import tempfile
import unittest

from tests.helpers import ROOT, load_tool

dl = load_tool("check-deny-lists.py")
CONFIG = os.path.join(ROOT, "config", "claude")


class DenyListTest(unittest.TestCase):
    """Requirements: R-CLEAN-4"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        for n in os.listdir(CONFIG):
            shutil.copyfile(os.path.join(CONFIG, n), os.path.join(self.dir, n))

    def tearDown(self):
        shutil.rmtree(self.dir)

    def edit(self, name, fn):
        p = os.path.join(self.dir, name)
        with open(p) as f:
            data = json.load(f)
        fn(data)
        with open(p, "w") as f:
            json.dump(data, f)

    def test_committed_configs_pass(self):
        self.assertEqual(dl.check(CONFIG), [])

    def test_clean_config_keeps_the_handmade_rules_unchanged(self):
        with open(os.path.join(CONFIG, "handmade-settings.json")) as f:
            handmade = json.load(f)["permissions"]["deny"]
        with open(os.path.join(CONFIG, "clean.json")) as f:
            clean = json.load(f)["permissions"]["deny"]
        self.assertEqual(clean[:len(handmade)], handmade)

    def test_dropping_any_entry_fails(self):
        for role in ("clean", "spec", "auditor", "porter"):
            with open(os.path.join(CONFIG, role + ".json")) as f:
                rules = json.load(f)["permissions"]["deny"]
            for rule in rules:
                self.setUp()
                self.edit(role + ".json",
                          lambda d: d["permissions"]["deny"].remove(rule))
                self.assertTrue(dl.check(self.dir), "%s %s" % (role, rule))

    def test_dropping_from_the_baseline_fails(self):
        # an entry ORIGINAL holds (a later one is still required of the config)
        self.edit("deny-baseline.json", lambda d: d["spec"].remove("Bash(git clone*dinghy*)"))
        self.assertTrue(dl.check(self.dir))

    def test_dropping_from_the_auditor_baseline_fails(self):
        self.edit("deny-baseline.json", lambda d: d["auditor"].pop())
        self.assertTrue(dl.check(self.dir))

    def test_dropping_from_the_porter_baseline_fails(self):
        self.edit("deny-baseline.json", lambda d: d["porter"].pop())
        self.assertTrue(dl.check(self.dir))

    def test_clean_and_spec_deny_cloning_the_port_repository(self):
        # since evening-1024 (the owner's decision)
        rule = "Bash(git clone*small-beeps-ports*)"
        for role in ("clean", "spec"):
            with open(os.path.join(CONFIG, role + ".json")) as f:
                self.assertIn(rule, json.load(f)["permissions"]["deny"], role)
            self.setUp()
            self.edit(role + ".json",
                      lambda d: d["permissions"]["deny"].remove(rule))
            self.assertTrue(dl.check(self.dir), role)

    def test_adding_an_entry_passes(self):
        self.edit("spec.json", lambda d: d["permissions"]["deny"].append("WebFetch(domain:example.org)"))
        self.assertEqual(dl.check(self.dir), [])

    def test_clean_config_must_turn_lazy_fetching_off(self):
        self.edit("clean.json", lambda d: d.pop("env"))
        self.assertTrue(dl.check(self.dir))

    def test_missing_banner_hook_fails(self):
        self.edit("clean.json", lambda d: d.pop("hooks"))
        self.assertTrue(dl.check(self.dir))

    def test_changed_handmade_file_fails(self):
        for name in ("handmade-settings.json", "handmade-spec-settings.json"):
            self.setUp()
            with open(os.path.join(self.dir, name), "a") as f:
                f.write("\n")
            self.assertTrue(dl.check(self.dir), name)

    def test_spec_config_keeps_the_handmade_spec_rules(self):
        with open(os.path.join(CONFIG, "handmade-spec-settings.json")) as f:
            handmade = json.load(f)["permissions"]["deny"]
        with open(os.path.join(CONFIG, "spec.json")) as f:
            spec = json.load(f)["permissions"]["deny"]
        self.assertEqual(spec[:len(handmade)], handmade)


if __name__ == "__main__":
    unittest.main()
