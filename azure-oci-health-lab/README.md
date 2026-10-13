# Azure–OCI health data lab

Azure SQL MI feeds ADW through GoldenGate. Synapse holds facility reference data, OIC triggers cleanup, and OCI GenAI summarizes the counts.

Based on the public [Tharseo/DC Health case study](https://docs.oracle.com/en/solutions/tharseo-data-platform-on-oci/index.html), with Azure, OIC, and GenAI added for this lab. Uses made-up records and no on-premises systems.

Run from this directory with Python 3.11+:

```sh
python -m healthlab.demo
python -m unittest discover -s tests -v
```

The sample produces 6 clean events and 48 visits from 13 revisions, with 3 rejects and 1 deleted event.

[Cloud setup](docs/setup.md) · [Accounts and parameters](docs/accounts.md) · [Architecture](docs/architecture.md)

Cloud setup costs money and still needs manual GoldenGate and OIC configuration. Deployment and replication have not been tested in live accounts.
