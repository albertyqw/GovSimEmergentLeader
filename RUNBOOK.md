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

Raw directories are write-once. Checks, manifests, reports and Parquet stay outside them. Derived builds select validated full runs; `--include-testing` is only for tool verification. Paid judging and embedding analyses remain deferred. A STOP, length-limit finish, credit/budget failure or unreconciled billing requires review; preserve all evidence.
