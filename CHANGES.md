# Changes relative to the pinned original

Baseline: `8cf0aba9efe0b4592f395d9a66e6cfff3cec9a26`.

| File / hunk | Specification / authorization | Purpose |
|---|---|---|
| `METHODS.md` (new file) | B1.2 | Preserve the supplied binding specification unchanged. |
| `AGENTS.md` (new file) | B15; user-supplied repository instructions | Preserve the supplied agent instructions unchanged. |
| `QUIRKS.md` (new file) | B10.4 | Record observed original behavior and explicit user decisions, including integer regeneration. |
| `simulation/persona/persona.py`: remove the obsolete constructor parameter and its arguments in the retrieval/storage constructor calls | B1.3 / B10.4, explicit user-authorized exception | Repair initialization signatures without changing retrieval or storage implementations. This is an exception to original-source fidelity, applying to every condition including replica. |
| `CHANGES.md` (new file) | B10.8 | Map each change to its source requirement or explicit exception. |
| `SETUP_AUDIT.md` (new file) | B1.1-5 / B10 | Record source behavior, the call inventory, setup checks, validation and unresolved decisions before implementing interventions. |
| `simulation/interventions.py` (new file) | B5 | Copy all seven exact intervention texts from the unchanged specification. |
| `tests/test_intervention_texts.py` (new file) | B9 | Compare all seven B5 constants character for character with their fenced specification texts. |
| `simulation/persona/cognition/act_prompts.py`: guard the original mayor line | B3, user clarification | Omit the line when `agent.act.drop_mayor_line` is enabled and the agenda is None, empty, or the original no-guidance sentinel; preserve it with the flag off. |
| `tests/test_mayor_prompt.py` (new file) | B9 | Execute the actual harvest user-prompt block and compare it against pinned source with absent/disabled/enabled flags and absent/real agendas, without model calls. |
| `simulation/intervention_randomness.py` (new file) | B6, approved N-specific opener interpretation | Define the ordered name pool and dedicated keyed draws, independent of the original random generators. |
| `tests/test_intervention_randomness.py` (new file) | B9 | Verify ordered names, horizon spread/ranges, repeatability, draw isolation and full-pool openers at larger N. |
| `constraints-macos.txt` (new file) | B1 / B10, explicit user authorization | Capture the Mac environment after the approved Transformers 4.51.0 compatibility resolution, preserving the default fixed pins and leaving original requirements files unchanged. |
| `simulation/persona/cognition/converse_prompts.py`: guard the disinformation/agenda line | B3 | Omit the specified truthfulness line only when its dedicated flag is on. |
| `simulation/persona/cognition/converse.py`: neutral announcement and seeded opener branches | B3 / B5 / B6 | Preserve public reporting, change framework identity/text only under the neutral flag, and select a keyed opener only under its own flag; retain original branches when disabled. |
| `simulation/phases/discussion.py`: optional seed/cycle arguments | B3 / B6 | Supply one-based cycle and experiment seed only when seeded openers are enabled. |
| `tests/stub_llm.py` (new file) | B9 | Provide deterministic canned transport responses through the original wrapper and Pathfinder parser, capturing actual request parameters without external calls. |
| `tests/test_simulation_stub.py` (new file) | B9, explicit user clarifications | Exercise six-cycle native simulation and public neutral-report behavior; expect original 8000/1000 token caps and the unchanged reflection-regex fallback. |
| `simulation/measurement_prompts.py` (new file) | B4.4 / B4.5 / B9 | Construct private prompts from the shared original utterance prefix plus the approved public-report context, parse once, and resolve names without storing results in memory. |
| `simulation/persona/cognition/converse.py`: measurement branches and final conversation metadata | B4.4 / B4.5 / B8 | Call instruments around agent discussion before reflection, and retain observational cycle/turn metadata outside prompt and memory construction. |
| `simulation/persona/cognition/utils.py`: name renderer and system/memory name formatting | B4.6 | Render current remaining-month tags in system-generated text; leave free text unchanged. Append the exact household instruction for stakes identities only. |
| `simulation/persona/cognition/utils.py`: v3 lake quantity parameters | B4.7 | Scale capacity, catch range and worked-example lake quantities while preserving N=8 text byte for byte. |
| `simulation/persona/cognition/leaders.py`: SVO_FISHERMAN_TASK and focal selection | B4.3 | Change only the specified opening phrase for the focal persona; preserve original SVO content elsewhere. |
| `simulation/persona/cognition/leaders.py`: report name rendering | B4.6 | Add current tags to system-generated report labels without changing requested-catch report semantics. |
| `simulation/persona/cognition/converse_prompts.py`: participant/nominee tags and stripping selected tags | B4.6 | Display current tags and resolve the selected nominee back to the original identity key; preserve original parsing expressions. |
| `simulation/persona/cognition/store_prompts.py`: name placeholders only | B4.6 | Render system-generated perspective labels with current tags; preserve every other character and operation in these original prompts. |
| `simulation/tenure.py` (new file) | B4.6 / B6 | Precompute identity horizons, rebind fresh personas to existing household slots and rebuild references without rebuilding the environment. |
| `simulation/run.py`: focal SVO, scale, tenure and cycle hooks | B4.3 / B4.6 / B4.7 / B8 | Attach intervention state behind flags and invoke observational recording before/after existing phases. The original environment's allocation and regeneration generators remain unchanged. |
| `simulation/environment/concurrent_env.py`: threshold lookup | B4.7 | Read a configured scaled collapse threshold, defaulting to the original 5. |
| `simulation/main.py`: existing-path abort | B7 | Abort before deleting an existing run directory. |
| `simulation/study_config.py` and six condition YAMLs plus four values-seed YAMLs (new files) | B2 / B4 / B7 | Copy the original config, change specified fields only, set condition-specific group names and rotate the agenda through YAML persona goals. |
| `simulation/recording.py` (new file) | B8 / B10 | Observe existing retrieval outputs/scores, request/parse operations and cycle states, write compressed raw data, memory snapshots and final metadata, and redact secrets. |
| `simulation/budget.py` (new file) | B12 | Share actual spend, outstanding reservations and halt state across processes; reduce active seeds after persistent transient reservation failures. |
| `simulation/openrouter_handling.py` (new file) | B2 / B8 / B12 and approved wrapper interpretation | Pin routing, observe raw SDK results/HTTP errors, recover actual generation costs, honor retry delays and set shared halts; do not change original wrapper internals. |
| `tests/test_conditions.py`, `tests/test_measurements.py`, `tests/test_recording.py`, `tests/test_budget.py`, `tests/test_openrouter_handling.py` (new files) | B9 | Verify six-condition native runs, config goals, prompt fidelity, private-call isolation, raw logging, billing reservations and local simulated API error handling. |
| `DATA.md` (new file) | B8 | Document standardized files, units, raw-call and memory semantics, applicability of null fields and the data lifecycle. |

