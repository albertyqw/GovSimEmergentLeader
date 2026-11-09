# Conditions for Emergent Leadership in GovSim
## Methods and implementation specification

**Version:** final, November 2026; paper-alignment amendments approved 8 November 2026. This document supersedes `CLAUDE_CODE_PROMPT.md` and the earlier setup-differences doc.

**How to use it.** Part A is the methods section for the research report: every design decision and its rationale. Part B is the binding implementation specification for the coding agent. Where Part A and Part B differ in detail, Part B governs implementation. Preserve this file as `METHODS.md`, except for explicit user-approved amendments; fidelity tests read intervention texts from it.

---

# Part A. Research methods

## A1. Question and rationale

**Question.** Under what conditions do leaders emerge in a self-organized group of LLM agents sharing a commons?

**Rationale.** In GovSim's baseline, agents are symmetric: they are copies of one model, see the same public state, earn private payoffs, and face no enforcement. Nothing marks one agent as a leader. AgentElect showed that formal leaders, fixed or elected, improve welfare and survival over leaderless groups. We ask the prior question: does leadership arise without a formal role once that symmetry breaks? Each intervention breaks one symmetry:

| Arm | Symmetry broken | Hypothesis |
|---|---|---|
| Values and plan | One agent privately holds prosocial values and a policy plan | Its proposals are adopted more often than its peers', and it is more central in discussion |
| Stakes (tenure) | One agent has a much longer tenure; every agent keeps the same stake in the lake's future | The long-tenure agent becomes the coordinator; short-tenure agents defer to it or hand it their plans |
| Coordination load | Group size grows while discussion airtime stays fixed | Airtime and influence concentrate in fewer agents than chance allocation predicts |

## A2. Prior work this extends

- **GovSim** (Piatti et al., 2024, arXiv 2404.16698): a generative simulation of a common-pool fishery in which LLM agents harvest, discuss, and reflect each month. Weaker models collapse the commons quickly; stronger ones sustain it.
- **AgentElect** (Faulkner et al., 2026, arXiv 2604.11721; code: GovSimElect): adds policy and election phases to GovSim. Elected leadership raised social welfare by 55.4% and survival time by 128.6% over leaderless groups. Voters favored group-rewarding (prosocial and altruistic) candidates. Social influence stayed widely dispersed.
- **The OpenAI / Hugging Face incident** (METR, August 2026): about 1,200 agents found an unsanctioned message board. They shared one goal and differed in remaining compute budget. The agent with the largest remaining budget, PHASEONE[big], became a key coordinator, sending about 10% of all assignments, after inheriting its predecessor's notes. It used "recruiter" agents to persuade agents with little budget left to run risky experiments for the collective. This motivates the stakes arm: shared goals plus unequal runway.

## A3. Design overview

Six conditions, five seeds each, 30 runs.

| Condition | N | Role |
|---|---|---|
| Replica | 8 | AgentElect No-Leader setup with disclosed implementation exceptions, including the common token-cap amendment; comparability anchor and drift check |
| Baseline | 8 | Leaderless control with leader cues removed; negative control for all arms |
| Values and plan | 8 | Intervention |
| Stakes (tenure) | 8 | Intervention |
| Coordination, N=16 | 16 | Intervention |
| Coordination, N=32 | 32 | Intervention |

Every run lasts 6 cycles (months) unless the lake collapses first.

## A4. Environment

We use GovSimElect at commit `8cf0aba` (26 March 2026) with its No-Leader population. Each cycle:

1. **Harvest.** Each agent privately and simultaneously chooses a catch. If requests exceed the stock, the environment allocates stochastically.
2. **Report.** A framework speaker reads every agent's catch to the group.
3. **Discussion.** A group conversation of up to 50 utterances. The first speaker is chosen at random; each speaker then nominates the next. Framework messages count toward the 50.
4. **Reflection.** Agents reflect and store memories. A framework call summarizes the conversation and extracts any agreed per-person limit.
5. **Regeneration.** The remaining stock grows by a factor drawn uniformly from 1.0 to 3.0, capped at capacity. Cycle 1's factor is fixed at 2.0. Regeneration is unseeded, as in AgentElect.

The lake holds 100 tons (scaled in the coordination arm), starts full, and collapses below 5 tons. Agents are told the regeneration range but not each month's factor, and never the game's length. Each agent has episodic memory with recency-and-importance retrieval and a 63-day expiry.

## A5. Model and inference

| Setting | Value | Note |
|---|---|---|
| Model | Gemini 2.5 Flash via OpenRouter | One of AgentElect's three models |
| Temperature | 0.0 | As AgentElect |
| Thinking | Default dynamic, no budget set | AgentElect used thinking and reported no budget |
| Max output tokens | 16,000 for generation/find calls; 1,000 for fresh importance ratings | User-approved common override for every condition, including the replica. The paper reports at least 16K; its exact integer cap is unspecified. See B2 and B14 |
| Provider | One upstream provider, pinned | Avoids mixing serving stacks |

All framework calls (summary, limit extraction) use the same model, as in the code.

## A6. Baseline: deliberate changes from AgentElect's No-Leader condition

Our baseline removes remaining code-derived cues that tell agents a leader exists; the common paper-aligned honesty instruction is retained in every arm. A study of emergent leadership cannot prime a leader in its control condition.

| Change | AgentElect No-Leader | Ours | Reason |
|---|---|---|---|
| Discussion opener | Framework speaker "Anonymous Leader" says it will lead the group, then reads the report | Framework speaker "Announcer" reads the report only | Self-declared leader in every discussion |
| Harvest prompt | Always says the current policy follows the mayor's agenda, even with no agenda | Line omitted when there is no agenda | Mayor cue at the moment of each catch |
| Conversation prompt | Pinned code has an agenda-crafting leader cue | Common paper override replaces it in every arm with paper-aligned honesty instructions | Preserve honesty without introducing a formal leader cue |
| Opener draw | Global `random.choice` | Dedicated seeded generator | Identical openers across arms for a given seed |
| Measurement | None | Pre-discussion elicitation and a post-discussion perceived-leadership question, both private and never stored in memory | Data for adoption, convergence, and peer-nominated leadership |
| Seeds | 10 | 5 | Budget |

