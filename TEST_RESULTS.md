# Pre-smoke validation

Validation on this Mac with the isolated Python 3.11.16 environment; no paid model calls were used for these checks.

- `python -m unittest discover -s tests -v`: 33 tests passed. Tests execute actual agents, environment, memory, wrapper and Pathfinder parsing against a deterministic transport stub. Six-cycle runs cover every condition. Additional checks cover exact B5 strings, pinned-source N=8 prompts, private-call isolation including silent agents, stakes handovers and nomination variants, integer stock regeneration, scaled thresholds, native unseeded-factor KS test (512 resets), configuration allowlists, data fields and budget/retry error paths.
- The original reflection-regex fallback is expected and remains unchanged; six N=8 cycles produce 48 caught warnings. Generation/importance caps remain 8000/1000.
- `python -m tools.build_fidelity`: replica fixed-state requests and canned responses match the pinned original byte for byte after the approved constructor repair. One-cycle request counts: replica 77, baseline/values/stakes 93, N16 181, N32 357. Full diffs and hashes are in `tests/golden`; rendered excerpts are in FIDELITY.md.
- CLI worker verification ran all six conditions for six cycles with raw recording and `check_data.py` (10 null replicates for this tool check). All validated. Harvest and nominee failures were zero; both private instruments parsed at 100% where applicable. This validates wiring with canned answers, not real-model parse quality.
- Separate analysis-environment Parquet build on those six stored stub runs: 36 cycles, 108 utterances, 83 identities, 5364 call-index rows, 9154 retrieval rows, 432 elicitations and 432 perceived-leadership rows. All seven tables were written. SHA-256 manifest generation also succeeded.
- `pip check`: no broken requirements. All nine selected original fixed pins match. Transformers is the user-approved 4.51.0; original dependency files are unchanged. Analysis PyArrow is isolated from simulation.
- METHODS.md and AGENTS.md compare byte-identically with the supplied parent copies. `git diff --check` passed; no formatter, linter or auto-fixer was run.

Remaining phase: one-cycle paid Flash-Lite smoke for each condition, followed by the user's tmux-started Flash pilot. Pilot completion is a STOP gate. This document does not claim a completed experiment or real-model smoke results.
