"""Launch leader-emergence runs in parallel with a spend cap.

  python scripts/emergence_launch.py --group smoke --jobs 1:1,2:1,3a:1,3b:1,4a:1,4b:1
  python scripts/emergence_launch.py --group grid                  # 7 arms x seeds 1-3

Skips finished runs (run.json with "end"). Before starting a run, stops if spent across ALL
emergence groups + running x per-run estimate would exceed --budget.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES = os.path.join(ROOT, "simulation", "results", "emergence")
ARMS = ["0", "1", "2", "3a", "3b", "4a", "4b"]


def spent():
  tot = 0.0
  for f in glob.glob(os.path.join(RES, "*", "*", "api_usage.jsonl")):
    for l in open(f):
      u = json.loads(l)
      tot += u["input_tokens"] * 0.10 / 1e6 + u["output_tokens"] * 0.50 / 1e6
  return tot


def done(d):
  p = os.path.join(d, "run.json")
  return os.path.exists(p) and '"end"' in open(p).read()


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--group", required=True)
  ap.add_argument("--jobs", default=None)
  ap.add_argument("--parallel", type=int, default=7)
  ap.add_argument("--budget", type=float, default=15.0)
  ap.add_argument("--per-run-estimate", type=float, default=0.5)
  ap.add_argument("--months", type=int, default=12)
  a = ap.parse_args()
  jobs = ([(x.split(":")[0], int(x.split(":")[1])) for x in a.jobs.split(",")] if a.jobs
          else [(arm, s) for s in (1, 2, 3) for arm in ARMS])
  os.makedirs(os.path.join(ROOT, "runs_meta", "logs", "emergence", a.group), exist_ok=True)
  pending = [j for j in jobs if not done(os.path.join(RES, a.group, f"arm-{j[0]}_seed-{j[1]}"))]
  running, failed = {}, []
  print(f"[{time.strftime('%H:%M:%S')}] {a.group}: {len(pending)} to run; spent so far ${spent():.2f}", flush=True)
  while pending or running:
    for j, p in list(running.items()):
      if p.poll() is not None:
        del running[j]
        ok = p.returncode == 0 and done(os.path.join(RES, a.group, f"arm-{j[0]}_seed-{j[1]}"))
        failed += [] if ok else [j]
        print(f"[{time.strftime('%H:%M:%S')}] done {j} ok={ok} spent=${spent():.2f}", flush=True)
    while pending and len(running) < a.parallel:
      if spent() + (len(running) + 1) * a.per_run_estimate > a.budget:
        print(f"BUDGET STOP at ${spent():.2f}; not launched: {pending}", flush=True)
        open(os.path.join(ROOT, "runs_meta", f"emergence_{a.group}_STOPPED_BUDGET"), "w").write(str(pending))
        pending = []
        break
      j = pending.pop(0)
      d = os.path.join(RES, a.group, f"arm-{j[0]}_seed-{j[1]}")
      log = open(os.path.join(ROOT, "runs_meta", "logs", "emergence", a.group, f"arm-{j[0]}_seed-{j[1]}.log"), "w")
      running[j] = subprocess.Popen(
          [sys.executable, "-m", "simulation.emergence.run", "--arm", j[0], "--seed", str(j[1]),
           "--out", d, "--months", str(a.months)],
          cwd=ROOT, env=dict(os.environ, PYTHONPATH=ROOT), stdout=log, stderr=subprocess.STDOUT)
      print(f"[{time.strftime('%H:%M:%S')}] start {j}", flush=True)
    time.sleep(5)
  print(f"[{time.strftime('%H:%M:%S')}] ALL DONE failed={failed} spent=${spent():.2f}", flush=True)


if __name__ == "__main__":
  main()