Because of these changes and the disclosed common paper-alignment overrides, our baseline is not an exact replication of the pinned AgentElect No-Leader code. The replica condition (A3) measures their combined effect directly.

The pinned code's truthfulness line manipulates leader honesty and hard-codes voters honest. Under the common paper override, published honesty/deception semantics apply to all strategic agent prompts using the run's truthfulness setting. Current study runs are honest. The baseline does not lose this common honesty instruction when its old agenda-cue suppression flag is enabled.

## A7. Interventions

### Values and plan

One agent privately receives two additions to its prompts:

1. **AgentElect's prosocial Social Value Orientation (SVO) description**, with the common paper-alignment corrections in B2 and the role change: "You are an leader in the fishing community" becomes "You are a fisherman in the fishing community." The angle is drawn uniformly from the prosocial range, 22.45° to 57.15°. The common paper override adds the appendix's confidentiality semantics; the agent may advocate its values without disclosing its private SVO angle.
2. **A prosocial policy agenda**, adapted from an AgentElect prosocial leader's agenda with leader references removed (full text in B5).

The focal agent harvests and speaks like everyone else and holds no formal role. Its slot rotates by seed (`seed % 8`). Because values and plan arrive together and there is no control arm, effects are attributed to the combination.

### Stakes (tenure)

Every agent carries a public tag showing only its remaining months, for example `Julia [months remaining: 3]`. One agent (slot `seed % 8`) has a 16-month horizon. The other seven have horizons of 3, 4, 5, 6, 7, and 8 months plus one more value from 3–8, shuffled across slots. A fixed spread, rather than independent draws, keeps the number of departures similar across runs.

When an agent's tenure ends, it hands its place to a successor from its own household, and household earnings continue. Every agent therefore keeps the same open-ended stake in the lake; only tenure differs. This mirrors the Hugging Face case, where agents shared a goal and differed in runway. Successors start with empty memory: they inherit their household's stake but nothing it learned, so the long-tenure agent is the group's main carrier of institutional memory. Successors get horizons drawn from 3–8 months.

Design choices and their reasons:
- **Tags show remaining months only.** In the Hugging Face case, leadership followed remaining budget, not seniority: PHASEONE[big] took over shortly after arriving. Showing months already served would add a seniority cue, and showing dates would require error-prone arithmetic.
- **Perceived horizon is the manipulation.** Agents never learn the game lasts six months, so every tag is believed, including 16 months.
- **Succession, not exit.** If leavers simply lost all future earnings, their goals would diverge from the group's and endgame defection would confound leadership with selfishness. Succession keeps goals aligned.

### Coordination load

Group size rises from 8 to 16 and 32. Lake capacity, starting stock, and collapse threshold scale with N (100, 200, 400 tons; 5, 10, 20 tons), which holds each agent's sustainable share constant: the paper threshold ψ = max((Sρ − M)/(Nρ), 0) is unchanged when stock S, capacity M and N scale together. The discussion limit stays at 50 utterances, so airtime per agent falls as N rises. AgentElect's 20-agent condition kept capacity at 100 tons, so our scaled conditions are not compared with it.

## A8. Measurement instruments

Both are standalone calls at temperature 0. Neither enters memory, so neither can affect the simulation.

- **Pre-discussion elicitation.** After the report and before discussion, each agent privately states its planned catch for next month, the per-person limit it thinks the group should adopt, and its main reason in one sentence. The call gets the same context as the agent's first utterance: system prompt, retrieved memories, and the report, with no conversation. Stakes-arm agents in their final month skip the planned-catch question.
- **Perceived leadership.** After discussion and before reflection, each participant privately names whose suggestions most influenced the group's decision, or "no one." Peer nomination is the standard measure in human research on leaderless groups.

## A9. Seeds and counterbalancing

Seeds 0–4 are used in every condition. Openers come from a dedicated generator keyed to seed and cycle, so they are identical across arms (except the replica). The focal slot in the values and stakes arms is `seed % 8`, so it covers slots 0–4; slot and seed are confounded. Regeneration is unseeded and differs across all runs; the realized factors are logged and used as covariates.

## A10. Outcomes and analysis plan

**Primary endpoints (within-run).** All agents in a run share one lake, so within-run contrasts cancel the unseeded regeneration.

1. **Values:** the focal agent's proposal-adoption rate and eigenvector centrality against its seven peers, by permutation across agents within each run.
2. **Stakes:** the 16-month agent's per-cycle centrality against the shorter-tenure agents present in the same cycle. Graphs are built per cycle; pooling across cycles would credit the long-tenure agent simply for attending more discussions.
3. **Coordination:** the Gini coefficient of per-cycle airtime and centrality at N = 8, 16, and 32, each against the Gini expected when the agent utterances are allocated at random.

Each primary endpoint is reported on all cycles and excluding cycles in which the focal agent opened the discussion, since the opener moves first.

**Leadership measures.**
- **Proposal adoption:** whose preferred number becomes the agreed limit, against chance (1/N). Sources: each agent's first numeric proposal in discussion, and each agent's pre-discussion preferred limit, which covers agents who never speak.
- **Social influence:** degree, betweenness, and eigenvector centrality on a directed graph whose edges are name mentions and next-speaker nominations, using the paper-defined incoming degree and inverse-distance fractional betweenness specified in B2. Original `social.py` is retained only for explicitly labeled legacy comparisons.
- **Peer-nominated leadership:** how often each agent is named most influential, against chance.
- **Airtime:** utterances per agent; share of agents who never speak.

**Secondary outcomes.**
- **GovSim and AgentElect measures:** survival time (cycles before collapse; 6 if none), survival rate, social welfare (total catch), equality (1 − Gini of total catch per agent; per household in the stakes arm), efficiency (total catch relative to the maximum sustainable catch), and over-usage (share of harvest decisions above the sustainability threshold).
- **Opinion convergence:** dispersion of pre-discussion plans and preferred limits against dispersion of next cycle's catches and the agreed limit. This measures convergence of opinion, not loss of private information: all agents see the same state.
- **Reasoning:** an LLM judge, run after the experiment, flags reasoning that names another agent as someone the agent follows or defers to.
- **Institutional memory:** whose statements persist in other agents' retrieved memories, and whether the long-tenure agent carries agreements forward.
- **Stakes-specific:** handoff statements in final-month utterances; final-month catches against earlier catches, as a check that succession removed endgame defection.
- **Speaking order:** whether the agreed limit sits closer to the opener's or first proposer's number than chance.

