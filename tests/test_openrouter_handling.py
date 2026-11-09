"""B12 error paths are exercised against a local SDK double, never a model."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from simulation.budget import SharedBudget, StudyHalt
from simulation.openrouter_handling import attach_openrouter
from simulation.recording import RunRecorder
from simulation.study_config import compose_study_config


class APIError(Exception):
    def __init__(self, status, reason):
        self.status_code = status
        self.body = {"error": {"reason": reason}}
        self.response = SimpleNamespace(headers={"Retry-After": "0"})


class OpenRouterHandlingTest(unittest.TestCase):
    def test_transient_budget_retries_reduce_parallel_seeds_and_preserve_parameters(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = compose_study_config("replica_N8", 0, cycles=1)
            recorder = RunRecorder(Path(temp) / "seed0", "replica_N8", 0, cfg, provider="google-ai-studio")
            budget = SharedBudget(Path(temp) / "budget.sqlite")
            model = SimpleNamespace(model_name="google/gemini-2.5-flash", seed=0)
            attempts = []
            raw = {"id": "gen-local", "model": model.model_name, "provider": "Google AI Studio",
                   "choices": [{"finish_reason": "stop", "message": {"content": "Answer: 2"}}],
                   "usage": {"prompt_tokens": 20, "completion_tokens": 5, "cost": 0.001}}

            def original(**kwargs):
                attempts.append(kwargs)
                if len(attempts) <= 3:
                    raise APIError(402, "in_flight_budget_exhausted")
                return SimpleNamespace(model_dump=lambda **kw: raw)

            model.client = SimpleNamespace(
                chat=SimpleNamespace(completions=SimpleNamespace(create=original)),
                _client=SimpleNamespace(event_hooks={"response": []}),
            )
            recorder.begin_chain("Julia", "harvesting", "choose_act_options")
            messages = [{"role": "user", "content": "Local test"}]
            recorder.begin_call(model, messages, 0, 1, 8000)
            attach_openrouter(model, recorder, budget, {"prompt": "0.0000003", "completion": "0.0000025"}, sleep=lambda _: None)
            kwargs = dict(model=model.model_name, messages=messages, temperature=0.0, top_p=1.0, seed=0, max_tokens=8000)
            model.client.chat.completions.create(**kwargs)
            self.assertEqual(len(attempts), 4)
            self.assertEqual(budget.capacity_limit(), 2)
            self.assertEqual(budget.totals(), (0.001, 0))
            for actual in attempts:
                self.assertEqual({key: value for key, value in actual.items() if key != "extra_body"}, kwargs)
                self.assertEqual(actual["extra_body"], {"provider": {"only": ["google-ai-studio"], "allow_fallbacks": False}})

    def test_fatal_credit_failure_sets_shared_halt(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = compose_study_config("replica_N8", 0, cycles=1)
            recorder = RunRecorder(Path(temp) / "seed0", "replica_N8", 0, cfg, provider="google-ai-studio")
            budget = SharedBudget(Path(temp) / "budget.sqlite")

            def original(**kwargs):
                raise APIError(402, "weight_exceeds_budget")

            model = SimpleNamespace(model_name="google/gemini-2.5-flash", seed=0,
                                    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=original)),
                                                           _client=SimpleNamespace(event_hooks={"response": []})))
            recorder.begin_chain("Julia", "harvesting", "choose_act_options")
            messages = [{"role": "user", "content": "Local test"}]
            recorder.begin_call(model, messages, 0, 1, 8000)
            attach_openrouter(model, recorder, budget, {"prompt": "0.0000003", "completion": "0.0000025"}, sleep=lambda _: None)
            with self.assertRaises(APIError):
                model.client.chat.completions.create(model=model.model_name, messages=messages, max_tokens=8000)
            with self.assertRaises(StudyHalt):
                budget.check()
            self.assertEqual(budget.totals(), (0, 0))


if __name__ == "__main__":
    unittest.main()
