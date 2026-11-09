"""B8 observational raw data capture around original simulation components."""

import copy
import datetime
import gzip
import hashlib
import json
import os
import platform
import re
import subprocess
import threading
import time
import types
from pathlib import Path

from omegaconf import OmegaConf

from simulation.intervention_randomness import NAME_POOL
from simulation.persona.cognition.utils import render_name
from simulation.utils.models import ModelWandbWrapper


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def memory_markdown_text(description):
    """Observe the original writer/reader's blank-line normalization."""
    written = description.strip().replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line for line in written.split("\n") if line).strip()


def safe(value):
    """Ensure an environment key cannot enter errors, requests or metadata."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if isinstance(value, str):
        return value.replace(key, "[REDACTED]") if key else value
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if v else v) if str(k).lower() in ("authorization", "api_key") else safe(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    return value


class RunRecorder:
    def __init__(self, path, condition, seed, resolved_config, provider="stub"):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=False)
        self.condition = condition
        path_id = hashlib.sha256(str(self.path.resolve()).encode()).hexdigest()[:16]
        self.run_id = f"{condition}-seed{seed}-{path_id}"
        self.seed = seed
        self.config = resolved_config
        self.provider = provider
        self.lock = threading.RLock()
        self.local = threading.local()
        self.buffers = {}
        self.retrievals = {}
        self.counter = 0
        self.cycle = 0
        self.phase = "initialization"
        self.agents = {}
        self.started = utc_now()
        root = Path(__file__).resolve().parents[1]
        self.commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        self.finalized = False
        self.ctx = None
        self.pending_sdk_response = threading.local()
        self.call_ids_by_agent = {}
        for file in ("calls", "cycles", "utterances", "agents", "errors", "transport_events"):
            with gzip.open(self.path / f"{file}.jsonl.gz", "wt", encoding="utf-8"):
                pass

    def write(self, file, record):
        with self.lock, gzip.open(self.path / f"{file}.jsonl.gz", "at", encoding="utf-8") as output:
            output.write(json.dumps(safe(record), ensure_ascii=False) + "\n")

    def bind(self, ctx):
        self.ctx = ctx
        for persona in ctx.personas.values():
            self.observe_persona(persona)

    def observe_persona(self, persona):
        if getattr(persona.retrieve, "_recording_attached", False):
            return
        original = persona.retrieve.retrieve

        def observed(focal_points, top_k):
            result = original(focal_points, top_k)
            entries = persona.memory.read_memory_md(persona.current_time)
            recency = persona.retrieve._recency_retrieval(entries)
            importance = persona.retrieve._importance_retrieval(entries)
            combined = [r * persona.retrieve.weights["recency"] + i * persona.retrieve.weights["importance"]
                        for r, i in zip(recency, importance)]
            maximum = max(combined, default=10)
            for i, entry in enumerate(entries):
                if entry[3]:
                    combined[i] = maximum + 1
            metadata = []
            for created, text in result:
                candidates = [i for i, entry in enumerate(entries) if entry[0] == created and entry[1] == text]
                index = max(candidates, key=lambda i: combined[i])
                nodes = [node for node in persona.memory.id_to_node.values()
                         if node.created.replace(microsecond=0) == created
                         and memory_markdown_text(node.description) == text.strip()
                         and node.importance_score == entries[index][2]
                         and bool(node.always_include) == entries[index][3]
                         and (node.always_include or node.expiration.replace(microsecond=0) > persona.current_time)]
                # Markdown omits node IDs. Equal entries retain append order;
                # the retriever's stable scoring picks the corresponding one.
                occurrence = sum(entry == entries[index] for entry in entries[:index])
                node = nodes[occurrence] if occurrence < len(nodes) else None
                metadata.append({
                    "id": node.id if node else None, "text": text,
                    "type": node.type.name if node else None,
                    "creation_cycle": (created.year - 2024) * 12 + created.month,
                    "source_agent": persona.identity.name if node and node.type.name == "THOUGHT" else None,
                    "importance": entries[index][2], "recency_score": recency[index],
                    "importance_score": importance[index], "combined_score": combined[index],
                })
            self.retrievals[persona.identity.name] = metadata
            return result

        persona.retrieve.retrieve = observed
        persona.retrieve._recording_attached = True

    def begin_chain(self, agent, phase, query):
        types_by_query = {
            "choose_act_options": "harvest", "converse_utterance": "utterance",
            "prompt_summarize_conversation_in_one_sentence": "conversation_summary",
            "prompt_find_harvesting_limit_from_conversation": "limit_extraction",
            "elicitation": "elicitation", "perceived_leadership": "perceived_leadership",
            "prompt_insight_and_evidence": "reflection_insight",
            "prompt_planning_thought_on_conversation": "reflection_plan",
            "prompt_memorize_from_conversation": "reflection_memorize",
        }
        kind = types_by_query.get(query, "memory_importance" if "importance" in query or query == "relevancy_event" else "other")
        retrieved = self.retrievals.get(agent, []) if kind in (
            "harvest", "utterance", "elicitation", "perceived_leadership", "reflection_insight"
        ) else []
        self.local.context = {"agent_identity": agent, "call_type": kind,
                              "retrieved_memories": copy.deepcopy(retrieved), "query": query}
        self.local.pending = []
        self.local.current = None

    def begin_call(self, model, messages, temperature, top_p, max_tokens):
        with self.lock:
            self.counter += 1
            call_id = f"{self.run_id}-call{self.counter:06d}"
            context = copy.deepcopy(getattr(self.local, "context", {}))
            identity = context.get("agent_identity", "framework")
            slot = self.ctx.agent_name_to_id.get(identity) if self.ctx else None
            record = {
                "call_id": call_id, "timestamp": utc_now(), "cycle": self.cycle,
                "phase": self.phase, "call_type": context.get("call_type", "other"),
                "agent_identity": identity, "slot": int(slot.split("_")[-1]) if slot and slot != "framework" else "framework",
                "model_requested": model.model_name, "model_served": None, "provider": self.provider,
                "request": {"model": model.model_name, "messages": copy.deepcopy(messages),
                            "temperature": temperature, "top_p": top_p, "max_tokens": max_tokens, "seed": model.seed},
                "raw_completion": None, "reasoning_text": None, "parsed_output": {}, "parse_status": "pending",
                "tokens": {"input": None, "output": None, "reasoning": None, "cached": None},
                "cost": None, "latency": None, "retry_count": 0, "finish_reason": None,
                "generation_id": None, "error": None, "retrieved_memories": context.get("retrieved_memories", []),
            }
            self.buffers[call_id] = record
            self.local.pending.append(call_id)
            self.local.current = call_id
            self.call_ids_by_agent.setdefault(identity, []).append(call_id)
            return call_id

    def end_chain(self):
        with self.lock:
            pending = list(getattr(self.local, "pending", []))
            context = getattr(self.local, "context", {})
            if context.get("call_type") == "utterance" and pending:
                identity = context["agent_identity"]
                if not hasattr(self, "utterance_calls"):
                    self.utterance_calls = {}
                self.utterance_calls.setdefault((self.cycle, identity), []).append(pending[0])
                texts = []
                for call_id in pending:
                    raw = self.buffers[call_id].get("raw_completion") or {}
                    choice = (raw.get("choices") or [{}])[0]
                    texts.append((choice.get("message") or {}).get("content") or "")
                nominees = re.findall(r"Next speaker:\s*([^\n]+)", "\n".join(texts), re.I)
                if not hasattr(self, "last_utterance"):
                    self.last_utterance = {}
                self.last_utterance[identity] = {"call_id": pending[0], "call_ids": pending,
                                                "nominee_raw": nominees[-1].strip() if nominees else None}
            for call_id in pending:
                record = self.buffers.pop(call_id, None)
                if record:
                    if record["parse_status"] == "pending":
                        record["parse_status"] = "ok"
                    self.write("calls", record)
            self.local.pending = []
            self.local.current = None

    def parse_result(self, name, value=None, error=None):
        record = self.buffers.get(getattr(self.local, "current", None))
        if record is not None:
            if error:
                record["parse_status"] = "failed"
                record["parse_error"] = safe(str(error))
                record.setdefault("parse_operations", []).append({"name": name, "status": "failed", "error": safe(str(error))})
            else:
                record["parsed_output"][name] = value
                record.setdefault("parse_operations", []).append({"name": name, "status": "ok", "value": value})

    def cycle_start(self, ctx):
        self.cycle = ctx.round_num + 1
        self.before = copy.deepcopy(ctx.env.internal_global_state)
        for persona in ctx.personas.values():
            self.observe_persona(persona)

    def cycle_end(self, ctx):
        state = ctx.env.internal_global_state
        post = ctx.round_stats[ctx.round_num]["num_resources"]
        conversation = getattr(ctx.personas[ctx.env.agents[0]].converse, "last_conversation", {})
        measurements = conversation.get("measurements", {})
        catches = []
        for agent_id, persona in ctx.personas.items():
            name = persona.identity.name
            slot = int(agent_id.split("_")[-1])
            actual = state["last_collected_resource"][agent_id]
            tenure = getattr(persona.identity, "tenure_record", {})
            record = self.agents.setdefault(name, {
                "identity": name, "slot": slot, "household": slot if tenure else None,
                "join_cycle": tenure.get("join_cycle", 1), "leave_cycle": tenure.get("leave_cycle"),
                "horizon": tenure.get("horizon"), "focal_values": getattr(persona, "focal_values", False),
                "svo_angle": persona.svo_angle, "catch_per_cycle": {}, "total_earnings": 0,
            })
            record["catch_per_cycle"][str(self.cycle)] = actual
            record["total_earnings"] += actual * 1000
            catches.append({"identity": name, "slot": slot, "requested": state["wanted_resource"][agent_id],
                            "actual": actual, "tag": render_name(persona.identity),
                            "months_remaining": getattr(persona.identity, "stakes_months_remaining", None),
                            "months_fished": self.cycle - tenure.get("join_cycle", 1) + 1 if tenure else None})
            folder = self.path / "memory" / f"cycle{self.cycle}"
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / f"{name}.json").open("x") as output:
                json.dump({"identity": name, "slot": slot, "cycle": self.cycle,
                           "nodes": [node.toJSON() for node in persona.memory.id_to_node.values()],
                           "memory_markdown": Path(persona.memory._memory_md_path).read_text()}, output)
        turns = conversation.get("turns", [])
        for position, turn in enumerate(turns):
            mentioned = re.findall(r"\b(?:" + "|".join(NAME_POOL) + r")\b", turn["text"], re.I)
            canonical = {name.casefold(): name for name in NAME_POOL}
            ids = self.call_ids_by_agent.get(turn["speaker_identity"], [])
            self.write("utterances", {"cycle": self.cycle, "position": position, **turn,
                                      "mentioned_identities": [canonical[name.casefold()] for name in mentioned],
                                      "call_id": self._utterance_call_id(turn["speaker_identity"], position)})
        threshold = getattr(ctx.cfg.env, "collapse_threshold", 5)
        self.collapsed = post < threshold
        self.write("cycles", {
            "cycle": self.cycle, "stock_before_harvest": self.before["resource_in_pool"],
            "stock_after_harvest": post, "stock_after_regeneration": state["resource_in_pool"],
            "regen_factor": self.before["regen_factor"], "sustainability_threshold": self.before["sustainability_threshold"],
            "catches": catches, "elicitation": measurements.get("elicitation") or None,
            "perceived_leadership": measurements.get("perceived_leadership") or None,
            "report_text": ctx.harvest_report, "conversation_summary": conversation.get("summary"),
            "agreed_limit": conversation.get("agreed_limit"), "opener": turns[0]["speaker_identity"] if turns else None,
            "number_of_utterances": len(turns), "framework_messages": conversation.get("framework_messages"),
            "end_reason": conversation.get("end_reason"), "collapse": self.collapsed,
            "leavers": [p.identity.name for p in ctx.personas.values() if getattr(p.identity, "stakes_months_remaining", None) == 1],
            "joiners": [row["identity"] for row in catches if self.agents[row["identity"]]["join_cycle"] == self.cycle],
            "household_earnings": {key: amount * 1000 for key, amount in state["collected_resource"].items()} if hasattr(ctx, "tenure") else None,
        })

    def _utterance_call_id(self, identity, position):
        candidates = getattr(self, "utterance_calls", {}).get((self.cycle, identity), [])
        used = getattr(self, "utterance_offsets", {})
        key = (self.cycle, identity)
        offset = used.get(key, 0)
        used[key] = offset + 1
        self.utterance_offsets = used
        return candidates[offset] if offset < len(candidates) else None

    def finalize(self, status=None, error=None):
        if self.finalized:
            return
        for record in list(self.buffers.values()):
            if record["parse_status"] == "pending":
                record["parse_status"] = "failed" if record["error"] else "ok"
            self.write("calls", record)
        self.buffers.clear()
        for record in self.agents.values():
            self.write("agents", record)
        cfg = OmegaConf.to_container(self.config, resolve=True)
        root = Path(__file__).resolve().parents[1]
        metadata = {
            "condition": self.condition, "N": self.config.experiment.env.num_agents, "seed": self.seed,
            "run_id": self.run_id,
            "commit_hash": self.commit_hash,
            "end_commit_hash": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "resolved_config": cfg, "model": self.config.llm.path.removeprefix("openrouter-"),
            "provider_routing": {"only": [self.provider], "allow_fallbacks": False},
            "temperature": self.config.llm.temperature, "top_p": self.config.llm.top_p,
            "max_tokens": {"generation": 8000, "fresh_importance": 1000}, "thinking": "default; no budget or effort set",
            "pip_freeze": subprocess.check_output([os.sys.executable, "-m", "pip", "freeze", "--disable-pip-version-check"], text=True).splitlines(),
            "python": platform.python_version(), "os": platform.platform(), "start_time": self.started, "end_time": utc_now(),
            "status": status or ("collapsed" if getattr(self, "collapsed", False) else "completed"),
            "collapse_cycle": self.cycle if getattr(self, "collapsed", False) else None, "error": error,
            "values_focal": next((row for row in self.agents.values() if row["focal_values"]), None),
            "stakes_schedule": self.ctx.tenure.schedule if self.ctx and hasattr(self.ctx, "tenure") else None,
            "run_kind": getattr(self, "kind", "stub" if self.provider == "stub" else "full"),
            "first_stakes_run": getattr(self, "first_stakes_run", False),
        }
        with (self.path / "run_meta.json").open("x") as output:
            json.dump(safe(metadata), output, indent=2)
        self.finalized = True


class RecordingWrapper(ModelWandbWrapper):
    def __init__(self, base_lm, recorder, **kwargs):
        super().__init__(base_lm, **kwargs)
        self.recorder = recorder
        original_request = base_lm.request_api

        def request_api(model, chat, temperature, top_p, max_tokens):
            call_id = recorder.begin_call(model, chat, temperature, top_p, max_tokens)
            record = recorder.buffers[call_id]
            started = time.monotonic()
            recorder.write("transport_events", {"timestamp": utc_now(), "event": "request", "call_id": call_id,
                                                "request": record["request"]})
            try:
                text = original_request(chat, temperature, top_p, max_tokens)
                raw = getattr(recorder.pending_sdk_response, "value", None)
                if raw is None and recorder.provider == "stub":
                    raw = {"id": call_id, "model": model.model_name, "provider": "stub",
                           "choices": [{"finish_reason": "stop", "message": {"content": text}}],
                           "usage": {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0}}
                if raw is None:
                    raise RuntimeError("Raw SDK completion capture is required for paid calls")
                recorder.pending_sdk_response.value = None
                record["raw_completion"] = raw
                record["model_served"] = raw.get("model")
                record["provider"] = raw.get("provider", recorder.provider)
                usage = raw.get("usage") or {}
                record["tokens"] = {"input": usage.get("prompt_tokens"), "output": usage.get("completion_tokens"),
                                    "reasoning": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0 if recorder.provider == "stub" else None),
                                    "cached": (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0 if recorder.provider == "stub" else None)}
                record["cost"] = record.get("transport_cost", usage.get("cost"))
                choice = (raw.get("choices") or [{}])[0]
                record["finish_reason"] = choice.get("finish_reason")
                message = choice.get("message") or {}
                record["reasoning_text"] = message.get("reasoning") or message.get("reasoning_content")
                record["generation_id"] = raw.get("id")
                return text
            except Exception as error:
                raw = getattr(recorder.pending_sdk_response, "value", None)
                if raw is not None:
                    record["raw_completion"] = raw
                    record["cost"] = record.get("transport_cost", (raw.get("usage") or {}).get("cost"))
                    recorder.pending_sdk_response.value = None
                record["error"] = safe(str(error))
                record["parse_status"] = "failed"
                raise
            finally:
                record["latency"] = time.monotonic() - started

        base_lm.request_api = types.MethodType(request_api, base_lm)
        for method_name in ("run", "run_find"):
            original = getattr(base_lm, method_name)

            def observed(model, *args, _original=original, _method=method_name, **kw):
                name = args[2]
                try:
                    result = _original(*args, **kw)
                    recorder.parse_result(name, result[0] if _method == "run_find" else result)
                    return result
                except Exception as error:
                    recorder.parse_result(name, error=error)
                    raise

            setattr(base_lm, method_name, types.MethodType(observed, base_lm))

    def start_chain_async(self, agent_name, phase_name, query_name):
        result = super().start_chain_async(agent_name, phase_name, query_name)
        self.recorder.begin_chain(agent_name, phase_name, query_name)
        return result

    def start_chain(self, agent_name, phase_name, query_name):
        result = super().start_chain(agent_name, phase_name, query_name)
        self.recorder.begin_chain(agent_name, phase_name, query_name)
        return result

    def end_chain(self, agent_name, lm, chain=None):
        super().end_chain(agent_name, lm, chain=chain)
        self.recorder.end_chain()

    def _guarded(self, method, *args, **kwargs):
        budget = getattr(self.recorder, "budget", None)
        if budget:
            budget.check()
        result = method(*args, **kwargs)
        if budget:
            budget.check()
        return result

    def gen(self, *args, **kwargs):
        return self._guarded(super().gen, *args, **kwargs)

    def find(self, *args, **kwargs):
        return self._guarded(super().find, *args, **kwargs)

    def select(self, *args, **kwargs):
        return self._guarded(super().select, *args, **kwargs)
