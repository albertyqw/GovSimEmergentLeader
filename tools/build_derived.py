"""B8/B13 build cross-run Parquet in a separate analysis environment.

Run after the experiment with .venv/analysis/bin/python. This utility alone
requires PyArrow; it is never imported into the simulation environment.
"""

import argparse
import gzip
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


TABLES = ("cycles", "utterances", "agents", "calls_index", "memory_retrievals", "elicitations", "perceived_leadership")


def rows(path):
    with gzip.open(path, "rt") as source:
        return [json.loads(line) for line in source]


def normalize(record):
    # JSON columns preserve varying identity maps and heterogeneous nested
    # values without silently coercing a numeric limit into a string column.
    result = {}
    for key, value in record.items():
        if isinstance(value, (dict, list)):
            result[key + "_json"] = json.dumps(value, ensure_ascii=False)
        else:
            result[key] = value
    return result


def build(root, output, include_testing=False):
    root, output = Path(root), Path(output)
    selected = {}
    for file in sorted(root.rglob("run_meta.json")):
        meta = json.loads(file.read_text())
        if meta["status"] not in ("completed", "collapsed") or (not include_testing and meta.get("run_kind") != "full"):
            continue
        check = file.parent.parent.parent / "checks" / meta["condition"] / f"{file.parent.name}.json"
        if not check.exists() or not json.loads(check.read_text()).get("valid"):
            continue
        key = (meta["condition"], meta["seed"])
        order = int(file.parent.name.split("_attempt")[-1]) if "_attempt" in file.parent.name else 1
        if key not in selected or order > selected[key][0]:
            selected[key] = (order, file, meta)
    tables = {name: [] for name in TABLES}
    commits = {}
    for _, file, meta in selected.values():
        commits.setdefault(meta["condition"], set()).add(meta["commit_hash"])
        if len(commits[meta["condition"]]) > 1:
            raise ValueError("B10 forbids mixed source commits within a condition")
        base = {"condition": meta["condition"], "N": meta["N"], "seed": meta["seed"],
                "commit_hash": meta["commit_hash"], "attempt": file.parent.name}
        for name in ("cycles", "utterances", "agents"):
            for record in rows(file.parent / f"{name}.jsonl.gz"):
                tables[name].append({**base, **normalize(record)})
                if name == "cycles":
                    for identity, result in (record.get("elicitation") or {}).items():
                        values = {**result, "preferred_limit_none": result.get("preferred_limit") == "none"}
                        if values["preferred_limit_none"]:
                            values["preferred_limit"] = None
                        tables["elicitations"].append({**base, "cycle": record["cycle"], "identity": identity, **normalize(values)})
                    for identity, result in (record.get("perceived_leadership") or {}).items():
                        tables["perceived_leadership"].append({**base, "cycle": record["cycle"], "identity": identity, **normalize(result)})
        for call in rows(file.parent / "calls.jsonl.gz"):
            index = {key: value for key, value in call.items() if key not in (
                "request", "raw_completion", "reasoning_text", "parsed_output", "parse_operations", "retrieved_memories", "parse_error", "attempt_completions"
            )}
            if index["slot"] == "framework":
                index["slot"] = None
            tables["calls_index"].append({**base, **normalize(index)})
            for position, memory in enumerate(call["retrieved_memories"]):
                tables["memory_retrievals"].append({**base, "call_id": call["call_id"], "cycle": call["cycle"],
                                                  "agent_identity": call["agent_identity"], "position": position, **memory})
    output.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, records in tables.items():
        keys = sorted({key for record in records for key in record})
        complete = [{key: record.get(key) for key in keys} for record in records]
        table = pa.Table.from_pylist(complete) if records else pa.table({"condition": pa.array([], type=pa.string())})
        pq.write_table(table, output / f"{name}.parquet", compression="zstd")
        counts[name] = table.num_rows
    (output / "build_meta.json").write_text(json.dumps({"pyarrow": pa.__version__, "counts": counts,
                                                       "selected_runs": len(selected)}, indent=2) + "\n")
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--output", default="derived")
    parser.add_argument("--include-testing", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.output, args.include_testing), indent=2))


if __name__ == "__main__":
    main()
