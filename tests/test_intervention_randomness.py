"""B6/B9: keyed draws, counterbalancing, and the exact ordered name pool."""

import ast
import re
import unittest
from collections import Counter
from pathlib import Path

from simulation import intervention_randomness as draws


ROOT = Path(__file__).resolve().parents[1]


class InterventionRandomnessTest(unittest.TestCase):
    def test_names_match_methods_in_order(self):
        text = (ROOT / "METHODS.md").read_text().split("**Name pool, in order.**", 1)[1]
        names = re.search(r"```\n(.*?)\n```", text, re.S).group(1).split(", ")
        self.assertEqual(tuple(names), draws.NAME_POOL)
        self.assertEqual(len(set(names)), 40)

    def test_schedule_has_focal_and_fixed_spread(self):
        for seed in range(5):
            horizons = draws.initial_stakes_horizons(seed)
            self.assertEqual(horizons, draws.initial_stakes_horizons(seed))
            self.assertEqual(len(horizons), 8)
            self.assertEqual(horizons[seed % 8], 16)
            self.assertEqual(horizons.count(16), 1)
            short = Counter(h for h in horizons if h != 16)
            self.assertTrue(all(short[h] >= 1 for h in range(3, 9)))
            self.assertEqual(sum(short.values()), 7)

    def test_opener_is_independent_of_other_intervention_draws(self):
        for seed in range(5):
            for cycle in range(1, 7):
                for n in (8, 16, 32):
                    before = draws.opener_slot(seed, cycle, n)
                    draws.initial_stakes_horizons(seed)
                    draws.values_svo_angle(seed)
                    draws.successor_horizon(seed, 0, cycle)
                    self.assertEqual(before, draws.opener_slot(seed, cycle, n))
                    self.assertIn(before, range(n))

    def test_larger_groups_can_open_outside_first_eight_slots(self):
        for n in (16, 32):
            slots = {draws.opener_slot(seed, cycle, n) for seed in range(5) for cycle in range(1, 7)}
            self.assertTrue(any(slot >= 8 for slot in slots))

    def test_angle_and_successor_ranges(self):
        for seed in range(5):
            angle = draws.values_svo_angle(seed)
            self.assertEqual(angle, draws.values_svo_angle(seed))
            self.assertTrue(22.45 <= angle <= 57.15)
            for slot in range(8):
                for cycle in range(1, 7):
                    horizon = draws.successor_horizon(seed, slot, cycle)
                    self.assertEqual(horizon, draws.successor_horizon(seed, slot, cycle))
                    self.assertIn(horizon, range(3, 9))

    def test_module_uses_only_dedicated_random_instances(self):
        tree = ast.parse((ROOT / "simulation/intervention_randomness.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "random":
                self.assertEqual(node.attr, "Random")


if __name__ == "__main__":
    unittest.main()
