# OCI GenAI inference

Ask simple questions about the [Azure–OCI health lab](../azure-oci-health-lab). An OCI chat model interprets the question, then Python reads ADW's summary view and returns counts with the rows used to calculate them.

Try the offline preview with Python 3.11+:

```sh
python -m inference --question "Which ward had the most outreach visits?"
python -m unittest discover -s tests -v
```

The sample returns **ward 7, 23 visits**. Preview mode uses a small rule set and synthetic data; it makes no model calls.

For real inference, install `requirements.txt`, configure OCI, and run:

```sh
python -m inference --backend oci --source adw \
  --config ../azure-oci-health-lab/config.json \
  --question "How many visits are there in ward 4?"
```

[Setup](docs/setup.md) · [Model notes](docs/model.md)

Uses a pretrained OCI model. No training or new cloud infrastructure is required. Live OCI/ADW execution needs your configured account; local and CI tests use a mock cloud transport.
