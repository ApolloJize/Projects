"""Build the small, numeric-only evidence packet sent to GenAI."""
import json
from .clean import SERVICES


def evidence_packet(rows):
    result = []
    for ward, service, visits, event_count in rows:
        if ward not in range(1, 9) or service not in SERVICES:
            raise ValueError("Unexpected category in report")
        if int(visits) != visits or visits < 0 or int(event_count) != event_count or event_count < 0:
            raise ValueError("Invalid aggregate")
        result.append({"ward": int(ward), "service_type": service,
                       "visits": int(visits), "events": int(event_count)})
    return {"dataset": "synthetic demonstration", "rows": result,
            "total_visits": sum(r["visits"] for r in result)}


def prompt_for(packet):
    return ("Summarize these synthetic service-activity counts in at most 100 words. "
            "Use only the supplied numbers. State the total and the largest service count. "
            "Do not infer population rates, health outcomes, causes, or trends. "
            "No patient records are present. Do not generate SQL.\n" + json.dumps(packet, sort_keys=True))
