from __future__ import annotations

import argparse
import sys
from pathlib import Path

from evidenceai.constants import REGISTERED_SEED
from evidenceai.evaluation import evaluate, write_report
from evidenceai.pipeline import RegistrationDeviation, run_slice
from evidenceai.store import Database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evidenceai")
    sub = parser.add_subparsers(dest="command", required=True)

    slice_cmd = sub.add_parser("slice", help="Generate the fixture and project the graph")
    slice_cmd.add_argument("--out", type=Path, default=Path("data/slice"))
    slice_cmd.add_argument("--seed", type=int, default=REGISTERED_SEED)

    harness = sub.add_parser("harness", help="Score the fixture stored in a slice database")
    harness.add_argument("--db", type=Path, required=True)
    harness.add_argument("--out", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "slice":
        return _slice(args.out, args.seed)
    if args.command == "harness":
        return _harness(args.db, args.out)
    return 2


def _slice(out_dir: Path, seed: int) -> int:
    try:
        result = run_slice(out_dir, seed=seed)
    except RegistrationDeviation as exc:
        print(str(exc), file=sys.stderr)
        return 2
    counts = result["counts"]
    print(f"db={result['db_path']}")
    print(f"documents={counts['documents']}")
    print(f"claims={counts['claims']}")
    print(f"pair_assessments={counts['pair_assessments']}")
    print(f"answers={counts['answers']}")
    print(f"duration_seconds={result['duration_seconds']}")
    return 0


def _harness(db_path: Path, out_path: Path) -> int:
    db = Database(db_path, readonly=True)
    try:
        summary = evaluate(db)
    finally:
        db.close()
    write_report(summary, out_path)
    rule = summary["methods"]["numeric_rule_v0"]["false_conflict_rate"]
    baseline = summary["methods"]["surface_string_baseline"]["false_conflict_rate"]
    print(f"report={out_path}")
    print(f"numeric_rule_v0_false_conflict_rate={_print_rate(rule)}")
    print(f"surface_string_baseline_false_conflict_rate={_print_rate(baseline)}")
    print(f"directional_expectation_met={str(summary['directional_expectation_met']).lower()}")
    return 0


def _print_rate(rate: dict | None) -> str:
    if rate is None:
        return "undefined"
    return f"{rate['numerator']}/{rate['denominator']}"


if __name__ == "__main__":
    raise SystemExit(main())
