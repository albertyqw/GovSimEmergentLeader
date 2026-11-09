"""B9: B5 constants must match the unchanged binding specification."""

import re
import unittest
from pathlib import Path

from simulation import interventions


ROOT = Path(__file__).resolve().parents[1]


class ExactTextsTest(unittest.TestCase):
    def test_all_seven_constants_match_methods(self):
        methods = (ROOT / "METHODS.md").read_text()
        section = methods.split("## B5. Exact texts\n", 1)[1].split("## B6.", 1)[0]
        blocks = re.findall(
            r"\*\*([A-Z_]+):?\*\*[^\n]*\n```\n(.*?)\n```", section, re.S
        )
        self.assertEqual(len(blocks), 7)
        for name, expected in blocks:
            with self.subTest(constant=name):
                self.assertEqual(getattr(interventions, name), expected)
                self.assertFalse(getattr(interventions, name).endswith("\n"))


if __name__ == "__main__":
    unittest.main()
