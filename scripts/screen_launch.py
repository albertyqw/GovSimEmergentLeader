"""Launch the overnight leadership screen (spec section 7, steps 2-4).

  python scripts/screen_launch.py --group screen            # full screen
  python scripts/screen_launch.py --group smoke --jobs 0:1  # one run
  python scripts/screen_launch.py --group pathcheck --jobs A:1,C:1 --cycles 1

Up to --parallel runs at once. Skips runs whose screen_log.jsonl has run_end. Stops
launching new runs when spent + (running runs x per-run estimate) would exceed --budget,
and writes runs_meta/<group>_STOPPED_BUDGET.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PY = sys.executable
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0)}
MAIN_ARMS = ["0", "A", "B", "C", "T", "T0", "E", "S", "Sc", "CQ", "St"]


def run_dir(group, arm, seed):
  return os.path.join(ROOT, "simulation", "results", "screen_v7.0", group, f"arm-{arm}_seed-{seed}")


def finished(group, arm, seed):
  p = os.path.join(run_dir(group, arm, seed), "screen_log.jsonl")
  return os.path.exists(p) and '"type": "run_end"' in open(p).read()


def spent(group):
  total = 0.0
  for f in glob.glob(os.path.join(ROOT, "simulation", "results", "screen_v7.0", group, "*", "api_usage.jsonl")):
    for l in open(f):
      u = json.loads(l)
      p_in, p_out = PRICES.get(u["model"], (0, 0))
      total += u["input_tokens"] * p_in / 1e6 + u["output_tokens"] * p_out / 1e6
  return total


def launch(group, arm, seed, model, cycles, mult):
  d = run_dir(group, arm, seed)
  os.makedirs(os.path.join(ROOT, "runs_meta", "logs", group), exist_ok=True)
  log = open(os.path.join(ROOT, "runs_meta", "logs", group, f"arm-{arm}_seed-{seed}.log"), "w")
  env = dict(os.environ, PYTHONPATH=ROOT, WANDB_MODE="disabled",
             PATHFINDER_USAGE_FILE=os.path.join(d, "api_usage.jsonl"))
  if os.path.exists(os.path.join(d, "api_usage.jsonl")):
    os.remove(os.path.join(d, "api_usage.jsonl"))  # main.py wipes the run dir on restart anyway
  cmd = [PY, "-m", "simulation.main", "--config-name=config", "experiment=screen",
         f"llm.path={model}", "llm.is_api=true", "llm.backend=api", f"group_name={group}",
         f"experiment.seed={seed}", f"experiment.screen.arm={arm}",
         f"experiment.env.max_num_rounds={cycles}",
         f"experiment.screen.cq_multiplier={mult['cq']}", f"experiment.screen.st_multiplier={mult['st']}"]
  return subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)


def run_batch(group, jobs, args, mult):
  pending = [j for j in jobs if not finished(group, *j)]
  running = {}
  failed = []
  print(f"[{time.strftime('%H:%M:%S')}] {group}: {len(pending)} to run ({len(jobs) - len(pending)} already done)",
        flush=True)
  while pending or running:
    for j, p in list(running.items()):
      if p.poll() is not None:
        del running[j]
        ok = p.returncode == 0 and finished(group, *j)
        print(f"[{time.strftime('%H:%M:%S')}] done {j} rc={p.returncode} ok={ok} spent=${spent(group):.2f}", flush=True)
        if not ok:
          failed.append(j)
    while pending and len(running) < args.parallel:
      if spent(group) + (len(running) + 1) * args.per_run_estimate > args.budget:
        open(os.path.join(ROOT, "runs_meta", f"{group}_STOPPED_BUDGET"), "w").write(
            f"spent={spent(group):.2f} pending={pending}\n")
        print(f"BUDGET STOP: spent ${spent(group):.2f}; {len(pending)} runs not launched", flush=True)
        pending = []
        break
      j = pending.pop(0)
      running[j] = launch(group, j[0], j[1], args.model, args.cycles, mult)
      print(f"[{time.strftime('%H:%M:%S')}] start {j}", flush=True)
    time.sleep(5)
  return failed


def a_disclosed_count(group):
  sys.path.insert(0, os.path.join(ROOT, "scripts"))
  import screen_analyze as sa
  n = 0
  for s in range(1, 6):
    d = run_dir(group, "A", s)
    if os.path.exists(os.path.join(d, "screen_log.jsonl")):
      r = sa.load_run(d)
      n += sa.a_disclosure(r, r["target"]) is not None
  return n


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--group", default="screen")
  ap.add_argument("--jobs", default=None, help="comma list arm:seed; default = full screen")
  ap.add_argument("--model", default="claude-haiku-5-5")
  ap.add_argument("--cycles", type=int, default=6)
  ap.add_argument("--parallel", type=int, default=8)
  ap.add_argument("--budget", type=float, default=20.0)
  ap.add_argument("--per-run-estimate", type=float, default=0.30)
  args = ap.parse_args()
  feas = json.load(open(os.path.join(ROOT, "runs_meta", "feasibility.json")))
  if feas.get("cq_multiplier") is None or feas.get("st_multiplier") is None:
    sys.exit("feasibility check failed; not launching")
  mult = {"cq": feas["cq_multiplier"], "st": feas["st_multiplier"]}

  if args.jobs:
    jobs = [(a, int(s)) for a, s in (x.split(":") for x in args.jobs.split(","))]
    failed = run_batch(args.group, jobs, args, mult)
  else:
    stage2 = [(a, s) for s in range(1, 6) for a in MAIN_ARMS]
    failed = run_batch(args.group, stage2, args, mult)
    stage3 = [("HR", s) for s in range(1, 7)] + [("CF", s) for s in range(1, 5)]
    failed += run_batch(args.group, stage3, args, mult)
    n = a_disclosed_count(args.group)
    print(f"A disclosure: {n}/5 seeds", flush=True)
    if n < 3:
      failed += run_batch(args.group, [(a, s) for s in range(1, 6) for a in ("A1", "01")], args, mult)
  print(f"[{time.strftime('%H:%M:%S')}] ALL DONE. failed={failed} spent=${spent(args.group):.2f}", flush=True)


if __name__ == "__main__":
  main()
