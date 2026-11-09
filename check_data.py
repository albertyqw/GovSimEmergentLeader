"""B11 data validation and A10 feasibility checks on immutable raw runs."""

import argparse
import gzip
import json
from pathlib import Path

import numpy as np

from study_analysis import cycle_measures, gini


CALL_FIELDS = {
    "call_id", "timestamp", "cycle", "phase", "call_type", "agent_identity", "slot",
    "model_requested", "model_served", "provider", "request", "raw_completion", "reasoning_text",
    "parsed_output", "parse_status", "tokens", "cost", "latency", "retry_count", "finish_reason",
    "generation_id", "error", "retrieved_memories",
}
CYCLE_FIELDS = {
    "cycle", "stock_before_harvest", "stock_after_harvest", "stock_after_regeneration", "regen_factor",
    "sustainability_threshold", "catches", "elicitation", "perceived_leadership", "report_text",
    "conversation_summary", "agreed_limit", "opener", "number_of_utterances", "end_reason", "collapse",
    "leavers", "joiners", "household_earnings",
}


def jsonl(path):
    with gzip.open(path, "rt") as source:
        return [json.loads(line) for line in source]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_run(path, null_samples=1000):
    path = Path(path)
    metadata = json.loads((path / "run_meta.json").read_text())
    require(metadata["status"] in ("completed", "collapsed"), "Run did not complete")
    require(metadata.get("end_commit_hash", metadata["commit_hash"]) == metadata["commit_hash"], "Source commit changed during the run; review under B10")
    calls = jsonl(path / "calls.jsonl.gz")
    cycles = jsonl(path / "cycles.jsonl.gz")
    turns = jsonl(path / "utterances.jsonl.gz")
    agents = jsonl(path / "agents.jsonl.gz")
    errors = jsonl(path / "errors.jsonl.gz")
    require(calls and cycles and agents, "Required raw records are empty")
    ids = {row["call_id"] for row in calls}
    require(len(ids) == len(calls), "Call IDs are not unique")
    n = metadata["N"]
    replica = metadata["condition"] == "replica_N8"
    capacity = metadata["resolved_config"]["experiment"]["env"]["initial_resource_in_pool"]
    paper = metadata["resolved_config"]["experiment"]["env"].get("paper_definitions", False)
    outcomes = []
    totals = dict.fromkeys(range(n), 0)
    overusage = []
    final_month_catches = []
    for call in calls:
        require(CALL_FIELDS <= call.keys(), f"Missing call fields in {call['call_id']}")
        require(call["raw_completion"] is not None and call["request"].get("messages"), "Raw request/completion is missing")
        require(call["model_served"] and call["provider"] and call["generation_id"], "Serving metadata is missing")
        require(call["cost"] is not None and call["tokens"]["input"] is not None and call["tokens"]["output"] is not None,
                "Cost or token accounting is missing")
        require(call["parse_status"] != "pending", "A parse result was not finalized")
        if paper:
            fresh_rating = call["request"]["messages"][-1]["content"].startswith("Rating (1 to 10):")
            require(call["request"]["max_tokens"] == (1000 if fresh_rating else 16000), "Study token cap mismatch")
            if call["call_type"] in ("harvest", "utterance", "elicitation", "perceived_leadership", "reflection_insight"):
                require(call.get("retrieval_top_k") == 10, "Paper-aligned recall did not request ten entries")
        for memory in call["retrieved_memories"]:
            require(all(key in memory for key in ("id", "text", "type", "creation_cycle", "source_agent", "importance",
                                                  "recency_score", "importance_score", "combined_score")), "Retrieval metadata incomplete")
            require(memory["id"] is not None and memory["type"], "Retrieved memory cannot be linked to its node")
    for index, cycle in enumerate(cycles):
        require(CYCLE_FIELDS <= cycle.keys(), "Cycle fields missing")
        require(cycle["cycle"] == index + 1, "Cycles are not consecutive")
        require(len(cycle["catches"]) == n, "Population size changed")
        require(cycle["stock_after_regeneration"] == int(min(capacity, cycle["stock_after_harvest"] * cycle["regen_factor"])),
                "Regeneration does not match original integer behavior")
        require(cycle["stock_before_harvest"] - sum(row["actual"] for row in cycle["catches"]) == cycle["stock_after_harvest"],
                "Catch and stock accounting disagree")
        require(cycle["report_text"] and cycle["conversation_summary"], "Report or summary missing")
        if paper:
            from simulation.paper_definitions import sustainability_threshold
            expected = sustainability_threshold(cycle["stock_before_harvest"], capacity, n, cycle["regen_factor"])
            require(abs(cycle["sustainability_threshold"] - expected) < 1e-9, "Paper sustainability threshold mismatch")
            for catch in cycle["catches"]:
                require(f"{catch['tag']} caught {catch['actual']} tons of fish" in cycle["report_text"],
                        "Paper-aligned public report does not show actual allocated catch")
        if index == 0:
            require(cycle["regen_factor"] == 2.0, "First regeneration factor changed")
        else:
            require(cycle["stock_before_harvest"] == cycles[index - 1]["stock_after_regeneration"], "Stock discontinuity")
        if replica:
            require(cycle["elicitation"] is None and cycle["perceived_leadership"] is None, "Replica gained private instruments")
        else:
            require(len(cycle["elicitation"] or {}) == n and len(cycle["perceived_leadership"] or {}) == n,
                    "Private instruments do not cover all present agents")
        cycle_turns = [turn for turn in turns if turn["cycle"] == cycle["cycle"]]
        require(len(cycle_turns) == cycle["number_of_utterances"], "Utterance count mismatch")
        for position, turn in enumerate(cycle_turns):
            require(turn["position"] == position and turn["call_id"] in ids, "Turn ordering or call link is invalid")
            require("nominee_options" in turn and "nominee_options_rendered" in turn, "Offered nominee options were not captured")
        for catch in cycle["catches"]:
            require(catch["actual"] >= 0 and catch["actual"] <= max(catch["requested"], 0), "Invalid actual catch")
            totals[catch["slot"]] += catch["actual"]
            overusage.append(catch["requested"] > cycle["sustainability_threshold"])
            snapshot = path / "memory" / f"cycle{cycle['cycle']}" / f"{catch['identity']}.json"
            require(snapshot.exists(), "Full memory snapshot missing")
            memory = json.loads(snapshot.read_text())
            require("nodes" in memory and "memory_markdown" in memory, "Incomplete memory snapshot")
            if catch["months_remaining"] == 1:
                final_month_catches.append(catch["actual"])
        outcomes.append(cycle_measures(metadata, cycle, cycle_turns, samples=null_samples))
    require(sum(row["total_earnings"] for row in agents) == sum(totals.values()) * 1000, "Identity earnings do not sum to actual catches")
    benchmark = sum(capacity * (cycle["regen_factor"] - 1) / cycle["regen_factor"] for cycle in cycles)
    convergence = []
    for current, following in zip(cycles, cycles[1:]):
        pre = current.get("elicitation") or {}
        paired = [(pre[row["identity"]].get("plan"), row["actual"]) for row in following["catches"] if row["identity"] in pre]
        paired = [(plan, actual) for plan, actual in paired if isinstance(plan, (int, float))]
        convergence.append({"cycle": current["cycle"], "paired_agents": len(paired),
                            "next_catch_dispersion": float(np.std([actual for _, actual in paired])) if paired else None,
                            "plan_to_catch_mean_absolute_difference": float(np.mean([abs(plan - actual) for plan, actual in paired])) if paired else None})
    harvests = {}
    for call in calls:
        if call["call_type"] == "harvest":
            harvests.setdefault((call["cycle"], call["agent_identity"]), []).extend(call.get("parse_operations", []))
    failed_harvests = sum(any(op["name"] == "option" and op["status"] == "failed" for op in operations)
                          for operations in harvests.values())
    nominees = [op for call in calls if call["call_type"] == "utterance"
                for op in call.get("parse_operations", []) if op["name"] == "next_speaker"]
    parse_rates = {"harvest_failure_rate": failed_harvests / len(harvests) if harvests else None,
                   "nominee_failure_rate": sum(op["status"] == "failed" for op in nominees) / len(nominees) if nominees else None}
    for kind in ("elicitation", "perceived_leadership"):
        subset = [call for call in calls if call["call_type"] == kind]
        parse_rates[kind + "_success_rate"] = sum(call["parse_status"] == "ok" for call in subset) / len(subset) if subset else None
    if metadata.get("run_kind") == "full" and metadata["condition"] == "baseline_N8" and metadata["seed"] == 0:
        require(all((parse_rates[kind + "_success_rate"] or 0) >= 0.97
                    for kind in ("elicitation", "perceived_leadership")),
                "Baseline seed 0 failed B11's 97% instrument parsing gate")
    return {
        "valid": True, "condition": metadata["condition"], "seed": metadata["seed"], "commit_hash": metadata["commit_hash"],
        "survival_time": len(cycles), "survived": not any(cycle["collapse"] for cycle in cycles),
        "final_stock": cycles[-1]["stock_after_regeneration"], "total_catch": sum(totals.values()),
        "equality": 1 - gini(totals.values()), "efficiency": sum(totals.values()) / benchmark if benchmark else None,
        "overusage": sum(overusage) / len(overusage), "mean_regen_factor": float(np.mean([cycle["regen_factor"] for cycle in cycles])),
        "cost": sum(call["cost"] for call in calls), "tokens": {key: sum((call["tokens"][key] or 0) for call in calls)
                                                                 for key in ("input", "output", "reasoning", "cached")},
        "token_field_coverage": {key: sum(call["tokens"][key] is not None for call in calls) / len(calls)
                                 for key in ("input", "output", "reasoning", "cached")},
        "429_count": sum(error["type"] == 429 for error in errors), "402_count": sum(error["type"] == 402 for error in errors),
        "cycles": outcomes, "convergence": convergence, "final_month_catch_mean": float(np.mean(final_month_catches)) if final_month_catches else None,
        "parse_rates": parse_rates,
        "truncation_count": sum(call["finish_reason"] == "length" for call in calls),
        "parse_failure_operations": sum(op["status"] == "failed" for call in calls for op in call.get("parse_operations", [])),
        "fallback_operations": sum(bool(op.get("fallback_applied")) for call in calls for op in call.get("parse_operations", [])),
        "post_experiment_inputs": {
            "discussion_proposal_extraction": {"utterances": len(turns), "status": "stored_text_available"},
            "reasoning_judge": {"calls": len(calls), "status": "raw_completions_available"},
            "memory_attribution_embeddings": {"retrievals": sum(len(call["retrieved_memories"]) for call in calls), "status": "stored_text_available"},
            "handoff_judge": {"final_month_utterances": sum(
                turn["speaker_identity"] == catch["identity"] for cycle in cycles for catch in cycle["catches"]
                if catch["months_remaining"] == 1 for turn in turns if turn["cycle"] == cycle["cycle"]), "status": "stored_text_available"},
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory")
    parser.add_argument("--null-samples", type=int, default=1000)
    parser.add_argument("--output")
    args = parser.parse_args()
    require(args.null_samples > 0, "Null sample count must be positive")
    result = check_run(args.run_directory, args.null_samples)
    text = json.dumps(result, indent=2)
    if args.output:
        output = Path(args.output)
        require(not output.resolve().is_relative_to(Path(args.run_directory).resolve()), "Derived checks must stay outside immutable raw runs")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