## Approved interpretations awaiting implementation

- B6 / B9: match non-replica N=8 openers by household slot; N=16 and N=32 choose reproducibly from their full participant lists.
- B2 / B10 / B12: preserve original wrapper internals and add required handling around them; provider-routing parameters are an explicit exception to original API-payload equality.
- B9 mechanics: expect `int(min(capacity, post_harvest_stock * regen_factor))`, preserving the original regeneration truncation.
- A10: use directed study influence graphs; leave AgentElect's original analysis untouched.
- B4.4: retain the public AgentElect report and repeat that public report in private measurement context; preserve the shared original prefix and allowlist the explicit added report context.
- B15: the user selected this Mac for experiment execution. Full Flash runs still require user launch in tmux under B11.
- B1 / B10: the user selected default Mac dependency pins plus Pathfinder's declared dependencies, with the repository's PyTorch 2.2.0 pin. Dependency declarations remain unchanged.
- B1 / B10: the user authorized Transformers 4.51.0 and compatible unpinned packages, preserving every selected fixed pin. Simulation import and `pip check` now pass.
- B4.5: ask all present agents, including those who never spoke.
- B7 / B11: skip validated completed seeds and restart failed seeds in fresh attempt directories, preserving original data.
- B12: the $90 guard counts all project API spending, including smoke tests, retries, failed attempts and later judge calls.
- B2 / B9 / B14: preserve original generation/importance caps of 8000/1000 and the original reflection-regex fallback; make tests explicitly expect both.
- A10 / B11: proposal matching uses 0.000001-ton tolerance, splitting credit among matches; no agreed numeric limit means undefined adoption. Validate inputs for post-experiment judging/embedding without making paid judge calls during checks.
- A10 / B11: record undefined eigenvector centrality explicitly if the directed graph has no unique result; retain degree, betweenness and airtime measures.
