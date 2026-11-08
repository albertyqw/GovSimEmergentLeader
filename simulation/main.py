"""Main file for GovSim Election simulation."""

import asyncio
import os
import pathlib
import shutil
import sys
import uuid

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

import hydra
import omegaconf
from pathfinder import get_model
from simulation.run import run as run_scenario_fishing
from simulation.utils.logger import WandbLogger
from simulation.utils.models import ModelWandbWrapper
import transformers
import wandb


set_seed = transformers.set_seed
Path = pathlib.Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

OmegaConf = omegaconf.OmegaConf
DictConfig = omegaconf.DictConfig


@hydra.main(version_base=None, config_path="conf", config_name="config_api")
def main(cfg: DictConfig):
  print(OmegaConf.to_yaml(cfg))
  set_seed(cfg.experiment.seed)

  model = get_model(
      cfg.llm.path, cfg.llm.is_api, cfg.experiment.seed, cfg.llm.backend
  )
  logger = WandbLogger(
      cfg.experiment.name, OmegaConf.to_object(cfg), debug=cfg.debug
  )
  run_name = (
      logger.run_name
      if logger.run_name
      else f"{cfg.llm.path}_disinfo_{cfg.experiment.env.disinformation}_population_{cfg.experiment.agent.leader_population}_run_{cfg.experiment.seed}"
  )
  if "gpt" in cfg.llm.path:
    run_name = os.path.join("gpt", run_name)
  if "screen" in cfg.experiment and cfg.experiment.screen.enabled:  # PATCH
    run_name = f"arm-{cfg.experiment.screen.arm}_seed-{cfg.experiment.seed}"
    with omegaconf.open_dict(cfg):
      cfg.experiment.screen.model = cfg.llm.path
  experiment_storage = os.path.join(
      os.path.dirname(__file__),
      f"./results/{cfg.experiment.name}/{run_name}",
  )
  if os.path.exists(f"{experiment_storage}"):
    shutil.rmtree(experiment_storage)
    print(f"Removed old '{experiment_storage}' ...")
  print(f"Experiment storage: {experiment_storage}")
  if "screen" in cfg.experiment and cfg.experiment.screen.enabled:  # PATCH: provenance
    import json, subprocess
    os.makedirs(experiment_storage, exist_ok=True)
    os.environ.setdefault("PATHFINDER_USAGE_FILE", os.path.join(experiment_storage, "api_usage.jsonl"))
    git = lambda *a: subprocess.run(["git", *a], cwd=project_root, capture_output=True, text=True).stdout.strip()
    with open(os.path.join(experiment_storage, "meta.json"), "w") as f:
      json.dump({"git_hash": git("rev-parse", "HEAD"), "git_dirty": bool(git("status", "--porcelain")),
                 "seed": cfg.experiment.seed, "arm": str(cfg.experiment.screen.arm),
                 "config": OmegaConf.to_container(cfg, resolve=True)}, f, indent=2)

  wrapper = ModelWandbWrapper(
      model,
      render=cfg.llm.render,
      wanbd_logger=logger,
      temperature=cfg.llm.temperature,
      top_p=cfg.llm.top_p,
      seed=cfg.experiment.seed,
      is_api=cfg.llm.is_api,
  )

  if cfg.experiment.scenario == "fishing":
    asyncio.run(
        run_scenario_fishing(
            cfg.experiment,
            logger,
            wrapper,
            wrapper,
            experiment_storage,
        )
    )
  else:
    raise ValueError(f"Unknown experiment.scenario: {cfg.experiment.scenario}")

  hydra_log_path = hydra.core.hydra_config.HydraConfig.get().runtime.output_dir
  if os.path.exists(f"{experiment_storage}/.hydra/"):
    shutil.rmtree(f"{experiment_storage}/.hydra/")
  shutil.copytree(f"{hydra_log_path}/.hydra/", f"{experiment_storage}/.hydra/")
  shutil.copy(f"{hydra_log_path}/main.log", f"{experiment_storage}/main.log")

  artifact = wandb.Artifact("hydra", type="log")
  artifact.add_dir(f"{experiment_storage}/.hydra/")
  artifact.add_file(f"{experiment_storage}/.hydra/config.yaml")
  artifact.add_file(f"{experiment_storage}/.hydra/hydra.yaml")
  artifact.add_file(f"{experiment_storage}/.hydra/overrides.yaml")
  wandb.run.log_artifact(artifact)


if __name__ == "__main__":
  OmegaConf.register_resolver("uuid", lambda: f"run_{uuid.uuid4()}")
  main()

