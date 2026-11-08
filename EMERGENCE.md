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
- **Pre-season discussion (user-approved after smoke tests):** every arm opens with a
  month-0 discussion before the first harvest ("Welcome to the start of the fishing
  season…"), opener set by the arm (3a fixed agent; 3b rotation includes it; others
  random from separate draws, so months 1-12 keep their draws). Reason: month-1 requests
  ranged 45-97 tons; arm 3a (identical to baseline in month 1) collapsed before any talk.
  Its proposals are adopted against the month-1 harvest.
- **Arm 2 timing (user-approved):** the replaced agent fishes in month 3 and leaves; the
  newcomer takes its place in the month-3 discussion (announced: "joined us and fishes
  here from next month") and fishes from month 4 with no memory of months 1-3 beyond that
  discussion. As specified, the newcomer took all 75 tons on its first harvest.
- **Harvest parse fallback:** no "Answer:" line → last "N tons" in the reply (flagged).
- **API:** 120 s request timeout; patient retries on 429/overload; Mac kept awake.
- **Analysis:** proposals are labelled per_person / group_total; totals are divided by
  the number present. Credit per spec (first proposer that month) plus an `originator`
  column (first proposer of that number anywhere in the run).
