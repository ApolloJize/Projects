# Cloud setup

This has not been applied to live Azure/OCI accounts. It is a provisionable starting point with explicit service-configuration steps, not a prevalidated customer deployment. Allow time for SQL MI and the VPN gateway to provision. Check region support and quotas for all SKUs first.

SQL MI, Synapse dedicated SQL pool, two GoldenGate deployments, ADW, OIC, the VPN gateway, private DNS resolver and runner are billable. An empty database does not stop those charges.

## 1. Authenticate and fill the parameters

Install Terraform 1.12.2, Azure CLI, OCI CLI, Python 3.11+, and Git. Use [accounts.md](accounts.md) for identities and permissions. `identity/` is optional if accounts already exist. Select a regional Ubuntu 22.04 x86_64 image for the runner and supply only your SSH public key.

From `azure-oci-health-lab/`:

```sh
umask 077
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit placeholders, and set up ~/.oci/config using config/oci-config.example.
az login --tenant YOUR_TENANT_ID
az account set --subscription YOUR_SUBSCRIPTION_ID
terraform -chdir=terraform init
terraform -chdir=terraform plan -out=lab.tfplan
terraform -chdir=terraform apply lab.tfplan
terraform -chdir=terraform output -json connections > config.json
terraform -chdir=terraform output access
```

Keep `enable_gg_connections=false` on this first apply. The Terraform machine's outbound IP must match `operator_cidr` for Azure Key Vault data-plane writes. Provider downloads need internet access. Use a protected backend for durable state; do not upload the plan.

If OCI's asynchronously created DNS resolver association is still `PROVISIONING`, wait for it to become `AVAILABLE` and rerun the plan/apply. IAM policy propagation can also take time. Do not turn off TLS validation to get past a connection failure.

## 2. Set up the OIC outbound endpoint

On the operator machine:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export OCI_AUTH=api_key OCI_CONFIG_PROFILE=HEALTHLAB
python -m scripts.configure_oic_endpoint
```

The pinned Terraform provider exposes this endpoint as read-only, so the script uses OCI's supported `change_private_endpoint_outbound_connection` API. Wait for the reported work request to succeed. The provider manages OIC itself; the script owns this one endpoint lifecycle.

## 3. Reach the private runner

Open the provisioned OCI Bastion, create a **port forwarding** session to the runner's private IP, TCP 22, and provide your SSH public key. Use the SSH command shown on the session page. Connect through its local forwarded port as `ubuntu`.

Clone this repository onto the runner and securely copy only `config.json` there. Run `bash scripts/install_runner.sh`, create a Python venv, and install `requirements.txt`. Use `OCI_AUTH=instance_principal`; no OCI API private key is needed on the VM. Check that SQL MI and Synapse names resolve to private addresses, Azure VPN connections are connected, and TCP 1433 is reachable before database bootstrap. The operator browser can reach private GoldenGate consoles through an SSH SOCKS tunnel on this runner, using remote DNS in the proxy settings.

```sh
export OCI_AUTH=instance_principal
python -m scripts.bootstrap_cloud
```

This creates empty source/raw tables, Synapse reference table, ADW schemas, grants, and the cleanup package. It enables database CDC but leaves table-level GoldenGate setup to the next step. `USER_ERRORS` is checked for PL/SQL compilation errors.

## 4. Connect GoldenGate, then start CDC

On the operator machine, set `enable_gg_connections=true` in the tfvars file and run a new plan/apply. Follow [goldengate.md](goldengate.md) to configure TRANDATA, the purge task, Extract, distribution path, and Replicat. Do this while both source and raw event tables are empty. If you already seeded them, an initial-load/CDC synchronization plan is required; do not assume a current-time Extract backfills existing data.

## 5. Seed Azure and load the reference data

On the private runner, after capture and apply are running:

```sh
python -m scripts.seed_azure
python -m scripts.sync_reference
```

The seed command writes only to Azure: 13 event revisions in SQL MI and 3 facility rows in Synapse. GoldenGate must deliver the events to ADW. Wait until ADW `RAW_APP.HEALTH_EVENTS` has 13 rows and GoldenGate reports no lag/abends.

## 6. Bind and activate OIC

Follow [oic.md](oic.md). Create the ADW adapter connection, REST-trigger integration, and OAuth client. Copy `config/runtime.env.example` to `.env`, fill the OIC OAuth values, and select the GenAI model/region. Keep the endpoint/OCID values in `config.json`; environment values override them, so remove unused `REPLACE` lines from `.env`.

```sh
set -a
. ./.env
set +a
python -m scripts.promote --run-id demo-001
python -m scripts.check_cloud
python -m scripts.genai_summary
```

Reusing `demo-001` is safe for a retry. Use `demo-002` after new events arrive. Expected acceptance results: raw 13, curated 6, rejects 3, total visits 48. The generated summary must be checked against the printed aggregate evidence.

## 7. Teardown

Deactivate the OIC integration and stop Extract/Replicat. On the operator machine, with the same `config.json` and API profile, run `python -m scripts.configure_oic_endpoint --remove`; wait for completion. End active Bastion sessions. Then review `terraform -chdir=terraform plan -destroy` and run `terraform -chdir=terraform destroy`. Destroy the optional identity stack last if those accounts are no longer needed.

OCI Vault secret/key deletion can involve a scheduled deletion window. Azure Key Vault uses soft delete. Inspect both cloud consoles for retained resources after Terraform finishes. Keep protected state until teardown and scheduled deletions are resolved.
