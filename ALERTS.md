# ALERTS.md

Monitoring configuration for the Azure Function that syncs workbooks to GitHub. Two scheduled-query alerts are defined in Azure Monitor.

---

## Alert 1: Function Execution Failures

**Name:** `your-function-app-errors`
**Severity:** 2 (Warning)
**Evaluation frequency:** Every 15 minutes
**Window size:** 15 minutes

**What it detects:**
Any failed function execution as reported by Application Insights. Fires when `success == false` is recorded for the function app within a 15-minute window.

**KQL query:**
```kusto
requests
| where cloud_RoleName == 'YOUR_FUNCTION_APP_NAME'
| where success == false
```

**Creation command:**
```bash
az monitor scheduled-query create \
  --name "your-function-app-errors" \
  --resource-group "YOUR_RESOURCE_GROUP" \
  --scopes "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP/providers/microsoft.insights/components/YOUR_APP_INSIGHTS_NAME" \
  --condition "count 'failures' > 0 at least 1 violations out of 1 aggregated points" \
  --condition-query failures="requests | where cloud_RoleName == 'YOUR_FUNCTION_APP_NAME' | where success == false" \
  --evaluation-frequency "PT15M" \
  --window-size "PT15M" \
  --severity 2 \
  --description "Fires when the function app has any failed executions" \
  --action-groups "YOUR_ACTION_GROUP_RESOURCE_ID"
```

**Remediation:**

1. Open Application Insights in the Azure Portal and go to **Logs**.
2. Run the query above to identify which function invocation failed and what error was returned.
3. If the error is transient (network, throttling), check whether the next scheduled run recovered.
4. If the error is persistent:
   - Check the function app's **Log stream** for stack traces.
   - Verify all app settings are present: `AZURE_SUBSCRIPTION_ID`, `WORKBOOK_RESOURCE_GROUP`, `GIT_TOKEN`, `GIT_OWNER`, `GIT_REPO`, `GIT_BRANCH`, `GIT_BASE_URL`.
   - If a setting is missing or malformed, add it via the Azure Portal under **Configuration** or with:
     ```bash
     az functionapp config appsettings set \
       --name "YOUR_FUNCTION_APP_NAME" \
       --resource-group "YOUR_RESOURCE_GROUP" \
       --settings "SETTING_NAME=value"
     ```
5. Redeploy if code changes are required: `./deploy.sh`

---

## Alert 2: Timer Not Firing

**Name:** `your-function-app-timer-not-firing`
**Severity:** 1 (Critical)
**Evaluation frequency:** Every 30 minutes
**Window size:** 30 minutes

**What it detects:**
The timer trigger (`sync_workbooks_timer`) has not executed at all within a 30-minute window. This indicates the trigger is not registered with Azure's scheduler — not just that it failed, but that it never ran.

**KQL query:**
```kusto
requests
| where cloud_RoleName == 'YOUR_FUNCTION_APP_NAME'
| where name == 'sync_workbooks_timer'
```

**Creation command:**
```bash
az monitor scheduled-query create \
  --name "your-function-app-timer-not-firing" \
  --resource-group "YOUR_RESOURCE_GROUP" \
  --scopes "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP/providers/microsoft.insights/components/YOUR_APP_INSIGHTS_NAME" \
  --condition "count 'executions' < 1 at least 1 violations out of 1 aggregated points" \
  --condition-query executions="requests | where cloud_RoleName == 'YOUR_FUNCTION_APP_NAME' | where name == 'sync_workbooks_timer'" \
  --evaluation-frequency "PT30M" \
  --window-size "PT30M" \
  --severity 1 \
  --description "Fires when the timer has not executed in 30 minutes" \
  --action-groups "YOUR_ACTION_GROUP_RESOURCE_ID"
```

**Remediation:**

This alert typically means the timer trigger is not registered with Azure's scheduler. This can happen silently after a failed deployment — the Azure Portal may show the function app as "Running" even though no triggers are firing.

1. **Verify the trigger is registered:**
   ```bash
   az rest --method post \
     --url "https://management.azure.com/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP/providers/Microsoft.Web/sites/YOUR_FUNCTION_APP_NAME/syncfunctiontriggers?api-version=2022-03-01"
   ```
   Expected response: `{"status": "success"}`

2. **Redeploy using the deploy script**, which enforces trigger sync verification:
   ```bash
   ./deploy.sh
   ```
   The script will fail explicitly if trigger sync does not confirm success.

3. **Verify APPLICATIONINSIGHTS_CONNECTION_STRING is set correctly.** The app setting must be named exactly `APPLICATIONINSIGHTS_CONNECTION_STRING`. If it is named anything else, logs will not reach App Insights and failures will be invisible.
   ```bash
   az functionapp config appsettings list \
     --name "YOUR_FUNCTION_APP_NAME" \
     --resource-group "YOUR_RESOURCE_GROUP" \
     --query "[?name=='APPLICATIONINSIGHTS_CONNECTION_STRING']"
   ```
   If the setting is missing or misnamed, set it:
   ```bash
   az functionapp config appsettings set \
     --name "YOUR_FUNCTION_APP_NAME" \
     --resource-group "YOUR_RESOURCE_GROUP" \
     --settings "APPLICATIONINSIGHTS_CONNECTION_STRING=YOUR_CONNECTION_STRING"
   ```

4. **Confirm the host is alive** by hitting the HTTP endpoint:
   ```bash
   FUNC_KEY=$(az functionapp keys list \
     --name "YOUR_FUNCTION_APP_NAME" \
     --resource-group "YOUR_RESOURCE_GROUP" \
     --query "functionKeys.default" -o tsv)

   curl -s -o /dev/null -w "%{http_code}" \
     -X POST "https://YOUR_FUNCTION_HOST_URL/api/exportworkbooktogit?code=${FUNC_KEY}" \
     -H "Content-Type: application/json" -d '{}'
   ```
   A `400` response confirms the host is alive. Any other response requires further investigation.

---

## Action Group Setup

Before creating the alerts above, create an action group that defines who gets notified:

```bash
az monitor action-group create \
  --name "YOUR_ACTION_GROUP_NAME" \
  --resource-group "YOUR_RESOURCE_GROUP" \
  --short-name "your-app" \
  --action email recipient1 "recipient1@example.com" \
  --action email recipient2 "recipient2@example.com"
```

The `--action-groups` parameter in the alert creation commands above accepts the full resource ID of this action group:

```
/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP/providers/microsoft.insights/actionGroups/YOUR_ACTION_GROUP_NAME
```
