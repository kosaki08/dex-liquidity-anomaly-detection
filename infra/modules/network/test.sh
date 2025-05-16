#!/usr/bin/env bash
set -euo pipefail

terraform init -backend=false
terraform test
