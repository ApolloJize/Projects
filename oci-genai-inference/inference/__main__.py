import argparse
import json
import sys
from .cloud import Settings, connect_adw, make_planner
from .model import InferenceModel
from .planning import PreviewPlanner
from .sources import ADWSource, SampleSource


def build_model(backend, source, config=None):
    settings = Settings(config)
    planner = PreviewPlanner() if backend == "preview" else make_planner(settings)
    data = SampleSource() if source == "sample" else ADWSource(lambda: connect_adw(settings))
    return InferenceModel(planner, data)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Query the health lab's aggregate data with OCI GenAI.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--backend", choices=["preview", "oci"], default="preview")
    parser.add_argument("--source", choices=["sample", "adw"], default="sample")
    parser.add_argument("--config", help="Path to the health lab's Terraform connections JSON")
    args = parser.parse_args(argv)
    try:
        result = build_model(args.backend, args.source, args.config).predict(args.question)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ImportError:
        print("Install cloud dependencies with: pip install -r requirements.txt", file=sys.stderr)
        return 1
    except Exception as exc:
        # SDK/DB exceptions can contain connection details. Print identifiers,
        # not credentials, prompts, raw database errors or full responses.
        print(f"Cloud request failed ({type(exc).__name__}); check the profile, region, IAM grants and private connectivity.", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
