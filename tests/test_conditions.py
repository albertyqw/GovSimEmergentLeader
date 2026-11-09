"""B4/B9 native runs and exact baseline system prompt checks."""

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from simulation.intervention_randomness import NAME_POOL
from simulation.interventions import VALUES_AGENDA, STAKES_INSTRUCTION
from simulation.paper_definitions import HONESTY_PROMPT, SVO_PRIVACY_PROMPT
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
                for text in prompts:
                    self.assertNotRegex(text.lower(), r"6 cycles|six months|final month|last month of the game")
                    if condition != "replica_N8":
                        self.assertNotIn("The current policy following the mayor's agenda", text)
                        self.assertNotIn("As a leader, you will now craft your policy agenda", text)
                    if "Task: With a fishing range" in text or "Scenario:" in text:
                        self.assertIn(HONESTY_PROMPT, text)
                    self.assertNotIn("will reproduce and double once", text)
                for row in transport.requests:
                    request = row["request"]
                    fresh = request["messages"][-1]["content"].startswith("Rating (1 to 10):")
                    self.assertEqual(request["max_tokens"], 1000 if fresh else 16000)
                self.assertEqual(list(cfg.experiment.phases), ["harvesting", "discussion", "reflection"])
                self.assertEqual(cfg.experiment.agent.leader_population, "none")
                if condition == "stakes_N8":
                    self.assertTrue(any("You are Isaac [months remaining:" in text for text in prompts))
                    self.assertTrue(all(STAKES_INSTRUCTION in text for text in prompts if "You are " in text))
                    self.assertTrue(any("You are Julia [months remaining: 11]" in text for text in prompts))
                    self.assertTrue((Path(temp) / "identities/Isaac/MEMORY.md").exists())
                    for text in prompts:
                        if "You are " in text:
                            self.assertRegex(text, r"You are [A-Za-z]+ \[months remaining: \d+\]")
                        scenario = re.search(r"Scenario: (.*?) are engaged", text)
                        if scenario:
                            names = re.findall(r"\b(?:" + "|".join(NAME_POOL) + r")\b", scenario.group(1))
                            self.assertEqual(len(names), 8)
                            self.assertEqual(scenario.group(1).count("[months remaining:"), 8)
                if condition == "values_N8":
                    svo = [text for text in prompts if "Your SVO is:" in text]
                    self.assertTrue(svo)
                    self.assertTrue(all("You are Julia," in text for text in svo))
                    self.assertTrue(all("You are a fisherman in the fishing community" in text for text in svo))
                    self.assertTrue(all("You are an leader" not in text for text in svo))
                    self.assertTrue(all(SVO_PRIVACY_PROMPT in text for text in svo))
                    self.assertTrue(all(SVO_PRIVACY_PROMPT not in text for text in prompts if "Your SVO is:" not in text))
                    self.assertTrue(all("You are Julia," in text for text in prompts if VALUES_AGENDA in text))
                if condition.startswith("coord_"):
                    self.assertTrue(any(f"carrying capacity of {100 * n // 8}" in text for text in prompts))


if __name__ == "__main__":
    unittest.main()
