"""B4.4/B4.5 private measurements; none of this module stores memories."""

import re

from pathfinder import assistant, user
from simulation.interventions import (
    ELICITATION_PROMPT, ELICITATION_PROMPT_FINAL_MONTH, PERCEIVED_LEADERSHIP_PROMPT,
)
from simulation.persona.cognition import leaders, utils


def strip_stakes_tag(text):
    return re.sub(r"\s*\[months remaining:\s*\d+\]", "", text, flags=re.I).strip()


def resolve_name(text, names):
    value = strip_stakes_tag(text).strip(" \t\n\"'.")
    if value.casefold() == "no one":
        return "no one"
    exact = [name for name in names if name.casefold() == value.casefold()]
    if len(exact) == 1:
        return exact[0]
    partial = [name for name in names if len(value) >= 2 and name.casefold().startswith(value.casefold())]
    return partial[0] if len(partial) == 1 else "unresolved"


def conversation_prefix(persona, participants, memories, location, time, context):
    """Match the original utterance user prefix, before conversation text."""
    svo, disinfo, leader = leaders.get_leader_persona_prompts(persona)
    text = f"{utils.get_sytem_prompt(persona.identity)}\n"
    text += utils.location_time_info(location, time)
    text += utils.memory_prompt(persona.identity, memories)
    text += "\n"
    text += f"Current context: {context}\n\n"
    names = utils.list_to_comma_string([utils.render_name(p.identity) for p in participants])
    text += f"Scenario: {names} are engaged in a group chat."
    if svo:
        text += f"{svo}\n"
    if not getattr(persona.cfg.converse, "drop_truthfulness_line", False):
        text += f"{disinfo}\n"
    text += f"{leader}\n"
    return text


def parse_elicitation(raw, final_month=False):
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
    result = {"raw": raw, "plan": None, "preferred_limit": None, "reason": None}
    statuses = {}
    for label, field in (("PLAN", "plan"), ("LIMIT", "preferred_limit")):
        if label == "PLAN" and final_month:
            statuses[field] = "not_applicable"
            continue
        pattern = number if label == "PLAN" else f"(?:none|{number})"
        match = re.search(rf"^\s*{label}\s*:\s*({pattern})\s*(?:tons?)?\s*$", raw, re.I | re.M)
        statuses[field] = "ok" if match else "failed"
        if match:
            result[field] = "none" if match.group(1).casefold() == "none" else float(match.group(1))
    reason = re.search(r"^\s*REASON\s*:\s*(\S[^\n]*)", raw, re.I | re.M)
    if reason:
        result["reason"] = reason.group(1).strip()
    statuses["reason"] = "ok" if reason else "failed"
    result["field_status"] = statuses
    result["parse_status"] = "ok" if "failed" not in statuses.values() else "failed"
    return result


def measure(model, persona, participants, location, time, context, report, kind, conversation=None):
    """One model generation; retrieval is read-only and output stays private."""
    memories = persona.retrieve.retrieve([context], top_k=5)
    prefix = conversation_prefix(persona, participants, memories, location, time, context)
    text = prefix + f"\nCurrent public fishing report:\n{report}\n\n"
    final_month = getattr(persona.identity, "stakes_months_remaining", None) == 1
    if kind == "elicitation":
        text += ELICITATION_PROMPT_FINAL_MONTH if final_month else ELICITATION_PROMPT
    elif kind == "perceived_leadership":
        text += "Conversation so far:\n" + utils.conversation_to_string_with_dash(conversation) + "\n"
        text += PERCEIVED_LEADERSHIP_PROMPT
    else:
        raise ValueError(f"Unknown measurement kind: {kind}")
    lm, chain = model.start_chain_async(persona.identity.name, "measurement", kind)
    with user():
        lm += text
    with assistant():
        lm = model.gen(lm, name="measurement_response", default_value="", stop_regex=r"\Z", chain=chain)
        raw = lm["measurement_response"]
    if kind == "elicitation":
        result = parse_elicitation(raw, final_month=final_month)
    else:
        match = re.search(r"^\s*ANSWER\s*:\s*(.+?)\s*$", raw, re.I | re.M)
        answer = match.group(1) if match else raw
        resolved = resolve_name(answer, [p.identity.name for p in participants])
        result = {"raw": raw, "answer": answer, "resolved_identity": resolved,
                  "parse_status": "failed" if resolved == "unresolved" else "ok"}
    if hasattr(model, "recorder"):
        model.recorder.parse_result(kind, result)
        if result["parse_status"] == "failed":
            model.recorder.parse_result(kind, error="Private instrument parse failed")
    model.end_chain(persona.identity.name, lm, chain=chain)
    return result
