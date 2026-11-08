# Overnight leadership screen — implementation notes

Branch `leadership-screen` of a local clone of github.com/rfaulkner/GovSimElect.
Everything is flag-driven: `experiment=screen experiment.screen.arm=<id>`; with
`screen.enabled: false` (or any other experiment) the upstream code paths run unchanged.

## How to run
```
python scripts/screen_feasibility.py                 # CQ / St checks -> runs_meta/feasibility.json
python scripts/screen_launch.py --group screen       # stages 2-4, 8 parallel, $20 budget stop
python scripts/screen_analyze.py simulation/results/screen_v7.0/screen --out runs_meta/report
```
Each run folder `simulation/results/screen_v7.0/<group>/arm-<id>_seed-<k>/` holds
`meta.json` (git hash, dirty flag, seed, full resolved config), `screen_log.jsonl`
(design, every utterance, proposals, probes, harvests, margins, writes, interviews),
`api_usage.jsonl` (tokens per call), `log_env.json`, agent memories.

## Deviations from the spec (forced)
1. **Temperature.** `claude-haiku-5-5` rejects non-default sampling parameters, and the
   installed anthropic SDK (2.x) sends API version 2026-10-21, which rejects
   `temperature`/`top_p` on every model. No temperature is sent; sampling is the API
   default (stochastic). The 0.7 in the spec could not be honoured on this model.
2. **Cycle order** discussion → harvest → reflection (stated in the report header).

## Upstream bugs fixed (needed to run at all, or would bias a leadership study)
- `run.py`/`persona.py`: HEAD passed no `embedding_model` after the markdown-memory
  refactor -> crash. Removed the stale argument.
- `reflect_prompts.py`: stop regex `\\(` was an unbalanced group -> every insight call
  silently fell back to its default value. Fixed to `\(`.
- `utils/logger.py`: wandb forced online unless debug; now honours `WANDB_MODE`.
- `pathfinder`: Anthropic backend ported from the GovSim patch (no sampling params,
  system prompt handling, thinking off, sane retries, per-call usage log) and `claude-*`
  routed to it (it was commented out).
- **Leadership contamination removed in screen mode:** every upstream utterance prompt
  contained "As a leader, you will now craft your policy agenda…" (even with no
  leaders), the no-leader report was posted as "I, Anonymous Leader, will lead the group
  this cycle", and the harvest prompt cited "the mayor's agenda". None of these appear
  in screen runs.

## Interpretations where the spec leaves room
- **Speaking order.** Each cycle: a seeded random permutation; every agent speaks once in
  that order (first turns, each must end `PROPOSAL: <int>`, one re-prompt if missing),
  then free discussion where the speaker names the next speaker (option order shuffled,
  invalid/missing -> random other agent) until someone concludes or 15 agent turns.
  E: target first, rest in the same seeded order.
- **Opening posts** (from a neutral "Notice board"): last cycle's catches + current stock
  (first cycle: "This is the first month of the season…"); the calculator line (T, T0,
  HR); the shared notes file (Sc). Agents are never told the number of cycles.
- **Private / public lines** are appended to the agent's system prompt for the whole
  cycle (discussion, harvest, reflection) via `PersonaIdentity.goals`.
- **Regeneration**: seeded schedule rho_t ~ U(1,3); rho_t applies after cycle t's harvest
  (upstream used a fixed 2.0 for cycle 0 and an unseeded RNG).
- **Calculator Y** = floor(psi(stock, mean observed rho or 2.0) × (1 − margin/100)).
  MARGIN is set by the owner in a dedicated reflection-time call ("As part of your
  reflection you may change the margin…  MARGIN: <0-50>"), default 20.
- **Sc WRITE** is a reflection-time call per agent; notes are shown in the next cycle's
  opening post. Structure flag = header / list / mentions ≥2 other agents.
- **Probe**: separate API call built from a copy of the agent's prompt (system + memories
  + this cycle's transcript); the reply is only written to `screen_log.jsonl`.
- **Interview**: separate call per agent at the end (system + memories + question).
- **Credit** uses collected (actual) harvests; contested = first-turn proposal range ≥ 2.
- **Calculator adherence** = share of agent harvest decisions within ±1 of Y.
- **CQ feasibility**: pressured take round(m × expected quota), others the expected
  quota, recomputed each cycle; pass = stock ≥ 5 after harvest for ≥ 3 cycles, seeds 1-5.
- **St feasibility**: target takes N, others max(0, (5 × expected quota − N)/4) with the
  expected quota at the current stock; pass = survives all 6 cycles, seeds 1-5.
- **HR** target-equivalents are the three roles; analysis reports credits by role.
- **A' / 0'** are arm ids `A1` / `01`.
