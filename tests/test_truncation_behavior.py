"""Fixed-cap partial responses follow the original parser, with full logs."""

import copy
import gzip
import importlib
import json
import tempfile
import unittest
import warnings
from pathlib import Path
from types import SimpleNamespace

from pathfinder import ModelAPI, assistant, user

from simulation.budget import SharedBudget
from simulation.openrouter_handling import attach_openrouter
from simulation.recording import RecordingWrapper, RunRecorder
from simulation.study_config import compose_study_config
from tests.stub_llm import StubLogger


class TruncationBehaviorTest(unittest.TestCase):
    def test_original_parse_continuation_and_zero_fallback_keep_caps_and_are_logged(self):
        cases = (
            (["Reasoning. Answer: 7 and unfinished detail"], "7", False),
            (["Unfinished reasoning without a decision", "Answer: 6"], "6", False),
            (["Unfinished reasoning without a decision", "Still undecided"], "0", True),
        )
        for responses, expected, fallback in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp:
                cfg = compose_study_config("replica_N8", 0, cycles=1)
                recorder = RunRecorder(Path(temp) / "run", "replica_N8", 0, cfg, provider="google-ai-studio")
                budget = SharedBudget(Path(temp) / "cost.sqlite")
                calls = []
                tape = iter(responses)

                def create(**kwargs):
                    content = next(tape)
                    calls.append(copy.deepcopy(kwargs))
                    finish = "length" if len(calls) == 1 else "stop"
                    raw = {"id": f"local-{len(calls)}", "model": "google/gemini-2.5-flash-lite", "provider": "Google AI Studio",
                           "choices": [{"message": {"content": content}, "finish_reason": finish}],
                           "usage": {"prompt_tokens": 20, "completion_tokens": 5, "cost": 0.001,
                                     "prompt_tokens_details": {"cached_tokens": 0},
                                     "completion_tokens_details": {"reasoning_tokens": 0}}}
                    return SimpleNamespace(model_dump=lambda **_: copy.deepcopy(raw), system_fingerprint=None,
                                           choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)])

                adapter = importlib.import_module(ModelAPI.__module__).OpenRouter
                model = adapter.__new__(adapter)
                ModelAPI.__init__(model, "google/gemini-2.5-flash-lite", 0)
                model.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
                                               _client=SimpleNamespace(event_hooks={"response": []}))
                attach_openrouter(model, recorder, budget, {"prompt": "0.0000001", "completion": "0.0000004"},
                                  sleep=lambda _: None, get=lambda _: self.fail("Unexpected metadata request"))
                wrapper = RecordingWrapper(model, recorder, render=False, wanbd_logger=StubLogger(),
                                           temperature=0.0, top_p=1.0, seed=0, is_api=True)
                wrapper.study_generation_max_tokens = 16000
                lm, chain = wrapper.start_chain_async("Julia", "harvesting", "choose_act_options")
                with warnings.catch_warnings(record=True):
                    with user():
                        lm += "Provide reasoning followed by Answer: N tons."
                    with assistant():
                        lm = wrapper.gen(lm, "reasoning", stop_regex=r"Answer:", save_stop_text=True, chain=chain)
                        lm = wrapper.find(lm, regex=r"\d+", default_value="0", name="option", chain=chain)
                self.assertEqual(lm["option"], expected)
                wrapper.end_chain("Julia", lm, chain=chain)
                budget.check()
                self.assertEqual(len(calls), len(responses))
                self.assertEqual([call["max_tokens"] for call in calls], [16000] * len(responses))
                self.assertEqual(budget.totals(), (0.001 * len(responses), 0))
                if len(calls) > 1:
                    self.assertEqual(calls[1]["messages"][-1]["role"], "assistant")
                    self.assertEqual(calls[1]["messages"][-1]["content"], responses[0])
                with gzip.open(recorder.path / "calls.jsonl.gz", "rt") as source:
                    rows = [json.loads(line) for line in source]
                self.assertEqual(rows[0]["finish_reason"], "length")
                self.assertTrue(rows[0]["truncated"])
                with gzip.open(recorder.path / "errors.jsonl.gz", "rt") as source:
                    errors = [json.loads(line) for line in source]
                self.assertEqual(errors[0]["type"], "length")
                self.assertEqual(errors[0]["resolution"], "continued_repository_parser")
                if fallback:
                    operation = next(op for op in rows[-1]["parse_operations"] if op["name"] == "option")
                    self.assertEqual(operation["status"], "failed")
                    self.assertTrue(operation["fallback_applied"])
                    self.assertEqual(operation["fallback_value"], "0")
                    self.assertEqual(rows[-1]["parsed_output"]["option"], "0")


if __name__ == "__main__":
    unittest.main()
