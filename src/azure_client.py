"""
Azure API client for workbook operations.
"""

import logging
from typing import List, Dict, Any
import requests

from .config import CredentialManager


class AzureWorkbookClient:
    """Client for interacting with Azure Workbooks API."""
    
    MGMT_BASE_URL = "https://management.azure.com"
    API_VERSION = "2021-08-01"
    
    def __init__(self):
        self.base_url = self.MGMT_BASE_URL
        self.api_version = self.API_VERSION
    
    def _get_token(self) -> str:
        """Get Azure management API access token."""
        credential = CredentialManager.get_credential()
        token = credential.get_token("https://management.azure.com/.default")
        return token.token
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Azure API requests."""
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }
    
    def list_workbooks(self, subscription_id: str, resource_group: str) -> List[Dict[str, Any]]:
        """
        List all workbooks in a resource group.
        
        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            
        Returns:
            List of workbook resources
        """
        url = (
            f"{self.base_url}/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group}"
            f"/providers/Microsoft.Insights/workbooks"
            f"?api-version={self.api_version}"
        )
        
        resp = requests.get(url, headers=self._get_headers(), timeout=30)
        resp.raise_for_status()
        return resp.json().get("value", [])
    
    def get_workbook(self, subscription_id: str, resource_group: str, workbook_id: str) -> Dict[str, Any]:
        """
        Get a specific workbook by ID.
        
        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            workbook_id: Workbook resource ID
            
        Returns:
            Workbook resource data
        """
        url = (
            f"{self.base_url}/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group}"
            f"/providers/Microsoft.Insights/workbooks/{workbook_id}"
            f"?api-version={self.api_version}&canFetchContent=true"
        )
        
        resp = requests.get(url, headers=self._get_headers(), timeout=30)
        resp.raise_for_status()
        workbook = resp.json()
        
        # Diagnostic logging
        has_serialized_data = bool(workbook.get("properties", {}).get("serializedData"))
        logging.info(
            "Fetched workbook %s - serializedData present: %s",
            workbook.get("id", "unknown"),
            has_serialized_data
        )
        
        return workbook