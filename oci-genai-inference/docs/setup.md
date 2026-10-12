# Setup

## Local preview

Run commands from `oci-genai-inference/`. Python 3.11+ is enough for preview mode; it does not need Oracle credentials or cloud packages.

```sh
python -m inference --question "How many visits are there?"
python -m inference --question "Compare visits by ward."
python -m inference --question "Compare visits by service in ward 4."
python evaluate.py
```

The fixture matches the first project's seeded/cleaned snapshot: 48 visits across six events. Evaluation in preview mode checks the demo's rules, not a hosted model's accuracy.

## OCI model with the sample fixture

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config/runtime.env.example .env
# Fill the model/region and choose your auth mode, then:
set -a
. ./.env
set +a
python -m inference --backend oci --source sample \
  --config ../azure-oci-health-lab/config.json \
  --question "Which ward had the most outreach visits?"
```

Use OCI Generative AI's model catalog/playground to choose an available **on-demand model with Generic chat format** in your selected region. Copy its model ID into `GENAI_MODEL_ID` and the region into `GENAI_REGION`. Model availability changes, so there is no hardcoded default model. This adapter doesn't use Cohere-format requests or provision a dedicated cluster.

For an operator machine use `OCI_AUTH=api_key` and the first project's `~/.oci/config` profile `HEALTHLAB`. On its OCI runner use `OCI_AUTH=instance_principal`. The calling principal needs `use generative-ai-family` in the lab compartment; the first project's runner already has that policy. An operator's API group may need the equivalent grant from an administrator.

## Connect the existing ADW

Finish the first project's cloud setup and OIC promotion first. Export its connection settings if needed:

```sh
umask 077
terraform -chdir=../azure-oci-health-lab/terraform output -json connections \
  > ../azure-oci-health-lab/config.json
python -m inference --backend oci --source adw \
  --config ../azure-oci-health-lab/config.json \
  --question "How many visits are there in ward 4?"
```

Run this from the existing private OCI runner or a host with the same ADW network access. The connection uses ADW `REPORT_APP`, reads its `<prefix>-report-app` password from OCI Vault, and queries only `PIPELINE_APP.WARD_SUMMARY`. There are no schema changes. The selected principal also needs permission to read that Vault secret. TLS uses the existing ADW connection descriptor; no new access key or database administrator password is needed.

| Setting | Source |
| --- | --- |
| `OCI_COMPARTMENT_OCID` | Existing Terraform output; compartment for inference calls |
| `OCI_REGION`, `OCI_VAULT_OCID`, `SECRET_PREFIX`, `ADW_DSN` | Existing Terraform output; ADW/Vault access |
| `GENAI_REGION`, `GENAI_MODEL_ID` | Regional model catalog |
| `OCI_AUTH` | `api_key` on the operator machine; `instance_principal` on the runner |
| `OCI_CONFIG_PROFILE` | Local API signing profile; defaults to `HEALTHLAB` |

Environment values override the JSON config. `.env` is sourced explicitly and is gitignored. Keep filled configuration and private keys outside source control.

## Check a real model

```sh
python evaluate.py --backend oci --config ../azure-oci-health-lab/config.json
```

This makes **10 paid inference requests**, one per question, and reports exact query-plan matches. It doesn't read ADW. Review any incorrectly interpreted question before relying on that model. CI never runs this cloud evaluation.

## Python use

```python
from inference import InferenceModel
from inference.cloud import Settings, connect_adw, make_planner
from inference.sources import ADWSource

settings = Settings("../azure-oci-health-lab/config.json")
model = InferenceModel(make_planner(settings), ADWSource(lambda: connect_adw(settings)))
result = model.predict("Which ward had the most outreach visits?")
print(result["answer"])
```

If you receive a model-format error, choose a Generic chat model. If the plan is rejected, inspect the question/model configuration and rerun; invalid output never falls back to a fabricated cloud result. For `no_data`, check the filters and whether the first project's OIC run completed. Access/timeout errors require checking IAM, Vault and private connectivity.
