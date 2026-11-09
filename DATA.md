# B8 raw data contract

Each attempt gets a new directory. Existing attempts are never deleted or overwritten. Standardized JSONL files are gzip-compressed; native AgentElect logs are also retained. A completed attempt's raw files are immutable. Derived checks and later tables belong outside these directories.

## Files and units

| File | Contents |
|---|---|
| `run_meta.json` | Condition, N, seed, source commit, resolved config with secrets redacted, model/routing/settings, actual Python/package/OS environment, timestamps, final status/collapse cycle, focal-values details and full planned stakes schedule. Written once at finalization. |
| `calls.jsonl.gz` | One record per actual model transport invocation, including failed invocations; logical local parsing operations are attached to the response they consume. API retries are counted and their individual HTTP errors are in errors. |
| `cycles.jsonl.gz` | One record per completed cycle: stocks, realized factor, native integer sustainability threshold, requested/actual catches, private instruments, public report, summary, limit, opener, discussion length/end, collapse and stakes transitions/household totals. |
| `utterances.jsonl.gz` | Agent turns only, with zero-based position, identity/household slot, displayed tag, text, raw/resolved nominee, end flag, mentions and primary/raw call links. Framework messages are counted separately in cycle records. |
| `agents.jsonl.gz` | One record per identity: slot/household, join/leave schedule and horizon, focal/SVO information, actual catch by cycle and total earnings. |
| `memory/cycle{c}/{identity}.json` | The full in-memory node store and native MEMORY.md text after each cycle, before any leaver is replaced. Includes expired nodes still in the original store. |
| `errors.jsonl.gz` | Timestamped HTTP errors, call ID, code/reason, Retry-After and handling action; zero-error runs have a valid empty gzip stream. |
| `consolidated_results.json`, `responses.json`, `log_env.json`, persona `MEMORY.md` | Original native logs and memories, with the original schemas and quirks preserved. |

Cycles are one-based in standardized data and zero-based in native AgentElect logs. Slots/households are zero-based and persist across successor identities. Fish quantities are tons; earnings are dollars at $1000 per ton. Limits can be null when no agreement exists. A private preferred limit can be the string `none`; a missing/failed parse is separately identified by its parse status. Final-month stakes plans are legitimately absent.

## Calls

Every record contains `call_id`, `timestamp`, `cycle`, `phase`, `call_type`, `agent_identity`, `slot`, `model_requested`, `model_served`, `provider`, `request`, `raw_completion`, `reasoning_text`, `parsed_output`, `parse_status`, `tokens`, `cost`, `latency`, `retry_count`, `finish_reason`, `generation_id`, `error`, and `retrieved_memories`. Parse failures additionally carry the original error; native wrapper defaults are preserved. A call ID includes the attempt-directory name, so restarted attempts do not collide in the shared ledger.

The request captures messages and inference parameters, including the approved provider-routing exception. Authorization headers and API-key values are never stored. `raw_completion` preserves the complete SDK JSON response. `tokens` includes input, output, reasoning and cached counts. Cost is USD and uses the actual response cost or generation metadata; missing actual cost halts paid work. Latency is wall time through the original transport and required metadata lookup, including retries.

Call types distinguish harvest, utterance, the two private instruments, summary, limit extraction, insight/planning/memorization reflection and memory importance. Fresh importance selections retain the original 1000-token cap; generations retain 8000. The original malformed reflection regex remains active and its caught fallback is logged as a parse failure.

Retrieval metadata includes node ID/type, text, creation cycle, source agent where identifiable, importance and the original recency/importance/combined scores. Recording reads the original retriever's outputs and uses its pure scoring functions; it does not alter retrieval or memory. Original always-include score boosts and deduplication behavior remain intact. Retrieved text can legitimately contain older tags or publicly disclosed information.

## Stakes

The full planned schedule is deterministic before the run. Schedule `leave_cycle` is the inclusive planned final tenure cycle, even if the simulation ends earlier. Actual identities observed and their catches appear in cycle and agent records. A successor joins at the start of the next cycle after its predecessor's reflection and final snapshot; no environment rebuild occurs. Original environment cumulative catches remain household totals, while standardized identity earnings stop at handover.

## Nulls and deferred work

Replica instrument fields are null by design. Framework calls have no agent slot. Some memories have no uniquely identifiable source agent. A no-agreement limit, final-month plan, absent reasoning text, zero-error log, silent agent and undefined eigenvector centrality are distinct from an unrecorded required field. Validation must respect those applicability rules.

Paid LLM judging and embeddings are deferred until after the experiment, as the user confirmed. The data checker will compute available measures and validate their stored inputs. Proposal-adoption ties split credit among matching numeric proposals within 0.000001 tons; without a numeric agreement adoption is undefined. Directed graph centrality is used for study outcomes; original AgentElect analysis files remain untouched.

## Budget and raw storage lifecycle

The $90 ledger counts all project API spending, including smoke tests, retries, failed attempts and later judging. Atomic SQLite reservations account for outstanding requests across processes. Reservations left by uncertain/crashed requests remain conservative until explicit reconciliation; they are not silently released. The $100 OpenRouter key limit remains the external backstop.

Completed raw files will be indexed by SHA-256 in the manifest. Storage size and the raw-log hosting decision are made after the pilot under B8. Cross-run Parquet conversion and final manifest generation are still pending; do not treat these initial schemas or focused tests as a completed experiment dataset.
