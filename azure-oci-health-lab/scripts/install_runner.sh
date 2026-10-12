#!/usr/bin/env bash
set -euo pipefail
# For the Ubuntu 22.04 runner image selected in Terraform. Run manually on it.
task_download_dir=$(mktemp -d)
trap 'rm -rf "$task_download_dir"' EXIT
curl --fail --show-error --location \
  https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb \
  --output "$task_download_dir/microsoft.deb"
sudo dpkg -i "$task_download_dir/microsoft.deb"
sudo apt-get update
sudo env ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev python3-venv git
