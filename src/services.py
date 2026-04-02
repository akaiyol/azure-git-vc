"""
Business logic services for workbook operations.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional

from .models import WorkbookExportResult
from .azure_client import AzureWorkbookClient
from .github_client import GitHubClient
from .validation import WorkbookValidator
from .file_preparation import WorkbookFilePreparation
from .path_utils import PathManager


class WorkbookExportService:
    """Service for exporting workbooks to Git."""
    
    def __init__(
        self,
        azure_client: AzureWorkbookClient,
        github_client: GitHubClient,
        config: Dict[str, Any]
    ):
        """
        Initialize export service.
        
        Args:
            azure_client: Azure API client
            github_client: GitHub API client
            config: Configuration dictionary
        """
        self.azure_client = azure_client
        self.github_client = github_client
        self.config = config
    
    def export_workbook(
        self,
        subscription_id: str,
        resource_group: str,
        workbook_id: str
    ) -> WorkbookExportResult:
        """
        Export a single workbook with validation and dual-file format.
        
        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            workbook_id: Workbook resource ID
            
        Returns:
            WorkbookExportResult with export details
            
        Raises:
            ValueError: If workbook validation fails
        """
        # Fetch and validate workbook
        workbook = self.azure_client.get_workbook(subscription_id, resource_group, workbook_id)
        display_name = workbook.get("properties", {}).get("displayName", workbook_id)
        
        validation = WorkbookValidator.validate(workbook)
        if not validation.is_valid:
            logging.error(f"Validation failed for workbook {display_name}: {validation.error_message}")
            raise ValueError(validation.error_message)
        
        # Prepare export files
        metadata_json, definition_json, arm_json = WorkbookFilePreparation.prepare_files(
            workbook,
            validation.workbook_definition,
            self.config.get("PRESERVE_ARM_PAYLOAD", False)
        )
        
        metadata_path, definition_path, arm_path = PathManager.generate_paths(
            display_name,
            self.config["WORKBOOK_NAME_PREFIX"],
            self.config.get("PRESERVE_ARM_PAYLOAD", False)
        )
        
        # Check for changes and commit
        commits = self._commit_changes(
            workbook,
            workbook_id,
            display_name,
            metadata_json,
            definition_json,
            arm_json,
            metadata_path,
            definition_path,
            arm_path
        )
        
        message = "No changes detected" if not commits else "Workbook exported successfully"
        
        return WorkbookExportResult(
            message=message,
            workbook_name=display_name,
            metadata_path=metadata_path,
            definition_path=definition_path,
            arm_path=arm_path,
            commits=commits
        )
    
    def _put_file_with_retry(
        self,
        path: str,
        content: str,
        message: str,
        sha: Optional[str],
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Put file to GitHub with optimistic locking and content comparison.
        
        Handles 409 conflicts by:
        1. Retrying with exponential backoff
        2. Checking if content already matches (skip if duplicate)
        3. Using fresh SHA on each retry
        
        Args:
            path: File path in repository
            content: File content
            message: Commit message
            sha: Current file SHA (None for new files)
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            GitHub API response
            
        Raises:
            RuntimeError: If the operation fails after all retries
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return self.github_client.put_file(path, content, message, sha)
                
            except RuntimeError as e:
                error_str = str(e)
                
                # Parse error properly instead of string matching
                try:
                    error_data = json.loads(error_str)
                    status_code = error_data.get("status_code")
                except (json.JSONDecodeError, KeyError):
                    # Not our structured error format, re-raise
                    raise
                
                # Only retry on 409 conflicts
                if status_code != 409:
                    raise
                
                last_error = e
                
                # Final attempt failed
                if attempt == max_retries - 1:
                    logging.error(
                        f"Max retries ({max_retries}) exceeded for {path} - "
                        f"persistent 409 conflict detected"
                    )
                    raise
                
                # Exponential backoff: 0.5s, 1s, 2s...
                delay = 0.5 * (2 ** attempt)
                logging.warning(
                    f"409 conflict detected for {path} (attempt {attempt + 1}/{max_retries}), "
                    f"checking current content and retrying in {delay}s"
                )
                
                # Small delay to allow GitHub to stabilize
                time.sleep(delay)
                
                # Get current file state
                fresh_sha, fresh_content = self.github_client.get_file(path)
                
                if fresh_sha is None:
                    logging.error(f"File {path} disappeared during conflict resolution")
                    raise RuntimeError(f"File {path} not found during retry attempt")
                
                # Check if someone else already made our change
                if not self.github_client.has_changed(content, fresh_content):
                    logging.info(
                        f"File {path} already has our content (content match detected), "
                        f"skipping update"
                    )
                    # Return success without committing - content already matches
                    return {
                        "commit": {"sha": fresh_sha},
                        "content": {"sha": fresh_sha},
                        "message": "Content already up-to-date (no commit needed)"
                    }
                
                # Content still needs updating, retry with fresh SHA
                logging.info(
                    f"Content differs, retrying with fresh SHA: {fresh_sha} "
                    f"(attempt {attempt + 2}/{max_retries})"
                )
                sha = fresh_sha
        
        # Should never reach here, but safety net
        if last_error:
            raise last_error
        raise RuntimeError(f"Failed to update {path} after {max_retries} attempts")
    
    def _commit_changes(
        self,
        workbook: Dict[str, Any],
        workbook_id: str,
        display_name: str,
        metadata_json: str,
        definition_json: str,
        arm_json: Optional[str],
        metadata_path: str,
        definition_path: str,
        arm_path: Optional[str]
    ) -> List[Dict[str, str]]:
        """Check for changes and commit files to Git."""
        commits = []
        workbook_version = workbook.get("properties", {}).get("version", "unknown")
        commit_context = f"{display_name} (v{workbook_version}, id: {workbook_id[:8]}...)"
        
        # Check and commit metadata
        logging.info(f"Checking metadata file: {metadata_path}")
        metadata_sha, metadata_existing = self.github_client.get_file(metadata_path)
        logging.info(f"Metadata SHA retrieved: {metadata_sha}")
        
        if GitHubClient.has_changed(metadata_json, metadata_existing):
            logging.info(f"Metadata has changed, committing with SHA: {metadata_sha}")
            result = self._put_file_with_retry(
                metadata_path,
                metadata_json,
                f"Update workbook metadata: {commit_context}",
                metadata_sha
            )
            commits.append({
                "type": "metadata",
                "path": metadata_path,
                "sha": result.get("commit", {}).get("sha")
            })
        
        # Check and commit definition
        logging.info(f"Checking definition file: {definition_path}")
        definition_sha, definition_existing = self.github_client.get_file(definition_path)
        logging.info(f"Definition SHA retrieved: {definition_sha}")
        
        if GitHubClient.has_changed(definition_json, definition_existing):
            logging.info(f"Definition has changed, committing with SHA: {definition_sha}")
            result = self._put_file_with_retry(
                definition_path,
                definition_json,
                f"Update workbook definition: {commit_context}",
                definition_sha
            )
            commits.append({
                "type": "definition",
                "path": definition_path,
                "sha": result.get("commit", {}).get("sha")
            })
        
        # Check and commit ARM payload (if enabled)
        if arm_path and arm_json:
            arm_sha, arm_existing = self.github_client.get_file(arm_path)
            if GitHubClient.has_changed(arm_json, arm_existing):
                result = self._put_file_with_retry(
                    arm_path,
                    arm_json,
                    f"Update workbook ARM payload: {commit_context}",
                    arm_sha
                )
                commits.append({
                    "type": "arm",
                    "path": arm_path,
                    "sha": result.get("commit", {}).get("sha")
                })
        
        return commits


class WorkbookSyncService:
    """Service for syncing multiple workbooks."""
    
    def __init__(
        self,
        export_service: WorkbookExportService,
        azure_client: AzureWorkbookClient,
        config: Dict[str, Any]
    ):
        """
        Initialize sync service.
        
        Args:
            export_service: Workbook export service
            azure_client: Azure API client
            config: Configuration dictionary
        """
        self.export_service = export_service
        self.azure_client = azure_client
        self.config = config
    
    def sync_workbooks(self, subscription_id: str, resource_group: str) -> Dict[str, Any]:
        """
        Sync all workbooks matching the configured prefix.
        
        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            
        Returns:
            Dictionary with sync results (processed, skipped, failed counts and details)
        """
        workbooks = self.azure_client.list_workbooks(subscription_id, resource_group)
        
        processed = []
        skipped = []
        failed = []
        
        for wb in workbooks:
            workbook_id = wb.get("name")
            display_name = wb.get("properties", {}).get("displayName", "")
            
            if not display_name.startswith(self.config["WORKBOOK_NAME_PREFIX"]):
                skipped.append({
                    "workbookName": display_name,
                    "reason": "Does not match prefix"
                })
                continue
            
            try:
                result = self.export_service.export_workbook(subscription_id, resource_group, workbook_id)
                processed.append(result.to_dict())
            except ValueError as ex:
                # Validation error
                logging.warning(f"Skipping workbook {display_name} due to validation failure: {ex}")
                failed.append({
                    "workbookName": display_name,
                    "workbookId": workbook_id,
                    "error": str(ex),
                    "errorType": "validation"
                })
            except Exception as ex:
                # System error
                logging.exception(f"Failed exporting workbook {display_name}")
                failed.append({
                    "workbookName": display_name,
                    "workbookId": workbook_id,
                    "error": str(ex),
                    "errorType": "system"
                })
        
        return {
            "processedCount": len(processed),
            "skippedCount": len(skipped),
            "failedCount": len(failed),
            "processed": processed,
            "skipped": skipped,
            "failed": failed,
        }