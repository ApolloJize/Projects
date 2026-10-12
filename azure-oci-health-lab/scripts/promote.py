"""Invoke the activated OIC REST integration; reuse run-id when retrying."""
import argparse
import requests
from healthlab.cloud import setting, secret


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not 1 <= len(args.run_id) <= 64:
        parser.error("run-id must contain 1 to 64 characters")
    token = requests.post(setting("OIC_TOKEN_URL"),
        auth=(setting("OIC_CLIENT_ID"), secret(ocid=setting("OIC_CLIENT_SECRET_OCID"))),
        data={"grant_type": "client_credentials", "scope": setting("OIC_SCOPE")}, timeout=30)
    token.raise_for_status()
    response = requests.post(setting("OIC_BASE_URL").rstrip("/") + setting("OIC_INTEGRATION_PATH"),
        headers={"Authorization": "Bearer " + token.json()["access_token"]},
        json={"run_id": args.run_id}, timeout=120)
    response.raise_for_status()
    print(response.text)


if __name__ == "__main__":
    main()
