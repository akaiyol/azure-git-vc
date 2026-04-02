"""
Path generation utilities for workbook files.
"""

from typing import Tuple, Optional


class PathManager:
    """Manages file path generation for workbooks."""
    
    DEFAULT_FOLDER = "misc"
    
    @staticmethod
    def sanitize_filename(text: str) -> str:
        """
        Sanitize text for use in filenames.
        
        - Converts to lowercase
        - Replaces spaces with hyphens
        - Keeps only alphanumeric, hyphens, and underscores
        - Removes consecutive hyphens
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized filename-safe string
        """
        text = text.strip().lower().replace(" ", "-")
        allowed = []
        
        for ch in text:
            if ch.isalnum() or ch in "-_":
                allowed.append(ch)
            else:
                allowed.append("-")
        
        cleaned = "".join(allowed)
        
        # Remove consecutive dashes
        while "--" in cleaned:
            cleaned = cleaned.replace("--", "-")
        
        return cleaned.strip("-_")
    
    @staticmethod
    def generate_paths(
        display_name: str,
        prefix: str,
        preserve_arm: bool
    ) -> Tuple[str, str, Optional[str]]:
        """
        Generate repository paths for workbook files.
        
        All workbooks are placed under the workbooks/ directory.
        
        Naming convention:
            {prefix}-{folder}-{name} -> workbooks/{folder}/{name}/metadata.json
                                        workbooks/{folder}/{name}/definition.json
            
        Example:
            workbook-security-audit -> workbooks/security/audit/metadata.json
                                       workbooks/security/audit/definition.json
            workbook-cost-analysis -> workbooks/cost/analysis/metadata.json
                                      workbooks/cost/analysis/definition.json
        
        Args:
            display_name: Workbook display name
            prefix: Workbook name prefix to match
            preserve_arm: Whether to generate ARM payload path
            
        Returns:
            Tuple of (metadata_path, definition_path, arm_path_or_none)
        """
        name = PathManager.sanitize_filename(display_name)
        sanitized_prefix = PathManager.sanitize_filename(prefix).rstrip("-")
        
        # Check if name matches prefix pattern
        if not name.startswith(sanitized_prefix + "-"):
            return PathManager._fallback_paths(name, preserve_arm)
        
        parts = name.split("-")
        if len(parts) >= 3:
            folder = parts[1]
            workbook_name = "-".join(parts[2:])
            return (
                f"workbooks/{folder}/{workbook_name}/metadata.json",
                f"workbooks/{folder}/{workbook_name}/definition.json",
                f"workbooks/{folder}/{workbook_name}/arm.json" if preserve_arm else None
            )
        
        return PathManager._fallback_paths(name, preserve_arm)
    
    @staticmethod
    def _fallback_paths(name: str, preserve_arm: bool) -> Tuple[str, str, Optional[str]]:
        """
        Generate fallback paths for workbooks without standard naming.
        
        Args:
            name: Sanitized workbook name
            preserve_arm: Whether to generate ARM payload path
            
        Returns:
            Tuple of paths in workbooks/misc/ folder
        """
        return (
            f"workbooks/{PathManager.DEFAULT_FOLDER}/{name}-metadata.json",
            f"workbooks/{PathManager.DEFAULT_FOLDER}/{name}-definition.json",
            f"workbooks/{PathManager.DEFAULT_FOLDER}/{name}-arm.json" if preserve_arm else None
        )
