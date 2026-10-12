# Accounts, keys, and parameters

Use a dedicated Azure subscription/resource group and OCI compartment. The examples intentionally contain placeholders. No tenant IDs or private keys belong in a public commit.

## Provisioning identities

| Identity | Inputs / permissions |
| --- | --- |
| Azure operator | `azure_tenant_id`, `azure_subscription_id`; Contributor plus permission to create role assignments in the lab scope. Resource-group creation requires subscription scope. Register Microsoft.Network, Microsoft.Sql, Microsoft.Synapse, Microsoft.Storage and Microsoft.KeyVault. |
| Entra database-admin group | `azure_entra_admin_object_id`, `azure_entra_admin_name`; its members can administer SQL MI and Synapse through Entra. An Entra admin may need to grant SQL MI's system identity Directory Readers for directory lookup; see Microsoft documentation. |
| Optional Azure Terraform app | `identity/` creates application/client ID, service principal and GitHub main-branch federation. An Azure administrator assigns Contributor and User Access Administrator in the isolated lab scope. No automatic apply workflow is included. |
| OCI operator | API user OCID, tenancy OCID, API public-key fingerprint, local private-key path and profile. A tenancy admin runs the root stack initially because it creates dynamic groups and compartment policies. |
| Optional OCI API account | `identity/` creates a user/group in the Default domain and attaches an existing public API key. Keep its private key outside the repo. Its compartment policies do not grant tenancy-wide dynamic-group or identity-domain administration. |
| OIC provisioner | `oci_identity_domain_ocid`; needs permission to provision OIC in that domain, in addition to OCI integration-instance/network permissions. Domain permissions may require an identity-domain administrator. |
| Python runner | Instance principal; the exact VM OCID is in a dynamic group. Read lab Vault secrets and use GenAI in the lab compartment. Bootstrap can read database-admin secrets; reduce this policy after setup if keeping the VM. |
| GoldenGate | Deployment resource principals in a dynamic group; read lab secret bundles and use the lab Vault/key. Console login is a separate `ggadmin` account. |

For interactive Azure use, `az login --tenant <tenant-id>` and `az account set --subscription <subscription-id>` supply Terraform credentials. Automation uses `ARM_TENANT_ID`, `ARM_SUBSCRIPTION_ID`, `ARM_CLIENT_ID` plus either OIDC (`ARM_USE_OIDC=true` and a federated assertion) or `ARM_CLIENT_SECRET`. The optional identity module creates OIDC trust only; create a client secret separately only if you choose that mode.

OCI uses `config/oci-config.example` copied into `~/.oci/config`, with the private key at the referenced path and mode 600. `oci_config_profile` selects it. `oci_home_region` must match the tenancy's actual home region. `OCI_AUTH=instance_principal` is for the OCI runner; `OCI_AUTH=api_key` uses the local profile for operator scripts.

## Database and integration accounts

| Account | Secret suffix in OCI Vault | Purpose |
| --- | --- | --- |
| SQL MI `labadmin` | `azure-sql-admin` | Initial schema, CDC database preparation and sample seed |
| SQL MI `gg_reader` | `gg-source` | GoldenGate capture; database owner in this lab, not permanent server sysadmin |
| Synapse `labadmin` | `synapse-admin` | Seed/read the tiny warehouse reference table |
| ADW `ADMIN` | `adw-admin` | Create users and grants |
| ADW `GGADMIN` | `gg-target` | Apply replication to `RAW_APP.HEALTH_EVENTS` |
| ADW `RAW_APP` | `raw-app` | Own the replicated table |
| ADW `PIPELINE_APP` | `pipeline-app` | Own cleanup, curated/reference tables and audit ledger |
| ADW `OIC_APP` | `oic-app` | Execute `PIPELINE_APP.CLEAN_INGEST`; no direct table writes |
| ADW `REPORT_APP` | `report-app` | Read `PIPELINE_APP.WARD_SUMMARY` only |
| GoldenGate console `ggadmin` | `gg-admin` | Administer the two deployments |
| GoldenGate path user | Create separately in the target deployment | Operator role for source-to-target trail transport; store its credential in the source deployment's path credential store |
| OIC OAuth client | Operator-created Vault secret OCID | Confidential app in the OIC identity domain, client-credentials grant, OIC `ServiceInvoker` application role |

The generated secret name is `<prefix>-<suffix>`. Azure SQL admin secrets are also copied to Azure Key Vault. Terraform generates VPN pre-shared keys; they are not printed. No storage access key is needed by the Python pipeline: Synapse's system identity gets Storage Blob Data Contributor. Provider bootstrap may use the storage account's key internally.

Create the OIC confidential application in the same identity domain as OIC. Authorize its client-credentials grant for the OIC resource/scope, assign ServiceInvoker, activate it, and put its client secret in the lab Vault. Fill `OIC_TOKEN_URL`, `OIC_CLIENT_ID`, `OIC_SCOPE`, and `OIC_CLIENT_SECRET_OCID` from that application. Do not substitute a user password for the client secret.

## Configuration files

- `terraform/terraform.tfvars.example`: cloud IDs, regions, non-overlapping networks, operator /32, runner image/public SSH key and the GoldenGate connection gate.
- `identity/terraform.tfvars.example`: optional identity bootstrap with existing admin group members and an OCI API public key.
- `config/oci-config.example`: OCI API signing profile. There is no OCI access-key/secret-key pair for these SDK calls.
- `config/runtime.env.example`: Python auth mode, endpoints, OIC OAuth values and GenAI model/region. Most endpoints come from Terraform's `connections` output.

`GENAI_MODEL_ID` must be a currently available on-demand chat model that supports the OCI **Generic** API format in `GENAI_REGION`. Model IDs and regional availability change, so the sample does not hardcode one. Cohere-format-only models need a different request class.

Terraform state contains generated passwords and VPN keys even when fields are marked sensitive. Use an encrypted, access-controlled backend before applying, or keep local state in a protected directory for a disposable run. Never commit state, plans, `.env`, filled `.tfvars`, API private keys, wallet archives, or OIC exports containing credentials. Credential rotation requires updating the database accounts as well as Vault; bootstrap only creates missing SQL users and is not a rotation tool.
