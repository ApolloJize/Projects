# OCI GenAI inference

Ask questions about the [health lab](../azure-oci-health-lab). An OCI chat model interprets the question; Python queries ADW and calculates the answer.

Run from this directory with Python 3.11+:

```sh
python -m inference --question "Which ward had the most outreach visits?"
python -m unittest discover -s tests -v
```

This returns **ward 7, 23 visits**. The offline preview uses rules and made-up data; it doesn't call an AI model.

For a pretrained OCI model and the existing ADW, follow [setup](docs/setup.md). No training or new infrastructure is needed. Live OCI/ADW execution hasn't been tested; cloud calls are mocked in tests. [Model notes](docs/model.md) cover the supported questions.
