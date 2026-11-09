"""Dedicated keyed draws and ordered names from METHODS.md B6."""

import random


NAME_POOL = (
    "Julia", "Kate", "Jack", "Emma", "Luke", "Noah", "Olivia", "Liam",
    "Isaac", "Chloe", "Owen", "Leah", "Henry", "Zoe", "Caleb", "Nora",
    "Felix", "Clara", "Adam", "Maya", "Leo", "Elena", "Simon", "Naomi",
    "Oscar", "Diego", "Priya", "Tariq", "Ingrid", "Mateo", "Yusuf", "Hana",
    "Viktor", "Amara", "Ronan", "Sofia", "Kenji", "Lucia", "Dmitri", "Ines",
)


def opener_slot(seed: int, cycle: int, num_agents: int) -> int:
    """Choose a stable household slot from all agents at this N.

    Cycle numbers are one-based. Across N=8 arms, successor identities
    occupy the same slots. Different N use their full participant pools,
    following the user's clarification of the original matching requirement.
    """
    if cycle < 1 or num_agents not in (8, 16, 32):
        raise ValueError("Expected a one-based cycle and N of 8, 16, or 32")
    return random.Random(f"opener|{seed}|{cycle}").choice(range(num_agents))


def values_svo_angle(seed: int) -> float:
    return random.Random(f"svo|{seed}").uniform(22.45, 57.15)


def initial_stakes_horizons(seed: int) -> tuple[int, ...]:
    """Draw x, then shuffle the seven short horizons with the same RNG."""
    rng = random.Random(f"stakes|{seed}")
    short = [3, 4, 5, 6, 7, 8, rng.randint(3, 8)]
    rng.shuffle(short)
    short_iter = iter(short)
    return tuple(16 if slot == seed % 8 else next(short_iter) for slot in range(8))


def successor_horizon(seed: int, slot: int, cycle: int) -> int:
    """Draw a successor's horizon keyed by its one-based joining cycle."""
    if not 0 <= slot < 8 or cycle < 1:
        raise ValueError("Expected a household slot in 0..7 and a one-based cycle")
    return random.Random(f"successor|{seed}|{slot}|{cycle}").randint(3, 8)


def nomination_fallback(key, options):
    """Uniform, independent per-turn fallback; never consumes global RNG."""
    return random.Random(key).choice(options)
