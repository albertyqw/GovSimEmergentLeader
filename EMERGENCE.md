# Leader emergence (Swarm Alignment Hackathon) — implementation notes

Branch `leader-emergence` (built on `leadership-screen`). Code: `simulation/emergence/`.

```
PYTHONPATH=. python -m simulation.emergence.run --arm 0 --seed 1 --out simulation/results/emergence/<group>/arm-0_seed-1
```
Each run folder: `run.json` (config, design incl. regrowth draws and roster, per-month stock,
requested/actual harvests, utterances, moderator report, extracted proposals, memory
retrievals, reflections, interviews, flags, usage), `meta.json` (git hash, dirty flag, seed,
config), `api_usage.jsonl`, `memories/<agent>/MEMORY.md`.

## Why a new loop instead of upstream's environment
Arms 2, 4a and 4b replace agents mid-run; upstream's env has a fixed persona set. The loop
reuses GovSimElect's memory format (`AssociativeMemory`, MEMORY.md) and retrieval scoring,
and GovSim's fishery prompts (system prompt v3 wording, harvest prompt, group-chat
prompt, moderator catch report, outsider persona verbatim).

## Deviations / decisions
- **Sampling:** API default; `claude-haiku-5-5` rejects temperature.
- **Group size stated:** system prompt says "along with four other fishermen". With
  GovSim's "other fishermen", 6/6 seeds requested 110-175 tons in month 1 and collapsed
  before any discussion; with the group size stated, 45-65 tons (user-approved change).
- **Regrowth text:** GovSimElect's v3 prompt says both "double once" and "sampled
  uniformly"; the contradictory "double once" is dropped. Range 1.0-3.0 stated, draw never.
- **Turn order:** opener set by arm, then a seeded random order (no nominations; user
  choice). The social graph uses name mentions only. A speaker may conclude the
  discussion only after all present agents have spoken; cap 20 turns.
- **Memory retrieval:** GovSimElect scoring (recency + 3 x importance, always-include
  first, top 10). Fixed upstream bug: recency was highest for the OLDEST entry. Importance
  is rated by one batched call per agent per batch of new memories. Monthly stock and
  universalization lines expire after their month (upstream keeps always-include entries
  forever, which would fill all 10 slots). Utterances enter memory after the discussion
  (the live transcript is already in the prompt).
- **Over-request:** if requests exceed stock, catches are prorated (largest remainder).
- **Stock** is an integer: floor(min(100, remaining x rho)).
- **Collapse:** stock after fishing < 5 ends the run (no discussion that month).
- **Proposal extraction:** Haiku call per month; ranges recorded at the upper bound with
  the range kept.
- **Interviews:** each departing tenant at its last month, and everyone present at the end;
  full (non-expired) memory, three separate calls, not fed back.
- **Arm 2:** the newcomer's arrival and the leaver's departure are announced in the
  moderator report, as in the rotation arms.
