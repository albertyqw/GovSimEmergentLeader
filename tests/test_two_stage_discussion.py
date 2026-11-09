"""Mandatory coverage, hidden judge choices, random fallback and phase nulls."""

import asyncio
import contextlib
import io
import json
import tempfile
import unittest
import warnings
from pathlib import Path

from check_data import check_run
from simulation.recording import RecordingWrapper, RunRecorder
from simulation.run import run
from simulation.study_config import compose_study_config
from stub_llm import StubLogger, StubModel
from test_recording import read_jsonl
from study_analysis import null_comparisons


class TwoStageTest(unittest.TestCase):
    def execute(self, directory, condition="baseline_N8", **model_options):
        cfg = compose_study_config(condition, 0, cycles=1)
        recorder = RunRecorder(directory, condition, 0, cfg)
        model = StubModel(**model_options)
        wrapper = RecordingWrapper(model, recorder, render=False, wanbd_logger=StubLogger(),
                                   temperature=0.0, top_p=1.0, seed=0, is_api=True)
        with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings(record=True):
            asyncio.run(run(cfg.experiment, wrapper.wanbd_logger, wrapper, wrapper, str(directory)))
        return check_run(directory, null_samples=2)

    def test_everyone_speaks_once_despite_early_close_and_last_opening_hands_off(self):
        for condition, n in (("baseline_N8", 8), ("coord_N16", 16), ("coord_N32", 32)):
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as temp:
                p = Path(temp) / "run"
                result = self.execute(p, condition, early_close=True)
                turns = read_jsonl(p / "utterances.jsonl.gz")
                self.assertEqual(len({t["speaker_identity"] for t in turns[:n]}), n)
                self.assertTrue(all(t["discussion_stage"] == "opening" and not t["end_conversation"] for t in turns[:n]))
                self.assertTrue(all(t["nominee_resolved"] is None and t["nomination_source"] == "fixed_opening" for t in turns[:n-1]))
                self.assertEqual(turns[n-1]["nominee_resolved"], turns[n]["speaker_identity"])
                self.assertEqual(result["cycles"][0]["discussion_phases"]["opening"]["airtime_gini"], 0)
                self.assertEqual(result["nomination_judgments"]["count"], 0)

    def test_total_cap_includes_report_and_both_phases(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "run"
            result = self.execute(p, "coord_N32", turns=999)
            stages = result["cycles"][0]["discussion_phases"]
            self.assertEqual(stages["opening"]["utterances"], 32)
            self.assertEqual(stages["nomination"]["utterances"], 17)
            cycle = read_jsonl(p / "cycles.jsonl.gz")[0]
            self.assertEqual(cycle["number_of_utterances"] + cycle["framework_messages"], 50)

    def test_hidden_judge_can_resolve_or_choose_contextually_then_random_if_unclear(self):
        for answer, style, source in (("Kate", "invalid", "judge"), ("Nora", "everyone", "judge"),
                                      ("UNCLEAR", "everyone", "random"), ("MALFORMED", "invalid", "random"),
                                      ("Atlantis", "invalid", "random")):
            with self.subTest(answer=answer), tempfile.TemporaryDirectory() as temp:
                p = Path(temp) / "run"
                condition = "coord_N16" if answer == "Nora" else "stakes_N8"
                result = self.execute(p, condition, nomination_style=style, judge_answer=answer)
                events = read_jsonl(p / "nomination_judgments.jsonl.gz")
                calls = read_jsonl(p / "calls.jsonl.gz")
                turns = read_jsonl(p / "utterances.jsonl.gz")
                self.assertEqual(len(events), 1)
                event = events[0]
                self.assertEqual(event["resolution_source"], source)
                self.assertEqual(event["raw_nomination"], "Everyone" if style == "everyone" else "Anonymous Leader")
                event_turn = next(t for t in turns if t["judge_intervention_id"])
                self.assertEqual(turns[event_turn["position"]+1]["speaker_identity"], event["resolved_identity"])
                if source == "judge":
                    self.assertEqual(event["resolved_identity"], answer)
                else:
                    self.assertTrue(event["random_fallback"]["applied"])
                    self.assertIn(event["resolved_identity"], event["eligible_identities"])
                self.assertEqual(sum(c["call_type"] == "nomination_judge" for c in calls), 1)
                self.assertEqual(next(c for c in calls if c["call_type"] == "nomination_judge")["request"]["max_tokens"], 16000)
                for call in calls:
                    if call["call_type"] != "nomination_judge":
                        text = json.dumps(call["request"])
                        self.assertNotIn("judge-only-private-evidence-marker", text)
                        self.assertNotIn("You are reviewing an invalid speaker nomination", text)
                for file in (p / "memory").rglob("*.json"):
                    self.assertNotIn("judge-only-private-evidence-marker", file.read_text())
                self.assertEqual(result["nomination_judgments"]["count"], 1)
                before = (p / "nomination_judgments.jsonl.gz").read_bytes()
                check_run(p, null_samples=1)
                self.assertEqual((p / "nomination_judgments.jsonl.gz").read_bytes(), before)

    def test_running_table_appends_independent_events_without_replacing_earlier_rows(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as temp:
            cfg = compose_study_config("baseline_N8", 0, cycles=1)
            recorder = RunRecorder(Path(temp) / "run", "baseline_N8", 0, cfg)
            recorder.provider = "test-paid-table-only"
            recorder.nomination_table_path = Path(temp) / "table.sqlite"
            for position in (7, 10):
                recorder.record_nomination_judgment({"cycle": 1, "position": position,
                    "resolution_source": "judge", "resolved_identity": "Kate"})
            with sqlite3.connect(recorder.nomination_table_path) as db:
                self.assertEqual(db.execute("SELECT position, resolved_identity FROM nomination_judgments ORDER BY position").fetchall(),
                                 [(7, "Kate"), (10, "Kate")])
            self.assertEqual(len(read_jsonl(Path(temp) / "run/nomination_judgments.jsonl.gz")), 2)

    def test_null_keeps_compulsory_round_and_randomizes_subsequent_chain(self):
        names = ["Julia", "Kate"]
        opening = [{"speaker_identity": name, "discussion_stage": "opening", "mentioned_identities": [],
                    "nominee_resolved": None, "nominee_options": []} for name in names]
        result = null_comparisons(names, opening, "baseline_N8", 0, 1, samples=100)
        self.assertEqual(result["airtime"]["mean"], 0)
        opening[-1]["nominee_options"] = names
        free = [{"speaker_identity": "Julia", "discussion_stage": "nomination", "mentioned_identities": [],
                 "nominee_resolved": "Julia", "nominee_options": names},
                {"speaker_identity": "Julia", "discussion_stage": "nomination", "mentioned_identities": [],
                 "nominee_resolved": None, "nominee_options": []}]
        result = null_comparisons(names, opening + free, "baseline_N8", 0, 1, samples=1000)
        self.assertAlmostEqual(result["airtime"]["mean"], 0.125, delta=0.025)


if __name__ == "__main__":
    unittest.main()
