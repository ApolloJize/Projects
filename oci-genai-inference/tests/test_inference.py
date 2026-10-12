import json
import tempfile
import unittest
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock
from evaluate import evaluate
from inference.cloud import Settings
from inference.contracts import PlanError, QueryPlan, SummaryRow, validate_rows
from inference.model import InferenceModel, calculate
from inference.planning import Prediction, PreviewPlanner
from inference.sources import ADWSource, SampleSource, SUMMARY_SQL


class InferenceTests(unittest.TestCase):
    def setUp(self):
        self.model = InferenceModel(PreviewPlanner(), SampleSource())

    def test_total_and_evidence(self):
        result = self.model.predict("How many visits are there?")
        self.assertEqual(result["metrics"], {"total_visits": 48, "event_count": 6})
        self.assertEqual(len(result["evidence"]), 3)
        self.assertEqual(result["model_id"], "preview-rules")

    def test_service_filter_and_top_ward(self):
        result = self.model.predict("Which ward had the most outreach visits?")
        self.assertEqual(result["plan"]["service"], "OUTREACH")
        self.assertEqual(result["metrics"]["busiest_wards"], [7])
        self.assertEqual(result["metrics"]["highest_visits"], 23)
        self.assertEqual(result["evidence"][0]["id"], "ward-7-outreach")

    def test_ward_filter(self):
        result = self.model.predict("Compare visits by service in ward 4.")
        self.assertEqual(result["metrics"]["by_service"], [{"service": "IMMUNIZATION", "visits": 9}])

    def test_ties_are_preserved(self):
        rows = [SummaryRow(1, "SCREENING", 5, 1), SummaryRow(4, "OUTREACH", 5, 1)]
        result = calculate(QueryPlan("busiest_ward"), rows)
        self.assertEqual(result["metrics"]["busiest_wards"], [1, 4])
        self.assertIn("tied", result["answer"])

    def test_missing_data_is_not_zero(self):
        absent = self.model.predict("How many visits are there in ward 8?")
        self.assertEqual(absent["status"], "no_data")
        self.assertEqual(absent["metrics"], {})
        zero = calculate(QueryPlan("total_visits"), [SummaryRow(8, "SCREENING", 0, 1)])
        self.assertEqual(zero["status"], "answered")
        self.assertEqual(zero["metrics"]["total_visits"], 0)

    def test_unsupported_request_does_not_read_database(self):
        source = MagicMock(name="source")
        source.name = "spy"
        result = InferenceModel(PreviewPlanner(), source).predict("Predict next month's visits.")
        self.assertEqual(result["status"], "unsupported")
        source.fetch.assert_not_called()

    def test_plan_rejects_injection_and_wrong_types(self):
        for bad in [
            {"operation": "DROP TABLE", "ward": None, "service": None},
            {"operation": "total_visits", "ward": "1 OR 1=1", "service": None},
            {"operation": "total_visits", "ward": True, "service": None},
            {"operation": "total_visits", "ward": 9, "service": None},
            {"operation": "total_visits", "ward": None, "service": "OUTREACH; DELETE"},
            {"operation": "total_visits", "ward": None, "service": []},
            {"operation": "total_visits", "ward": None, "service": None, "sql": "SELECT *"},
        ]:
            with self.subTest(bad=bad), self.assertRaises(PlanError):
                QueryPlan.parse(json.dumps(bad))

    def test_malformed_duplicate_or_fenced_json_rejected(self):
        for text in ["not json", "[]", '{"operation":"total_visits","operation":"unsupported","ward":null,"service":null}',
                     '```json\n{"operation":"total_visits","ward":null,"service":null}\n```']:
            with self.subTest(text=text), self.assertRaises(PlanError):
                QueryPlan.parse(text)

    def test_duplicate_or_negative_aggregates_rejected(self):
        row = SummaryRow(1, "SCREENING", 1, 1)
        with self.assertRaises(ValueError):
            validate_rows([row, row])
        with self.assertRaises(ValueError):
            SummaryRow(1, "SCREENING", -1, 1)
        with self.assertRaises(ValueError):
            SummaryRow.from_record(1, "SCREENING", Decimal("1.5"), 1)
        self.assertEqual(SummaryRow.from_record(Decimal(1), "SCREENING", Decimal(2), 1).visits, 2)

    def test_adw_query_is_fixed_with_bound_filters(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchmany.return_value = [(4, "IMMUNIZATION", 9, 2)]
        result = ADWSource(lambda: connection).fetch(QueryPlan("total_visits", 4, "IMMUNIZATION"))
        cursor.execute.assert_called_once_with(SUMMARY_SQL, ward=4, service="IMMUNIZATION")
        self.assertEqual(result[0].visits, 9)
        self.assertNotIn("9", SUMMARY_SQL)

    def test_question_length(self):
        for question in ["", "   ", "x" * 1001]:
            with self.assertRaises(ValueError):
                self.model.predict(question)

    def test_settings_precedence_and_missing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text('{"SECRET_PREFIX":"old","OCI_REGION":"us-ashburn-1"}')
            settings = Settings(path, {"SECRET_PREFIX": "healthlab"})
            self.assertEqual(settings.require("SECRET_PREFIX"), "healthlab")
            self.assertEqual(settings.require("OCI_REGION"), "us-ashburn-1")
            with self.assertRaises(ValueError):
                settings.require("GENAI_MODEL_ID")

    def test_preview_regression_cases(self):
        path = Path(__file__).resolve().parents[1] / "data" / "eval_cases.json"
        result = evaluate(PreviewPlanner(), json.loads(path.read_text()))
        self.assertEqual(result["passed"], 10)


if __name__ == "__main__":
    unittest.main()
