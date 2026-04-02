# Testing Guide

This guide covers testing and debugging the Azure Workbooks backup system.

## Local Testing

### Prerequisites for Local Testing

1. Install [Azure Functions Core Tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local)
2. Install Python 3.9+ (or version matching your Azure Function)
3. Create `local.settings.json` from template:
   ```bash
   cp local.settings.template.json local.settings.json
   # Edit with your values
   ```

### Running the Function Locally

1. Open terminal in the project directory
2. Create and activate virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the function:
   ```bash
   func start
   ```
5. The function will start and display available endpoints

### Force a Manual Save (Local Testing)

To trigger the function manually for testing purposes:

#### Local Development (using func start)
```bash
curl -X POST http://localhost:7071/admin/functions/sync_workbooks_timer
```

#### Azure Deployed Function (HTTP Trigger)
```bash
curl -X POST "https://YOUR-FUNCTION-APP-NAME.azurewebsites.net/api/ExportWorkbookToGit?code=YOUR_FUNCTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "subscriptionId": "YOUR_SUBSCRIPTION_ID",
    "resourceGroup": "YOUR_RESOURCE_GROUP",
    "workbookId": "YOUR_WORKBOOK_ID"
  }'
```

Replace:
- `YOUR-FUNCTION-APP-NAME` with your Azure Function App name
- `YOUR_FUNCTION_KEY` with your function's access key (found in Azure Portal under Function → Function Keys)
- `YOUR_SUBSCRIPTION_ID` with your Azure subscription ID
- `YOUR_RESOURCE_GROUP` with the resource group containing the workbook
- `YOUR_WORKBOOK_ID` with the specific workbook ID you want to export

These commands will immediately execute the sync function without waiting for the timer trigger.

### Test the Function in Azure Portal

1. Go to your Function App
2. Click **Functions** in the left menu
3. Click **sync_workbooks_timer**
4. Click **Code + Test** tab
5. Click **Test/Run** at the top
6. Click **Run**
7. Check the **Logs** panel for success messages

### Check GitHub for Results

1. Go to your GitHub repository
2. Look for a new `workbooks/` directory
3. Inside should be folders matching your workbook names
4. Each folder should have `metadata.json` and `definition.json` files

## Debugging

### Common Issues

#### Function not running

- Check that the Managed Identity has **Reader** role on the workbook resource group
- Verify all environment variables are set correctly
- Check the Function logs for error messages

#### Workbooks not appearing in Git

- Verify workbook names start with your configured prefix (default `workbook-`)
- Check that `WORKBOOK_NAME_PREFIX` matches your naming
- Ensure `WORKBOOK_RESOURCE_GROUP` is correct

#### GitHub commits failing

- Verify your GitHub token is valid and has `repo` scope
- Check that `GITHUB_REPO_OWNER` and `GITHUB_REPO_NAME` are correct
- Ensure the branch specified in `GITHUB_BRANCH` exists

#### Permission errors

- Confirm Managed Identity is enabled
- Verify the Reader role assignment is in place
- Check that you're using the correct subscription and resource group

### Viewing Logs

#### Azure Portal Logs

1. Go to your Function App
2. Navigate to **Monitor** → **Log stream**
3. Watch real-time logs as the function executes

#### Application Insights (if enabled)

1. Go to your Function App
2. Click **Application Insights** in the left menu
3. View detailed telemetry and error tracking

### Testing Environment Variables

Verify all required environment variables are set:

```bash
# In Azure Portal
Function App → Settings → Environment variables
```

Required variables:
- `GIT_TOKEN`
- `GIT_OWNER`
- `GIT_REPO`
- `GIT_BRANCH`
- `GIT_BASE_URL`
- `AZURE_SUBSCRIPTION_ID`
- `WORKBOOK_RESOURCE_GROUP`
- `WORKBOOK_NAME_PREFIX`

### Testing Workbook Detection

To test if workbooks are being detected correctly:

1. Check the function logs for messages about discovered workbooks
2. Verify workbook naming follows the pattern: `{prefix}-{category}-{name}`
   - Example: `workbook-security-audit`
3. Confirm the workbooks are in the specified resource group

### Debugging Authentication Issues

#### Managed Identity

1. Verify Managed Identity is enabled:
   - Function App → Settings → Identity → System assigned = On
2. Check role assignments:
   - Resource Group → Access control (IAM) → Role assignments
   - Look for your Function App with **Reader** role

#### GitHub Token

1. Verify token has correct scopes:
   - GitHub → Settings → Developer settings → Personal access tokens
   - Check that **repo** scope is enabled
2. Test token manually (GitHub.com):
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
   ```
3. For GitHub Enterprise, use your organization's API URL

## Getting Help

If you encounter issues:

1. Check the Function App logs: Function App → **Monitor** → **Log stream**
2. Review error messages in Application Insights (if enabled)
3. Verify all prerequisites are met
4. Double-check all configuration values
5. Test with the manual trigger endpoint first