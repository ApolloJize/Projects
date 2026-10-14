# Model notes

`InferenceModel.predict(question)` asks OCI GenAI for an `operation`, `ward`, and `service`. Python validates the plan, reads `WARD_SUMMARY` with bound filters, and calculates the answer. The result includes the plan, metrics, and source rows. Generated SQL or code never runs.

Supported questions cover totals, comparisons by ward/service, and the busiest ward. Ties are kept. Missing rows return `no_data`, not zero; duplicate or invalid aggregates are rejected. The hosted model sees the question and schema instructions, not database records.

The small summary view doesn't need embeddings. This uses pretrained weights with no fine-tuning. `PreviewPlanner` is a local rule set for a few question patterns. Preview tests check those rules; they don't measure a hosted model's accuracy.

Malformed JSON, extra keys, invalid filters, and unsupported operations are rejected. A valid plan can still misinterpret a question, so check the returned plan. The small evaluation set isn't an accuracy benchmark.

Dates, trends, forecasts, rates, multiple ward/service selections, and patient-level questions aren't supported. These are synthetic service counts, not unique patients. `checked_at_utc` is the request time, not the data's observation date.

The CLI makes at most one model call, disables automatic retries, caps output at 180 tokens, and returns an OCI `request_id`. Tests mock cloud calls; live OCI/ADW execution still needs checking.

References: [OCI chat client](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/generative_ai_inference/client/oci.generative_ai_inference.GenerativeAiInferenceClient.html), [Generic chat request](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/generative_ai_inference/models/oci.generative_ai_inference.models.GenericChatRequest.html), [Oracle bind variables](https://python-oracledb.readthedocs.io/en/latest/user_guide/bind.html).
