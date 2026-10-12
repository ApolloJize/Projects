"""Run the small plan regression set. --backend oci makes paid model calls."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path
from inference.cloud import Settings, make_planner
from inference.planning import PreviewPlanner


def evaluate(planner, cases):
    results = []
    for case in cases:
        try:
            actual = asdict(planner.predict(case["question"]).plan)
            results.append({"question": case["question"], "expected": case["plan"],
                            "actual": actual, "passed": actual == case["plan"]})
        except Exception as exc:
            results.append({"question": case["question"], "passed": False, "error_type": type(exc).__name__})
    return {"cases": len(cases), "passed": sum(r["passed"] for r in results), "results": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["preview", "oci"], default="preview")
    parser.add_argument("--config")
    args = parser.parse_args()
    cases = json.loads((Path(__file__).parent / "data" / "eval_cases.json").read_text())
    planner = PreviewPlanner() if args.backend == "preview" else make_planner(Settings(args.config))
    result = {"backend": args.backend, **evaluate(planner, cases)}
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] == result["cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