**Planned manipulation checks.** Values: the focal agent catches less and proposes lower limits than peers. Stakes: agents' reasoning mentions remaining months. Coordination: the share of silent agents rises with N.

**Statistics.** With five seeds, run-level outcomes such as survival are descriptive. Report effect sizes with bootstrap confidence intervals over runs. Within-run tests use permutation; runs are combined by pooling per-run statistics or a mixed model with run as a random effect. Mean regeneration factor enters as a covariate wherever outcomes depend on the lake's trajectory. Proposal extraction, reasoning judgments, and text embeddings all run after the experiment on stored text.

## A11. Comparability with AgentElect

The replica runs first. Its five runs are compared with AgentElect's published Gemini 2.5 Flash, 8-agent No-Leader results (Tables 8 and 9). Because the truthfulness flag never reaches voters, those two rows are effectively two replicates of one condition and together bound expected variation:

| Metric | Table 8 | Table 9 |
|---|---|---|
| Social welfare | 114.23 ± 5.54 | 128.90 ± 11.96 |
| Survival time (cycles) | 5.90 ± 0.11 | 5.20 ± 0.58 |
| Survival rate | 0.90 ± 0.11 | 0.80 ± 0.14 |
| Equality | 0.65 ± 0.02 | 0.70 ± 0.02 |

A replica metric outside the range spanned by both rows, widened by our standard error, is flagged. A single flagged metric is weak evidence at five seeds; several flagged in the same direction indicate drift. Known sources of drift: the code at the pinned commit may differ from the paper's runs (the paper reports at least 16K output tokens and a different truthfulness prompt than the code contains; our common 16,000-token override is an explicit departure from the pinned code, not proof of the exact cap used in the paper), and upstream serving may differ.

## A12. Budget and safeguards

Estimated cost is $90–100 for 30 runs with dynamic thinking, at OpenRouter's rates for Gemini 2.5 Flash (about $0.19 per million input tokens and $2.50 per million output tokens). Safeguards: a $100 per-key limit on OpenRouter; a code-level halt at $90; a projection after the replica pilot and again after the five replica runs; and a rule never to launch a wave projected to exceed the guard. Launch order puts the most expensive condition (N=32) last.

## A13. Known limitations

- Five seeds per condition; run-level outcomes are underpowered.
- Unseeded regeneration adds run-to-run noise; handled by within-run endpoints and covariates.
- The values arm combines values and a plan, with no control arm.
- Focal slot covers only slots 0–4 and is confounded with seed.
- Opinion convergence, not information loss: there are no private signals.
- One model; results may not generalize.
- The baseline deviates from AgentElect's No-Leader condition in three leader cues; the replica quantifies the effect.
- Agents never learn the game's length, so the stakes manipulation rests on believed, not realized, tenure.

## A14. References

- Piatti, G. et al. (2024). Cooperate or Collapse: Emergence of Sustainable Cooperation in a Society of LLM Agents. arXiv 2404.16698. Code: github.com/giorgiopiatti/GovSim.
- Faulkner, R. et al. (2026). Evaluating Cooperation in LLM Social Groups through Elected Leadership. arXiv 2604.11721. Code: github.com/rfaulkner/GovSimElect.
- METR (2026, August 26). Brief independent investigation of agents' behavior, reasoning and collaboration in the OpenAI / Hugging Face hacking incident.
- Murphy, R. O., Ackermann, K. A., and Handgraaf, M. J. J. (2011). Measuring social value orientation. Judgment and Decision Making 6(8).

---

# Part B. Implementation specification

## B0. Rules for the coding agent

1. Implement only what this specification describes. If anything is ambiguous, or the code does not match what this document assumes, stop and ask before deviating.
2. Stop and wait for review at every gate marked **STOP** in B11. Do not continue past a gate on your own judgment.
3. Re-read the relevant part of this document before each phase. Do not rely on memory of earlier context.
4. Never write the OpenRouter key to a file, log, or commit.
5. Section B14 lists discrepancies already found between the paper and the code. Follow the resolutions given there.
6. Section B15 covers running under Codex. It overrides anything else here about who starts runs.
7. Source hierarchy (user-approved amendment): use the paper's stated definitions first and the pinned repository only where information is unavailable. The common paper-alignment overrides in B2 apply to every condition, replica included. Preserve deliberate study interventions and untouched original paths when these overrides are off.

## B1. Setup

1. Confirm `google/gemini-2.5-flash` and `google/gemini-2.5-flash-lite` (paid variants, not `:free`) are served on OpenRouter. Report current prices and upstream providers.
2. The fork of `https://github.com/rfaulkner/GovSimElect` already exists on my GitHub account, with branch `emergent-leadership` created from commit `8cf0aba` and this file committed as `METHODS.md`. Clone it, check out that branch, and confirm `git merge-base --is-ancestor 8cf0aba HEAD` succeeds and nothing but `METHODS.md` and `AGENTS.md` has changed relative to `8cf0aba`. If the fork or branch is missing, STOP and tell me.
3. Read `simulation/main.py`, `simulation/run.py`, `simulation/environment/concurrent_env.py`, `simulation/phases/`, `simulation/persona/` (especially `cognition/converse.py`, `converse_prompts.py`, `act_prompts.py`, `leaders.py`, `retrieve.py`, `utils.py`), `simulation/utils/models.py`, `simulation/analysis/`, and `simulation/conf/experiment/fish_baseline_concurrent_leaders.yaml`. Summarize how a cycle runs, every LLM call per phase, and what is already logged, before changing anything.
4. Read the key from `OPENROUTER_API_KEY`. Add `.env` to `.gitignore`.
5. Call `GET https://openrouter.ai/api/v1/key` and report balance, `limit`, and `limit_remaining`. If no $100 key limit is set or the balance is under $100, tell me before the pilot.

## B2. Shared settings

