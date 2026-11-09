# Current two-stage source amendment

The user approved a mandatory opening round, nomination handoff by its final speaker, a hidden contextual nomination judge, random fallback when unclear, a separate running intervention table, and 50 messages total. All study configs require `round_robin_discussion: true`. Earlier smoke/pilot versions are preserved and superseded. All six two-stage smokes validated on 036c30c; the user starts the replacement pilot after the final tag is pushed; retain final-runs and final-runs-v2 and freeze the replacement as final-runs-v3. Never launch a full run from Codex.

The shared judge table is `runs/.control/nomination_judgments.sqlite`. Export a readable snapshot with `.venv/bin/python -m tools.nomination_table`; the default destination is `runs/nomination_judgments.tsv`. Judge calls appear in the ordinary raw calls and cost ledger.

# Current source amendment

All study conditions now require `agent.neutral_study: true`: explicit participant counts, neutral scripted prompts, and keyed uniform invalid-nomination fallback. The initial full pilot is superseded and preserved under `final-runs`. All six revised smokes passed on 499f8d2; see SMOKE_REPORT.md. The user may start the replacement pilot after the final source tag is pushed. Freeze the replacement source as `final-runs-v2`, retaining the original tag. The same pilot command will allocate a fresh attempt because the resolved config differs. No full pilot is launched by Codex. Historical procedures below otherwise apply.

# Running the study on this Mac

Repository: `/Users/yongqi/Documents/emergent_leaders/GovSimEmergentLeader`.

The user supplies the key only through the hidden Terminal prompt. It remains in the govsim shell and tmux environment. Never paste it into chat, command arguments, files or logs. Codex reads it internally through `tools.with_tmux_key` for approved smoke commands; no pane capture is needed.

## Validation and smoke

```
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m tools.build_fidelity
.venv/bin/python run_study.py baseline_N8 0 --mode stub
.venv/bin/python -m tools.with_tmux_key replica_N8 0 --mode smoke
```

The last command is a one-cycle paid Flash-Lite smoke; repeat for baseline_N8, values_N8, stakes_N8, coord_N16 and coord_N32. Commit source first. Codex runs these commands and validates every resulting run. Network and tmux socket access require normal approval. All paid calls share `runs/.control/spend.sqlite`; do not delete or reset it. Stub runs have zero API spending.

## User-started pilot

After all smoke tests pass and the source commit is tagged `final-runs`, inside the existing govsim tmux shell:

```
cd /Users/yongqi/Documents/emergent_leaders/GovSimEmergentLeader
./launch.sh replica_N8 0
```

This command starts the full six-cycle Flash pilot. Codex must never execute it. Tell Codex once it starts; Codex monitors `runs/logs`, raw records and the shared budget. At completion Codex produces the B11.2 pilot report and transcript, then stops for review. No replica seeds 1–4 or later conditions start in this session.

## Resume and later waves

Repeat a reviewed launcher command after a crash. Validated completed seeds are skipped; failed attempts get `_attempt2`, `_attempt3`, etc. Originals are retained. A changed source commit requires STOP review under B10 and rerunning every affected run; do not mix commits within a condition. Keep source frozen during experiments, including documentation commits that would change recorded HEAD.

`--parallel N` controls seed concurrency (default 5). After the pilot, each invocation needs `--projected-total DOLLARS`: reviewed cumulative project spending expected after that invocation, including prior smoke, failures and retries. It must not exceed $90. No later command is authorized by this runbook: B11 review gates determine when it may run. Baseline seed 0 and the first stakes seed run alone. Baseline instruments must parse at least 97%; a first stakes collapse within two cycles stops later stakes seeds.

## Data tools

```
.venv/bin/python check_data.py runs/replica_N8/seed0 --output runs/checks/replica_N8/seed0.json
.venv/bin/python -m tools.manifest runs --output manifest.json
.venv/analysis/bin/python -m tools.build_derived runs --output derived
```

Raw directories are write-once. Checks, manifests, reports and Parquet stay outside them. Derived builds select validated full runs; `--include-testing` is only for tool verification. Paid judging and embedding analyses remain deferred. Scheduled STOP gates, credit/budget failures and unreconciled billing require review. Length finishes and individual parse failures are logged and follow repository continuation/default behavior at fixed caps; preserve all evidence.

## Current paper-alignment profile

The amended study uses paper-defined thresholds, incoming degree, inverse-weight fractional betweenness, ten-entry recall, altruistic range 57.15–90 (if ever used), aligned prompt semantics and 16000/1000 generation/rating caps. All six smokes passed under this profile and the fixed-cap continuation policy on commit 4fdcbb9; see SMOKE_REPORT.md. The worker compares resolved config before reusing a completion; older validated attempts cannot satisfy the new profile and are preserved in place. Do not clear an unrelated budget/credit halt when reviewing the old length-limit halt. No full Flash run has started.

Current truncation policy is repository_parser_fixed_caps. Old-policy completions are preserved but do not satisfy new-policy resume checks. Do not increase caps or add length-triggered retry loops. Report all truncations, subsequent calls and parse fallbacks at pilot review.
