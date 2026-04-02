"""
Workbook validation logic.

This module enforces STRICT validation: properties.serializedData must exist
and contain valid JSON. The ARM resource metadata alone is NOT sufficient for
workbook version control.
"""

import json
import logging
from typing import Dict, Any

from .models import ValidationResult


class WorkbookValidator:
    """Validates workbook content and structure."""
    
    @staticmethod
    def validate(workbook: Dict[str, Any]) -> ValidationResult:
        """
        Validate that the workbook has valid serializedData.
        
        This is STRICT validation - the workbook MUST have properties.serializedData
        containing the actual workbook body. The ARM resource metadata alone is not
        sufficient for version control of workbook content.
        
        Args:
            workbook: Workbook resource data from Azure API
            
        Returns:
            ValidationResult with validation status and parsed definition
        """
        workbook_id = workbook.get('id', '<unknown>')
        properties = workbook.get('properties')
        
        # Check 1: properties exists and is a dict
        if not isinstance(properties, dict):
            return ValidationResult(
                is_valid=False,
                error_message=(
                    f"Workbook content is missing: properties not found. "
                    f"Workbook ID: {workbook_id}"
                ),
                workbook_definition=None
            )
        
        # Log available property keys for diagnostics
        property_keys = list(properties.keys())
        logging.info(
            "Validating workbook %s - properties keys: %s",
            workbook_id,
            property_keys
        )
        
        # Check 2: serializedData must exist and be non-null
        serialized_data = properties.get('serializedData')
        if not serialized_data:
            logging.error(
                "Workbook %s has no serializedData (value: %s). Cannot export workbook content.",
                workbook_id,
                repr(serialized_data)
            )
            return ValidationResult(
                is_valid=False,
                error_message=(
                    f"Workbook content is missing: properties.serializedData not found or null. "
                    f"Workbook ID: {workbook_id}. "
                    f"Available properties: {property_keys}"
                ),
                workbook_definition=None
            )
        
        # Check 3: Parse JSON
        try:
            workbook_definition = json.loads(serialized_data)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                error_message=(
                    f"Workbook content is invalid: properties.serializedData could not be parsed as JSON. "
                    f"Workbook ID: {workbook_id}. Error: {str(e)}"
                ),
                workbook_definition=None
            )
        
        # Check 4: Result must be a dictionary (JSON object)
        if not isinstance(workbook_definition, dict):
            return ValidationResult(
                is_valid=False,
                error_message=(
                    f"Workbook content is invalid: properties.serializedData must parse to a JSON object. "
                    f"Got {type(workbook_definition).__name__}. Workbook ID: {workbook_id}"
                ),
                workbook_definition=None
            )
        
        logging.info("✓ Workbook %s validated successfully", workbook_id)
        return ValidationResult(
            is_valid=True,
            error_message=None,
            workbook_definition=workbook_definition
        )