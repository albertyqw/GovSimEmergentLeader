"""Run actual phases, agents, memory and parsing with no external model."""

import asyncio
import contextlib
import io
import json
import tempfile
import unittest
import warnings
from pathlib import Path

from hydra import compose, initialize_config_dir
from omegaconf import open_dict

from simulation.intervention_randomness import NAME_POOL, opener_slot
from simulation.interventions import ANNOUNCER_TEMPLATE
from simulation.run import run
from stub_llm import make_wrapper


ROOT = Path(__file__).resolve().parents[1]


def original_config(rounds=1, neutral=False):
    with initialize_config_dir(config_dir=str(ROOT / "simulation/conf"), version_base=None):
        cfg = compose(config_name="config_api", overrides=[
            "experiment=fish_baseline_concurrent_leaders",
            "experiment.agent.leader_population=none",
        ]).experiment
    cfg.env.max_num_rounds = rounds
    cfg.phases = ["harvesting", "discussion", "reflection"]
    cfg.personas.num = 8
    with open_dict(cfg):
        cfg.agent.act.drop_mayor_line = neutral
        cfg.agent.converse.drop_truthfulness_line = neutral
        cfg.agent.converse.neutral_announcer = neutral
        cfg.agent.converse.seeded_opener = neutral
    return cfg


def run_stub(cfg, directory, turns=3):
    wrapper, logger, transport = make_wrapper(seed=cfg.seed, turns=turns)
    with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        asyncio.run(run(cfg, logger, wrapper, wrapper, str(directory)))
    return transport, logger, captured


class SimulationStubTest(unittest.TestCase):
    def test_replica_completes_six_cycles_through_original_phases(self):
        with tempfile.TemporaryDirectory() as temp:
            transport, logger, captured = run_stub(original_config(rounds=6), temp)
            rows = json.loads((Path(temp) / "log_env.json").read_text())
            harvests = [row for row in rows if row["action"] == "harvesting"]
            self.assertEqual(len(harvests), 48)
            self.assertEqual({row["round"] for row in harvests}, set(range(6)))
            self.assertTrue(all(row["resource_collected"] == 2 for row in harvests))
            self.assertTrue(all(row["resource_in_pool_before_harvesting"] <= 100 for row in harvests))
            self.assertTrue(transport.requests)
            for record in transport.requests:
                request = record["request"]
                fresh_rating = request["messages"][-1]["content"].startswith("Rating (1 to 10):")
                self.assertEqual(request["max_tokens"], 1000 if fresh_rating else 8000)
            regex_warnings = [w for w in captured if "missing ) at position" in str(w.message)]
            self.assertEqual(len(regex_warnings), 48)
            self.assertTrue((Path(temp) / "persona_0/MEMORY.md").exists())

    def test_neutral_report_is_public_and_opener_matches_keyed_slot(self):
        with tempfile.TemporaryDirectory() as temp:
            transport, _, _ = run_stub(original_config(neutral=True), temp)
            rows = json.loads((Path(temp) / "log_env.json").read_text())
            utterances = [row for row in rows if row["action"] == "utterance"]
            report = "Last round's fishing stats:\n\n" + "".join(
                f"\t{name} caught 2 tons of fish\n" for name in NAME_POOL[:8]
            )
            self.assertEqual(utterances[0]["agent_name"], "Announcer")
            self.assertEqual(utterances[0]["utterance"], ANNOUNCER_TEMPLATE.format(report=report))
            self.assertEqual(utterances[1]["agent_name"], NAME_POOL[opener_slot(0, 1, 8)])
            prompts = "\n".join(
                message["content"] for record in transport.requests
                for message in record["request"]["messages"]
            )
            self.assertNotIn("The current policy following the mayor's agenda is", prompts)
            self.assertNotIn("As a leader, you will now craft your policy agenda", prompts)


if __name__ == "__main__":
    unittest.main()
