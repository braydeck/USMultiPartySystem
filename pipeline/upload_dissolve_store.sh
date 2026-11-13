#!/usr/bin/env bash
# Upload the dissolve scenarios (data/dissolve_store, built by build_dissolve_scenarios.py) to the
# R2 bucket the Pages Function reads (viz/functions/data/dissolve/[[path]].ts, binding DISSOLVE).
# Resumable: sync skips files already uploaded unchanged. Run after the build finishes, so no
# half-written combination goes up.
#
# Needs an AWS CLI profile "r2" holding an R2 API token, with endpoint_url set to
# https://<account-id>.r2.cloudflarestorage.com (see `aws configure --profile r2`).
#
#   pipeline/upload_dissolve_store.sh            # bucket stv-dissolve
#   BUCKET=other-name pipeline/upload_dissolve_store.sh
set -euo pipefail
cd "$(dirname "$0")/.."
BUCKET="${BUCKET:-stv-dissolve}"
STORE=data/dissolve_store

built=$(ls "$STORE"/*/done.json 2>/dev/null | wc -l | tr -d ' ')
echo "uploading $built built combinations to r2://$BUCKET"
# The objects are already gzip-compressed JSON; the Function declares that encoding when serving.
aws s3 sync "$STORE" "s3://$BUCKET" --profile r2 --exclude "_work/*" --exclude "*/done.json" --exclude "*/done.stale.json" --only-show-errors
echo "done"
