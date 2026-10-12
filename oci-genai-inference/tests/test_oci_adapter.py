import importlib.util
import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from inference.contracts import PlanError
from inference.model import InferenceModel
from inference.planning import OCIPlanner


@unittest.skipUnless(importlib.util.find_spec("oci"), "Install requirements.txt for OCI SDK contract tests")
class OCIAdapterTests(unittest.TestCase):
    def client(self, text):
        response = SimpleNamespace(
            data=SimpleNamespace(chat_response=SimpleNamespace(api_format="GENERIC", choices=[
                SimpleNamespace(message=SimpleNamespace(content=[SimpleNamespace(type="TEXT", text=text)]))])),
            headers={"opc-request-id": "mock-request-id"})
        client = MagicMock()
        client.chat.return_value = response
        return client

    def test_real_sdk_request_with_mock_transport(self):
        import oci
        client = self.client('{"operation":"total_visits","ward":4,"service":null}')
        planner = OCIPlanner(client, "ocid1.compartment.oc1..REPLACE", "sample-model")
        prediction = planner.predict("How many visits are there in ward 4?")
        request = oci.util.to_dict(client.chat.call_args.args[0])
        self.assertEqual(request["serving_mode"]["model_id"], "sample-model")
        self.assertEqual(request["chat_request"]["api_format"], "GENERIC")
        self.assertEqual([m["role"] for m in request["chat_request"]["messages"]], ["SYSTEM", "USER"])
        self.assertEqual(request["chat_request"]["max_tokens"], 180)
        self.assertEqual(prediction.plan.ward, 4)
        self.assertEqual(prediction.request_id, "mock-request-id")
        self.assertNotIn("48", json.dumps(request))  # the planner receives no database rows

    def test_invalid_model_output_does_not_reach_database(self):
        source = MagicMock()
        planner = OCIPlanner(self.client("DROP TABLE health_events"), "compartment", "model")
        with self.assertRaises(PlanError):
            InferenceModel(planner, source).predict("How many visits are there?")
        source.fetch.assert_not_called()

    def test_cloud_error_has_no_preview_fallback(self):
        client = self.client("unused")
        client.chat.side_effect = RuntimeError("service unavailable")
        with self.assertRaises(RuntimeError):
            OCIPlanner(client, "compartment", "model").predict("How many visits are there?")


if __name__ == "__main__":
    unittest.main()