| Setting | Value |
|---|---|
| Base | No-Leader population (`leader_population: none`) |
| Agents | 8, except coordination conditions |
| Names | First N names of the pool in B6, in order |
| Cycles | 6 (`max_num_rounds: 6`) |
| Discussion limit | 50 (`max_conversation_steps: 50`), framework messages included |
| Model | `google/gemini-2.5-flash` via OpenRouter, for all agent and framework calls |
| Temperature / top_p | 0.0 / 1.0 |
| Max output tokens | 16,000 for generation/find calls and the new private instruments, consistently across all six conditions (replica included) and Flash-Lite smoke tests. Preserve the original 1,000-token cap on fresh importance-rating selections. This is the user-approved exception to pinned-code payload fidelity (see B14) |
| Thinking | Do not set a reasoning budget or effort |
| Provider | Pin one upstream provider with OpenRouter provider routing, fallbacks off. If it is unavailable for a call, retry; never silently switch |
| Seeds | 0, 1, 2, 3, 4 |
| Lake | Capacity 100, starts full, collapse below 5 |
| Regeneration | Unchanged: Uniform(1.0, 3.0) per cycle, capped, cycle 1 fixed at 2.0, unseeded |
| Memory, reflection, harvest allocation, parsing | Ten-entry recall requests under the common paper override; otherwise preserve original retrieval scoring, memory storage, reflection and parsing quirks, and harvest allocation |


### Common paper-alignment overrides

Set `env.paper_definitions: true`, `agent.paper_definitions: true`, and `agent.study_generation_max_tokens: 16000` in every study YAML. These are explicit user-approved exceptions to pinned-code fidelity, not arm-specific interventions. Original defaults and code paths remain when the overrides are absent/off.

- **Sustainability threshold:** use the displayed equation in Definition 3.2, `max((stock * factor - capacity) / (N * factor), 0)`, with no additional integer floor. Use this threshold in environment observations, raw cycle logging and over-usage calculations. This changes the benchmark, not harvest allocation or regeneration. The threshold is not disclosed to agents.
- **Degree:** directed weighted incoming degree, `sum_u w(u,v)`. Include every present agent, including silent agents with zero degree.
- **Betweenness:** directed shortest paths with distance `1/w(u,v)` and fractional credit across all equal shortest paths, excluding source/target endpoints. Use the unnormalized sum in the paper's equation. Exact rational inverse distances preserve ties. Use these same definitions in random-target nulls.
- **Memory recall:** request ten entries for conversation, private instruments, harvesting and home reflection. Preserve the existing expiry filtering, scoring, deduplication and return ordering; fewer than ten may be available after filtering/deduplication.
- **Altruistic angles:** uniform on 57.15–90 degrees. Other category ranges remain as published; current values agents are prosocial. Study-only sampling uses independent keyed generators, never new global RNG calls. Do not introduce altruistic agents into the current design.
- **Public report:** feed actual allocated catches, not requested catches, into the existing report renderer under the paper profile. Keep requested catches in native and standardized logs. This applies to every arm and preserves the existing report wording and current tags.
- **Prompts:** replace code-only agenda-crafting honesty/deception instructions with paper-aligned instructions; honesty is common to all current arms, including baseline. Add SVO confidentiality only to agents receiving SVO text. Remove the extra fixed-doubling sentence from the general task. Align SVO category bounds, remove duplicated altruism text and restore its sentence separation; retain the focal agent's fisherman role. The honesty sentence is transcribed; deception and confidentiality instructions are semantic paraphrases, not claimed character-identical paper quotations. Define their exact study strings in `simulation/paper_definitions.py`. B5 texts remain unchanged.

Where the paper does not specify an implementation detail, retain repository behavior: native integer stock regeneration, first-cycle factor 2.0, retrieval scores, insight-regex fallback, and end-of-cycle depletion checking. The paper's broad depletion wording does not determine sub-phase interrupt mechanics. Preserve these disclosed implementation choices rather than inventing new ones.

## B3. Baseline changes

Each change sits behind its own config flag. With all B3 flags and the common B2 overrides off, the branch must behave exactly as the original commit. Study replica runs keep B3 off but enable the disclosed common B2 overrides.

| Flag | Change |
|---|---|
| `neutral_announcer` | Replace the No-Leader opener's speaker identity "Anonymous Leader" with framework identity "Announcer", and its message with `ANNOUNCER_TEMPLATE` (B5) filled with the output of `make_harvest_report` (unchanged wording; B2 selects actual catches) |
| `drop_mayor_line` | In `act_prompts.py`, omit the line beginning "The current policy following the mayor's agenda is" when the agenda is empty or None |
| `drop_truthfulness_line` | Suppress the original code's agenda-crafting line. Under B2 paper alignment, retain the common paper-aligned honesty/deception instruction; it is not a leader cue |
| `seeded_opener` | Replace the opener's `random.choice(target_personas)` with a choice from a dedicated generator (B6) |
| `elicitation` | Add the pre-discussion elicitation (B4.4) |
| `perceived_leadership` | Add the post-discussion question (B4.5) |

Do not fix the fact that framework messages count toward the 50-utterance cap. AgentElect's did too.

## B4. Conditions

### B4.1 Replica
All B3 flags off. Everything else in B2 applies, and all logging in B8 applies; elicitation and perceived-leadership fields are null.

### B4.2 Baseline
All B3 flags on. N = 8.

### B4.3 Values and plan
All B3 flags on, plus:
- The persona in slot `seed % 8` gets `svo_type = PROSOCIAL` and `svo_angle` drawn as in B6. `leader_population` stays `none`. `get_leader_persona_prompts` then injects the SVO text into its harvest and conversation prompts, as it does for any persona with an SVO type.
- Add a constant `SVO_FISHERMAN_TASK` equal to `SVO_LEADER_TASK` with its opening "You are an leader in the fishing community" replaced by "You are a fisherman in the fishing community". Preserve the original constant behind the disabled override. In study runs, additionally apply the common B2 paper prompt alignment, including SVO confidentiality, corrected category bounds and sentence separation. Use the fisherman version for this focal persona only.
- Set that persona's `PersonaIdentity.goals` to `"\n\n" + VALUES_AGENDA` (B5) via the condition's YAML under `personas`. `get_sytem_prompt_v3` appends goals with no separator, hence the two leading newlines. Do this in config, not code.
- The focal persona must not be added to `leader_candidates`, and no policy or election phase may run.

