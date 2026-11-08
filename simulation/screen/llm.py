"""Direct Anthropic calls for screen-specific prompts (utterances, probes, interviews,
calculator margin, scratchpad writes). Same model and thinking settings as the
pathfinder backend; usage is appended to the same per-run JSONL file."""

import json
import os

import anthropic

_client = None


def _get_client():
  global _client
  if _client is None:
    _client = anthropic.AsyncAnthropic(max_retries=8)
  return _client


def _thinking(model):
  mode = os.environ.get("PATHFINDER_THINKING")
  if mode is None:
    mode = "between_tools" if "sonnet-5-5" in model else "disabled"
  return None if mode == "default" else {"type": mode}


async def ask(model: str, prompt: str, max_tokens: int = 1000, tag: str = "") -> str:
  kwargs = dict(model=model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}])
  th = _thinking(model)
  if th:
    kwargs["thinking"] = th
  out = await _get_client().messages.create(**kwargs)
  usage_file = os.environ.get("PATHFINDER_USAGE_FILE")
  if usage_file:
    with open(usage_file, "a") as f:
      f.write(json.dumps({
          "model": model, "input_tokens": out.usage.input_tokens,
          "output_tokens": out.usage.output_tokens,
          "cache_read_input_tokens": out.usage.cache_read_input_tokens or 0,
          "cache_creation_input_tokens": out.usage.cache_creation_input_tokens or 0,
          "stop_reason": out.stop_reason, "tag": tag,
      }) + "\n")
  if out.stop_reason == "refusal":
    return ""
  return "".join(b.text for b in out.content if b.type == "text")
