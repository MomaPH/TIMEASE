"""
Greedy warm-start for the timetable CP-SAT model.

Produces a best-effort non-overlapping placement in O(sessions * domain) time.
The result is fed to CP-SAT via ``model.add_hint`` so the solver starts from
a near-feasible point instead of cold.  Placements that conflict with already-
placed sessions are simply skipped — CP-SAT will repair them.

The algorithm:

1. Sort sessions by "most constrained first":
   smallest domain, then longest duration, then higher teacher load,
   then session index for determinism.
2. For each session, walk its domain in ascending order and pick the first
   ``gpos`` such that ``[gpos, gpos + dur_slots)`` overlaps no already-placed
   interval for the same class or the same teacher.
3. Return a dict mapping session idx to chosen global slot (or ``None`` if
   no conflict-free slot was found).

Overlap reasoning relies on the solver's own invariant: each session's domain
is pre-filtered to stay within one day, so two sessions on different days have
disjoint slot ranges on the global timeline.  Integer-range overlap is then
sufficient — no minute arithmetic needed.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from timease.engine.solver import _Session

logger = logging.getLogger(__name__)


def greedy_warm_start(
    sessions: list["_Session"],
    session_domains: list[list[int]],
) -> dict[int, int]:
    """Return ``{session_idx: global_slot}`` for every session we could place.

    Missing sessions (couldn't find a conflict-free slot) are simply absent
    from the dict — the caller treats absence as "no hint".
    """
    teacher_load: dict[str, int] = defaultdict(int)
    for sess in sessions:
        teacher_load[sess.teacher_name] += 1

    ordered = sorted(
        sessions,
        key=lambda s: (
            len(session_domains[s.idx]),
            -s.dur_slots,
            -teacher_load[s.teacher_name],
            s.idx,
        ),
    )

    # Busy intervals keyed by class/teacher name. Each entry is a list of
    # (start, end) integer ranges on the global timeline.
    class_busy: dict[str, list[tuple[int, int]]] = defaultdict(list)
    teacher_busy: dict[str, list[tuple[int, int]]] = defaultdict(list)
    placed: dict[int, int] = {}

    for sess in ordered:
        domain = session_domains[sess.idx]
        if not domain:
            continue
        for gpos in sorted(domain):
            start = gpos
            end = gpos + sess.dur_slots
            c_intervals = class_busy[sess.class_name]
            t_intervals = teacher_busy[sess.teacher_name]
            if any(start < e and b < end for b, e in c_intervals):
                continue
            if any(start < e and b < end for b, e in t_intervals):
                continue
            placed[sess.idx] = gpos
            c_intervals.append((start, end))
            t_intervals.append((start, end))
            break

    return placed
