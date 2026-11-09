"""B11 bounded seed concurrency and fresh-attempt resumption."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from simulation.budget import SharedBudget, StudyHalt
from simulation.study_config import CONDITIONS


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("condition", choices=CONDITIONS)
    parser.add_argument("seeds", nargs="+", type=int, choices=range(5))
    parser.add_argument("--mode", choices=("stub", "smoke", "full"), default="full")
    parser.add_argument("--parallel", type=int, default=5)
    parser.add_argument("--projected-total", type=float)
    parser.add_argument("--output-root")
    parser.add_argument("--null-samples", type=int, default=1000)
    args = parser.parse_args()
    if args.parallel < 1 or len(set(args.seeds)) != len(args.seeds):
        parser.error("Use positive parallelism and distinct seeds")
    root = Path(args.output_root) if args.output_root else ROOT / "runs"
    if args.mode != "full" and not args.output_root:
        root /= args.mode
    budget = SharedBudget(ROOT / "runs/.control/spend.sqlite") if args.mode != "stub" else None
    if args.mode == "full":
        pilot = args.condition == "replica_N8" and args.seeds == [0]
        if not pilot and args.projected_total is None:
            parser.error("A reviewed cumulative cost projection is required via --projected-total")
        if args.projected_total is not None and args.projected_total > 90:
            parser.error("B11 forbids launching a wave projected above $90")
        if args.condition == "baseline_N8" and 0 in args.seeds and args.seeds != [0]:
            parser.error("B11 requires baseline seed 0 alone before the rest")
        if args.condition == "stakes_N8":
            previous = list((root / args.condition).glob("seed*/run_meta.json"))
            if not previous and len(args.seeds) != 1:
                parser.error("Launch the first stakes seed alone so its early-collapse gate protects later seeds")
            previous_meta = sorted((json.loads(file.read_text()) for file in previous), key=lambda run: run["start_time"])
            if previous_meta:
                first = previous_meta[0]
                if first["status"] == "collapsed" and (first["collapse_cycle"] or 99) <= 2:
                    parser.error("The stakes early-collapse STOP gate requires review")
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    waiting = list(args.seeds)
    active = {}
    failed = False
    while waiting or active:
        if budget:
            try:
                budget.check()
            except StudyHalt:
                failed = True
                waiting.clear()
        limit = min(args.parallel, budget.capacity_limit() or args.parallel) if budget else args.parallel
        while waiting and len(active) < limit and not failed:
            seed = waiting.pop(0)
            stamp = time.time_ns()
            path = logs / f"{args.condition}_seed{seed}_{stamp}.log"
            output = path.open("x")
            command = [sys.executable, str(ROOT / "run_study.py"), args.condition, str(seed),
                       "--mode", args.mode, "--output-root", str(root), "--null-samples", str(args.null_samples)]
            process = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                       env={**os.environ, "WANDB_DISABLED": "true"})
            active[seed] = (process, output, path)
            print(f"START seed={seed} pid={process.pid} log={path}", flush=True)
        for seed, (process, output, path) in list(active.items()):
            status = process.poll()
            if status is not None:
                output.close()
                del active[seed]
                print(f"END seed={seed} status={status} log={path}", flush=True)
                if status != 0:
                    failed = True
        if failed:
            waiting.clear()
        if waiting or active:
            time.sleep(1)
    if failed:
        raise SystemExit("A seed failed; inspect logs and resume into a fresh attempt directory")


if __name__ == "__main__":
    main()
