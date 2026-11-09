"""B9 stock dynamics, scaled collapse thresholds and unseeded regeneration."""

import tempfile
import unittest

from scipy.stats import kstest

from simulation.environment.concurrent_env import ConcurrentEnv
from simulation.persona.common import PersonaAction, PersonaActionChat, PersonaActionHarvesting
from simulation.study_config import compose_study_config


def one_empty_cycle(env, post_stock=None):
    agent, obs = env.reset()
    while env.phase == "lake":
        agent, obs, _, _ = env.step(PersonaActionHarvesting(agent, "lake", 0))
    while env.phase == "pool_after_harvesting":
        agent, obs, _, _ = env.step(PersonaAction(agent, "lake"))
    agent, obs, _, _ = env.step(PersonaActionChat(agent, "restaurant", [], None, html_interactions=["summary", "limit"]))
    if post_stock is not None:
        env.internal_global_state["resource_in_pool"] = post_stock
    for _ in env.agents:
        agent, obs, _, terminated = env.step(PersonaAction(agent, "home"))
    return terminated


class MechanicsTest(unittest.TestCase):
    def test_scaled_collapse_boundary_uses_post_harvest_stock(self):
        for condition, threshold in (("baseline_N8", 5), ("coord_N16", 10), ("coord_N32", 20)):
            cfg = compose_study_config(condition, 0).experiment.env
            with tempfile.TemporaryDirectory() as temp:
                names = {f"persona_{i}": f"Agent{i}" for i in range(cfg.num_agents)}
                env = ConcurrentEnv(cfg, temp, names, regen_factor_range=(1.0, 3.0))
                terminated = one_empty_cycle(env, threshold - 1)
                self.assertTrue(all(terminated.values()))
                self.assertEqual(env.internal_global_state["resource_in_pool"], (threshold - 1) * 2)
                terminated = one_empty_cycle(env, threshold)
                self.assertFalse(any(terminated.values()))

    def test_regeneration_is_uniform_and_not_repeated_by_project_seed(self):
        cfg = compose_study_config("replica_N8", 0).experiment.env
        with tempfile.TemporaryDirectory() as temp:
            names = {f"persona_{i}": f"Agent{i}" for i in range(8)}
            env = ConcurrentEnv(cfg, temp, names, regen_factor_range=(1.0, 3.0))
            samples = []
            for _ in range(512):
                one_empty_cycle(env)
                samples.append(env.regen_factor)
            self.assertTrue(all(1 <= factor <= 3 for factor in samples))
            self.assertNotEqual(samples[0], samples[1])
            self.assertGreater(kstest(samples, "uniform", args=(1, 2)).pvalue, 1e-6)


if __name__ == "__main__":
    unittest.main()
