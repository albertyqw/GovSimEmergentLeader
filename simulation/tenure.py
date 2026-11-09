"""B4.6 fixed household slots, precomputed tenure and fresh successors."""

import os

from simulation.intervention_randomness import NAME_POOL, initial_stakes_horizons, successor_horizon
from simulation.persona.common import PersonaIdentity
from simulation.persona.persona import PersonaAgent
from simulation.persona.cognition.utils import render_name


class TenureState:
    def __init__(self, seed, max_cycles):
        self.schedule = []
        self.by_cycle = {}
        self.retired = []
        self.departures = {}
        next_name = 8
        active = []
        for slot, horizon in enumerate(initial_stakes_horizons(seed)):
            record = self._record(NAME_POOL[slot], slot, 1, horizon)
            active.append(record)
            self.schedule.append(record)
        for cycle in range(1, max_cycles + 1):
            for slot, record in enumerate(active):
                if record["leave_cycle"] < cycle:
                    horizon = successor_horizon(seed, slot, cycle)
                    record = self._record(NAME_POOL[next_name], slot, cycle, horizon)
                    next_name += 1
                    active[slot] = record
                    self.schedule.append(record)
            self.by_cycle[cycle] = list(active)

    @staticmethod
    def _record(name, slot, join, horizon):
        return {"identity": name, "slot": slot, "household": slot,
                "join_cycle": join, "leave_cycle": join + horizon - 1, "horizon": horizon}

    def apply(self, ctx, cycle, framework_wrapper):
        """Rebind personas only; the environment and its eight slots persist."""
        expected = self.by_cycle[cycle]
        changed = False
        for record in expected:
            slot = record["slot"]
            agent_id = f"persona_{slot}"
            persona = ctx.personas[agent_id]
            if persona.identity.name != record["identity"]:
                self.retired.append(persona)
                self.departures.setdefault(cycle - 1, []).append(persona.identity.name)
                ctx.agent_name_to_id.pop(persona.identity.name)
                identity_config = dict(ctx.cfg.personas[agent_id])
                identity_config["name"] = record["identity"]
                identity = PersonaIdentity(
                    agent_id=agent_id, **identity_config, environment=persona.identity.env,
                )
                persona = PersonaAgent(
                    ctx.cfg.agent, ctx.wrapper, framework_wrapper,
                    os.path.join(ctx.experiment_storage, "identities", record["identity"]),
                    experiment_storage=ctx.experiment_storage,
                )
                persona.init_persona(agent_id, identity, social_graph=None)
                if getattr(ctx.cfg.agent, "paper_definitions", False):
                    identity.paper_definitions = True
                    persona.paper_disinformation = bool(ctx.cfg.env.disinformation)
                if persona.memory.id_to_node:
                    raise AssertionError("A successor must start with empty memory")
                ctx.personas[agent_id] = persona
                ctx.agent_name_to_id[identity.name] = agent_id
                ctx.agent_id_to_name[agent_id] = identity.name
                changed = True
            persona.identity.stakes_months_remaining = record["horizon"] - (cycle - record["join_cycle"])
            persona.identity.tenure_record = record
        if changed:
            for persona in ctx.personas.values():
                persona.other_personas.clear()
                persona.other_personas_from_id.clear()
                for component in (persona.perceive, persona.retrieve, persona.store,
                                  persona.reflect, persona.plan, persona.act, persona.converse):
                    component.other_personas.clear()
            for persona in ctx.personas.values():
                for other in ctx.personas.values():
                    persona.add_reference_to_other_persona(other)
        ctx.env.agent_id_to_name = {
            agent_id: render_name(persona.identity) for agent_id, persona in ctx.personas.items()
        }
        ctx.env.agent_id_to_name["framework"] = "framework"