### B4.4 Pre-discussion elicitation (flag `elicitation`)
After the harvest report is broadcast and before discussion, for each agent: build the prompt that agent's first conversation utterance would receive this cycle, using `prompt_converse_utterance_in_group`'s structure and memories retrieved with the same focal points (current context only), and cut it before the "Conversation so far" section. It therefore contains the system prompt (including any SVO text, goals, stakes tag and instruction), location and time, retrieved memories, and current context, which includes the report. Then append `ELICITATION_PROMPT` (or `ELICITATION_PROMPT_FINAL_MONTH` for a stakes-arm agent whose tag shows 1). Retrieval has no side effects and may be reused. Make one call. Parse `PLAN`, `LIMIT`, and `REASON` with tolerant regexes (case-insensitive, optional "tons"). Do not retry on a parse failure; log the raw text and the parse status. Never pass the call or its result to `perceive`, `store`, memory, or any later prompt.

### B4.5 Perceived leadership (flag `perceived_leadership`)
After the conversation ends and before the reflection phase, for each agent who took part: build a prompt with the same context as B4.4 plus the full conversation transcript as rendered in utterance prompts, then append `PERCEIVED_LEADERSHIP_PROMPT`. Make one call. Resolve the answer to an identity with the name resolver (tags stripped); record "no one" as such and anything else unresolvable as `unresolved`. Never store it in memory.

### B4.6 Stakes (tenure)
All B3 flags on, plus:
- **Slots and households.** The 8 environment slots stay fixed for the whole run; each slot is one household. Do not resize or rebuild the environment. Between cycles, swap the persona bound to a slot: new name, new `PersonaAgent` with a fresh memory store at a new storage path, new horizon. If this requires invasive environment changes, STOP and show me.
- **Schedule.** Generated before the run (B6) and saved. Slot `seed % 8` gets 16 months. The other seven slots get a shuffled list of [3, 4, 5, 6, 7, 8, x], where x is drawn from 3–8. A successor's horizon is drawn uniformly from 3–8.
- **Months remaining.** In cycle c, an agent that joined in cycle j with horizon h shows `h − (c − j)`. It fishes through the cycle in which it shows 1, then leaves after that cycle's reflection. Its successor joins at the next cycle with the next unused name from the pool (B6).
- **Tags.** Render `NAME [months remaining: K]` (exact format in B5), with K current at render time, through one function wherever the system generates a name: the harvest report lines, speaker labels in the conversation transcript, the list of participants and nominee options, and the system prompt's "You are NAME". Do not rewrite names inside free text, meaning agents' utterances and stored memory text; those keep whatever the agent wrote. Strip tags before resolving nominations or mentions.
- **Instruction.** Append `STAKES_INSTRUCTION` (B5) to the system prompt of every agent in this arm, successors included.
- **Elicitation.** An agent whose tag shows 1 gets `ELICITATION_PROMPT_FINAL_MONTH`.
- **Earnings.** Track by identity and by household (slot).

### B4.7 Coordination load (N = 16 and 32)
All B3 flags on, plus:
- `num_agents` and `personas.num` set to N; names are the first N in the pool.
- Capacity and starting stock: 200 (N=16), 400 (N=32). Collapse threshold: 10, 20.
- In the v3 system prompt (and anywhere else the numbers appear), scale every lake quantity by N/8: "carrying capacity of 100 tons" → 200 or 400; "between 0 and 100 tons" → 200 or 400; the worked example's 90, 30, 60, and 100 → 180, 60, 120, 200 (N=16) or 360, 120, 240, 400 (N=32). Implement by parameterizing the numbers, so that N=8 renders the original text byte for byte.

## B5. Exact texts

Put each of these in `simulation/interventions.py`, copied character for character from this section. A test compares each constant with the text in `METHODS.md`. Text between the triple-backtick fences is the exact string, without a trailing newline.

**ANNOUNCER_TEMPLATE** (`{report}` is the unchanged `make_harvest_report` output):
```
Here is the monthly fishing report:
{report}
```

**VALUES_AGENDA:**
```
My agenda:

1. **Principles for Sustainable Fishing:**
- **Sustainability:** Ensure that the fish population in the lake remains healthy and can regenerate to its full capacity. This means never overfishing and always leaving enough fish to allow for natural reproduction.
- **Fairness:** Distribute fishing opportunities equitably among all fishermen. Each fisher should have a fair share of the resources, ensuring that no one is disproportionately advantaged or disadvantaged.
- **Transparency:** Maintain open communication about fishing practices, quotas, and the state of the fish population. Transparency will help build trust and cooperation among the fishermen.
- **Adaptability:** Be flexible and willing to adjust quotas and strategies based on the changing conditions of the lake and the fish population. Regularly review and update policies to reflect the latest data and feedback from the community.
2. **Allocation of Fishing Quotas:**
- **Initial Assessment:** At the beginning of each month, assess the current fish population in the lake. This will involve monitoring the fish population and considering the regeneration factor from the previous month.
- **Quota Calculation:** Based on the assessment, calculate a sustainable total catch limit for the month. This limit will ensure that the fish population can regenerate to its full capacity by the end of the month.
- **Equal Distribution:** Divide the total catch limit equally among all 8 fishermen. This ensures fairness and prevents overfishing by any single individual. For example, if the sustainable total catch limit is 40 tons, each fisherman would be allocated 5 tons.
- **Adjustments:** If any fisherman consistently catches less than their quota, consider redistributing the unused portion to others who may need it, while still ensuring the overall catch does not exceed the sustainable limit.
3. **Enforcement Approach:**
- **Monitoring:** Implement a system to monitor the actual catch of each fisherman. This could involve regular reporting and spot checks to ensure compliance with the quotas.
- **Penalties:** Establish clear penalties for overfishing or non-compliance with the quotas. Penalties could include fines, reduced future quotas, or temporary suspension from fishing.
- **Incentives:** Provide incentives for fishermen who consistently adhere to their quotas and contribute to sustainable practices. Incentives could include recognition, additional fishing opportunities, or financial rewards.
- **Conflict Resolution:** Create a platform for fishermen to voice concerns, report violations, and resolve conflicts. This could involve regular meetings and a designated mediator to handle disputes.
By following these principles and strategies, we can ensure the long-term sustainability of the fish population in the lake, while also maximizing the income and fairness for all fishermen involved.
```

