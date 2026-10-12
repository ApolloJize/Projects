"""Connection helpers. Passwords are fetched from OCI Vault, never logged."""
import base64
import json
import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def settings():
    path = Path(os.getenv("LAB_CONFIG", "config.json"))
    return json.loads(path.read_text()) if path.exists() else {}


def setting(name, default=None):
    value = os.getenv(name) or settings().get(name) or default
    if not value or "REPLACE" in str(value):
        raise ValueError(f"Set {name} in the environment or config.json")
    return value


def oci_client(client_class, region=None, **kwargs):
    import oci
    region = region or setting("OCI_REGION")
    if os.getenv("OCI_AUTH", "instance_principal") == "instance_principal":
        config = {"region": region}
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        return client_class(config, signer=signer, **kwargs)
    config = oci.config.from_file(profile_name=os.getenv("OCI_CONFIG_PROFILE", "HEALTHLAB"))
    config["region"] = region
    return client_class(config, **kwargs)


@lru_cache(maxsize=32)
def secret(name=None, ocid=None):
    import oci
    client = oci_client(oci.secrets.SecretsClient)
    if ocid:
        bundle = client.get_secret_bundle(ocid).data
    else:
        bundle = client.get_secret_bundle_by_name(
            secret_name=f"{setting('SECRET_PREFIX')}-{name}",
            vault_id=setting("OCI_VAULT_OCID")).data
    return base64.b64decode(bundle.secret_bundle_content.content).decode("utf-8")


def oracle(user, password_name):
    import oracledb
    return oracledb.connect(user=user, password=secret(password_name), dsn=setting("ADW_DSN"))


def sql_server(kind, database=None):
    import pyodbc
    if kind not in ("SQLMI", "SYNAPSE"):
        raise ValueError("kind must be SQLMI or SYNAPSE")
    # Escape ODBC values, including closing braces in credentials.
    def value(text):
        return "{" + str(text).replace("}", "}}") + "}"
    password = secret("azure-sql-admin" if kind == "SQLMI" else "synapse-admin")
    fields = {"DRIVER": "ODBC Driver 18 for SQL Server", "SERVER": setting(f"{kind}_HOST") + ",1433",
              "DATABASE": database or setting(f"{kind}_DATABASE"), "UID": "labadmin", "PWD": password,
              "Encrypt": "yes", "TrustServerCertificate": "no", "Connection Timeout": "30"}
    return pyodbc.connect(";".join(f"{k}={value(v)}" for k, v in fields.items()), autocommit=True)
