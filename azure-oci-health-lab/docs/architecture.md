# How it fits together

GoldenGate copies event revisions from Azure SQL Managed Instance to ADW's raw table. A Python script copies facility references from Synapse. OIC calls `CLEAN_INGEST` to build the curated snapshot, then Python sends ward/service counts to GenAI.

The [DC Health reference](references.md) uses GoldenGate, an Oracle staging database, ADW, and OCI Data Integration. This lab stages directly in ADW and adds Azure, OIC, and GenAI. It uses commercial regions and has no on-premises sources. SQL MI is the CDC source; Synapse reference data uses the separate Python copy.

## Network

Azure `10.50.0.0/16` and OCI `10.60.0.0/16` connect over two static-route IPSec tunnels. SQL MI uses its private endpoint in Proxy mode on port 1433; Synapse uses a SQL private endpoint. OCI forwards Azure database DNS lookups to Azure Private DNS Resolver over the VPN.

ADW, both GoldenGate deployments, the runner, and OIC's outbound endpoint use a private OCI subnet. Python and GoldenGate use ADW TLS; OIC can use an mTLS wallet. Both verify certificates. Bastion provides temporary access to the runner, which has no public IP.

OIC's REST endpoint is public, restricted to the operator and OCI NAT IPs. The OCI service subnet allows outbound traffic. Synapse's ADLS account has an authenticated public endpoint and holds no sample records. A larger deployment would need tighter egress, separate service subnets, and ADLS private endpoints.

## Data rules

`row_id` identifies an immutable revision. The latest `(revision, row_id)` wins for each `event_id`, even when it is invalid. Cleanup normalizes categories, checks dates/counts, joins facilities, and records rejects. A tombstone removes an event; a newer valid revision restores it.

Cleanup rebuilds the snapshot atomically. A lock serializes cleanup and reference updates; repeating a `run_id` returns the original result. Use a new ID for a new snapshot. The SQLite demo checks these rules locally, without emulating GoldenGate or OIC. Full refresh is only intended for this small dataset.

GenAI receives aggregate counts from a fixed view, never raw records or control over SQL. The records are synthetic service counts, unsuitable for medical conclusions or population rates.
