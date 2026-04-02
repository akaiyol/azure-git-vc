"""
GitHub Enterprise API client for repository operations.
"""

import base64
import logging
from typing import Optional, Dict, Tuple, Any
import requests


class GitHubClient:
    """Client for interacting with GitHub Enterprise API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize GitHub client.
        
        Args:
            config: Configuration dictionary with GitHub settings
        """
        self.config = config
        self.base_url = config["GIT_BASE_URL"]
        self.owner = config["GIT_OWNER"]
        self.repo = config["GIT_REPO"]
        self.branch = config["GIT_BRANCH"]
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for GitHub API requests."""
        return {
            "Authorization": f"token {self.config['GIT_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }
    
    def get_file(self, path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get file from repository.
        
        Args:
            path: File path in repository
            
        Returns:
            Tuple of (sha, base64_content) if file exists, (None, None) otherwise
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{path}"
        
        logging.info(f"GET file: {path} on branch: {self.branch}")
        
        resp = requests.get(
            url,
            headers=self._get_headers(),
            params={"ref": self.branch},
            timeout=30
        )
        
        if resp.status_code == 404:
            logging.info(f"File {path} does not exist on branch {self.branch}")
            return None, None
        
        if resp.status_code == 200:
            data = resp.json()
            sha = data["sha"]
            logging.info(f"File {path} exists on branch {self.branch}, SHA: {sha}")
            return sha, data["content"]
        
        # Unexpected status code
        logging.error(f"Unexpected status {resp.status_code} for GET {path}: {resp.text}")
        resp.raise_for_status()
        
        return None, None
    
    def put_file(
        self,
        path: str,
        content: str,
        message: str,
        sha: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update file in repository.
        
        Args:
            path: File path in repository
            content: File content (will be base64 encoded)
            message: Commit message
            sha: Existing file SHA for updates (None for new files)
            
        Returns:
            GitHub API response data
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{path}"
        
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": self.branch,
        }
        
        if sha:
            payload["sha"] = sha
            logging.info(f"PUT (UPDATE) file: {path} on branch: {self.branch} with SHA: {sha}")
        else:
            logging.info(f"PUT (CREATE) file: {path} on branch: {self.branch} (no SHA)")
        
        try:
            resp = requests.put(url, headers=self._get_headers(), json=payload, timeout=30)
            
            logging.info(
                f"GitHub PUT response: status={resp.status_code} url={resp.url} branch={self.branch} path={path} used_sha={sha}"
            )
            
            if resp.status_code not in (200, 201):
                # Use structured error with full context
                body = None
                try:
                    body = resp.json()
                except Exception:
                    body = resp.text

                details = {
                    "status_code": resp.status_code,
                    "url": resp.url,
                    "response_body": body,
                    "step": "put_file",
                    "branch": self.branch,
                    "path": path,
                    "used_sha": sha,
                    "payload_keys": sorted(payload.keys())
                }

                import json
                error_msg = json.dumps(details, indent=2, default=str)
                logging.error(f"GitHub API error: {error_msg}")
                raise RuntimeError(error_msg)
            
            result = resp.json()
            commit_sha = result.get("commit", {}).get("sha", "unknown")
            logging.info(f"Successfully committed {path}, commit SHA: {commit_sha}")
            return result
        except RuntimeError:
            # Re-raise our structured errors
            raise
        except requests.exceptions.HTTPError as e:
            logging.error(f"PUT failed for {path}: {e.response.status_code} - {e.response.text}")
            logging.error(f"Payload was: branch={self.branch}, sha={sha}, message={message[:50]}...")
            raise
    
    @staticmethod
    def has_changed(new_content: str, existing_b64_content: Optional[str]) -> bool:
        """
        Check if content has changed compared to existing file.
        
        Args:
            new_content: New file content
            existing_b64_content: Existing file content (base64 encoded)
            
        Returns:
            True if content has changed or file doesn't exist
        """
        if not existing_b64_content:
            return True
        
        old_content = base64.b64decode(existing_b64_content).decode("utf-8")
        return old_content != new_content