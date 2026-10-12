# Optional account bootstrap

Run this once with an Entra administrator and OCI tenancy administrator. It creates an Entra database-admin group, an application/service principal with GitHub OIDC trust, and an OCI Default-domain API user/group with a public signing key. It creates no private keys or Azure client secret.

Copy `terraform.tfvars.example` to `terraform.tfvars`, fill it in, then run `terraform init`, `terraform plan`, and `terraform apply` here. Use the outputs in the main stack's parameters and your OCI profile.

Azure resource roles and OCI tenancy-level grants still need an administrator. The exact scope and choices are in [accounts.md](../docs/accounts.md). The checked-in CI has no cloud authentication or deployment job; OIDC trust alone doesn't deploy anything.
