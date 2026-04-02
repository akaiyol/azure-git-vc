"""
Data models for the Workbook Export application.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Any


@dataclass
class ValidationResult:
    """Result of workbook validation."""
    is_valid: bool
    error_message: Optional[str]
    workbook_definition: Optional[Dict[str, Any]]
    
    @property
    def has_serialized_data(self) -> bool:
        """Check if the definition came from serializedData or is the full workbook."""
        if not self.workbook_definition:
            return False
        # If it has 'properties' and 'id', it's likely the full workbook
        return not ('properties' in self.workbook_definition and 'id' in self.workbook_definition)


@dataclass
class WorkbookExportResult:
    """Result of a workbook export operation."""
    message: str
    workbook_name: str
    metadata_path: str
    definition_path: str
    arm_path: Optional[str]
    commits: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "message": self.message,
            "workbookName": self.workbook_name,
            "metadataPath": self.metadata_path,
            "definitionPath": self.definition_path,
            "armPath": self.arm_path,
            "commits": self.commits
        }