"""B2/B8/B12 routing and observation around the unchanged SDK invocation.

Routing and generation metadata follow OpenRouter's official API docs:
https://openrouter.ai/docs/guides/routing/provider-selection
https://openrouter.ai/docs/api/api-reference/generations/get-generation
"""

import datetime
import copy
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime

from simulation.budget import StudyHalt
from simulation.recording import safe, utc_now


def authenticated_get(resource):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise StudyHalt("OPENROUTER_API_KEY is absent from the process environment")
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/" + resource,
        headers={"Authorization": "Bearer " + key},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def retry_delay(value, attempt):
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                return max(0.0, (date - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
            except (ValueError, TypeError):
                pass
    return min(60, 2 ** min(attempt, 6))


def find_reason(value):
    if isinstance(value, dict):
        if value.get("reason"):
            return str(value["reason"])
        for nested in value.values():
            reason = find_reason(nested)
            if reason:
                return reason
    if isinstance(value, list):
        for nested in value:
            reason = find_reason(nested)
            if reason:
                return reason
    if isinstance(value, str) and "in_flight_budget_exhausted" in value:
        return "in_flight_budget_exhausted"
    return ""


def attach_openrouter(model, recorder, budget, pricing, sleep=time.sleep, get=authenticated_get):
    """Preserve wrapper/SDK retries and expose each SDK HTTP error via hooks."""
    original_create = model.client.chat.completions.create
    recorder.budget = budget
    budget.register(recorder.run_id)

    def on_response(response):
        record = recorder.buffers.get(getattr(recorder.local, "current", None))
        if record is None:
            return
        record["http_attempts"] = record.get("http_attempts", 0) + 1
        record["retry_count"] = record["http_attempts"] - 1
        response.read()
        try:
            body = response.json()
        except Exception:
            body = {"message": "Non-JSON error response"}
        try:
            record["request"] = json.loads(response.request.content)
        except (AttributeError, ValueError, TypeError):
            pass
        recorder.write("transport_events", {"timestamp": utc_now(), "event": "http_response", "call_id": record["call_id"],
                                            "http_status": response.status_code, "request": record["request"], "body": safe(body)})
        if response.status_code < 400:
            return
        reason = safe(find_reason(body))
        code = response.status_code
        fatal = code == 403 or (code == 402 and reason != "in_flight_budget_exhausted")
        recorder.write("errors", {
            "timestamp": utc_now(), "call_id": record["call_id"], "type": code,
            "reason": reason or safe(body), "retry_after": response.headers.get("Retry-After"),
            "resolution": "halted" if fatal else "retry_scheduled",
        })
        if fatal:
            budget.halt(f"OpenRouter HTTP {code}: {reason or 'key, credit, or budget failure'}")

    model.client._client.event_hooks.setdefault("response", []).append(on_response)

    def create(**kwargs):
        call_id = recorder.local.current
        record = recorder.buffers[call_id]
        routing = {"only": [recorder.provider], "allow_fallbacks": False}
        kwargs["extra_body"] = {**kwargs.get("extra_body", {}), "provider": routing}
        record["request"]["provider"] = routing
        # A conservative byte-based upper bound, plus role framing, is used
        # only for reservations; final spend always uses reported actual cost.
        input_bound = len(json.dumps(kwargs["messages"], ensure_ascii=False).encode()) + 512 * len(kwargs["messages"])
        reservation = input_bound * float(pricing["prompt"]) + kwargs["max_tokens"] * float(pricing["completion"])
        budget.wait_for_turn(recorder.run_id)
        budget.reserve(call_id, reservation)
        reservation_id = call_id
        completed_cost = 0.0
        attempt = 0
        transient_budget_errors = 0
        while True:
            budget.check()
            try:
                response = original_create(**kwargs)
                raw = response.model_dump(mode="json")
                raw["_sdk_original"] = copy.deepcopy(raw)
                recorder.pending_sdk_response.value = raw
                choice = (raw.get("choices") or [{}])[0]
                if choice.get("finish_reason") == "error":
                    error = raw.get("error", choice.get("error", {}))
                    code = error.get("code") if isinstance(error, dict) else None
                    if str(code) == "429":
                        partial_cost = (raw.get("usage") or {}).get("cost")
                        if partial_cost is None and raw.get("id"):
                            partial_cost = get("generation?" + urllib.parse.urlencode({"id": raw["id"]}))["data"]["total_cost"]
                        partial_cost = partial_cost or 0.0
                        budget.settle(reservation_id, partial_cost)
                        completed_cost += partial_cost
                        record["transport_cost"] = completed_cost
                        record.setdefault("attempt_completions", []).append(raw)
                        recorder.write("errors", {"timestamp": utc_now(), "call_id": call_id,
                                                   "type": 429, "reason": safe(error), "retry_after": None,
                                                   "resolution": "retry_scheduled"})
                        attempt += 1
                        record["retry_count"] += 1
                        sleep(retry_delay(None, attempt))
                        reservation_id = f"{call_id}/attempt{attempt}"
                        budget.reserve(reservation_id, reservation)
                        continue
                    budget.halt("OpenRouter returned an error completion")
                usage = raw.get("usage") or {}
                if usage.get("cost") is not None:
                    budget.settle(reservation_id, usage["cost"])
                    record["transport_cost"] = completed_cost + usage["cost"]
                if usage.get("cost") is None or not raw.get("provider") or usage.get("prompt_tokens_details") is None or usage.get("completion_tokens_details") is None:
                    generation = None
                    for metadata_attempt in range(6):
                        try:
                            generation = get("generation?" + urllib.parse.urlencode({"id": raw.get("id", "")}))["data"]
                            break
                        except urllib.error.HTTPError as error:
                            if error.code not in (404, 429, 500, 502, 503):
                                raise
                            sleep(retry_delay(error.headers.get("Retry-After"), metadata_attempt))
                    if generation is None:
                        budget.halt("Generation metadata unavailable; actual spend cannot be reconciled")
                        raise StudyHalt("Generation metadata unavailable")
                    usage["cost"] = generation.get("total_cost")
                    raw["provider"] = generation.get("provider_name")
                    raw["generation_metadata"] = generation
                    if usage.get("prompt_tokens") is None:
                        usage["prompt_tokens"] = generation.get("tokens_prompt", generation.get("native_tokens_prompt"))
                    if usage.get("completion_tokens") is None:
                        usage["completion_tokens"] = generation.get("tokens_completion", generation.get("native_tokens_completion"))
                    if usage.get("prompt_tokens_details") is None:
                        usage["prompt_tokens_details"] = {"cached_tokens": generation.get("native_tokens_cached")}
                    if usage.get("completion_tokens_details") is None:
                        usage["completion_tokens_details"] = {"reasoning_tokens": generation.get("native_tokens_reasoning")}
                    raw["usage"] = usage
                budget.settle(reservation_id, usage.get("cost"))
                record["transport_cost"] = completed_cost + usage["cost"]
                if raw.get("provider") not in ("Google AI Studio", recorder.provider):
                    budget.halt("Served provider did not match the pinned provider")
                if raw.get("model") != kwargs["model"]:
                    budget.halt("Served model did not match the requested model")
                if choice.get("finish_reason") == "length":
                    budget.halt("Completion reached the length limit; review required under B11/B14")
                return response
            except StudyHalt:
                raise
            except Exception as error:
                status = getattr(error, "status_code", None)
                reason = safe(find_reason(getattr(error, "body", None)))
                if status == 403 or (status == 402 and reason != "in_flight_budget_exhausted"):
                    budget.release_unbilled(reservation_id)
                    budget.halt(f"OpenRouter HTTP {status}: {reason or 'credit, key, or budget failure'}")
                    raise StudyHalt(safe(str(error))) from None
                if status == 402 and reason == "in_flight_budget_exhausted":
                    transient_budget_errors += 1
                    if transient_budget_errors >= 3:
                        budget.capacity_limit(reduce=True)
                        budget.wait_for_turn(recorder.run_id)
                elif status not in (429, 500, 502, 503, 504) and not (
                    status == 404 and "no endpoints" in str(getattr(error, "body", "")).lower()
                ):
                    # Preserve the reservation when a transport failure leaves
                    # billing uncertain; subsequent calls must not spend it.
                    budget.halt("Unreconciled API or transport failure")
                    raise StudyHalt(safe(str(error))) from None
                attempt += 1
                headers = getattr(getattr(error, "response", None), "headers", {})
                sleep(retry_delay(headers.get("Retry-After"), attempt))

    model.client.chat.completions.create = create
