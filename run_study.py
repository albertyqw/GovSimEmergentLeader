"""B7/B11 study worker. Full Flash mode is launched by the user in tmux."""

import argparse
import asyncio
import json
import os
import subprocess
from pathlib import Path
from transformers import set_seed

from pathfinder import get_model

from check_data import check_run
from simulation.budget import SharedBudget, StudyHalt
from simulation.openrouter_handling import attach_openrouter, authenticated_get
from simulation.recording import RecordingWrapper, RunRecorder
from simulation.run import run
from simulation.study_config import CONDITIONS, compose_study_config
from simulation.utils.logger import WandbLogger


ROOT = Path(__file__).resolve().parent


def allocate_attempt(root, condition, seed):
    base = root / condition / f"seed{seed}"
    candidates = [base] + sorted(base.parent.glob(f"seed{seed}_attempt*"))
    for candidate in candidates:
        if (candidate / "run_meta.json").exists():
            try:
                result = check_run(candidate, null_samples=1)
                if result["valid"]:
                    return candidate, True
            except (ValueError, OSError, KeyError):
                pass
    if not base.exists():
        return base, False
    attempt = 2
    while base.with_name(f"seed{seed}_attempt{attempt}").exists():
        attempt += 1
    return base.with_name(f"seed{seed}_attempt{attempt}"), False


def live_preflight(model_id, provider):
    if subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode or subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=ROOT
    ).returncode:
        raise StudyHalt("Commit the implementation before a paid run")
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "--", "simulation", "tools", "tests", "run_study.py", "check_data.py", "study_analysis.py"],
        cwd=ROOT, text=True,
    )
    if untracked.strip():
        raise StudyHalt("Untracked implementation or test files must be committed before a paid run")
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise StudyHalt("OPENROUTER_API_KEY is absent from this process environment")
    key = authenticated_get("key")["data"]
    credit = authenticated_get("credits")["data"]
    balance = credit["total_credits"] - credit["total_usage"]
    print(json.dumps({"balance": balance, "limit": key.get("limit"), "limit_remaining": key.get("limit_remaining")}))
    if key.get("limit") != 100:
        raise StudyHalt("B1/A12 requires the $100 key-limit backstop before paid runs")
    if balance < 100:
        print("B1_ACCOUNT_NOTICE: account balance is below $100; report before the pilot")
    endpoints = authenticated_get(f"models/{model_id}/endpoints")["data"]["endpoints"]
    selected = [endpoint for endpoint in endpoints if endpoint.get("tag") == provider]
    if len(selected) != 1:
        raise StudyHalt("The pinned provider endpoint is unavailable or ambiguous")
    return selected[0]["pricing"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("condition", choices=CONDITIONS)
    parser.add_argument("seed", type=int, choices=range(5))
    parser.add_argument("--mode", choices=("stub", "smoke", "full"), default="stub")
    parser.add_argument("--output-root")
    parser.add_argument("--provider", default="google-ai-studio")
    parser.add_argument("--null-samples", type=int, default=1000)
    parser.add_argument("--budget-ledger", default=str(ROOT / "runs/.control/spend.sqlite"))
    args = parser.parse_args()
    os.environ["WANDB_DISABLED"] = "true"
    cycles = 1 if args.mode == "smoke" else 6
    cfg = compose_study_config(args.condition, args.seed, cycles=cycles)
    model_id = "google/gemini-2.5-flash-lite" if args.mode == "smoke" else "google/gemini-2.5-flash"
    cfg.llm.path = "openrouter-" + model_id
    default_root = ROOT / "runs" if args.mode == "full" else ROOT / "runs" / args.mode
    output_root = Path(args.output_root) if args.output_root else default_root
    path, complete = allocate_attempt(output_root, args.condition, args.seed)
    if complete:
        metadata = json.loads((path / "run_meta.json").read_text())
        current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        if args.mode == "full" and metadata["commit_hash"] != current:
            raise StudyHalt("Completed run uses another commit; B10 requires review before any rerun")
        print(f"SKIPPED_VALIDATED {path}")
        return
    if args.mode == "full":
        current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        for file in (output_root / args.condition).glob("seed*/run_meta.json"):
            previous = json.loads(file.read_text())
            if previous["status"] in ("completed", "collapsed") and previous["commit_hash"] != current:
                raise StudyHalt("Another seed in this condition uses another commit; STOP under B10")
    budget = None
    pricing = None
    if args.mode != "stub":
        pricing = live_preflight(model_id, args.provider)
        budget = SharedBudget(args.budget_ledger)
        budget.check()
    recorder = RunRecorder(path, args.condition, args.seed, cfg, provider="stub" if args.mode == "stub" else args.provider)
    recorder.kind = args.mode
    recorder.first_stakes_run = args.mode == "full" and args.condition == "stakes_N8" and not any(
        json.loads(file.read_text()).get("status") in ("completed", "collapsed")
        for file in (output_root / args.condition).glob("seed*/run_meta.json")
    )
    hydra_folder = path / ".hydra"
    hydra_folder.mkdir()
    from omegaconf import OmegaConf
    OmegaConf.save(cfg, hydra_folder / "config.yaml")
    try:
        # Preserve main.py's existing setup seeding and model/logger order.
        # Intervention draws still use their independent B6 generators.
        set_seed(args.seed)
        if args.mode == "stub":
            from tests.stub_llm import StubLogger, StubModel
            model = StubModel(seed=args.seed)
            logger = StubLogger()
        else:
            model = get_model(cfg.llm.path, True, args.seed, cfg.llm.backend)
            logger = WandbLogger(cfg.experiment.name, OmegaConf.to_object(cfg), debug=cfg.debug)
            attach_openrouter(model, recorder, budget, pricing)
        wrapper = RecordingWrapper(model, recorder, render=False, wanbd_logger=logger,
                                   temperature=cfg.llm.temperature, top_p=cfg.llm.top_p,
                                   seed=args.seed, is_api=True)
        asyncio.run(run(cfg.experiment, logger, wrapper, wrapper, str(path)))
    except BaseException as error:
        recorder.finalize(status="halted", error=str(error))
        raise
    finally:
        if budget:
            budget.unregister(recorder.run_id)
    try:
        result = check_run(path, args.null_samples)
    except ValueError:
        if budget:
            budget.halt("Completed run failed data validation; B11 requires review")
        raise
    checks = output_root / "checks" / args.condition
    checks.mkdir(parents=True, exist_ok=True)
    (checks / f"{path.name}.json").write_text(json.dumps(result, indent=2) + "\n")
    if args.mode == "full" and args.condition == "baseline_N8" and args.seed == 0:
        rates = result["parse_rates"]
        if any((rates[key + "_success_rate"] or 0) < 0.97 for key in ("elicitation", "perceived_leadership")):
            budget.halt("Baseline seed 0 instrument parsing failed B11's 97% gate")
            raise StudyHalt("Baseline seed 0 failed instrument parsing gate")
    if recorder.first_stakes_run and not result["survived"] and result["survival_time"] <= 2:
        budget.halt("First stakes run collapsed within two cycles; B11 requires review")
        raise StudyHalt("Stakes early-collapse gate requires review")
    print(f"VALIDATED {path}")


if __name__ == "__main__":
    main()
