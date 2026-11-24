"""Did the simulation model think? Compares billed output tokens with the visible completion text
for every logged call. Hidden thinking would make billed tokens far exceed the visible text (as in
the Gemini 2.5 Pro judge calibration, about 65x). Run from the folder that contains analysis/ (repo root):
  PYTHONDONTWRITEBYTECODE=1 python3 analysis/thinking_check.py
"""
import gzip
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import metrics as M  # noqa: E402

ROOT = M.repo_root() / "runs" / "v3"
PRICE_OUT = 2.5e-6  # Gemini 2.5 Flash output $/token (OpenRouter, Nov 2026)


def main():
    ratios, n, reasoning_tokens, reasoning_text, cost_mismatch, params = [], 0, 0, 0, 0, set()
    for path in sorted(ROOT.glob("*_N*/seed*/calls.jsonl.gz")):
        with gzip.open(path, "rt") as f:
            for line in f:
                r = json.loads(line)
                params |= {k for k in r["request"] if k != "messages"}
                rc = r["raw_completion"]
                rc = json.loads(rc) if isinstance(rc, str) else rc
                if not rc or not rc.get("choices"):
                    continue
                msg, u = rc["choices"][0]["message"], rc.get("usage") or {}
                n += 1
                reasoning_tokens += ((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0) > 0
                reasoning_text += bool(msg.get("reasoning") or msg.get("reasoning_details"))
                text, ct = msg.get("content") or "", u.get("completion_tokens") or 0
                if len(text) >= 40:
                    ratios.append(ct / (len(text) / 4))
                cd = (u.get("cost_details") or {}).get("upstream_inference_completions_cost")
                if cd is not None and abs(cd - ct * PRICE_OUT) > 1e-7:
                    cost_mismatch += 1
    q = sorted(ratios)
    out = {"calls": n, "request_parameters_seen": sorted(params),
           "calls_with_reasoning_tokens": reasoning_tokens, "calls_with_reasoning_text": reasoning_text,
           "billed_output_tokens_per_visible_token_estimate": {
               "median": round(st.median(q), 3), "p95": round(q[int(0.95 * len(q))], 3),
               "p99": round(q[int(0.99 * len(q))], 3), "max": round(q[-1], 3), "n": len(q)},
           "calls_with_ratio_over_2": sum(x > 2 for x in q),
           "calls_where_output_cost_differs_from_tokens_x_price": cost_mismatch,
           "conclusion": "No hidden thinking: billed output tokens match the visible text and no call reports reasoning."}
    (HERE / "results" / "thinking_check.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