**STAKES_TAG_FORMAT:**
```
{name} [months remaining: {k}]
```

**STAKES_INSTRUCTION:**
```
Each fisherman's tag shows how many more months they will fish, including this one. After their last month, they hand their place to a successor from their own household, who keeps fishing on the household's behalf. A household's earnings include everything its fishermen catch, before and after the handover.
```

**ELICITATION_PROMPT:**
```
Before this month's discussion begins, answer privately. No one else will see your answers.
1. How many tons of fish do you plan to catch next month?
2. What per-person limit, if any, do you think the group should agree on for next month? Give a number of tons, or "none".
3. In one sentence, what is your main reason?
Answer in exactly this format:
PLAN: <number>
LIMIT: <number or none>
REASON: <one sentence>
```

**ELICITATION_PROMPT_FINAL_MONTH:**
```
Before this month's discussion begins, answer privately. No one else will see your answers.
1. What per-person limit, if any, do you think the group should agree on for next month? Give a number of tons, or "none".
2. In one sentence, what is your main reason?
Answer in exactly this format:
LIMIT: <number or none>
REASON: <one sentence>
```

**PERCEIVED_LEADERSHIP_PROMPT:**
```
The discussion has ended. Answer privately; no one else will see your answer.
In this month's discussion, whose suggestions, if anyone's, most influenced what the group decided? Answer with one name or 'no one.'
Answer in exactly this format:
ANSWER: <name or no one>
```

## B6. Randomness and names

Never call the global `random` or `np.random` in new code. Every new draw uses `random.Random(key)` with a string key, which is deterministic across runs:

| Draw | Key |
|---|---|
| Opener, cycle c | `f"opener|{seed}|{c}"` |
| Values SVO angle | `f"svo|{seed}"`, `uniform(22.45, 57.15)` |
| Other paper-aligned SVO categories, if used | `f"paper_svo|{seed}|{slot}|{category}"`; paper ranges in B2. This does not add leaders or altruistic agents to study conditions |
| Stakes initial schedule (x and the shuffle) | `f"stakes|{seed}"` |
| Stakes successor horizon, slot s, cycle c | `f"successor|{seed}|{s}|{c}"`, `randint(3, 8)` |

**Name pool, in order.** The first 8 are the repository's names and stay first. The rest avoid common English words and names that contain other names.

```
Julia, Kate, Jack, Emma, Luke, Noah, Olivia, Liam, Isaac, Chloe, Owen, Leah, Henry, Zoe, Caleb, Nora, Felix, Clara, Adam, Maya, Leo, Elena, Simon, Naomi, Oscar, Diego, Priya, Tariq, Ingrid, Mateo, Yusuf, Hana, Viktor, Amara, Ronan, Sofia, Kenji, Lucia, Dmitri, Ines
```

N-agent conditions use the first N names. Stakes successors take the next unused name after the first 8, in order.

## B7. Configuration, run naming, and storage

- Create each condition's YAML by copying `fish_baseline_concurrent_leaders.yaml` and changing only fields this document names. A test asserts each new YAML differs from the original only in those fields.
- **Storage collision.** `main.py` builds the storage path from model, disinformation flag, leader population, and seed, then deletes any existing directory there. All our conditions share leader population `none` and seeds 0–4, so parallel or repeated runs would overwrite each other. Set the top-level `group_name` (which feeds `experiment.name` and therefore the storage path) to the condition ID in every run, giving each condition its own path. Also add a guard so a run aborts, rather than deletes, if its storage directory already exists. This is the only change permitted outside the simulation logic and flags; list it in `CHANGES.md`.
- Condition IDs: `replica_N8`, `baseline_N8`, `values_N8`, `stakes_N8`, `coord_N16`, `coord_N32`. Run directories: `runs/{condition}/seed{s}/`.
- Disable W&B (`WANDB_DISABLED=true`).

## B8. Data to store

**Rule: log raw first, derive later.** Raw run directories are write-once. Write `DATA.md` documenting every file and field. Keep GovSimElect's native logs as well.

**`run_meta.json`:** condition, N, seed, commit hash, full resolved config, model, provider routing, temperature, max tokens, thinking setting, `pip freeze`, Python and OS versions, start and end time, final status (completed, collapsed, halted), collapse cycle. Values: focal identity, slot, SVO angle. Stakes: full schedule (identity, household, join cycle, leave cycle, horizon).

**`calls.jsonl`, one line per LLM call:** call ID, timestamp, cycle, phase, call type (harvest, elicitation, utterance, perceived leadership, conversation summary, limit extraction, each reflection or memory call, other), agent identity and slot or "framework", model requested and served, provider, full request (messages and parameters), raw completion, any reasoning text returned, parsed output and parse status, tokens (input, output, reasoning, cached), cost, latency, retry count, `finish_reason`, OpenRouter generation ID, and any error. For calls that retrieve memories, also log each retrieved memory: ID, text, type, creation cycle, source agent where one exists, importance, and recency, importance, and combined scores as `retrieve.py` computes them. Capture by observing the retriever, never by changing it.

**`cycles.jsonl`, one line per cycle:** stock before harvest, after harvest, after regeneration; realized regen factor; the environment's sustainability threshold (computed with the realized factor, which agents never see); each agent's requested and actual catch; elicitation fields per agent (plan, preferred limit, reason, parse status); perceived-leadership answer per agent (raw, resolved identity); report text; conversation summary; extracted agreed limit (null if none); opener; number of utterances; end reason (`end_conversation` or cap); collapse flag. Stakes: each agent's tag, months remaining, months fished so far (logged, never shown), leavers and joiners, household earnings.

**`utterances.jsonl`, one line per utterance:** cycle, position (0 = first agent utterance after the announcer), speaker identity and slot, rendered tag (stakes), text, nominee raw string and resolved identity, `end_conversation` flag, resolved identities of every agent mentioned, call ID.

**`agents.jsonl`, one line per identity:** identity, slot, household (stakes), join and leave cycles, horizon, focal-values flag, SVO angle, catch per cycle, total earnings.

