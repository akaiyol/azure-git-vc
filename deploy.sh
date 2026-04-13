#!/usr/bin/env bash
# deploy.sh
#
# Deploys the function app and verifies that the timer trigger is registered
# with Azure's scheduler. Exits non-zero if trigger sync does not confirm
# success within the polling window.
#
# Prerequisites:
#   - Azure Functions Core Tools installed (func CLI)
#   - Azure CLI installed and authenticated (az login)
#   - FUNCTION_APP_NAME and RESOURCE_GROUP set below or via environment

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — set these to match your Azure deployment
# ---------------------------------------------------------------------------
FUNCTION_APP_NAME="${FUNCTION_APP_NAME:-YOUR_FUNCTION_APP_NAME}"
RESOURCE_GROUP="${RESOURCE_GROUP:-YOUR_RESOURCE_GROUP}"
SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-YOUR_SUBSCRIPTION_ID}"

# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------
echo "Deploying to ${FUNCTION_APP_NAME}..."
func azure functionapp publish "${FUNCTION_APP_NAME}" --python

# ---------------------------------------------------------------------------
# Sync function triggers — poll until success or timeout
# ---------------------------------------------------------------------------
echo "Syncing function triggers..."

SYNC_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${FUNCTION_APP_NAME}/syncfunctiontriggers?api-version=2022-03-01"

MAX_ATTEMPTS=9    # 9 x 10s = 90s
ATTEMPT=0
SYNCED=false

while [[ ${ATTEMPT} -lt ${MAX_ATTEMPTS} ]]; do
    RESPONSE=$(az rest --method post --url "${SYNC_URL}" 2>/dev/null || true)
    STATUS=$(echo "${RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || true)

    if [[ "${STATUS}" == "success" ]]; then
        SYNCED=true
        break
    fi

    ATTEMPT=$((ATTEMPT + 1))
    echo "  Trigger sync not confirmed yet (attempt ${ATTEMPT}/${MAX_ATTEMPTS}), retrying in 10s..."
    sleep 10
done

if [[ "${SYNCED}" != "true" ]]; then
    echo "ERROR: Trigger sync did not return success after $((MAX_ATTEMPTS * 10))s."
    echo "The timer trigger may not be registered. Check the Azure Portal and re-run this script."
    exit 1
fi

echo "Trigger sync confirmed."

# ---------------------------------------------------------------------------
# Smoke test — confirm the function host responds to an HTTP request
# ---------------------------------------------------------------------------
echo "Verifying function host is alive..."

FUNC_KEY=$(az functionapp keys list \
    --name "${FUNCTION_APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "functionKeys.default" -o tsv)

# The host URL pattern for Flex Consumption is:
# https://<app-name>-<random-suffix>.<region>-01.azurewebsites.net
# Replace the placeholder below with your actual host URL after first deployment.
HOST_URL="${FUNCTION_HOST_URL:-https://YOUR_FUNCTION_HOST_URL}"

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${HOST_URL}/api/exportworkbooktogit?code=${FUNC_KEY}" \
    -H "Content-Type: application/json" \
    -d '{}')

# A 400 response means the host is alive and rejected the empty payload — expected.
if [[ "${HTTP_STATUS}" == "400" || "${HTTP_STATUS}" == "200" ]]; then
    echo "Function host is responding (HTTP ${HTTP_STATUS})."
    echo "Deployment successful."
else
    echo "WARNING: Function host returned HTTP ${HTTP_STATUS}."
    echo "The host may still be starting up. Check the Azure Portal for errors."
    exit 1
fi
