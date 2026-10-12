"""Read-only acceptance checks after replication, reference sync and OIC."""
from healthlab.cloud import oracle, sql_server


def expect(label, actual, wanted):
    if actual != wanted:
        raise AssertionError(f"{label}: expected {wanted}, got {actual}")
    print(f"OK {label}: {actual}")


def main():
    with sql_server("SQLMI") as db:
        expect("Azure events", db.cursor().execute("SELECT COUNT(*) FROM dbo.health_events").fetchone()[0], 13)
    with sql_server("SYNAPSE") as db:
        expect("Synapse references", db.cursor().execute("SELECT COUNT(*) FROM dbo.facilities").fetchone()[0], 3)
    with oracle("PIPELINE_APP", "pipeline-app") as db:
        cur = db.cursor()
        for label, query, expected in [
            ("replicated revisions", "SELECT COUNT(*) FROM raw_app.health_events", 13),
            ("curated events", "SELECT COUNT(*) FROM curated_events", 6),
            ("rejects", "SELECT COUNT(*) FROM rejects", 3),
            ("total visits", "SELECT SUM(visits) FROM curated_events", 48)]:
            expect(label, cur.execute(query).fetchone()[0], expected)
        print("Latest runs:", cur.execute("SELECT run_id,accepted_count,rejected_count,deleted_count "
             "FROM pipeline_runs ORDER BY completed_at DESC FETCH FIRST 3 ROWS ONLY").fetchall())


if __name__ == "__main__":
    main()