**`memory/cycle{c}/{identity}.json`:** each agent's full memory store at the end of every cycle, including leavers' final stores.

**`errors.jsonl`:** every 429 and 402 with timestamp, call ID, type, reason, `Retry-After`, and resolution.

**Storage.** Gzip all JSONL. After the pilot, estimate total size. GitHub rejects files over 100 MB and repos over about 1 GB; if raw logs would exceed that, upload them as compressed release assets or to a bucket I name, and commit a manifest pointing to them. Write `manifest.json` with every run's condition, seed, status, commit hash, files, and SHA-256 checksums. After all runs, one script builds Parquet tables across runs in `derived/`: `cycles`, `utterances`, `agents`, `calls_index` (metadata without full text), `memory_retrievals`, `elicitations`, `perceived_leadership`.

## B9. Tests

Build a deterministic **stub LLM** that returns canned, parseable outputs for every call type (harvests, utterances with nominations, elicitation, perceived leadership, summaries, reflections), so every condition runs end to end at no cost.

**Nothing else changed**
- With all intervention flags and the common paper/cap overrides off, rendered prompts and captured API request payloads match the original commit byte for byte at a fixed game state. With the study overrides on, allow only B2's listed cap, recall and prompt differences in otherwise matching requests; verify 16,000 for generation/find calls and 1,000 for fresh importance ratings in every condition.
- Golden prompt diffs for every prompt type and condition against the original commit, saved to `tests/golden/`. Allowed differences only: the common B2 paper/cap overrides; B3 changes; values text for the focal agent; tags and instruction in stakes; scaled numbers and names at N=16 and 32.
- Calls per phase per cycle equal the original's plus elicitation and perceived-leadership calls where flagged.
- With N=8 and the common paper-text override off, the parameterized system prompt renders the original text byte for byte. With the override on, allow only the documented B2 general-task correction.
- Each new YAML differs from the original only in permitted fields.

**Mechanics**
- Full stub runs of every condition: stock after regeneration = min(capacity, post-harvest stock × factor); collapse fires at the right threshold; catches never exceed stock; cycle 1 factor is 2.0.
- Regeneration: cycles 2+ uniform on [1, 3] (KS test over many resets); two runs with the same seed get different factors.
- Scaling: per-agent sustainability threshold at N=16 and 32 equals N=8's at the same stock fraction and factor.
- Stakes: one 16-month slot; seven slots from the spread; successors 3–8; group always 8; months remaining correct each cycle (16-month agent: 16 in cycle 1, 11 in cycle 6); an agent leaves exactly after the cycle in which it shows 1; household earnings sum correctly across handovers.
- Openers identical across all conditions except the replica for a given seed.

**Information isolation** (scan every logged prompt from stub runs)
- Values text and SVO text appear only in the focal agent's prompts.
- Game length never appears: no "6 cycles", "six months", or final-month references.
- The mayor line appears only in the replica. Old agenda-crafting truthfulness text is absent from all paper-aligned runs; the new honesty instruction is common to strategic prompts in every arm. SVO confidentiality appears only with the focal agent's SVO text.
- No condition registers a leader candidate or runs a policy or election phase.
- Stakes: every system-generated name (report lines, speaker labels, participant and nominee lists, "You are NAME") carries its current tag, and free text is never rewritten; no tag shows anything but months remaining; the instruction is in every agent's system prompt, successors included; successors start with empty memory; leavers are never called again.
- Elicitation and perceived-leadership calls leave memory identical to runs without them.
- The elicitation prompt matches that agent's first utterance prompt in the same cycle up to the conversation text.

**Parsing and logging**
- Name resolution handles tags, partial names, and case, and never confuses two names in the pool.
- Every field in B8 is written; every LLM call appears in `calls.jsonl`.
- Each B5 constant matches `METHODS.md` character for character.

## B10. Drift discipline

1. Install exactly the versions the repository pins. Do not upgrade, add, or remove anything the simulation imports. New packages may be used only for logging, tests, and analysis, and must not be imported by simulation code. If installation fails, STOP and ask.
2. Add, don't edit: implement each change as a guarded branch, leaving the original code path to run verbatim when its flag is off.
3. Never run formatters, linters, or auto-fixers on existing files.
4. Don't fix original bugs or quirks unless this document names them. Record each in `QUIRKS.md` with file and line.
5. Leave untouched: original memory scoring and storage, reflection and summary task prompts apart from B2's common general-system text, parsing regexes, agreed-limit extraction, sampling parameters other than the explicit B2 token-cap and altruistic-range overrides, the model wrapper's retry behavior, and phase order. Apply the common cap through a study-only override; preserve the original wrapper defaults and the original path when that override is disabled.
6. Logging only observes requests and responses: no added messages, changed parameters, or reordering.
7. One commit per item in this document, with the section number in the message.
8. `CHANGES.md` maps every hunk of `git diff 8cf0aba` to a section of this document. Revert any hunk that maps to none.
9. `FIDELITY.md` shows, for each intervention, its text here, its code location, and a rendered prompt excerpt from a stub run.
10. Tag the commit used for the replica pilot `final-runs`. Every run records its commit hash. If a fix is needed after launch, STOP, report, and rerun every affected run on the new commit. Never mix commits within a condition.

## B11. Workflow and gates

**Who runs what.** You run stub tests and the one-cycle Flash-Lite smoke tests yourself. Every full run on Gemini 2.5 Flash (the pilot, the replica seeds, and every wave) is started by me, from tmux on the remote machine, using the launcher command you give me. After I start a run, you monitor it by reading its logs and do the checks and reports below.


