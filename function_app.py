"""
Azure Function App for Workbook Export

This module provides HTTP and timer-triggered Azure Functions for exporting
Azure Monitor Workbooks to GitHub Enterprise.

For detailed documentation, see README.md and WORKFLOW.md
"""

import json
import logging
import azure.functions as func

from src.config import ConfigManager
from src.azure_client import AzureWorkbookClient
from src.github_client import GitHubClient
from src.services import WorkbookExportService, WorkbookSyncService


# Initialize Azure Function App
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="ExportWorkbookToGit", methods=["POST"])
def export_workbook_to_git(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint for manual workbook export.
    
    Request body:
    {
      "subscriptionId": "...",
      "resourceGroup": "...",
      "workbookId": "..."
    }
    
    Returns:
        200: Export successful with commit details
        400: Missing required parameters
        422: Workbook validation failed
        500: Internal server error
    """
    try:
        # Load configuration
        ConfigManager.clear_cache()
        config = ConfigManager.load_config()
        
        # Parse and validate request
        body = req.get_json()
        subscription_id = body.get("subscriptionId")
        resource_group = body.get("resourceGroup")
        workbook_id = body.get("workbookId")
        
        if not all([subscription_id, resource_group, workbook_id]):
            return func.HttpResponse(
                json.dumps({
                    "error": "Missing required parameters",
                    "required": ["subscriptionId", "resourceGroup", "workbookId"]
                }, indent=2),
                status_code=400,
                mimetype="application/json"
            )
        
        # Initialize services
        azure_client = AzureWorkbookClient()
        github_client = GitHubClient(config)
        export_service = WorkbookExportService(azure_client, github_client, config)
        
        # Export workbook
        result = export_service.export_workbook(subscription_id, resource_group, workbook_id)
        
        return func.HttpResponse(
            json.dumps(result.to_dict(), indent=2),
            status_code=200,
            mimetype="application/json"
        )
    
    except ValueError as ex:
        # Validation error
        logging.error(f"Workbook validation failed: {ex}")
        return func.HttpResponse(
            json.dumps({
                "error": "Workbook validation failed",
                "details": str(ex)
            }, indent=2),
            status_code=422,
            mimetype="application/json"
        )
    except Exception as ex:
        # System error
        logging.exception("ExportWorkbookToGit failed")
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "details": str(ex)
            }, indent=2),
            status_code=500,
            mimetype="application/json"
        )


@app.timer_trigger(
    schedule="0 */15 * * * *",
    arg_name="mytimer",
    run_on_startup=False,
    use_monitor=True
)
def sync_workbooks_timer(mytimer: func.TimerRequest) -> None:
    """
    Timer trigger for scheduled workbook sync.
    
    Runs every 15 minutes to sync all workbooks matching the configured prefix.
    Logs results and continues on validation failures without crashing.
    
    Can be disabled for local testing by setting ENABLE_TIMER=false in local.settings.json
    """
    try:
        if mytimer.past_due:
            logging.warning("The timer is past due.")
        
        # Load configuration
        ConfigManager.clear_cache()
        config = ConfigManager.load_config()
        
        # Check if timer is disabled (useful for local testing)
        import os
        if os.getenv("ENABLE_TIMER", "true").lower() != "true":
            logging.info("Timer trigger disabled via ENABLE_TIMER setting")
            return
        
        logging.info("Starting scheduled workbook sync")
        
        # Initialize services
        azure_client = AzureWorkbookClient()
        github_client = GitHubClient(config)
        export_service = WorkbookExportService(azure_client, github_client, config)
        sync_service = WorkbookSyncService(export_service, azure_client, config)
        
        # Sync workbooks
        result = sync_service.sync_workbooks(
            subscription_id=config["AZURE_SUBSCRIPTION_ID"],
            resource_group=config["WORKBOOK_RESOURCE_GROUP"]
        )
        
        logging.info("Scheduled workbook sync completed: %s", json.dumps(result, indent=2))
        
        # Log validation failures
        if result["failedCount"] > 0:
            validation_failures = [
                f for f in result["failed"] 
                if f.get("errorType") == "validation"
            ]
            if validation_failures:
                logging.warning(
                    f"Skipped {len(validation_failures)} workbook(s) due to missing serializedData: %s",
                    json.dumps(validation_failures, indent=2)
                )
    
    except Exception:
        logging.exception("sync_workbooks_timer failed")
        raise
