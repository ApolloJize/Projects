"""Copy the small Synapse reference table to ADW; keep CDC separate."""
from healthlab.cloud import oracle, sql_server


def main():
    with sql_server("SYNAPSE") as source:
        rows = [tuple(r) for r in source.cursor().execute(
            "SELECT facility_id,facility_name,ward FROM dbo.facilities").fetchall()]
    if len({r[0] for r in rows}) != len(rows) or any(not 1 <= r[2] <= 8 for r in rows):
        raise ValueError("Invalid or duplicate facility reference rows")
    with oracle("PIPELINE_APP", "pipeline-app") as target:
        cur = target.cursor()
        cur.execute("SELECT id FROM pipeline_lock WHERE id=1 FOR UPDATE NOWAIT")
        cur.executemany("""MERGE INTO facilities t USING
          (SELECT :1 facility_id,:2 facility_name,:3 ward FROM dual) s
          ON (t.facility_id=s.facility_id)
          WHEN MATCHED THEN UPDATE SET t.facility_name=s.facility_name,t.ward=s.ward
          WHEN NOT MATCHED THEN INSERT VALUES(s.facility_id,s.facility_name,s.ward)""", rows)
        target.commit()
    print(f"Synced {len(rows)} facility references. This lab upserts; retirement is a separate workflow.")


if __name__ == "__main__":
    main()
