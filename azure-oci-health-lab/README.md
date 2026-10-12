# Azure–OCI health data lab

A small cross-cloud ingestion lab: Azure SQL Managed Instance → GoldenGate → ADW. Synapse holds facility reference data, OIC runs the cleanup procedure, and OCI GenAI summarizes the resulting counts.

Inspired by the public [Tharseo/DC Health architecture](https://docs.oracle.com/en/solutions/tharseo-data-platform-on-oci/index.html). Azure, OIC, and GenAI are additions here. All records are made up; there is no on-premises component.

Try the data flow locally with Python 3.11+:

```sh
python -m healthlab.demo
python -m unittest discover -s tests -v
```

Expected: 13 source revisions, 6 clean events, 3 rejects, 1 deleted event, 48 visits.

[Cloud setup](docs/setup.md) · [Accounts and parameters](docs/accounts.md) · [Architecture](docs/architecture.md)

Terraform provisions the cloud resources. GoldenGate process setup and the OIC integration still need the steps in the setup guide. Cloud deployment and end-to-end replication have not been tested against live accounts. The cloud stack is a paid lab.
