from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from timease.engine.models import SchoolData
from timease.engine.solver import TimetableSolver

SAMPLE_JSON = Path(__file__).parent.parent / "timease" / "data" / "sample_school.json"
REAL_DAKAR_JSON = Path(__file__).parent.parent / "timease" / "data" / "real_school_dakar.json"
REAL_DAKAR_LOCKED_JSON = Path(__file__).parent.parent / "timease" / "data" / "real_school_dakar_LOCKED.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_variant(tmp_path: Path, name: str, payload: dict) -> Path:
    out = tmp_path / name
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


@pytest.mark.skipif(
    not SAMPLE_JSON.exists() or not REAL_DAKAR_JSON.exists() or not REAL_DAKAR_LOCKED_JSON.exists(),
    reason="One or more real scenario files are missing",
)
def test_ladder_l1_to_l5_non_diluted_and_expected_outcomes(tmp_path: Path) -> None:
    l1 = _load_json(REAL_DAKAR_LOCKED_JSON)
    l2 = _load_json(REAL_DAKAR_JSON)

    l3 = deepcopy(l2)
    l3_constraints = list(l3.get("constraints", []))
    l3_constraints.extend(
        [
            {
                "id": "L3-S8",
                "type": "soft",
                "category": "teacher_day_off",
                "description_fr": "Préférence: demi-journée libre mardi matin (Samba Diallo)",
                "priority": 6,
                "parameters": {"teacher": "Samba Diallo", "day": "mardi", "session": "Matin"},
            },
            {
                "id": "L3-S9",
                "type": "soft",
                "category": "teacher_time_preference",
                "description_fr": "Préférence: cours du matin pour Fatou Mbaye",
                "priority": 5,
                "parameters": {"teacher": "Fatou Mbaye", "preferred_session": "Matin"},
            },
            {
                "id": "L3-S10",
                "type": "soft",
                "category": "heavy_subjects_morning",
                "description_fr": "Mathématiques et Physique-Chimie priorisées le matin",
                "priority": 5,
                "parameters": {"subjects": ["Mathématiques", "Physique-Chimie"]},
            },
            {
                "id": "L3-H9",
                "type": "hard",
                "category": "max_sessions_per_day",
                "description_fr": "Pas plus de 2 séances d'une même matière par jour",
                "priority": 5,
                "parameters": {"max_sessions": 2},
            },
        ]
    )
    l3["constraints"] = l3_constraints

    l4 = _load_json(SAMPLE_JSON)

    l5 = deepcopy(l4)
    all_days = [d["name"] for d in l5["timeslot_config"]["days"]]
    l5_constraints = list(l5.get("constraints", []))
    for i, day in enumerate(all_days, start=1):
        l5_constraints.append(
            {
                "id": f"L5-H{i}",
                "type": "hard",
                "category": "day_off",
                "description_fr": f"Jour bloqué: {day}",
                "priority": 5,
                "parameters": {"day": day, "session": "all"},
            }
        )
    l5["constraints"] = l5_constraints

    l1_path = _write_variant(tmp_path, "L1-real-locked.json", l1)
    l2_path = _write_variant(tmp_path, "L2-real-dakar.json", l2)
    l3_path = _write_variant(tmp_path, "L3-real-dakar-constrained.json", l3)
    l4_path = _write_variant(tmp_path, "L4-sample-school.json", l4)
    l5_path = _write_variant(tmp_path, "L5-sample-impossible.json", l5)

    sd_l1 = SchoolData.from_json(l1_path)
    sd_l2 = SchoolData.from_json(l2_path)
    sd_l3 = SchoolData.from_json(l3_path)
    sd_l4 = SchoolData.from_json(l4_path)
    sd_l5 = SchoolData.from_json(l5_path)

    # Anti-dilution checks: scenarios must keep real-world scale.
    assert len(sd_l1.classes) >= 4 and len(sd_l1.teachers) >= 14 and len(sd_l1.curriculum) >= 30
    assert len(sd_l2.classes) >= 4 and len(sd_l2.rooms) >= 6 and len(sd_l2.curriculum) >= 32
    assert len(sd_l3.constraints) >= 10 and len(sd_l3.curriculum) >= 32
    assert len(sd_l4.classes) >= 8 and len(sd_l4.teachers) >= 14 and len(sd_l4.curriculum) >= 82
    assert len(sd_l5.classes) >= 8 and len(sd_l5.curriculum) >= 82 and len(sd_l5.constraints) >= 12

    solver = TimetableSolver()
    r1 = solver.solve(sd_l1, timeout_seconds=120)
    r2 = solver.solve(sd_l2, timeout_seconds=120)
    r3 = solver.solve(sd_l3, timeout_seconds=120)
    r4 = solver.solve(sd_l4, timeout_seconds=120)
    r5 = solver.solve(sd_l5, timeout_seconds=60)

    # Expected ladder outcomes: L1-L4 feasible/usable, L5 deliberately infeasible.
    assert r1.solved or r1.partial
    assert r2.solved or r2.partial
    assert r3.solved or r3.partial
    assert r4.solved or r4.partial
    assert len(r1.assignments) > 0 and len(r2.assignments) > 0 and len(r3.assignments) > 0 and len(r4.assignments) > 0

    assert r5.solved is False
    assert (r5.conflicts and len(r5.conflicts) > 0) or (r5.unscheduled and len(r5.unscheduled) > 0)
