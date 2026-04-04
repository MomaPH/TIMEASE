"""
CLI solver for TIMEASE — Excel input.

Usage
-----
    python scripts/solve_from_excel.py <file.xlsx> [options]

Options
-------
    --output DIR    Output directory (default: ./exports/)
    --timeout N     Solver time limit in seconds (default: 120)

Outputs written to *output*:
    {stem}_timetable.xlsx
    {stem}_timetable.pdf
    {stem}_timetable.docx
    {stem}_timetable.md

Examples
--------
    python scripts/solve_from_excel.py school_data.xlsx
    python scripts/solve_from_excel.py school_data.xlsx --output ./results --timeout 60
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from timease.engine.solver import TimetableSolver
from timease.io.excel_export import export_timetable
from timease.io.excel_import import read_template
from timease.io.md_export import export_markdown
from timease.io.pdf_export import export_pdf
from timease.io.word_export import export_word

DEFAULT_TIMEOUT = 120
DEFAULT_OUTPUT = "./exports"

# ── ANSI helpers (mirrors solve_from_json.py) ──────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"


def ok(msg: str)   -> str: return f"{GREEN}✓{RESET} {msg}"
def err(msg: str)  -> str: return f"{RED}✗{RESET} {msg}"
def warn(msg: str) -> str: return f"{YELLOW}⚠{RESET}  {msg}"


def header(title: str) -> str:
    line = "─" * 58
    return f"\n{BOLD}{CYAN}{line}{RESET}\n{BOLD}  {title}{RESET}\n{CYAN}{line}{RESET}"


# ── Argument parsing ────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Génère un emploi du temps TIMEASE depuis un fichier Excel.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("excel_file", help="Chemin vers le fichier .xlsx")
    p.add_argument(
        "--output", default=DEFAULT_OUTPUT, metavar="DIR",
        help=f"Répertoire de sortie (défaut : {DEFAULT_OUTPUT})",
    )
    p.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT, metavar="N",
        help=f"Limite du solveur en secondes (défaut : {DEFAULT_TIMEOUT}s)",
    )
    return p.parse_args()


# ── Main logic ──────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> int:
    # ------------------------------------------------------------------ parse
    print(header("LECTURE DU FICHIER EXCEL"))

    path = Path(args.excel_file)
    if not path.exists():
        print(err(f"Fichier introuvable : {path}"), file=sys.stderr)
        return 1
    if path.suffix.lower() not in (".xlsx", ".xls", ".xlsm"):
        print(err(f"Format non reconnu : {path.suffix}  (attendu : .xlsx)"),
              file=sys.stderr)
        return 1

    print(f"  Fichier : {BOLD}{path.name}{RESET}")

    data, errors = read_template(str(path))

    if errors:
        print(f"\n  {RED}{BOLD}{len(errors)} erreur(s) d'import / validation :{RESET}")
        for e in errors:
            print(f"  {err(e)}")
        return 1

    print(f"  {ok('Import et validation réussis')}")
    print(f"  {BOLD}École{RESET}       : {data.school.name}  ({data.school.academic_year})")
    print(f"  {BOLD}Ville{RESET}       : {data.school.city}")
    print(f"  {BOLD}Classes{RESET}     : {len(data.classes)}")
    print(f"  {BOLD}Enseignants{RESET} : {len(data.teachers)}")
    print(f"  {BOLD}Matières{RESET}    : {len(data.subjects)}")
    print(f"  {BOLD}Salles{RESET}      : {len(data.rooms)}")
    n_hard = sum(1 for c in data.constraints if c.type == "hard")
    n_soft = sum(1 for c in data.constraints if c.type == "soft")
    print(f"  {BOLD}Contraintes{RESET} : {n_hard} dures, {n_soft} souples")

    for w in data.validate_warnings():
        print(f"  {warn(w)}")

    # ------------------------------------------------------------------ solve
    print(header(f"RÉSOLUTION  (limite : {args.timeout}s)"))
    print("  Lancement du solveur…")

    t0 = time.time()
    result = TimetableSolver().solve(data, timeout_seconds=args.timeout)
    elapsed = time.time() - t0

    if not result.solved and not result.partial:
        print(f"\n  {err(f'Aucune solution trouvée en {elapsed:.1f}s.')}")
        # Suggest conflict analysis
        try:
            from timease.engine.conflicts import ConflictAnalyzer
            reports = ConflictAnalyzer(data).analyze()
            if reports:
                print(f"\n  {YELLOW}Conflits détectés :{RESET}")
                for rep in reports:
                    print(f"    • {rep.description_fr}")
                    for opt in rep.fix_options[:2]:
                        print(f"      → {opt.fix_fr}")
        except Exception:
            pass
        return 1

    if result.solved:
        status_msg = f"Solution complète trouvée en {elapsed:.1f}s"
    else:
        status_msg = (
            f"Solution partielle en {elapsed:.1f}s  "
            f"({len(result.unscheduled_sessions)} sessions non planifiées)"
        )
    print(f"  {ok(status_msg)}")
    print(f"  Sessions planifiées : {BOLD}{len(result.assignments)}{RESET}")

    violations = result.verify(data)
    if violations:
        print(f"\n  {RED}{BOLD}{len(violations)} violation(s) :{RESET}")
        for v in violations[:5]:
            print(f"  {err(v)}")
        if len(violations) > 5:
            print(f"  {RED}… et {len(violations) - 5} autre(s){RESET}")
    else:
        print(f"  {ok('Vérification post-solve : aucune violation')}")

    # ------------------------------------------------------------------ export
    print(header("EXPORT"))

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = path.stem

    exports: list[tuple[str, Path, object]] = [
        ("Excel",    out_dir / f"{stem}_timetable.xlsx", export_timetable),
        ("PDF",      out_dir / f"{stem}_timetable.pdf",  export_pdf),
        ("Word",     out_dir / f"{stem}_timetable.docx", export_word),
        ("Markdown", out_dir / f"{stem}_timetable.md",   export_markdown),
    ]

    all_ok = True
    for fmt, dest, fn in exports:
        try:
            fn(result, data, str(dest))
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
