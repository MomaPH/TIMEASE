"""
CLI solver for TIMEASE.

Run from the project root:
    uv run python scripts/solve_from_json.py <school.json> [options]

Options
-------
--timeout N     Solver time limit in seconds (default: 120).
--output DIR    Output directory (default: ./exports/).
--class NAME    Print only the timetable for this class.

Examples
--------
    uv run python scripts/solve_from_json.py timease/data/sample_school.json
    uv run python scripts/solve_from_json.py timease/data/real_school_dakar.json --timeout 60
    uv run python scripts/solve_from_json.py timease/data/sample_school.json --class "6ème A"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from timease.engine.models import Assignment, SchoolData
from timease.engine.solver import TimetableSolver
from timease.io.excel_export import export_timetable
from timease.io.md_export import export_markdown
from timease.io.pdf_export import export_pdf
from timease.io.word_export import export_word

DEFAULT_TIMEOUT = 120
DEFAULT_OUTPUT = "./exports"
SATISFACTION_THRESHOLD = 80.0

# ---------------------------------------------------------------------------
# ANSI colours
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"

SUBJECT_COLORS = [
    "\033[94m", "\033[92m", "\033[93m", "\033[95m",
    "\033[96m", "\033[91m", "\033[33m", "\033[35m",
    "\033[34m", "\033[32m", "\033[36m",
]

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def vlen(s: str) -> int:
    """Visual length of a string (ignores ANSI escape codes)."""
    return len(_ANSI_RE.sub("", s))


def vljust(s: str, width: int) -> str:
    """Left-justify s to visual width, padding with spaces."""
    return s + " " * max(0, width - vlen(s))


def _subject_color(subject: str, palette: dict[str, str]) -> str:
    if subject not in palette:
        palette[subject] = SUBJECT_COLORS[len(palette) % len(SUBJECT_COLORS)]
    return palette[subject]


def ok(msg: str)   -> str: return f"{GREEN}✓{RESET} {msg}"
def err(msg: str)  -> str: return f"{RED}✗{RESET} {msg}"
def warn(msg: str) -> str: return f"{YELLOW}⚠{RESET}  {msg}"


def header(title: str) -> str:
    line = "─" * 58
    return f"\n{BOLD}{CYAN}{line}{RESET}\n{BOLD}  {title}{RESET}\n{CYAN}{line}{RESET}"


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _to_min(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _fmt_min(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# ---------------------------------------------------------------------------
# Grid printer
# ---------------------------------------------------------------------------

CELL_W = 20   # visual characters per day column (content only, no border)
TIME_W = 5    # HH:MM


def _print_grid(
    cls_name: str,
    assignments: list[Assignment],
    sd: SchoolData,
    palette: dict[str, str],
) -> None:
    tc   = sd.timeslot_config
    days = tc.days

    # Build the ordered list of slot start-minutes within the week schedule
    slot_mins: list[int] = []
    for sess in tc.sessions:
        t = _to_min(sess.start_time)
        end = _to_min(sess.end_time)
        while t < end:
            slot_mins.append(t)
            t += tc.base_unit_minutes
    slot_mins = sorted(set(slot_mins))

    # covered[(day, minute)] = Assignment that occupies this slot
    covered: dict[tuple[str, int], Assignment] = {}
    for a in assignments:
        t = _to_min(a.start_time)
        while t < _to_min(a.end_time):
            covered[(a.day, t)] = a
            t += tc.base_unit_minutes

    # ── header ──────────────────────────────────────────────────────────────
    print(f"\n{BOLD}  ── {cls_name} ──{RESET}")

    def sep_line(left: str, mid: str, right: str) -> str:
        bar = "─" * (TIME_W + 2)
        cols = (mid + "─" * (CELL_W + 2)) * len(days)
        return f"  {left}{bar}{cols}{right}"

    # Top border
    print(sep_line("┌", "┬", "┐"))

    # Day-name header row
    time_cell = vljust("", TIME_W)
    day_cells = "".join(
        f"│ {vljust(BOLD + d.capitalize() + RESET, CELL_W)} "
        for d in days
    )
    print(f"  │ {time_cell} {day_cells}│")

    # Sub-header separator
    print(sep_line("├", "┼", "┤"))

    # ── rows ────────────────────────────────────────────────────────────────
    prev_sess_per_day: dict[str, Assignment | None] = {d: None for d in days}

    for i, slot_m in enumerate(slot_mins):
        # Detect session boundary: draw a thin separator between sessions
        boundary = False
        for day in days:
            a = covered.get((day, slot_m))
            prev = prev_sess_per_day[day]
            if prev is not None and (a is None or a is not prev):
                boundary = True
                break
        if boundary and i > 0:
            print(sep_line("├", "┼", "┤"))

        time_label = vljust(f"{DIM}{_fmt_min(slot_m)}{RESET}", TIME_W)

        cells: list[str] = []
        for day in days:
            a = covered.get((day, slot_m))
            if a is None:
                cells.append(" " * CELL_W)
            else:
                col = _subject_color(a.subject, palette)
                is_first = _to_min(a.start_time) == slot_m
                if is_first:
                    # Subject (up to 13 chars) + space + teacher last name (up to 6 chars)
                    subj  = a.subject[:13]
                    last  = a.teacher.split()[-1][:6]
                    raw   = f"{col}{subj}{RESET} {DIM}{last}{RESET}"
                    cells.append(vljust(raw, CELL_W))
                else:
                    # Continuation row: dim bar
                    raw = f"{col}{DIM}{'╌' * 16}{RESET}"
                    cells.append(vljust(raw, CELL_W))
            prev_sess_per_day[day] = a

        row_cells = "".join(f"│ {c} " for c in cells)
        print(f"  │ {time_label} {row_cells}│")

    # Bottom border
    print(sep_line("└", "┴", "┘"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Génère un emploi du temps TIMEASE depuis un fichier JSON."
    )
    p.add_argument("school_json", help="Chemin vers le fichier JSON de l'école")
    p.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT, metavar="N",
        help=f"Durée limite du solveur en secondes (défaut : {DEFAULT_TIMEOUT}s)",
    )
    p.add_argument(
        "--output", default=DEFAULT_OUTPUT, metavar="DIR",
        help=f"Répertoire de sortie (défaut : {DEFAULT_OUTPUT})",
    )
    p.add_argument(
        "--class", dest="only_class", metavar="NOM",
        help="N'afficher que l'emploi du temps de cette classe",
    )
    return p.parse_args()


def run(args: argparse.Namespace) -> int:
    import time

    path = Path(args.school_json)
    if not path.exists():
        print(err(f"Fichier introuvable : {path}"), file=sys.stderr)
        return 1

    # ------------------------------------------------------------------ load
    print(header("CHARGEMENT ET VALIDATION"))
    try:
        sd = SchoolData.from_json(path)
    except Exception as exc:
        print(err(f"Erreur de chargement : {exc}"), file=sys.stderr)
        return 1

    errors   = sd.validate()
    warnings = sd.validate_warnings()

    print(f"  {BOLD}École{RESET}        : {sd.school.name}  ({sd.school.academic_year})")
    print(f"  {BOLD}Classes{RESET}      : {len(sd.classes)}")
    print(f"  {BOLD}Enseignants{RESET}  : {len(sd.teachers)}")
    print(f"  {BOLD}Curriculum{RESET}   : {len(sd.curriculum)} entrées")
    n_hard = sum(1 for c in sd.constraints if c.type == "hard")
    n_soft = sum(1 for c in sd.constraints if c.type == "soft")
    print(f"  {BOLD}Contraintes{RESET}  : {n_hard} dures, {n_soft} souples")

    if errors:
        print(f"\n  {RED}{BOLD}{len(errors)} erreur(s) de validation :{RESET}")
        for e in errors:
            print(f"  {err(e)}")
        return 1
    print(f"  {ok('Validation : aucune erreur')}")
    for w in warnings:
        print(f"  {warn(w)}")

    # ------------------------------------------------------------------ solve
    print(header(f"RÉSOLUTION  (limite : {args.timeout}s)"))
    print("  Lancement du solveur…")

    solver  = TimetableSolver()
    t0      = time.time()
    result  = solver.solve(sd, timeout_seconds=args.timeout)
    elapsed = time.time() - t0

    if not result.solved:
        print(f"\n  {err(f'Aucune solution trouvée en {elapsed:.1f}s.')}")
        print(f"\n  {YELLOW}Diagnostic en cours…{RESET}")

        from timease.engine.conflicts import ConflictAnalyzer
        reports = ConflictAnalyzer(sd).analyze()

        if reports:
            print(header("CONFLITS DÉTECTÉS"))
            for i, r in enumerate(reports, 1):
                print(f"\n  {BOLD}{RED}Conflit {i}{RESET}  [{DIM}{r.source}{RESET}]")
                print(f"  {r.description_fr}")
                print(f"  {DIM}Suggestions :{RESET}")
                for opt in r.fix_options:
                    stars = "★" * opt.ease + "☆" * (3 - opt.ease)
                    print(f"    {stars}  {CYAN}{opt.fix_fr}{RESET}")
                    print(f"          {DIM}→ {opt.impact_fr}{RESET}")
        else:
            print(f"  {warn('Aucun conflit détecté — essayez un timeout plus long.')}")
        return 1

    print(f"  {ok(f'Solution trouvée en {elapsed:.1f}s')}")
    print(f"  Sessions planifiées : {BOLD}{len(result.assignments)}{RESET}")

    # --------------------------------------------------------------- verify
    violations = result.verify(sd)
    if violations:
        print(f"\n  {RED}{BOLD}{len(violations)} violation(s) :{RESET}")
        for v in violations:
            print(f"  {err(v)}")
    else:
        print(f"  {ok('Vérification : aucune violation')}")

    # --------------------------------------------------------------- soft
    if result.soft_constraint_details:
        print(header("CONTRAINTES SOUPLES"))
        satisfied = 0
        for d in result.soft_constraint_details:
            pct     = d["satisfaction_percent"]
            cid     = d["constraint_id"]
            details = d["details_fr"]
            flag    = ok if pct >= SATISFACTION_THRESHOLD else err
            if pct >= SATISFACTION_THRESHOLD:
                satisfied += 1
            print(f"  {flag(f'[{cid}] {pct:5.1f}%  {details}')}")
        total = len(result.soft_constraint_details)
        color = GREEN if satisfied == total else YELLOW
        print(f"\n  {color}{BOLD}{satisfied}/{total} contraintes souples respectées{RESET}"
              f"  (seuil {SATISFACTION_THRESHOLD:.0f}%)")

    # --------------------------------------------------------------- timetable
    print(header("EMPLOI DU TEMPS"))
    palette: dict[str, str] = {}

    if args.only_class:
        cls_names = [c.name for c in sd.classes]
        if args.only_class not in cls_names:
            print(err(f"Classe '{args.only_class}' introuvable. "
                      f"Disponibles : {', '.join(cls_names)}"))
            return 1
        classes_to_show = [args.only_class]
    else:
        classes_to_show = sorted({a.school_class for a in result.assignments})

    for cls_name in classes_to_show:
        cls_a = [a for a in result.assignments if a.school_class == cls_name]
        _print_grid(cls_name, cls_a, sd, palette)

    print()

    # ------------------------------------------------------------------ export
    print(header("EXPORT"))

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.school_json).stem

    exports: list[tuple[str, Path, object]] = [
        ("Excel",    out_dir / f"{stem}_timetable.xlsx", export_timetable),
        ("PDF",      out_dir / f"{stem}_timetable.pdf",  export_pdf),
        ("Word",     out_dir / f"{stem}_timetable.docx", export_word),
        ("Markdown", out_dir / f"{stem}_timetable.md",   export_markdown),
    ]

    all_ok = True
    for fmt, dest, fn in exports:
        try:
            fn(result, sd, str(dest))
            size = dest.stat().st_size
            print(f"  {ok(f'{fmt:<10} → {dest}  ({size:,} octets)')}")
        except Exception as exc:
            print(f"  {err(f'{fmt}: {exc}')}")
            all_ok = False

    if all_ok:
        print(f"\n  {GREEN}{BOLD}Tous les exports réussis.{RESET}")
    else:
        print(f"\n  {YELLOW}Certains exports ont échoué.{RESET}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(run(parse_args()))
