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
| `simulation/intervention_randomness.py` (new file) | B6, approved N-specific opener interpretation | Define the ordered name pool and dedicated keyed draws, independent of the original random generators. Helpers are not yet connected to the runner. |
| `tests/test_intervention_randomness.py` (new file) | B9 | Verify ordered names, horizon spread/ranges, repeatability, draw isolation and full-pool openers at larger N. |
| `constraints-macos.txt` (new file) | B1 / B10, explicit user authorization | Capture the Mac environment after the approved Transformers 4.51.0 compatibility resolution, preserving the default fixed pins and leaving original requirements files unchanged. |
| `simulation/persona/cognition/converse_prompts.py`: guard the disinformation/agenda line | B3 | Omit the specified truthfulness line only when its dedicated flag is on. |
| `simulation/persona/cognition/converse.py`: neutral announcement and seeded opener branches | B3 / B5 / B6 | Preserve public reporting, change framework identity/text only under the neutral flag, and select a keyed opener only under its own flag; retain original branches when disabled. |
| `simulation/phases/discussion.py`: optional seed/cycle arguments | B3 / B6 | Supply one-based cycle and experiment seed only when seeded openers are enabled. |
| `tests/stub_llm.py` (new file) | B9 | Provide deterministic canned transport responses through the original wrapper and Pathfinder parser, capturing actual request parameters without external calls. |
| `tests/test_simulation_stub.py` (new file) | B9 | Exercise six-cycle native simulation and public neutral-report behavior; the all-8000 cap assertion currently exposes an unresolved original/specification mismatch. |

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
