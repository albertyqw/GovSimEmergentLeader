# Flash-Lite smoke review

All runs below use paid `google/gemini-2.5-flash-lite`, seed 0, one cycle, pinned Google AI Studio with fallbacks disabled. No full Flash pilot has started. Generation/fresh-importance caps remain 8000/1000.

| Condition | Attempt | Status | Calls | Cost (USD) | Result |
|---|---|---|---:|---:|---|
| replica_N8 | seed0 | collapsed | 126 | 0.04406774 | failed retrieval-node-ID validation |
| baseline_N8 | seed0 | halted | 78 | 0.02262374 | Completed run failed data validation; B11 requires review |
| replica_N8 | seed0_attempt2 | collapsed | 113 | 0.03321622 | validated |
| baseline_N8 | seed0_attempt2 | collapsed | 120 | 0.02619029 | validated |
| values_N8 | seed0 | collapsed | 118 | 0.02604069 | validated |
| stakes_N8 | seed0 | collapsed | 132 | 0.03599391 | validated |
| coord_N16 | seed0 | halted | 30 | 0.01605270 | Completion reached the length limit; review required under B11/B14 |
| coord_N32 | seed0 | halted | 32 | 0.02578620 | Completion reached the length limit; review required under B11/B14 |

## Accepted checks

Replica, baseline, values and stakes passed `check_data.py` with its default 1000 null replicates. Harvest and nominee failure rates are zero. Both private instruments parsed at 100% where applicable. All token counters were present. There were no 429/402 errors and no length-limit endings in accepted runs. All four lakes collapsed in cycle 1; this observed outcome was preserved.

## Required decision before continuing

The N=32 smoke had two harvest completions with `finish_reason: length`: Emma (7977 reported output tokens) and Henry (7978), both requesting the unchanged 8000 cap. Their prompts correctly specify the 0–400 fishing range. Both responses continued lengthy step-by-step discussion without reaching a final answer. The shared guard halted N=32 and the concurrent N=16 run. Both attempts and their complete raw responses are retained. No token cap or prompt was changed in response.

B2 fixes generation at 8000 tokens, and B14 reserves a decision to raise it across conditions for the user. The handler conservatively applies its no-truncation guard during smoke testing as well as the pilot. Review is needed before clearing this halt and retrying the interrupted smokes, or authorizing a consistent cap change. The `final-runs` tag has not been created and no full pilot command is ready to start.

## Spending and source

Total project smoke spending, including every failed/interrupted attempt: **$0.22997149**. Outstanding reservations: **$0.00000000**. The shared halt remains set. The initial account balance was $100; the key limit remains $100. The final account GET reports balance and limit_remaining of **$99.77002851**, limit **$100**, usage **$0.22997149**. The $100 initial balance minus the final balance matches the shared ledger exactly to reported precision.


The first logging-only failure was repaired by matching the original Markdown reader's empty-line normalization; native retrieval/storage stayed unchanged. Initial attempts were preserved. Final stub suite: 34 tests passed. The accepted N8 smoke commits are dc5d025 (replica/baseline) and 09ea3b2 (values/stakes); the interrupted larger smokes use 246d699. Later commits before the pilot changed only launcher/error safeguards and reports, with no full run performed. No condition has mixed full-run commits because no full runs exist.

