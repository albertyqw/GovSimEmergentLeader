"""B9 fixed-state fixture process, usable against pinned or current source."""

import asyncio
import contextlib
import io
import json
import sys
import warnings
from pathlib import Path
from unittest.mock import patch

from hydra import compose, initialize_config_dir
from omegaconf import open_dict

from simulation.run import run
from tests.stub_llm import make_wrapper


def main():
    condition, output, raw_directory = sys.argv[1:]
    root = Path.cwd()
    with initialize_config_dir(config_dir=str(root / "simulation/conf"), version_base=None):
        overrides = ["experiment=fish_baseline_concurrent_leaders", "experiment.agent.leader_population=none"] if condition in ("original", "unmodified") else [f"experiment={condition}", f"group_name={condition}"]
        cfg = compose(config_name="config_api", overrides=overrides).experiment
    cfg.env.max_num_rounds = 1
    if condition in ("original", "unmodified"):
        cfg.phases = ["harvesting", "discussion", "reflection"]
        cfg.personas.num = 8
    wrapper, logger, transport = make_wrapper(seed=0, study=condition not in ("original", "unmodified"))
    with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings(record=True), patch(
        "simulation.persona.cognition.converse.random.choice", side_effect=lambda participants: participants[0]
    ):
        asyncio.run(run(cfg, logger, wrapper, wrapper, raw_directory))
    payload = sorted(transport.requests, key=lambda item: json.dumps(item, sort_keys=True))
    Path(output).write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
