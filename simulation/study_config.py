"""B2/B4/B7: compose the condition and seed-specific values YAMLs."""

from pathlib import Path

from hydra import compose, initialize_config_dir


CONDITIONS = ("replica_N8", "baseline_N8", "values_N8", "stakes_N8", "coord_N16", "coord_N32")


def compose_study_config(condition, seed, cycles=None):
    if condition not in CONDITIONS or seed not in range(5):
        raise ValueError("Expected a specified condition and seed 0..4")
    experiment = condition
    if condition == "values_N8" and seed != 0:
        experiment = f"values_N8_seed{seed}"
    overrides = [f"experiment={experiment}", f"experiment.seed={seed}",
                 f"group_name={condition}", "llm.path=openrouter-google/gemini-2.5-flash"]
    if cycles is not None:
        if cycles not in (1, 6):
            raise ValueError("Only one-cycle smoke tests or six-cycle runs are specified")
        overrides.append(f"experiment.env.max_num_rounds={cycles}")
    with initialize_config_dir(config_dir=str(Path(__file__).parent / "conf"), version_base=None):
        return compose(config_name="config_api", overrides=overrides)
