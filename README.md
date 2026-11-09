# AgentElect · Emergent Leadership in GovSim

**How do leadership, elections, and communication shape cooperation among LLM agents sharing a renewable resource?**

This is [albertyqw's research fork](https://github.com/albertyqw/GovSimEmergentLeader) of [AgentElect / GovSimElect](https://github.com/rfaulkner/GovSimElect), built on [GovSim](https://github.com/giorgiopiatti/GovSim). The fork is a workspace for investigating emergent leadership and collective resource management in simulated fishing communities.

The current implementation combines configurable simulation phases, leader-candidate populations, optional disinformation, and Markdown-backed agent memory. These mechanisms provide experimental controls for studying leadership and developing new interventions.

![AgentElect overview](imgs/agent_elect.png)

[Setup](#setup) · [Run a simulation](#run-a-simulation) · [Configuration](#configuration) · [Agent memory](#agent-memory) · [Results and analysis](#results-and-analysis) · [Extend the simulation](#extend-the-simulation)

## What you can study

| Question | Existing controls |
| --- | --- |
| Does leadership change cooperation and resource use? | Multiple candidates, a single candidate, or no leader candidates |
| Does candidate motivation matter? | Social Value Orientation (SVO) population settings |
| How does misinformation affect collective decisions? | `experiment.env.disinformation` |
| Does the order of interaction matter? | Configurable policy, election, harvesting, discussion, and reflection phases |
| How does remembered experience influence behaviour? | Per-agent `MEMORY.md` records and retrieval scores |

With multiple candidates, agents vote on policy agendas. With a single candidate, the election phase selects that candidate without a vote, providing a fixed-leader control. With `leader_population=none`, policy-making and election phases skip leader selection.

## Setup

### Clone this fork

```bash
git clone https://github.com/albertyqw/GovSimEmergentLeader.git
cd GovSimEmergentLeader
```

PathFinder is included in this checkout. The current `.gitmodules` file is empty, so recursive submodule initialization is not required.

### Choose an environment

The setup recipes target a Python **3.11.5** research environment, with Linux/CUDA dependencies for local model inference. They need adaptation to your machine or cluster.

| Recipe | Intended environment | Before using it |
| --- | --- | --- |
| [setup.sh](setup.sh) | Conda with CUDA 12.1 / PyTorch 2.2 | Create and activate the `GovSim` environment first; review its installation commands |
| [setup_venv.sh](setup_venv.sh) | HPC modules and a `.venv` | Adapt its `module load` versions to your cluster |
| [setup_vllm.sh](setup_vllm.sh) | A separate Conda/CUDA environment for vLLM | Review GPU compatibility and the `GovComVLLMv2` environment configuration |

For the Conda recipe, start with:

```bash
conda create -n GovSim python=3.11.5 -y
conda activate GovSim
```

Review `setup.sh` before sourcing it in that shell. Its NumPy installation line currently uses `numpy=1.26.4`; pip requires `numpy==1.26.4`.

For an existing compatible Python environment, the dependency lists are [PathFinder requirements](pathfinder/requirements.txt), [project requirements](requirements.txt), and the more extensive [virtual-environment requirements](requirements_venv.txt). API-based inference does not require a locally hosted model, but the imported code still depends on PyTorch and Transformers.

### Configure credentials

```bash
cp .env_example .env
```

Edit `.env` locally with the credentials for your chosen provider. For the OpenRouter example below, set `OPENROUTER_API_KEY`. The example file also lists OpenAI, Anthropic, Mistral, DeepSeek, and Hugging Face variables; a variable's presence does not mean every provider/model is enabled by the simulation loader.

Export those values into the shell before running:

```bash
set -a
source .env
set +a
export PYTHONPATH="$PWD:$PWD/pathfinder${PYTHONPATH:+:$PYTHONPATH}"
```

Keep real tokens in `.env` or your environment. The repository ignores `.env`.

## Run a simulation

Run from the repository root after preparing your environment. The entry point is [simulation/main.py](simulation/main.py), which loads [config_api.yaml](simulation/conf/config_api.yaml) by default. Explicitly select an experiment: the inherited `basic` default does not have a corresponding experiment file in this checkout.

### API-based example

This uses the same OpenRouter model selection as the API launch script:

```bash
python -m simulation.main \
  experiment=fish_baseline_concurrent_leaders \
  llm.path=openrouter-google/gemini-2.5-flash \
  llm.is_api=true \
  experiment.seed=1 \
  experiment.agent.leader_population=balanced \
  experiment.env.disinformation=false \
  group_name=first_run \
  debug=true
```

`debug=true` selects disabled Weights & Biases logging through the logger. It still runs the simulation and makes model API calls. The model must be available to your provider account. Model routing is implemented in [PathFinder's loader](pathfinder/pathfinder/loader.py).

Choose a new `group_name` for a separate experiment. The entry point removes an existing result directory when the computed output path matches an earlier run.

### Local-model example

With a compatible GPU environment and access to the model weights:

```bash
python -m simulation.main \
  experiment=fish_baseline_concurrent_leaders \
  llm.path=meta-llama/Meta-Llama-3-8B-Instruct \
  llm.is_api=false \
  llm.backend=transformers \
  experiment.seed=1 \
  experiment.agent.leader_population=balanced \
  experiment.env.disinformation=false \
  group_name=local_first_run \
  debug=true
```

The loader also has a `vllm` backend. Check the model-name routing, chat templates, and installed backend before changing model families.

### Cluster launchers and sweeps

The scripts in [scripts/](scripts/) are research launch templates. They contain SLURM account settings, module loads, environment activation, and absolute project paths. Adapt those values before running them, including when invoking a script with `bash` outside SLURM.

| Script | Purpose |
| --- | --- |
| [launch_job_api.sh](scripts/launch_job_api.sh) | API-model simulation; positional arguments are seed, population, and disinformation |
| [launch_job.sh](scripts/launch_job.sh) | Local-model simulation with the same argument order |
| [launch_job_batch.sh](scripts/launch_job_batch.sh) | Population × disinformation × seed sweep |
| [launch_social_batch.sh](scripts/launch_social_batch.sh) | Social-metric analysis sweep |
| [launch_judge_batch.sh](scripts/launch_judge_batch.sh) | LLM-judge analysis sweep |

After adapting the API launcher:

```bash
sbatch scripts/launch_job_api.sh 1 balanced false
```

Batch scripts refer to sibling launchers as `./launch_*.sh`, so run them from the `scripts` directory after adapting their settings:

```bash
cd scripts
bash launch_job_batch.sh
```

The local-model launcher checks `$1` when choosing the default for its third argument; supply all three positional arguments explicitly. `launch_job_api_vanilla.sh` still selects `fish_baseline_concurrent_12_agents`, which is absent from this checkout. Use `leader_population=none` with an existing experiment for the current no-candidate control.

## Configuration

Hydra composes the top-level configuration with an experiment from [simulation/conf/experiment/](simulation/conf/experiment/). The checked-in experiment variants are `fish_baseline_concurrent_leaders` and `fish_baseline_concurrent_leaders_20`.

| Setting | Purpose |
| --- | --- |
| `llm.path`, `llm.is_api`, `llm.backend` | Model selection and inference backend |
| `experiment.seed` | Seed used by the simulation entry point |
| `experiment.agent.leader_population` | Number and SVO mix of candidate leaders |
| `experiment.env.disinformation` | Enables disinformation handling |
| `experiment.env.max_num_rounds` | Maximum simulation rounds |
| `experiment.env.regen_factor_range` | Resource regeneration range |
| `experiment.env.harvesting_order` | Harvesting order, such as `concurrent` |
| `experiment.phases` | Ordered phase list |
| `group_name` | Experiment grouping, interpolated into the experiment name |

Available candidate-population settings are:

```text
balanced
none
one_prosocial
one_altruistic
one_competitive
one_individualistic
lean_altruistic
lean_competitive
```

Candidate distributions are defined in [leaders.py](simulation/persona/cognition/leaders.py). When changing population size, keep `env.num_agents`, `personas.num`, persona definitions, and candidate count consistent. The runner checks that there are enough agents for the candidate population.

### Round structure

The default phase sequence is:

```text
Policy making → Election → Harvesting and report → Discussion → Reflection
```

| Phase | What happens |
| --- | --- |
| `policy_making` | Candidate leaders produce agendas from their identities and memories |
| `election` | Agents vote, or a single candidate is selected |
| `harvesting` | Agents take resources and generate the harvest report |
| `discussion` | Agents exchange messages about the round |
| `reflection` | Agents reflect and store memories |

Reorder phases in an experiment YAML or with a Hydra override, preserving each phase's prerequisites. For example, the election phase uses agendas generated by policy-making.

## Agent memory

This fork's current memory persistence is **Markdown-backed**. Each agent's memory directory contains `MEMORY.md`, with entries recording timestamps, memory type, importance, expiration, and an `always_include` flag.

New entries are appended as they are stored. Retrieval reads the file, filters expired entries, scores candidates using the configured recency and importance logic, prioritizes `always_include` entries, and returns selected memories. Focal-point arguments remain in the interface but are unused in this Markdown retrieval mode.

Implementation: [associative_memory.py](simulation/persona/memory/associative_memory.py) and [retrieve.py](simulation/persona/cognition/retrieve.py).

## Results and analysis

Simulation data is written under `simulation/results/<experiment name>/<run name>/`. Hydra's own run directory is under `outputs/`; the entry point copies configuration and log files into the experiment directory.

| Output | Contents |
| --- | --- |
| `consolidated_results.json` | Initialization, identities, elections, harvest statistics, and other run events |
| `log_env.json` | Environment observations and actions |
| Per-agent memory directories | Markdown memory records |
| `.hydra/` and `main.log` | Configuration, overrides, and execution log |

The [analysis modules](simulation/analysis/) cover survival, resource use, inequality, social/election metrics, plots, and a Dash interface. Some modules contain fixed result roots, model lists, seed ranges, and population constants; point these at your own outputs before analysing a run.

For social metrics, after updating `BASE_PATH` and the relevant settings in [social.py](simulation/analysis/social.py):

```bash
python -m simulation.analysis.social balanced false openrouter-google/gemini-2.5-flash
```

The [LLM Judge guide](llm_judge/README.md) documents the separate evaluation package. Its [leader sentiment example](llm_judge/examples/leader_sentiment.py) classifies cooperation, persuasion, and SVO-related language. Update its input/output roots, model settings, and credentials before running it.

```bash
cd llm_judge
python examples/leader_sentiment.py one_prosocial false persuasion
```

The existing `launch_analysis.sh` wrapper runs the leader-sentiment example; it is not a general runner for every analysis module.

For comparisons, record the commit, resolved Hydra configuration, model/provider, seed, candidate distribution, disinformation setting, and phase order alongside the results. Keep original run outputs when comparing a new intervention with a baseline.

## Extend the simulation

Phases implement the asynchronous interface in [simulation/phases/base.py](simulation/phases/base.py) and are registered in [simulation/run.py](simulation/run.py).

1. Add a phase module under `simulation/phases/`.
2. Implement `name` and `async execute(ctx)` using `PhaseContext`.
3. Register the phase class in `PHASE_REGISTRY`.
4. Add its name to an experiment's `phases` list.

```python
from simulation.phases.base import Phase, PhaseContext


class MyPhase(Phase):
    @property
    def name(self) -> str:
        return "my_phase"

    async def execute(self, ctx: PhaseContext) -> PhaseContext:
        # Inspect or update the shared context here.
        return ctx
```

Use the existing phases as examples for environment stepping, termination handling, memory storage, and logging.

## Repository map

```text
GovSimEmergentLeader/
├── simulation/
│   ├── main.py             # Hydra entry point and output setup
│   ├── run.py              # Phase registry and simulation runner
│   ├── conf/               # Model defaults, experiments, and persona configuration
│   ├── environment/        # Fishing environments
│   ├── phases/             # Policy, election, harvest, discussion, reflection
│   ├── persona/            # Agent identity, cognition, scratch state, memory
│   ├── analysis/           # Metrics, plots, and dashboard modules
│   └── utils/              # Logging and model wrappers
├── scripts/                # Cluster launch and analysis templates
├── pathfinder/             # Included model/prompting library
├── llm_judge/              # LLM-based conversation evaluation
├── imgs/                   # Project figures
├── .env_example            # Environment-variable template
├── requirements*.txt       # Dependency recipes
└── setup*.sh               # Environment setup recipes
```

## Acknowledgments and license

This fork builds on [AgentElect / GovSimElect](https://github.com/rfaulkner/GovSimElect), [GovSim](https://github.com/giorgiopiatti/GovSim), and its included [PathFinder](pathfinder/README.md) library. The existing [MIT license](LICENSE) and attribution are retained.
