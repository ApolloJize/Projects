# Model notes

`InferenceModel.predict(question)` has three parts:

1. OCI GenAI predicts `operation`, `ward`, and `service` from the question.
2. Python validates that plan and reads one fixed SQL view with bound filter values.
3. Python calculates the result and returns an answer, metrics, the interpreted plan, and source rows.

Supported operations are totals, comparisons by ward/service, and busiest ward. The model handles question interpretation; arithmetic and answer formatting are deterministic. No model-generated SQL, Python, or tool calls execute. The hosted model receives the question and the schema instructions, not database records. The complete evidence packet stays in the returned local result.

The existing lab's `WARD_SUMMARY` view is small, so this uses structured retrieval rather than embeddings or a vector database. It expects at most one row per ward/service and rejects duplicate or invalid aggregates. Ties are retained. Missing rows return `no_data`; they aren't treated as zero.

This is an inference application using pretrained weights, with no custom training/fine-tuning. `PreviewPlanner` is an explicitly labelled offline rule set for a few sentence patterns. It provides reproducible demos and regression tests, not AI quality measurements.

Plans with unexpected keys, invalid filters, malformed JSON, or an unsupported operation are rejected. The model can still misunderstand a question while returning a valid plan; the returned plan makes that interpretation inspectable. The evaluation set is a small starting check, not a benchmark or accuracy claim.

Dates, trends, forecasts, rates, multiple simultaneous ward/service filters, and patient-level questions are outside the contract. These are synthetic service counts, not unique patients. `checked_at_utc` records when the request was processed; it is not the source data's observation date or freshness guarantee.

The CLI issues at most one inference call per request, disables automatic model-call retries, and caps the response at 180 tokens. It returns `request_id` for OCI tracing. Neither unit tests nor CI call real cloud services. End-to-end OCI/ADW behavior must be checked with the configured tenancy.

Sources: [OCI chat client](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/generative_ai_inference/client/oci.generative_ai_inference.GenerativeAiInferenceClient.html), [Generic chat request](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/generative_ai_inference/models/oci.generative_ai_inference.models.GenericChatRequest.html), [Oracle bind variables](https://python-oracledb.readthedocs.io/en/latest/user_guide/bind.html).
