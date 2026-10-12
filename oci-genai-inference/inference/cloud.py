"""Reuse the first project's endpoints, Vault secret and REPORT_APP account."""
import base64
import json
import os
from pathlib import Path
from .planning import OCIPlanner


class Settings:
    def __init__(self, config_path=None, environ=None):
        values = json.loads(Path(config_path).read_text()) if config_path else {}
        if not isinstance(values, dict):
            raise ValueError("Config file must contain a JSON object")
        self.values = values | dict(os.environ if environ is None else environ)

    def get(self, name, default=None):
        return self.values.get(name) or default

    def require(self, name):
        value = self.get(name)
        if not isinstance(value, str) or not value.strip() or "REPLACE" in value:
            raise ValueError(f"Set {name} in the environment or config JSON")
        return value


def client(settings, client_class, region):
    import oci
    auth = settings.get("OCI_AUTH", "api_key")
    kwargs = {"timeout": (10, 60)}
    if auth == "instance_principal":
        config = {"region": region}
        kwargs["signer"] = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    elif auth == "api_key":
        config = oci.config.from_file(profile_name=settings.get("OCI_CONFIG_PROFILE", "HEALTHLAB"))
        config["region"] = region
    else:
        raise ValueError("OCI_AUTH must be api_key or instance_principal")
    return client_class(config, **kwargs)


def make_planner(settings):
    import oci
    region = settings.require("GENAI_REGION")
    compartment = settings.require("OCI_COMPARTMENT_OCID")
    model = settings.require("GENAI_MODEL_ID")
    return OCIPlanner(client(settings, oci.generative_ai_inference.GenerativeAiInferenceClient, region),
                      compartment, model)


def connect_adw(settings):
    import oci
    import oracledb
    dsn = settings.require("ADW_DSN")
    vault_id = settings.require("OCI_VAULT_OCID")
    secret_name = settings.require("SECRET_PREFIX") + "-report-app"
    secrets = client(settings, oci.secrets.SecretsClient, settings.require("OCI_REGION"))
    bundle = secrets.get_secret_bundle_by_name(secret_name=secret_name, vault_id=vault_id).data
    password = base64.b64decode(bundle.secret_bundle_content.content, validate=True).decode("utf-8")
    return oracledb.connect(user="REPORT_APP", password=password, dsn=dsn, tcp_connect_timeout=10)
