"""Create OIC's outbound private endpoint using the operator's OCI profile."""
import argparse
import oci
from healthlab.cloud import oci_client, setting


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove", action="store_true", help="Remove endpoint before Terraform destroy")
    args = parser.parse_args()
    client = oci_client(oci.integration.IntegrationInstanceClient)
    instance_id = setting("OIC_INSTANCE_OCID")
    current = client.get_integration_instance(instance_id)
    existing = current.data.private_endpoint_outbound_connection
    if args.remove:
        endpoint = oci.integration.models.NoneOutboundConnection()
    else:
        subnet, nsg = setting("OIC_SUBNET_OCID"), setting("OIC_NSG_OCID")
        if existing and existing.outbound_connection_type == "PRIVATE_ENDPOINT":
            if existing.subnet_id == subnet and set(existing.nsg_ids or []) == {nsg}:
                print("OIC private endpoint already matches.")
                return
            raise RuntimeError("OIC already has a different private endpoint; review it before changing it")
        endpoint = oci.integration.models.PrivateEndpointOutboundConnection(subnet_id=subnet, nsg_ids=[nsg])
    response = client.change_private_endpoint_outbound_connection(
        instance_id, oci.integration.models.ChangePrivateEndpointOutboundConnectionDetails(
            private_endpoint_outbound_connection=endpoint), if_match=current.headers["etag"])
    print("OIC work request:", response.headers.get("opc-work-request-id"))
    print("Wait for SUCCEEDED in the OCI work-request page before continuing.")


if __name__ == "__main__":
    main()
