"""No cloud SDKs or credentials needed: python -m healthlab.demo."""
import argparse
import csv
import json
import sqlite3
from pathlib import Path
from .clean import clean_snapshot

ROOT = Path(__file__).resolve().parents[1]


def load_csv(name):
    with (ROOT / "data" / name).open(newline="") as stream:
        return list(csv.DictReader(stream))


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    events = load_csv("events.csv")
    facilities = {row["facility_id"]: row for row in load_csv("facilities.csv")}
    clean, rejected, deleted = clean_snapshot(events, facilities)
    with sqlite3.connect(output / "adw-demo.sqlite") as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS curated(event_id TEXT PRIMARY KEY, revision INTEGER,
            facility_id TEXT, ward INTEGER, service_date TEXT, service_type TEXT, visits INTEGER);
        CREATE TABLE IF NOT EXISTS rejects(event_id TEXT PRIMARY KEY, row_id INTEGER, reason TEXT);
        """)
        db.execute("DELETE FROM curated")
        db.execute("DELETE FROM rejects")
        db.executemany("INSERT INTO curated VALUES (:event_id,:revision,:facility_id,:ward,:service_date,:service_type,:visits)", clean)
        db.executemany("INSERT INTO rejects VALUES (:event_id,:row_id,:reason)", rejected)
        rows = db.execute("SELECT ward,service_type,SUM(visits) FROM curated GROUP BY ward,service_type ORDER BY ward,service_type").fetchall()
    result = {"source_rows": len(events), "curated_events": len(clean),
              "rejected_events": len(rejected), "deleted_events": deleted,
              "total_visits": sum(row["visits"] for row in clean),
              "aggregates": [{"ward": w, "service_type": s, "visits": v} for w, s, v in rows],
              "rejects": rejected}
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="demo-output")
    print(json.dumps(run(parser.parse_args().output), indent=2))
