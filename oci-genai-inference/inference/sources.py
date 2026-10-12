import json
from pathlib import Path
from .contracts import SummaryRow, validate_rows

SAMPLE_PATH = Path(__file__).resolve().parents[1] / "data" / "ward_summary.json"
SUMMARY_SQL = """SELECT WARD, SERVICE_TYPE, VISITS, EVENT_COUNT
FROM PIPELINE_APP.WARD_SUMMARY
WHERE (:ward IS NULL OR WARD = :ward)
  AND (:service IS NULL OR SERVICE_TYPE = :service)
ORDER BY WARD, SERVICE_TYPE"""


def filter_rows(rows, plan):
    return [r for r in rows if (plan.ward is None or r.ward == plan.ward)
            and (plan.service is None or r.service_type == plan.service)]


class SampleSource:
    name = "synthetic-fixture"

    def __init__(self, path=SAMPLE_PATH):
        self.path = Path(path)

    def fetch(self, plan):
        data = json.loads(self.path.read_text())
        rows = validate_rows(SummaryRow.from_record(**row) for row in data["rows"])
        return filter_rows(rows, plan)


class ADWSource:
    name = "PIPELINE_APP.WARD_SUMMARY"

    def __init__(self, connect):
        self.connect = connect

    def fetch(self, plan):
        # Connection uses REPORT_APP, which only has SELECT on this view.
        with self.connect() as connection:
            connection.call_timeout = 10000
            with connection.cursor() as cursor:
                cursor.execute(SUMMARY_SQL, ward=plan.ward, service=plan.service)
                records = cursor.fetchmany(25)
        return validate_rows(SummaryRow.from_record(*row) for row in records)
