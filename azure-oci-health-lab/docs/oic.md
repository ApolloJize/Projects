# OIC cleanup integration

Build this in Oracle Integration 3 after its outbound private endpoint is active. The repository includes request/response examples and an exact mapping, not a fabricated importable `.iar` archive. Export a real integration from your instance after binding its connections.

1. In OCI ADW, download an instance wallet with a new wallet password. Keep the archive outside the repository. The OIC ADW adapter can use mTLS even though Python/GoldenGate use server-authenticated TLS. Configure the **Oracle Autonomous Data Warehouse** connection in OIC using the wallet, its service name, `OIC_APP`, and the `<prefix>-oic-app` Vault password. Choose **Private endpoint** for access. Test the connection. The OCI NSG allows 1522 and 1521 inside the private subnet.
2. Create an application integration with identifier `HEALTH_PROMOTE`, version `1.0.0`. Add a REST trigger: POST `/promote`, JSON request/response. Use [request.json](../oic/request.json) and [response.json](../oic/response.json) as samples. Use `run_id` as the business identifier and require a nonempty value of at most 64 characters.
3. Add an ADW invoke using **Invoke a Stored Procedure**. Select schema `PIPELINE_APP`, package `CLEAN_INGEST`, procedure `PROMOTE`. OIC_APP has an explicit execute grant; refresh adapter metadata if needed.
4. Map the request to `P_RUN_ID` and the outputs to the response below. The package does the deterministic cleaning; OIC handles the trigger, mapping, invocation and fault path.

| From | To |
| --- | --- |
| REST request `run_id` | ADW `P_RUN_ID` |
| Request `run_id` | REST response `run_id` |
| ADW `P_ACCEPTED` | Response `accepted` |
| ADW `P_REJECTED` | Response `rejected` |
| ADW `P_DELETED` | Response `deleted` |

5. Add a fault handler that returns an error response and preserves the instance tracking ID. Never map a database exception to a successful response. A concurrent run can receive Oracle ORA-00054; retry later with the same run ID. The procedure commits data and its run ledger atomically, so a lost HTTP response can be retried without another refresh.
6. Activate the integration and copy its actual REST endpoint path into `OIC_INTEGRATION_PATH`. The sample path assumes identifier `HEALTH_PROMOTE`, version `1.0`, and resource `/promote`; use the endpoint shown by your instance if it differs.
7. Configure the confidential OAuth application and Vault secret in [accounts.md](accounts.md). On the runner, run `python -m scripts.promote --run-id demo-001`. Expect accepted 6, rejected 3, deleted 1 after all 13 revisions have replicated.

The REST invocation and ADW adapter connection are distinct identities: the OAuth app gets ServiceInvoker; OIC_APP gets execute on one PL/SQL package. Do not use ADW ADMIN for the adapter.

References: [OIC private endpoints](https://docs.oracle.com/en-us/iaas/application-integration/doc/private-endpoints.html), [ADW adapter guide](https://docs.oracle.com/en/cloud/paas/application-integration/adw-adapter/using-oracle-autonomous-data-warehouse-adapter-oracle-integration-3.pdf).
