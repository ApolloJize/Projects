"""Small inference pipeline: plan, read one view, compute, return evidence."""
from dataclasses import asdict
from datetime import datetime, timezone
from time import perf_counter
from .contracts import validate_rows
from .planning import validate_question
from .sources import filter_rows


def calculate(plan, rows):
    rows = validate_rows(filter_rows(rows, plan))
    if not rows:
        return {"status": "no_data", "answer": "No rows match these filters; an absent row is not a zero count.",
                "metrics": {}, "evidence": []}
    total = sum(r.visits for r in rows)
    metrics = {"total_visits": total, "event_count": sum(r.event_count for r in rows)}
    scope = []
    if plan.ward is not None:
        scope.append(f"ward {plan.ward}")
    if plan.service:
        scope.append(plan.service.lower())
    label = " / ".join(scope) or "the selected snapshot"
    if plan.operation == "total_visits":
        answer = f"{total} visits in {label}."
    elif plan.operation in ("visits_by_ward", "busiest_ward"):
        by_ward = {}
        for row in rows:
            by_ward[row.ward] = by_ward.get(row.ward, 0) + row.visits
        metrics["by_ward"] = [{"ward": w, "visits": v} for w, v in sorted(by_ward.items())]
        if plan.operation == "busiest_ward":
            highest = max(by_ward.values())
            winners = [w for w, v in sorted(by_ward.items()) if v == highest]
            metrics["busiest_wards"] = winners
            metrics["highest_visits"] = highest
            subjects = "Ward " + str(winners[0]) if len(winners) == 1 else "Wards " + ", ".join(map(str, winners))
            answer = f"{subjects}: {highest} visits{' each (tied)' if len(winners) > 1 else ''}, within {label}."
        else:
            answer = "; ".join(f"ward {w}: {v}" for w, v in sorted(by_ward.items())) + " visits."
    elif plan.operation == "visits_by_service":
        by_service = {}
        for row in rows:
            by_service[row.service_type] = by_service.get(row.service_type, 0) + row.visits
        metrics["by_service"] = [{"service": s, "visits": v} for s, v in sorted(by_service.items())]
        answer = "; ".join(f"{s.lower()}: {v}" for s, v in sorted(by_service.items())) + " visits."
    else:
        raise ValueError("Cannot calculate this operation")
    return {"status": "answered", "answer": answer, "metrics": metrics,
            "evidence": [row.evidence() for row in rows]}


class InferenceModel:
    def __init__(self, planner, source):
        self.planner = planner
        self.source = source

    def predict(self, question):
        question = validate_question(question)
        started = perf_counter()
        prediction = self.planner.predict(question)
        plan = prediction.plan
        if plan.operation == "unsupported":
            result = {"status": "unsupported", "answer": "This model supports visit totals, ward/service comparisons, and busiest wards for the current snapshot.",
                      "metrics": {}, "evidence": []}
        else:
            result = calculate(plan, self.source.fetch(plan))
        return {"question": question, "plan": asdict(plan), **result,
                "source": self.source.name, "model_id": prediction.model_id,
                "request_id": prediction.request_id,
                "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                "latency_ms": round((perf_counter() - started) * 1000, 2)}
