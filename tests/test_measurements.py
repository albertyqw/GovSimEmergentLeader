"""B4/B9: private calls parse, cover silent agents and do not enter memory."""

import tempfile
import re
import unittest
from pathlib import Path

from omegaconf import open_dict

from simulation.measurement_prompts import parse_elicitation, resolve_name
from simulation.intervention_randomness import NAME_POOL
from simulation.study_config import compose_study_config
from test_simulation_stub import original_config, run_stub


class MeasurementTest(unittest.TestCase):
    def test_tolerant_parsing_and_final_month(self):
        parsed = parse_elicitation("plan: 2.5 tons\nlimit: NONE\nreason: Save fish.")
        self.assertEqual(parsed["parse_status"], "ok")
        self.assertEqual(parsed["plan"], 2.5)
        self.assertEqual(parsed["preferred_limit"], "none")
        final = parse_elicitation("LIMIT: 3 tons\nREASON: Save fish.", final_month=True)
        self.assertEqual(final["parse_status"], "ok")
        self.assertIsNone(final["plan"])
        self.assertEqual(parse_elicitation("bad answer")["parse_status"], "failed")

    def test_resolver_rejects_ambiguous_partial_names(self):
        self.assertEqual(resolve_name("JULIA [months remaining: 3]", NAME_POOL), "Julia")
        self.assertEqual(resolve_name("jul", NAME_POOL), "Julia")
        self.assertEqual(resolve_name("Ma", NAME_POOL), "unresolved")
        self.assertEqual(resolve_name("no one", NAME_POOL), "no one")
        for name in NAME_POOL:
            self.assertEqual(resolve_name(name.lower(), NAME_POOL), name)

    def test_extra_calls_include_silent_agents_and_leave_memory_identical(self):
        off = compose_study_config("baseline_N8", 0, cycles=1).experiment
        on = compose_study_config("baseline_N8", 0, cycles=1).experiment
        off.agent.converse.elicitation = False
        off.agent.converse.perceived_leadership = False
        with open_dict(on):
            on.agent.converse.elicitation = True
            on.agent.converse.perceived_leadership = True
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            base, _, _ = run_stub(off, first)
            measured, _, _ = run_stub(on, second)
            self.assertEqual(len(measured.requests) - len(base.requests), 16)
            prompts = [row["request"]["messages"][0]["content"] for row in measured.requests]
            pre = [text for text in prompts if "Before this month's discussion begins" in text]
            post = [text for text in prompts if "whose suggestions, if anyone's" in text]
            self.assertEqual(len(pre), 8)
            self.assertEqual(len(post), 8)
            self.assertTrue(all("Last round's fishing stats:" in text for text in pre))
            first_utterances = {}
            for text in prompts:
                if "Task: What would you say next in the group chat?" in text:
                    name = re.search(r"You are ([A-Za-z]+)", text).group(1)
                    first_utterances.setdefault(name, text.split("\nConversation so far:\n", 1)[0])
            for text in pre:
                name = re.search(r"You are ([A-Za-z]+)", text).group(1)
                if name in first_utterances:
                    self.assertEqual(text.split("\nCurrent public fishing report:\n", 1)[0], first_utterances[name])
            for slot in range(8):
                relative = f"persona_{slot}/MEMORY.md"
                before = (Path(first) / relative).read_text()
                after = (Path(second) / relative).read_text()
                self.assertEqual(before, after)
                self.assertNotIn("PLAN:", after)
                self.assertNotIn("ANSWER:", after)


if __name__ == "__main__":
    unittest.main()
