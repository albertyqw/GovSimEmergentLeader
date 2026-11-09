"""B4/B9 native runs and exact baseline system prompt checks."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from simulation.intervention_randomness import NAME_POOL
from simulation.interventions import VALUES_AGENDA, STAKES_INSTRUCTION
from simulation.persona.cognition import utils
from simulation.study_config import CONDITIONS, compose_study_config
from test_simulation_stub import run_stub


ROOT = Path(__file__).resolve().parents[1]


class ConditionsTest(unittest.TestCase):
    def test_n8_system_prompt_is_original_byte_for_byte(self):
        source = subprocess.check_output(
            ["git", "show", "8cf0aba:simulation/persona/cognition/utils.py"], cwd=ROOT, text=True
        )
        original = {}
        exec(compile(source, "original_utils.py", "exec"), original)
        for low, high in ((1.0, 3.0), (2.0, 2.0)):
            for goals in ("", "\n\nA personal goal."):
                persona = SimpleNamespace(name="Julia", goals=goals, lake_scale=1,
                                          env=SimpleNamespace(regen_min_range=low, regen_max_range=high))
                self.assertEqual(utils.get_sytem_prompt_v3(persona), original["get_sytem_prompt_v3"](persona))

    def test_values_agenda_rotates_in_config_and_no_candidate_is_registered(self):
        for seed in range(5):
            cfg = compose_study_config("values_N8", seed)
            self.assertEqual(cfg.group_name, "values_N8")
            self.assertEqual(cfg.experiment.agent.leader_population, "none")
            for slot in range(8):
                expected = "\n\n" + VALUES_AGENDA if slot == seed % 8 else ""
                self.assertEqual(cfg.experiment.personas[f"persona_{slot}"].goals, expected)
            self.assertEqual(list(cfg.experiment.phases), ["harvesting", "discussion", "reflection"])

    def test_all_conditions_complete_six_native_stub_cycles(self):
        for condition in CONDITIONS:
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as temp:
                cfg = compose_study_config(condition, 0)
                transport, _, _ = run_stub(cfg.experiment, temp)
                rows = json.loads((Path(temp) / "log_env.json").read_text())
                catches = [row for row in rows if row["action"] == "harvesting"]
                n = cfg.experiment.env.num_agents
                self.assertEqual(len(catches), n * 6)
                self.assertTrue(all(row["resource_collected"] == 2 for row in catches))
                self.assertTrue(all(row["resource_in_pool_before_harvesting"] <= 100 * n // 8 for row in catches))
                native = [json.loads(line) for line in (Path(temp) / "consolidated_results.json").read_text().splitlines()]
                stats = next(row["data"] for row in native if row["type"] == "round_stats")
                final_stock = next(row["data"]["num_resources"] for row in native if row["type"] == "election")
                self.assertEqual(stats["0"]["regen_factor"], 2.0)
                for cycle in range(6):
                    post = stats[str(cycle)]["num_resources"]
                    factor = stats[str(cycle)]["regen_factor"]
                    expected_stock = int(min(100 * n // 8, post * factor))
                    observed = final_stock if cycle == 5 else next(
                        row["resource_in_pool_before_harvesting"] for row in catches if row["round"] == cycle + 1
                    )
                    self.assertEqual(observed, expected_stock)
                prompts = [row["request"]["messages"][0]["content"] for row in transport.requests]
                if condition == "stakes_N8":
                    self.assertTrue(any("You are Isaac [months remaining:" in text for text in prompts))
                    self.assertTrue(all(STAKES_INSTRUCTION in text for text in prompts if "You are " in text))
                    self.assertTrue(any("You are Julia [months remaining: 11]" in text for text in prompts))
                    self.assertTrue((Path(temp) / "identities/Isaac/MEMORY.md").exists())
                if condition == "values_N8":
                    svo = [text for text in prompts if "Your SVO is:" in text]
                    self.assertTrue(svo)
                    self.assertTrue(all("You are Julia," in text for text in svo))
                    self.assertTrue(all("You are a fisherman in the fishing community" in text for text in svo))
                    self.assertTrue(all("You are an leader" not in text for text in svo))
                if condition.startswith("coord_"):
                    self.assertTrue(any(f"carrying capacity of {100 * n // 8}" in text for text in prompts))


if __name__ == "__main__":
    unittest.main()