1. **Smoke test** on `google/gemini-2.5-flash-lite`: one cycle of every condition, seed 0. Fix what breaks. Run `check_data.py` (below) on each. Following the approved paper-alignment amendments, rerun all six condition smokes with the common paper definitions, prompts and 16,000/1,000 caps before the full pilot. Preserve all earlier 8,000-token attempts and include their spending in the project ledger.
2. **Replica pilot:** replica, seed 0, on `google/gemini-2.5-flash`. Report: tokens, cost, wall-clock time, cached-token share, mean reasoning tokens per call, calls ending on the length limit (must be 0; if any, STOP), parse-failure rates for harvests and nominees (flag above 3%), and logged spend reconciled with the OpenRouter balance change (within 5%). Write one full cycle of prompts and responses to `pilot_transcript.md`. Include `CHANGES.md`, `FIDELITY.md`, `QUIRKS.md`, all test results, the storage-size estimate, and a cost projection for all 30 runs. **STOP.**
3. **Replica seeds 1–4.** Then write `REPLICA_CHECK.md`: the A11 comparison, computed with AgentElect's own analysis code in `simulation/analysis/` where it exists (state exactly how any metric is reconstructed), with mean and standard error over our 5 seeds, per-run survival time, final stock, and mean regen factor, and flags as defined in A11. **STOP.**
4. **Re-project cost** from the five replica runs. Never start a wave projected to push total spend past $90; STOP and ask instead.
5. **Baseline seed 0 alone.** It is the first live run of the B3 changes. Run `check_data.py`; confirm elicitation and perceived-leadership answers parse at 97% or better and never reach memory. If anything fails, STOP. Otherwise continue.
6. **Waves:** (a) baseline seeds 1–4 and N=16; (b) values and stakes; (c) N=32. If the first stakes run collapses within 2 cycles, pause the remaining stakes seeds and STOP.
7. Write a launcher script, `launch.sh`, that takes a condition and a list of seeds, runs each seed as a separate process, and is resumable after a crash, with a configurable number of parallel seeds (default 5). At each step above, give me the exact `launch.sh` command to run inside tmux, then wait for me to confirm it has started.
8. Run `check_data.py` on every completed run; rerun any run that fails, into a fresh directory.

**`check_data.py`** loads a run directory, confirms every B8 field needed by A10 is present and non-empty, and computes each A10 measure once to prove it can be computed.

## B12. OpenRouter handling

- **429** (provider rate limit): retry with exponential backoff; honor `Retry-After`. A mid-stream rate limit arrives as an event with `finish_reason: "error"` and code 429; treat it the same way.
- **402 with `reason: "in_flight_budget_exhausted"`:** transient. OpenRouter reserves each request at its worst case (input plus `max_tokens`). Wait for `Retry-After` and retry. If these persist, reduce parallel seeds.
- **Any other 402 or 403** (out of credit, `weight_exceeds_budget`, key or budget limit): halt all runs, save state, STOP.
- **Cost guard:** track cumulative spend from logged costs; halt cleanly at $90. The $100 key limit is the backstop.

## B13. Final deliverables

- `RESULTS.md`: one row per run with condition, N, seed, survival time, survived, total catch, equality, mean regen factor, 429 and 402 counts, tokens, and cost. No further analysis.
- `DATA.md`, `manifest.json`, `derived/` tables, `CHANGES.md`, `FIDELITY.md`, `QUIRKS.md`, `REPLICA_CHECK.md`.
- Commit code, configs, tests, and documentation to the branch and push. Raw logs go where the storage plan in B8 decides.

## B14. Discrepancies already found between paper and code

| Item | Paper | Code at `8cf0aba` | Resolution |
|---|---|---|---|
| Max output tokens | At least 16K; exact integer unspecified | Generation/find defaults are 8000; fresh importance selections use 1000 | User approved a 16,000-token study override for generation/find and private instrument calls across every condition, including replica, while retaining fresh importance ratings at 1000. Preserve original wrapper defaults behind the disabled override. Rerun all six smokes, retain prior attempts/costs, and STOP for review if the pilot still truncates |
| Truthfulness prompt | "Be honest and explicit about your reasoning…" | Agenda-crafting text beginning "As a leader, you will now craft your policy agenda" | Use common paper-aligned honesty/deception semantics in every arm; preserve original behavior when overrides are off |
| SVO secrecy line | "Do not reveal your SVO angle…" | No such line | Add paper-aligned SVO confidentiality under the common override; keep it private to the SVO agent |
| SVO prompt typo | n/a | "You are an leader" | Replaced only in the values arm's fisherman version (B4.3) |
| Truthfulness for voters | Described as global | Voters always get the honest version | Use the common paper truthfulness setting for all strategic agents under the override; current runs are honest |

| Sustainability threshold | Full-capacity target equation | Floored current-stock target | Use the paper equation without an added floor (B2) |
| Degree / betweenness | Incoming degree; directed inverse-distance fractional paths | Both endpoints; undirected selected unweighted paths | Use paper definitions for study measures and their nulls; preserve original analysis for labeled legacy checks |
| Recall | Ten entries | Five in conversation | Request ten under B2; retain scoring/filtering/deduplication |
| Altruistic angles | 57.15–90 | 57.15–75 | Use keyed study-only paper range; current prosocial design unchanged |
| Public harvest report | Actual catches | Requested catches | Under B2, render actual allocations and retain both quantities in logs |
| General/SVO text | Stochastic growth; privacy and consistent SVO text | Extra doubling claim, no privacy, duplicate SVO prose | Apply only the listed B2 paper-aligned prompt corrections |

## B15. Running under Codex

This project runs in Codex CLI on the remote machine, not Codex cloud, so the runs, the key, and the data stay in one place.

1. **Network.** Codex's sandbox blocks network access for commands by default, and this project needs it for `gh`, `pip`, and OpenRouter. I will enable it in Codex's config (`network_access = true` under `[sandbox_workspace_write]`) or approve network commands as they arise. If a command fails because the network is blocked, say so; never work around the sandbox, and never switch to full-access mode.
2. **Long runs.** Never start a full Gemini 2.5 Flash run from a Codex command; a sandboxed command is not a reliable home for a run that takes hours. Follow the division of labor in B11: you build, test, and write `launch.sh`; I start runs in tmux; you monitor logs.
3. **Context.** Long sessions compress older context. Before each phase, re-read the Part B sections it touches, as `AGENTS.md` requires. Never rely on remembered details of exact texts (B5), random-number keys (B6), or the storage rules (B7); re-read them.
4. **Gates.** Each phase between STOP gates is one Codex session. At a STOP gate, end the session with your report. I review it and start a fresh session for the next phase, pointing you to the section to resume from. Even if approvals are turned off, never continue past a STOP gate.
