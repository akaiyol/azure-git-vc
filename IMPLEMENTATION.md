# Implementation Guide

Deployment instructions for Azure Workbook backup system.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Azure Setup](#azure-setup)
4. [GitHub Configuration](#github-configuration)
5. [Function Deployment](#function-deployment)
6. [Local Development](#local-development)
7. [Configuration Reference](#configuration-reference)
8. [Workbook Naming Convention](#workbook-naming-convention)
9. [Troubleshooting](#troubleshooting)

## Architecture Overview

### System Components

```
┌───────────────────────────────────────────────────────────┐
│                     Azure Subscription                    │
│                                                           │
│  ┌─────────────────┐         ┌──────────────────────┐     │
│  │ Azure Monitor   │         │  Azure Function      │     │
│  │   Workbooks     │◄────────│  (Python 3.9+)       │     │
│  │                 │  Query  │                      │     │
│  │  • Security     │         │  • Timer Trigger     │     │
│  │  • Cost         │         │  • HTTP Trigger      │     │
│  │  • Performance  │         │  • Managed Identity  │     │
│  └─────────────────┘         └───────────┬──────────┘     │
│                                          │                │
└──────────────────────────────────────────┼────────────────┘
                                           │
                                           │ HTTPS
                                           │
                                      ┌────▼────┐
                                      │ GitHub  │
                                      │   API   │
                                      └────┬────┘
                                           │
                                    ┌──────▼──────┐
                                    │  Repository │
                                    │  workbooks/ │
                                    └─────────────┘
```

### Data Flow

1. Timer trigger (15 min) → Managed Identity auth
2. Query Azure Management API → Filter by prefix
3. Validate `serializedData` → Parse JSON
4. Fetch from GitHub → Compare hashes
5. Generate files → Commit if changed → Retry on conflict

### Output Files

**metadata.json**
```json
{
  "exportMetadata": {
    "exportedAt": "2024-01-01T00:00:00Z",
    "resourceId": "/subscriptions/.../workbooks/...",
    "displayName": "workbook-security-audit"
  },
  "resource": {
    "id": "...",
    "location": "eastus",
    "properties": { ... }
  }
}
```

**definition.json**
```json
{
  "$schema": "https://github.com/Microsoft/...",
  "version": "Notebook/1.0",
  "items": [ ... ],
  "parameters": [ ... ]
}
```

## Prerequisites

- Azure account with subscription permissions
- GitHub account with repo creation access

## Step 1: Fork or Clone This Repository

1. Go to your GitHub account
2. Create a new repository
3. Note the repository URL - you'll need it later

## Step 2: Create a GitHub Personal Access Token

This allows the Azure Function to commit files to your repository.

### For GitHub.com:
1. Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token** → **Generate new token (classic)**
3. Give it a name like "Azure Workbook Sync"
4. Set expiration to **No expiration** (or a far future date)
5. Select these scopes:
   - **repo** (Full control of private repositories)
6. Click **Generate token**
7. **IMPORTANT**: Copy the token immediately and save it somewhere safe - you won't see it again!

### For GitHub Enterprise:
Follow your organization's process for creating Personal Access Tokens with `repo` scope.

## Step 3: Set Up Azure Resources

### 3.1 Create a Resource Group (if needed)

1. Go to [Azure Portal](https://portal.azure.com)
2. Search for "Resource groups" and click **Create**
3. Choose your subscription
4. Enter a name like `workbook-automation-rg`
5. Select your preferred region
6. Click **Review + create**, then **Create**

### 3.2 Create Azure Function App

1. In Azure Portal, search for "Function App" and click **Create**
2. Fill in the details:
   - **Subscription**: Your Azure subscription
   - **Resource Group**: Select the one you created (or use existing)
   - **Function App name**: Choose a unique name
   - **Publish**: Code
   - **Runtime stack**: Python
   - **Version**: 3.13 (or latest available)
   - **Region**: Same as your resource group
3. Click **Review + create**, then **Create**
4. Wait for deployment to complete (2-3 minutes)

### 3.3 Enable Managed Identity

This allows the Function to access Azure resources securely without storing credentials.

1. Go to your Function App
2. In the left menu, find **Settings** → **Identity**
3. Under **System assigned** tab, toggle **Status** to **On**
4. Click **Save**
5. Click **Yes** to confirm
6. Copy the **Object (principal) ID** that appears - you'll need it next

### 3.4 Grant Permissions to Managed Identity

The Function needs permission to read your workbooks.

1. Go to the **Resource Group** that contains your workbooks
2. Click **Access control (IAM)** in the left menu
3. Click **+ Add** → **Add role assignment**
4. Search for and select **Reader** role
5. Click **Next**
6. Click **+ Select members**
7. Search for your Function App name
8. Select it and click **Select**
9. Click **Review + assign**

## Step 4: Configure Function Settings

Now we'll add all the configuration settings the Function needs.

1. Go to your Function App
2. In the left menu, find **Settings** → **Environment variables**
3. Click **+ Add** for each of these settings:

### Required Settings

| Name | Value | Description |
|------|-------|-------------|
| `GIT_TOKEN` | Your GitHub token from Step 2 | Allows commits to GitHub |
| `GIT_OWNER` | Your GitHub username/org | 
| `GIT_REPO` | Your repository name | 
| `GIT_BRANCH` | `main` or `develop` | Branch to commit to |
| `GIT_BASE_URL` | `https://api.github.com` | GitHub API URL (use default for GitHub.com) |
| `AZURE_SUBSCRIPTION_ID` | Your subscription ID | Find in Azure Portal → Subscriptions |
| `WORKBOOK_RESOURCE_GROUP` | Resource group with workbooks |
| `WORKBOOK_NAME_PREFIX` | `workbook-` | Only sync workbooks starting with this prefix |

### Optional Settings

| Name | Value | Description |
|------|-------|-------------|
| `PRESERVE_ARM_PAYLOAD` | `false` | Set to `true` to save full ARM data |
| `ENABLE_TIMER` | `true` | Set to `false` to disable automatic sync |

4. Click **Apply** at the bottom after adding all settings
5. Click **Confirm** when prompted

## Step 5: Deploy the Function Code

### Option A: Deploy from GitHub (Recommended)

1. In your Function App, go to **Deployment** → **Deployment Center**
2. Select **GitHub** as source
3. Sign in to GitHub and authorize Azure
4. Select:
   - **Organization**: Your GitHub account
   - **Repository**: Your forked repository
   - **Branch**: `main` or `develop`
5. Click **Save**
6. Wait for the initial deployment (5-10 minutes)

### Option B: Deploy from Local Code

If you have the code locally:

1. Install [Azure Functions Core Tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local)
2. Open terminal in the project directory
3. Run: `func azure functionapp publish YOUR-FUNCTION-APP-NAME`

## Step 6: Create local.settings.json (For Local Testing Only)

If you want to test the function locally before deploying:

1. Copy the template file:
   ```bash
   cp local.settings.template.json local.settings.json
   ```

2. Edit `local.settings.json` and fill in your values

**IMPORTANT**: This file contains secrets and should NEVER be committed to Git. It's already in `.gitignore` for protection.

## Step 7: Set Up Workbook Naming

For workbooks to be automatically tracked, they must follow this naming pattern:

`prefix-<category>-<workbook-name>`

Examples (using default `workbook-` prefix):
- `workbook-security-audit`
- `workbook-cost-analysis`
- `workbook-performance-dashboard`

To rename a workbook:
1. Open the workbook in Azure Portal
2. Click the **Edit** button
3. Change the title at the top
4. Click **Done Editing** then **Save**

## Step 8: Verify Everything Works

1. Go to your GitHub repository
2. Look for a new `workbooks/` directory
3. Inside should be folders matching your workbook names
4. Each folder should have `metadata.json` and `definition.json` files

For detailed testing and debugging instructions, see [TESTS.md](TESTS.md).

## Step 9: Enable Automatic Sync

The function is configured to run every 15 minutes automatically. To disable automatic sync (for example, during testing), set `ENABLE_TIMER=false` in your configuration.

## Configuration Reference

### Environment Variables

#### Required Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `GIT_TOKEN` | string | GitHub Personal Access Token with `repo` scope | `ghp_xxxxxxxxxxxx` |
| `GIT_OWNER` | string | GitHub username or organization | `myusername` |
| `GIT_REPO` | string | Repository name | `workbook-backups` |
| `GIT_BRANCH` | string | Target branch for commits | `main` |
| `GIT_BASE_URL` | string | GitHub API base URL | `https://api.github.com` |
| `AZURE_SUBSCRIPTION_ID` | GUID | Azure subscription ID | `xxxxxxxx-xxxx-...` |
| `WORKBOOK_RESOURCE_GROUP` | string | Resource group containing workbooks | `my-workbooks-rg` |

#### Optional Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WORKBOOK_NAME_PREFIX` | string | `workbook-` | Only sync workbooks starting with this prefix |
| `PRESERVE_ARM_PAYLOAD` | boolean | `false` | Save complete ARM response as arm.json |
| `ENABLE_TIMER` | boolean | `true` | Enable/disable automatic timer trigger |

### API Endpoints

#### Manual Export (HTTP Trigger)

```http
POST /api/ExportWorkbookToGit
Content-Type: application/json
x-functions-key: {function-key}

{
  "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "resourceGroup": "my-workbooks-rg",
  "workbookId": "workbook-resource-name"
}
```

**Response (200 OK):**
```json
{
  "message": "Workbook exported successfully",
  "workbookName": "workbook-security-audit",
  "metadataPath": "workbooks/security/audit/metadata.json",
  "definitionPath": "workbooks/security/audit/definition.json",
  "commits": [
    {
      "type": "metadata",
      "path": "workbooks/security/audit/metadata.json",
      "sha": "abc123..."
    },
    {
      "type": "definition",
      "path": "workbooks/security/audit/definition.json",
      "sha": "def456..."
    }
  ]
}
```

**Error Responses:**
- `400` - Missing required parameters
- `422` - Workbook validation failed (missing serializedData)
- `500` - Internal server error

#### Timer Trigger

Automatically runs on schedule (default: every 15 minutes)
- Cron expression: `0 */15 * * * *`
- Processes all workbooks matching prefix
- Logs results to Application Insights

## Advanced Configuration

### Using Azure Key Vault

For production deployments, store secrets in Azure Key Vault:

1. **Create Key Vault**
   ```bash
   az keyvault create \
     --name my-workbook-vault \
     --resource-group my-rg \
     --location eastus
   ```

2. **Store GitHub Token**
   ```bash
   az keyvault secret set \
     --vault-name my-workbook-vault \
     --name GIT-TOKEN \
     --value "ghp_your_token_here"
   ```

3. **Grant Function Access**
   ```bash
   az keyvault set-policy \
     --name my-workbook-vault \
     --object-id {function-managed-identity-id} \
     --secret-permissions get
   ```

4. **Update Function Configuration**
   ```
   GIT_TOKEN=@Microsoft.KeyVault(SecretUri=https://my-workbook-vault.vault.azure.net/secrets/GIT-TOKEN/)
   ```

### Custom Sync Schedule

Modify the timer trigger in `function_app.py`:

```python
@app.timer_trigger(
    schedule="0 0 * * * *",  # Every hour at minute 0
    arg_name="mytimer",
    run_on_startup=False,
    use_monitor=True
)
```

Cron format: `{second} {minute} {hour} {day} {month} {day-of-week}`

### GitHub Enterprise Configuration

For GitHub Enterprise:

1. Set `GIT_BASE_URL` to your enterprise API:
   ```
   GIT_BASE_URL=https://github.your-company.com/api/v3
   ```

2. Ensure your PAT has appropriate permissions in your org

3. Verify network connectivity from Azure to your GitHub instance

## Technical Architecture

### Code Organization

```
src/
├── azure_client.py       # Azure Management API client
│   └── AzureWorkbookClient
│       ├── list_workbooks()
│       └── get_workbook()
│
├── github_client.py      # GitHub REST API client
│   └── GitHubClient
│       ├── get_file()
│       ├── put_file()
│       └── has_changed()
│
├── services.py           # Business logic layer
│   ├── WorkbookExportService
│   │   └── export_workbook()
│   └── WorkbookSyncService
│       └── sync_workbooks()
│
├── validation.py         # Content validation
│   └── WorkbookValidator
│       └── validate()
│
├── file_preparation.py   # Export file generation
│   └── WorkbookFilePreparation
│       └── prepare_files()
│
├── path_utils.py         # Path management
│   └── PathManager
│       └── generate_paths()
│
├── models.py             # Data models
│   ├── ValidationResult
│   └── WorkbookExportResult
│
└── config.py             # Configuration management
    ├── ConfigManager
    └── CredentialManager
```

### Key Design Patterns

1. **Service Layer Architecture**
   - Separation of concerns
   - Testable business logic
   - Clean dependency injection

2. **Retry Logic with Exponential Backoff**
   - Handles GitHub API 409 conflicts
   - Automatic SHA refresh on conflicts
   - Content deduplication

3. **Optimistic Locking**
   - Uses SHA-based version control
   - Prevents lost updates
   - Safe concurrent operations

4. **Validation Pipeline**
   - Strict serializedData validation
   - JSON schema verification
   - Fail-fast error handling

## Security Best Practices

### Authentication

- **Use Managed Identity** for Azure authentication (no credentials in code)
- **Azure Key Vault** for GitHub token storage
- **Least Privilege** - Reader role only on workbook resources
- **Token Rotation** - Set expiration on GitHub PATs

### Network Security

- Consider **Private Endpoints** for Azure Function
- Use **VNet Integration** if accessing private resources
- Enable **IP Restrictions** on Function App
- Configure **CORS** if using HTTP trigger from web apps

### Data Protection

- Workbooks may contain **sensitive queries** - use private repos
- Enable **branch protection** on target branch
- Require **pull request reviews** for critical workbooks
- Consider **CODEOWNERS** file for governance

## Troubleshooting

For detailed testing and debugging instructions, see [TESTS.md](TESTS.md).

### Common Issues

#### 1. Workbooks Not Syncing

**Symptoms:** No files appearing in GitHub repository

**Checks:**
- Verify workbook names start with configured prefix
- Check Managed Identity has Reader role on resource group
- Review function logs for errors
- Confirm WORKBOOK_RESOURCE_GROUP is correct

**Solution:**
```bash
# List workbooks in resource group
az monitor app-insights workbook list \
  --resource-group {your-rg} \
  --query "[].{name:name, displayName:properties.displayName}"
```

#### 2. GitHub Commit Failures

**Symptoms:** Function runs but no commits appear

**Checks:**
- Verify GitHub token is valid: `curl -H "Authorization: token {token}" https://api.github.com/user`
- Confirm repository and branch exist
- Check token has `repo` scope
- Review rate limits (5000 requests/hour for authenticated)

**Solution:**
```bash
# Test GitHub authentication
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/{owner}/{repo}
```

#### 3. Authentication Errors

**Symptoms:** 401/403 errors in logs

**Checks:**
- Managed Identity is enabled and has role assignment
- Subscription ID matches the workbook location
- Function App has network access to Azure Management API

**Solution:**
```bash
# Verify role assignment
az role assignment list \
  --assignee {managed-identity-object-id} \
  --resource-group {workbook-rg}
```

#### 4. Validation Failures

**Symptoms:** "Workbook content is missing: properties.serializedData not found"

**Cause:** Workbook was created but never saved/published

**Solution:** Open workbook in Azure Portal, make a minor edit, and save

### Debug Logging

Enable detailed logging in `local.settings.json`:

```json
{
  "logging": {
    "logLevel": {
      "default": "Information",
      "Function": "Information"
    }
  }
}
```

### Performance Optimization

- **Batch Processing**: Function processes all matching workbooks in one execution
- **Change Detection**: Only commits when content actually differs
- **Concurrent Processing**: Could be enhanced with asyncio for large workbook sets
- **Caching**: Configuration is cached within function execution

## Monitoring & Alerts

### Application Insights Queries

**Successful Syncs:**
```kusto
traces
| where message contains "Scheduled workbook sync completed"
| extend result = parse_json(message)
| project timestamp, processedCount=result.processedCount, failedCount=result.failedCount
```

**Failed Exports:**
```kusto
traces
| where severityLevel >= 3
| where message contains "ExportWorkbookToGit failed" or message contains "sync_workbooks_timer failed"
| project timestamp, severityLevel, message
```

### Recommended Alerts

1. **Sync Failures**
   - Condition: failedCount > 0 for 2+ consecutive runs
   - Action: Email notification

2. **Function Execution Failures**
   - Condition: Function hasn't run successfully in 1 hour
   - Action: SMS/PagerDuty

3. **Rate Limiting**
   - Condition: GitHub API rate limit < 500 remaining
   - Action: Email warning

## Next Steps

Once everything is working:

1. **Set up alerts** for function failures in Application Insights
2. **Enable branch protection** in GitHub
3. **Review exported workbooks** to familiarize yourself with structure
4. **Consider CODEOWNERS** file for workbook governance
5. **Document your naming convention** for team members
6. **Schedule token rotation** (set calendar reminder)
7. **Test disaster recovery** by restoring a workbook from Git

## Additional Resources

- [Azure Functions Python Developer Guide](https://docs.microsoft.com/azure/azure-functions/functions-reference-python)
- [GitHub REST API Documentation](https://docs.github.com/en/rest)
- [Azure Monitor Workbooks Documentation](https://docs.microsoft.com/azure/azure-monitor/visualize/workbooks-overview)
- [Azure Managed Identity](https://docs.microsoft.com/azure/active-directory/managed-identities-azure-resources/overview)
