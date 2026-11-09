"""A10 checks for the user-defined nulls and explicit undefined results."""

import unittest

from study_analysis import adoption, graph_measures, null_comparisons


class AnalysisTest(unittest.TestCase):
    def test_adoption_splits_ties_and_has_no_credit_without_agreement(self):
        self.assertEqual(adoption({"Julia": 2, "Kate": 2, "Jack": 3}, 2), {"Julia": 0.5, "Kate": 0.5, "Jack": 0})
        self.assertIsNone(adoption({"Julia": 2}, None))

    def test_empty_graph_has_explicitly_undefined_eigenvector(self):
        result = graph_measures(["Julia", "Kate"], [])
        self.assertEqual(result["eigenvector_status"], "undefined")
        self.assertIsNone(result["eigenvector"])
        self.assertEqual(result["degree"], {"Julia": 0, "Kate": 0})

    def test_fixed_opener_random_chain_and_conditional_influence_are_repeatable(self):
        names = ["Julia", "Kate"]
        turns = [
            {"speaker_identity": "Julia", "mentioned_identities": ["Kate"], "nominee_resolved": "Kate", "nominee_options": names},
            {"speaker_identity": "Kate", "mentioned_identities": ["Julia"], "nominee_resolved": None, "nominee_options": []},
        ]
        result = null_comparisons(names, turns, "baseline_N8", 0, 1, samples=1000)
        self.assertEqual(result, null_comparisons(names, turns, "baseline_N8", 0, 1, samples=1000))
        self.assertAlmostEqual(result["airtime"]["mean"], 0.25, delta=0.04)
        self.assertEqual(result["influence"]["degree"]["mean"], 0)


if __name__ == "__main__":
    unittest.main()
