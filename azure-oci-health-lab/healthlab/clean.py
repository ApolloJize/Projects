"""Small, explicit rules, shared by the offline demo and its tests."""
import re
from datetime import date

SERVICES = {"SCREENING", "IMMUNIZATION", "OUTREACH"}


def clean_snapshot(events, facilities):
    """Latest revision wins; invalid corrections remove stale curated records."""
    latest = {}
    for row in events:
        key = row["event_id"]
        rank = (int(row["revision"]), int(row["row_id"]))
        if key not in latest or rank > latest[key][0]:
            latest[key] = (rank, dict(row))
    clean, rejected, deleted = [], [], 0
    for _, row in sorted(latest.values(), key=lambda item: item[1]["event_id"]):
        if row["is_deleted"].strip().upper() == "Y":
            deleted += 1
            continue
        facility = facilities.get(row["facility_id"].strip().upper())
        service = row["service_type"].strip().upper()
        visits = row["visits"].strip()
        day = row["service_date"].strip()
        reason = None
        if not facility:
            reason = "unknown_facility"
        elif service not in SERVICES:
            reason = "invalid_service"
        elif not re.fullmatch(r"[0-9]{1,6}", visits):
            reason = "invalid_visits"
        else:
            try:
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", day):
                    raise ValueError("date format")
                date.fromisoformat(day)
            except ValueError:
                reason = "invalid_date"
        if reason:
            rejected.append({"event_id": row["event_id"], "row_id": int(row["row_id"]), "reason": reason})
        else:
            clean.append({"event_id": row["event_id"], "revision": int(row["revision"]),
                          "facility_id": facility["facility_id"], "ward": int(facility["ward"]),
                          "service_date": day, "service_type": service, "visits": int(visits)})
    return clean, rejected, deleted
