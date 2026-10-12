"""Create empty source/reference/ADW schemas; seed only after CDC is running."""
import re
from pathlib import Path
from healthlab.cloud import oracle, secret, sql_server

ROOT = Path(__file__).resolve().parents[1]


def ddl_password(value):
    # These DDL positions cannot use bind variables. Accept only Terraform's
    # generated password alphabet; never interpolate arbitrary user input.
    if not re.fullmatch(r"[A-Za-z0-9_#]{20,128}", value):
        raise ValueError("Unexpected generated password alphabet")
    return value


def sql_batches(cursor, path):
    for batch in re.split(r"(?im)^GO\s*$", path.read_text()):
        batch = re.sub(r"(?m)^\s*--.*$", "", batch).strip()
        if batch:
            cursor.execute(batch)


def oracle_file(connection, name):
    import oracledb
    with connection.cursor() as cur:
        for statement in re.split(r"(?m)^/\s*$", (ROOT / "sql" / name).read_text()):
            statement = statement.strip()
            if not statement:
                continue
            try:
                cur.execute(statement)
            except oracledb.DatabaseError as exc:
                if exc.args[0].code != 955:  # table already exists on a rerun
                    raise
        cur.execute("SELECT name, line, text FROM user_errors ORDER BY name, sequence")
        errors = cur.fetchall()
        if errors:
            raise RuntimeError(f"Oracle compilation errors: {errors}")
    connection.commit()


def main():
    with sql_server("SQLMI", "master") as db:
        cur = db.cursor()
        password = ddl_password(secret("gg-source"))
        cur.execute("IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name='gg_reader') "
                    f"CREATE LOGIN gg_reader WITH PASSWORD='{password}';")
        cur.execute("GRANT VIEW SERVER STATE TO gg_reader;")
    with sql_server("SQLMI") as db:
        cur = db.cursor()
        sql_batches(cur, ROOT / "sql/source.sql")
        cur.execute("IF USER_ID('gg_reader') IS NULL CREATE USER gg_reader FOR LOGIN gg_reader;")
        cur.execute("ALTER ROLE db_owner ADD MEMBER gg_reader;")
    with sql_server("SYNAPSE") as db:
        sql_batches(db.cursor(), ROOT / "sql/synapse.sql")
    with oracle("ADMIN", "adw-admin") as db:
        cur = db.cursor()
        for user in ("RAW_APP", "PIPELINE_APP", "OIC_APP", "REPORT_APP"):
            password = ddl_password(secret(user.lower().replace("_", "-")))
            cur.execute("SELECT COUNT(*) FROM all_users WHERE username=:1", [user])
            if not cur.fetchone()[0]:
                cur.execute(f'CREATE USER {user} IDENTIFIED BY "{password}"')
            cur.execute(f"GRANT CREATE SESSION TO {user}")
        for user in ("RAW_APP", "PIPELINE_APP"):
            cur.execute(f"GRANT CREATE TABLE, CREATE VIEW, CREATE PROCEDURE TO {user}")
            cur.execute(f"ALTER USER {user} QUOTA 100M ON DATA")
        cur.execute(f'ALTER USER GGADMIN IDENTIFIED BY "{ddl_password(secret("gg-target"))}" ACCOUNT UNLOCK')
    with oracle("RAW_APP", "raw-app") as db:
        oracle_file(db, "raw.sql")
        db.cursor().execute("GRANT SELECT ON HEALTH_EVENTS TO PIPELINE_APP")
        db.cursor().execute("GRANT SELECT, INSERT, UPDATE, DELETE ON HEALTH_EVENTS TO GGADMIN")
    with oracle("PIPELINE_APP", "pipeline-app") as db:
        oracle_file(db, "pipeline.sql")
        db.cursor().execute("GRANT EXECUTE ON CLEAN_INGEST TO OIC_APP")
        db.cursor().execute("GRANT SELECT ON WARD_SUMMARY TO REPORT_APP")
    print("Schemas ready. Configure GoldenGate TRANDATA and start capture before seeding.")


if __name__ == "__main__":
    main()
