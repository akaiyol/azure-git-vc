# Azure Workbook Backup to GitHub

Automated Azure Function that exports Azure Monitor Workbooks to GitHub every 15 minutes, providing version control and disaster recovery.

## Development

Built through AI-assisted programming:
- **Requirements & Architecture**: ChatGPT
- **Implementation & Execution**: Cline

For custom instructions used: [AI Configs Repository](https://github.com/akaiyol/ai-configs)

## How It Works

```
┌─────────────────┐
│  Azure Monitor  │
│    Workbooks    │
└────────┬────────┘
         │
         │ (Every 15 minutes)
         │
    ┌────▼─────┐
    │  Azure   │
    │ Function │
    └────┬─────┘
         │
         │ (Detects changes)
         │
    ┌────▼─────┐
    │  GitHub  │
    │Repository│
    └──────────┘
```

1. Timer trigger (every 15 minutes)
2. Query Azure for workbooks matching prefix
3. Validate content and detect changes
4. Commit to GitHub if changed

## Features

- Scheduled sync every 15 minutes
- Change detection (commits only on actual changes)
- Auto-categorized folder structure
- Dual-file format (metadata + definition)
- HTTP endpoint for manual exports
- Azure Managed Identity authentication
- GitHub.com and GitHub Enterprise support

## Quick Start

1. **Clone this repository**
   ```bash
   git clone <your-repo-url>
   cd azure-workbook-exporter
   ```

2. **Configure settings**
   ```bash
   cp local.settings.template.json local.settings.json
   # Edit local.settings.json with your Azure & GitHub details
   ```

3. **Deploy to Azure**
   - Follow detailed instructions in [IMPLEMENTATION.md](IMPLEMENTATION.md)

4. **Name your workbooks**
   ```
   workbook-{category}-{name}
   Example: workbook-security-audit
   ```

## Repository Structure

Exported workbooks are organized as:
```
workbooks/
├── security/
│   └── audit/
│       ├── metadata.json      # Azure resource metadata
│       └── definition.json    # Workbook visualization
└── cost/
    └── analysis/
        ├── metadata.json
        └── definition.json
```

## Documentation

- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** - Complete setup and deployment guide
- **[TESTS.md](TESTS.md)** - Testing and debugging instructions

## Configuration

Key environment variables:
- `AZURE_SUBSCRIPTION_ID` - Your Azure subscription
- `WORKBOOK_RESOURCE_GROUP` - Resource group containing workbooks
- `GIT_OWNER` / `GIT_REPO` / `GIT_TOKEN` - GitHub repository details
- `WORKBOOK_NAME_PREFIX` - Filter workbooks by prefix (default: `workbook-`)

See `local.settings.template.json` for complete configuration options.

## Technology Stack

- **Runtime**: Azure Functions (Python 3.9+)
- **Authentication**: Azure Managed Identity
- **APIs**: Azure Management API, GitHub REST API
- **Architecture**: Modular service-based design

## Project Structure

```
azure-workbook-exporter/
├── src/                    # Core application modules
│   ├── azure_client.py    # Azure API client
│   ├── github_client.py   # GitHub API client
│   ├── services.py        # Business logic
│   ├── validation.py      # Content validation
│   └── ...
├── function_app.py        # Function entry point
└── requirements.txt       # Python dependencies
```

## Architecture

- Service layer pattern with dependency injection
- Retry logic with exponential backoff
- Optimistic locking for GitHub commits
- Strict validation pipeline


## Support

For setup help, see [IMPLEMENTATION.md](IMPLEMENTATION.md)  
For debugging, see [TESTS.md](TESTS.md)