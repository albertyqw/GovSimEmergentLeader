"""B7/B9 each copied YAML differs only in specification-named fields."""

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1] / "simulation/conf/experiment"


def differences(first, second, prefix=()):
    if isinstance(first, dict) and isinstance(second, dict):
        for key in first.keys() | second.keys():
            if key not in first or key not in second:
                yield prefix + (key,)
            else:
                yield from differences(first[key], second[key], prefix + (key,))
    elif first != second:
        yield prefix


class ConfigAllowlistTest(unittest.TestCase):
    def test_only_specified_fields_differ(self):
        original = yaml.safe_load((ROOT / "fish_baseline_concurrent_leaders.yaml").read_text())
        files = [file for file in ROOT.glob("*.yaml") if file.stem.startswith(("replica_N8", "baseline_N8", "values_N8", "stakes_N8", "coord_N"))]
        self.assertEqual(len(files), 10)
        allowed = {
            ("seed",), ("phases",), ("defaults",),
            ("env", "num_agents"), ("env", "initial_resource_in_pool"), ("env", "collapse_threshold"),
            ("personas", "num"), ("agent", "leader_population"), ("agent", "values_plan"),
            ("agent", "stakes_tenure"), ("agent", "lake_scale"), ("agent", "act", "drop_mayor_line"),
        }
        allowed.update(("agent", "converse", flag) for flag in (
            "neutral_announcer", "drop_truthfulness_line", "seeded_opener", "elicitation", "perceived_leadership"
        ))
        for file in files:
            with self.subTest(file=file.name):
                config = yaml.safe_load(file.read_text())
                for path in differences(original, config):
                    persona_change = len(path) >= 2 and path[0] == "personas" and path[1].startswith("persona_")
                    if persona_change:
                        self.assertTrue(len(path) == 2 or path[2] in ("name", "goals"), path)
                    else:
                        self.assertIn(path, allowed)
                self.assertEqual(config["defaults"][:len(original["defaults"])], original["defaults"])


if __name__ == "__main__":
    unittest.main()
