"""Load checked-in synthetic records into Azure. Never writes ADW raw rows."""
from healthlab.cloud import sql_server
from healthlab.demo import load_csv


def main():
    with sql_server("SYNAPSE") as db:
        # Dedicated pools don't enforce uniqueness; replace this tiny snapshot.
        db.autocommit = False
        cur = db.cursor()
        cur.execute("DELETE FROM dbo.facilities")
        cur.executemany("INSERT INTO dbo.facilities VALUES (?,?,?)", [
            (r["facility_id"], r["facility_name"], int(r["ward"])) for r in load_csv("facilities.csv")])
        db.commit()
    with sql_server("SQLMI") as db:
        db.autocommit = False
        cur = db.cursor()
        for r in load_csv("events.csv"):
            values = (int(r["row_id"]), r["event_id"], int(r["revision"]), r["facility_id"],
                      r["service_date"], r["service_type"], r["visits"], r["is_deleted"], r["updated_at"])
            cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.health_events WHERE row_id=?) "
                        "INSERT INTO dbo.health_events VALUES (?,?,?,?,?,?,?,?,?)", int(r["row_id"]), *values)
        db.commit()
    print("Azure seeded: 3 facilities, 13 event revisions. Wait for GoldenGate lag to reach zero.")


if __name__ == "__main__":
    main()
