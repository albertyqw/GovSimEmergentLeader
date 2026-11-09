"""Paper-equation boundaries and keyed SVO ranges, with legacy paths intact."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from simulation.environment.concurrent_env import ConcurrentEnv
from simulation.paper_definitions import sustainability_threshold
from simulation.paper_definitions import HONESTY_PROMPT, DECEPTION_PROMPT, SVO_PRIVACY_PROMPT
from simulation.persona.cognition import leaders
from simulation.persona.persona import SVOPersonaType
from simulation.study_config import compose_study_config


class PaperDefinitionsTest(unittest.TestCase):
    def test_paper_prompt_semantics_are_private_and_keep_an_original_path(self):
        persona = SimpleNamespace(cfg=SimpleNamespace(paper_definitions=True), svo_type=SVOPersonaType.PROSOCIAL,
                                  svo_angle=30, focal_values=True, disinfo=False, paper_disinformation=False,
                                  current_leader=None)
        svo, truthful, _ = leaders.get_leader_persona_prompts(persona)
        self.assertEqual(truthful, HONESTY_PROMPT)
        self.assertIn(SVO_PRIVACY_PROMPT, svo)
        self.assertIn("You are a fisherman", svo)
        self.assertEqual(svo.lower().count("altruistic individual"), 1)
        self.assertIn("(doing well for oneself).\nA PROSOCIAL", svo)
        persona.paper_disinformation = True
        self.assertEqual(leaders.get_leader_persona_prompts(persona)[1], DECEPTION_PROMPT)
        persona.cfg.paper_definitions = False
        old_svo, old_truthful, _ = leaders.get_leader_persona_prompts(persona)
        self.assertNotIn(SVO_PRIVACY_PROMPT, old_svo)
        self.assertEqual(old_truthful, leaders.HONEST_AGENDA_PROMPT)

    def test_threshold_uses_capacity_and_preserves_fractional_values_at_each_n(self):
        for condition, n in (("baseline_N8", 8), ("coord_N16", 16), ("coord_N32", 32)):
            cfg = compose_study_config(condition, 0).experiment.env
            with tempfile.TemporaryDirectory() as temp:
                env = ConcurrentEnv(cfg, temp, {f"persona_{i}": f"Agent{i}" for i in range(n)}, regen_factor_range=(1, 3))
                env.reset()
                for fraction, expected in ((1, 6.25), (0.8, 3.75), (0.5, 0), (0.25, 0)):
                    env.internal_global_state["resource_in_pool"] = cfg.initial_resource_in_pool * fraction
                    env._set_sustainability_threshold()
                    self.assertEqual(env.internal_global_state["sustainability_threshold"], expected)
                cfg.paper_definitions = False
                env.internal_global_state["resource_in_pool"] = cfg.initial_resource_in_pool / 2
                env._set_sustainability_threshold()
                self.assertEqual(env.internal_global_state["sustainability_threshold"], 3)
        self.assertAlmostEqual(sustainability_threshold(100, 100, 8, 1.57), 57 / 12.56)

    def test_paper_altruistic_range_is_keyed_and_original_sampler_stays_unchanged(self):
        angles = []
        with patch.object(leaders.np.random, "uniform", return_value=70) as legacy:
            for seed in range(25):
                first = leaders.sample_leader_svos(leaders.LeaderPopulationType.ONE_ALTRUISTIC, paper_seed=seed)
                second = leaders.sample_leader_svos(leaders.LeaderPopulationType.ONE_ALTRUISTIC, paper_seed=seed)
                self.assertEqual(first, second)
                angles.append(first[0][0])
            legacy.assert_not_called()
            self.assertTrue(all(57.15 <= angle <= 90 for angle in angles))
            self.assertTrue(any(angle > 75 for angle in angles))
            self.assertEqual(leaders.sample_svo_angle(SVOPersonaType.ALTRUISTIC), 70)
            legacy.assert_called_once_with(57.15, 75.0)


if __name__ == "__main__":
    unittest.main()
