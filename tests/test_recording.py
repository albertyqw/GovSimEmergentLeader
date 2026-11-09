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
from simulation.intervention_randomness import NAME_POOL
from stub_llm import StubLogger, StubModel
from check_data import check_run
from test_simulation_stub import original_config, run_stub


def read_jsonl(path):
    with gzip.open(path, "rt") as source:
        return [json.loads(line) for line in source]


class RecordingTest(unittest.TestCase):
    def test_stakes_nominations_resolve_tags_bare_case_and_partial_names(self):
        for style in ("tagged", "bare", "lowercase", "partial"):
            with self.subTest(style=style), tempfile.TemporaryDirectory() as temp:
                cfg = compose_study_config("stakes_N8", 0, cycles=1)
                path = Path(temp) / "run"
                recorder = RunRecorder(path, "stakes_N8", 0, cfg)
                transport = StubModel(nomination_style=style)
                wrapper = RecordingWrapper(transport, recorder, render=False, wanbd_logger=StubLogger(),
                                           temperature=0.0, top_p=1.0, seed=0, is_api=True)
                with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings(record=True):
                    asyncio.run(run(cfg.experiment, wrapper.wanbd_logger, wrapper, wrapper, str(path)))
                turns = read_jsonl(path / "utterances.jsonl.gz")
                names = NAME_POOL[:8]
                for current, following in zip(turns, turns[1:]):
                    self.assertEqual(current["nominee_resolved"], names[(names.index(current["speaker_identity"]) + 1) % 8])
                    self.assertEqual(current["nominee_resolved"], following["speaker_identity"])
                    self.assertTrue(current["nominee_raw"])
                self.assertEqual(check_run(path, null_samples=1)["parse_rates"]["nominee_failure_rate"], 0)

    def test_recording_does_not_change_requests_or_memory(self):
        cfg = compose_study_config("baseline_N8", 0, cycles=1)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "observed"
            plain_path = Path(temp) / "plain"
            normal, _, _ = run_stub(cfg.experiment, plain_path)
            recorder = RunRecorder(path, "baseline_N8", 0, cfg)
            observed = StubModel()
            logger = StubLogger()
            wrapper = RecordingWrapper(observed, recorder, render=False, wanbd_logger=logger,
                                       temperature=0.0, top_p=1.0, seed=0, is_api=True)
            with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                asyncio.run(run(cfg.experiment, logger, wrapper, wrapper, str(path)))
            normalize = lambda rows: sorted(json.dumps(row, sort_keys=True) for row in rows)
            self.assertEqual(normalize(normal.requests), normalize(observed.requests))
            for slot in range(8):
                relative = f"persona_{slot}/MEMORY.md"
                self.assertEqual((plain_path / relative).read_text(), (path / relative).read_text())
            # A structurally complete full baseline must not bypass its gate
            # on a later resume after poor instrument parsing.
            metadata_path = path / "run_meta.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["run_kind"] = "full"
            metadata_path.write_text(json.dumps(metadata))
            calls = read_jsonl(path / "calls.jsonl.gz")
            next(row for row in calls if row["call_type"] == "elicitation")["parse_status"] = "failed"
            with gzip.open(path / "calls.jsonl.gz", "wt") as output:
                for row in calls:
                    output.write(json.dumps(row) + "\n")
            with self.assertRaisesRegex(ValueError, "97%"):
                check_run(path, null_samples=1)

    def test_stakes_logs_every_request_snapshot_and_identity(self):
        cfg = compose_study_config("stakes_N8", 0)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            recorder = RunRecorder(path, "stakes_N8", 0, cfg)
            transport = StubModel(multiline_memory=True)
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
            self.assertTrue(any("Planning notes:\nI should" in m["text"] for m in memories))
            checked = check_run(path, null_samples=10)
            self.assertTrue(checked["valid"])
            self.assertEqual(checked["total_catch"], 96)
            self.assertEqual(checked["parse_rates"]["elicitation_success_rate"], 1)
            self.assertEqual(checked["parse_rates"]["perceived_leadership_success_rate"], 1)


if __name__ == "__main__":
    unittest.main()
