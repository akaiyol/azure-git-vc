"""
File preparation utilities for workbook exports.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional, Any


class WorkbookFilePreparation:
    """Prepares workbook export files."""
    
    @staticmethod
    def prepare_metadata(workbook: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare metadata export (ARM resource WITHOUT serializedData).
        
        Args:
            workbook: Workbook resource data
            
        Returns:
            Metadata dictionary ready for export
        """
        properties = workbook.get('properties', {})
        
        return {
            "exportMetadata": {
                "exportedAt": datetime.utcnow().isoformat() + "Z",
                "exportVersion": "1.0",
                "resourceId": workbook.get('id', ''),
                "resourceName": workbook.get('name', 'unnamed'),
                "displayName": properties.get('displayName', workbook.get('name', 'unnamed')),
                "location": workbook.get('location', '')
            },
            "resource": {
                "id": workbook.get('id', ''),
                "name": workbook.get('name', 'unnamed'),
                "type": workbook.get('type', ''),
                "location": workbook.get('location', ''),
                "tags": workbook.get('tags', {}),
                "kind": workbook.get('kind'),
                "etag": workbook.get('etag'),
                "properties": {
                    key: value for key, value in properties.items() 
                    if key != 'serializedData'
                }
            }
        }
    
    @staticmethod
    def normalize_definition(parsed_definition: Dict[str, Any], workbook: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize the workbook definition by adding standard fields if missing.
        
        Args:
            parsed_definition: Parsed serializedData
            workbook: Full workbook resource (for fallback values)
            
        Returns:
            Normalized definition with $schema and fallbackResourceIds
        """
        result = dict(parsed_definition)
        
        # Add $schema if missing (standard workbook schema)
        if "$schema" not in result:
            result["$schema"] = (
                "https://github.com/Microsoft/Application-Insights-Workbooks/blob/master/schema/workbook.json"
            )
        
        # Add fallbackResourceIds if missing
        if "fallbackResourceIds" not in result:
            source_id = workbook.get("properties", {}).get("sourceId")
            if source_id:
                result["fallbackResourceIds"] = [source_id]
        
        return result
    
    @staticmethod
    def canonicalize_json(data: Dict[str, Any]) -> str:
        """
        Convert dictionary to canonical JSON string.
        
        Uses sorted keys and 2-space indentation for consistent diffs.
        
        Args:
            data: Dictionary to convert
            
        Returns:
            Formatted JSON string
        """
        return json.dumps(data, indent=2, sort_keys=True)
    
    @staticmethod
    def prepare_files(
        workbook: Dict[str, Any],
        workbook_definition: Dict[str, Any],
        preserve_arm: bool
    ) -> Tuple[str, str, Optional[str]]:
        """
        Prepare all export files.
        
        - Metadata: ARM resource without serializedData
        - Definition: Normalized parsed serializedData (the workbook body)
        - ARM (optional): Complete raw ARM response
        
        Args:
            workbook: Complete workbook resource data
            workbook_definition: Parsed serializedData (workbook body)
            preserve_arm: Whether to preserve full ARM payload
            
        Returns:
            Tuple of (metadata_json, definition_json, arm_json_or_none)
        """
        # Prepare metadata (ARM resource without serializedData)
        metadata = WorkbookFilePreparation.prepare_metadata(workbook)
        metadata_json = WorkbookFilePreparation.canonicalize_json(metadata)
        
        # Normalize and prepare definition (parsed serializedData with standard fields)
        normalized_definition = WorkbookFilePreparation.normalize_definition(
            workbook_definition,
            workbook
        )
        definition_json = WorkbookFilePreparation.canonicalize_json(normalized_definition)
        
        logging.info("Definition prepared from serializedData (workbook body)")
        
        # Optional: preserve full ARM payload
        arm_json = None
        if preserve_arm:
            arm_json = WorkbookFilePreparation.canonicalize_json(workbook)
        
        return metadata_json, definition_json, arm_json