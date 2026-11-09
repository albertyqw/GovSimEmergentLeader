"""B12: process-shared reservation accounting and error classification."""

import tempfile
import unittest
from pathlib import Path

from simulation.budget import SharedBudget, StudyHalt
from simulation.openrouter_handling import find_reason, retry_delay


class BudgetTest(unittest.TestCase):
    def test_two_handles_share_pending_reservations_and_actual_spend(self):
        with tempfile.TemporaryDirectory() as temp:
            first = SharedBudget(Path(temp) / "budget.sqlite", limit=1)
            second = SharedBudget(first.path, limit=1)
            first.reserve("one", 0.7)
            with self.assertRaises(StudyHalt):
                second.reserve("two", 0.4)
            with self.assertRaises(StudyHalt):
                first.check()
            self.assertEqual(first.totals(), (0, 0.7))

    def test_settlement_replaces_reservation_with_actual_cost(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = SharedBudget(Path(temp) / "budget.sqlite")
            ledger.reserve("one", 0.02)
            ledger.settle("one", 0.003)
            self.assertEqual(ledger.totals(), (0.003, 0))
            ledger.reserve("two", 0.01)
            ledger.release_unbilled("two")
            self.assertEqual(ledger.totals(), (0.003, 0))

    def test_transient_reason_and_retry_after_are_explicit(self):
        self.assertEqual(find_reason({"error": {"metadata": {"reason": "in_flight_budget_exhausted"}}}), "in_flight_budget_exhausted")
        self.assertEqual(find_reason({"error": {"reason": "weight_exceeds_budget"}}), "weight_exceeds_budget")
        self.assertEqual(retry_delay("17", 1), 17)
        self.assertEqual(retry_delay(None, 3), 8)


if __name__ == "__main__":
    unittest.main()
