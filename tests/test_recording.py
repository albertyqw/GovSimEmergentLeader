"""B8/B9 observations must cover all calls without changing responses."""

import asyncio
import contextlib
import gzip
import io
import json
import tempfile
import unittest
import warnings
from pathlib import Path

from simulation.recording import RecordingWrapper, RunRecorder
from simulation.run import run
from simulation.study_config import compose_study_config
from stub_llm import StubLogger, StubModel


def read_jsonl(path):
    with gzip.open(path, "rt") as source:
        return [json.loads(line) for line in source]


class RecordingTest(unittest.TestCase):
    def test_stakes_logs_every_request_snapshot_and_identity(self):
        cfg = compose_study_config("stakes_N8", 0)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            recorder = RunRecorder(path, "stakes_N8", 0, cfg)
            transport = StubModel()
            wrapper = RecordingWrapper(
                transport, recorder, render=False, wanbd_logger=StubLogger(),
                temperature=0.0, top_p=1.0, seed=0, is_api=True,
            )
            with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                asyncio.run(run(cfg.experiment, wrapper.wanbd_logger, wrapper, wrapper, str(path)))
            calls = read_jsonl(path / "calls.jsonl.gz")
            cycles = read_jsonl(path / "cycles.jsonl.gz")
            agents = read_jsonl(path / "agents.jsonl.gz")
            utterances = read_jsonl(path / "utterances.jsonl.gz")
            self.assertEqual(len(calls), len(transport.requests))
            self.assertEqual(len(cycles), 6)
            self.assertEqual(len({row["call_id"] for row in calls}), len(calls))
            self.assertTrue(all(row["call_id"] for row in utterances))
            self.assertTrue(all(row["raw_completion"] is not None for row in calls))
            self.assertTrue(all(row["parse_status"] != "pending" for row in calls))
            self.assertEqual(sum(row["total_earnings"] for row in agents), 8 * 6 * 2 * 1000)
            self.assertTrue(any(row["identity"] == "Isaac" for row in agents))
            self.assertEqual(sum(len(row["catches"]) for row in cycles), 48)
            self.assertEqual(len(list((path / "memory").glob("cycle*/*.json"))), 48)
            metadata = json.loads((path / "run_meta.json").read_text())
            self.assertEqual(metadata["status"], "completed")
            self.assertTrue(metadata["stakes_schedule"])
            self.assertEqual(len(cycles[0]["perceived_leadership"]), 8)
            memories = [m for row in calls for m in row["retrieved_memories"]]
            self.assertTrue(memories)
            self.assertTrue(all(m["id"] is not None and m["type"] for m in memories))


if __name__ == "__main__":
    unittest.main()
