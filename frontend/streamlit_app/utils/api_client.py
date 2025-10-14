"""API client for communicating with the RelatAI backend service."""

from __future__ import annotations

import io
from typing import Any, Optional

import requests
import streamlit as st

from config import CONFIG


class APIError(Exception):
    """Base exception for API-related errors."""
    
    def __init__(self, message: str, status_code: int, details: Optional[dict[str, Any]] = None):
        """
        Initialize API error with details.
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code
            details: Additional error details from API response
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class RelatAIClient:
    """
    Client for interacting with the RelatAI backend REST API.
    
    Provides methods for dataset management, configuration, analysis execution,
    and result retrieval. Includes error handling, retry logic, and response caching.
    
    Attributes:
        base_url: Base URL of the backend API
        session: Requests session for connection pooling
        timeout: Default timeout for API requests
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize the API client.
        
        Args:
            base_url: Backend API base URL (defaults to CONFIG.backend_url)
            timeout: Request timeout in seconds (defaults to CONFIG.api_timeout)
        """
        self.base_url = (base_url or CONFIG.backend_url).rstrip('/')
        self.timeout = timeout or CONFIG.api_timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"RelatAI-Frontend/{CONFIG.page_title}",
        })
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any
    ) -> requests.Response:
        """
        Make an HTTP request to the backend API with error handling.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path (e.g., "/datasets")
            **kwargs: Additional arguments passed to requests
        
        Returns:
            Response object from the API
        
        Raises:
            APIError: If the request fails or returns an error status
        """
        url = f"{self.base_url}{endpoint}"
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Raise exception for 4xx and 5xx status codes
            if not response.ok:
                try:
                    error_detail = response.json()
                except Exception:
                    error_detail = {"detail": response.text}
                
                raise APIError(
                    message=error_detail.get("detail", f"HTTP {response.status_code}"),
                    status_code=response.status_code,
                    details=error_detail
                )
            
            return response
            
        except requests.exceptions.Timeout:
            raise APIError(
                message=f"Request timed out after {self.timeout} seconds",
                status_code=408,
                details={"timeout": self.timeout}
            )
        except requests.exceptions.ConnectionError:
            raise APIError(
                message=f"Cannot connect to backend at {self.base_url}. Is the server running?",
                status_code=503,
                details={"base_url": self.base_url}
            )
        except requests.exceptions.RequestException as e:
            raise APIError(
                message=f"Request failed: {str(e)}",
                status_code=500,
                details={"exception": str(e)}
            )
    
    # -------------------------------------------------------------------------
    # Dataset Operations
    # -------------------------------------------------------------------------
    
    def upload_dataset(self, file: io.BytesIO, filename: str) -> dict[str, Any]:
        """
        Upload a dataset file to the backend.
        
        Args:
            file: File-like object containing the dataset
            filename: Original filename with extension
        
        Returns:
            Dictionary containing dataset metadata and profile:
            {
                "dataset_id": str,
                "filename": str,
                "size_bytes": int,
                "uploaded_at": str (ISO timestamp),
                "profile": {
                    "row_count": int,
                    "column_count": int,
                    "columns": [...]
                }
            }
        
        Raises:
            APIError: If upload fails or file is rejected
        """
        files = {"file": (filename, file, "application/octet-stream")}
        response = self._make_request("POST", "/datasets", files=files)
        return response.json()
    
    def get_dataset(self, dataset_id: str) -> dict[str, Any]:
        """
        Retrieve metadata and profile for an existing dataset.
        
        Args:
            dataset_id: Unique identifier for the dataset
        
        Returns:
            Dictionary containing dataset metadata and profile
        
        Raises:
            APIError: If dataset not found or retrieval fails
        """
        response = self._make_request("GET", f"/datasets/{dataset_id}")
        return response.json()
    
    def list_datasets(self) -> list[dict[str, Any]]:
        """
        List all uploaded datasets.
        
        Returns:
            List of dataset metadata dictionaries
        
        Raises:
            APIError: If listing fails
        """
        response = self._make_request("GET", "/datasets")
        return response.json()
    
    # -------------------------------------------------------------------------
    # Configuration Operations
    # -------------------------------------------------------------------------
    
    def get_configuration(self, dataset_id: str) -> dict[str, Any]:
        """
        Get the current configuration for a dataset.
        
        Args:
            dataset_id: Unique identifier for the dataset
        
        Returns:
            Dictionary containing configuration settings:
            {
                "dataset_id": str,
                "selected_columns": list[str],
                "filters": dict[str, list],
                "analysis_mode": str,
                "max_variables": int,
                "interaction_depth": int,
                "anchor_columns": list[str]
            }
        
        Raises:
            APIError: If dataset not found or retrieval fails
        """
        response = self._make_request("GET", f"/datasets/{dataset_id}/configuration")
        return response.json()
    
    def update_configuration(
        self,
        dataset_id: str,
        updates: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update configuration options for a dataset.
        
        Args:
            dataset_id: Unique identifier for the dataset
            updates: Dictionary of configuration updates:
                - selected_columns: list[str] (optional)
                - filters: dict[str, list] or null (optional)
                - analysis_mode: str (optional)
                - max_variables: int (optional)
                - interaction_depth: int (optional)
                - anchor_columns: list[str] (optional)
        
        Returns:
            Updated configuration dictionary
        
        Raises:
            APIError: If update fails or validation errors occur
        """
        response = self._make_request(
            "PATCH",
            f"/datasets/{dataset_id}/configuration",
            json=updates
        )
        return response.json()
    
    def preview_configuration(
        self,
        dataset_id: str,
        limit: int = 50
    ) -> dict[str, Any]:
        """
        Preview the dataset after applying current configuration filters.
        
        Args:
            dataset_id: Unique identifier for the dataset
            limit: Maximum number of rows to return (default: 50, max: 500)
        
        Returns:
            Dictionary containing preview data:
            {
                "dataset_id": str,
                "row_count": int (total after filters),
                "columns": list[str],
                "preview": list[dict] (first N rows as records)
            }
        
        Raises:
            APIError: If preview generation fails
        """
        response = self._make_request(
            "GET",
            f"/datasets/{dataset_id}/configuration/preview",
            params={"limit": limit}
        )
        return response.json()
    
    # -------------------------------------------------------------------------
    # Template Operations
    # -------------------------------------------------------------------------
    
    def list_templates(self, dataset_id: str) -> list[dict[str, Any]]:
        """
        List all configuration templates for a dataset.
        
        Args:
            dataset_id: Unique identifier for the dataset
        
        Returns:
            List of template dictionaries with id, name, description, configuration
        
        Raises:
            APIError: If listing fails
        """
        response = self._make_request("GET", f"/datasets/{dataset_id}/templates")
        return response.json()
    
    def create_template(
        self,
        dataset_id: str,
        name: str,
        description: Optional[str] = None,
        configuration: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Create a new configuration template.
        
        Args:
            dataset_id: Unique identifier for the dataset
            name: Template name
            description: Optional template description
            configuration: Configuration to save (uses current if None)
        
        Returns:
            Created template dictionary with generated template_id
        
        Raises:
            APIError: If creation fails or validation errors occur
        """
        payload = {
            "name": name,
            "description": description,
            "configuration": configuration
        }
        response = self._make_request(
            "POST",
            f"/datasets/{dataset_id}/templates",
            json=payload
        )
        return response.json()
    
    def get_template(self, dataset_id: str, template_id: str) -> dict[str, Any]:
        """
        Retrieve a specific configuration template.
        
        Args:
            dataset_id: Unique identifier for the dataset
            template_id: Unique identifier for the template
        
        Returns:
            Template dictionary
        
        Raises:
            APIError: If template not found
        """
        response = self._make_request(
            "GET",
            f"/datasets/{dataset_id}/templates/{template_id}"
        )
        return response.json()
    
    def apply_template(self, dataset_id: str, template_id: str) -> dict[str, Any]:
        """
        Apply a configuration template to a dataset.
        
        Args:
            dataset_id: Unique identifier for the dataset
            template_id: Unique identifier for the template
        
        Returns:
            Updated configuration dictionary
        
        Raises:
            APIError: If template not found or application fails
        """
        response = self._make_request(
            "POST",
            f"/datasets/{dataset_id}/templates/{template_id}/apply"
        )
        return response.json()
    
    def delete_template(self, dataset_id: str, template_id: str) -> None:
        """
        Delete a configuration template.
        
        Args:
            dataset_id: Unique identifier for the dataset
            template_id: Unique identifier for the template
        
        Raises:
            APIError: If template not found or deletion fails
        """
        self._make_request(
            "DELETE",
            f"/datasets/{dataset_id}/templates/{template_id}"
        )
    
    # -------------------------------------------------------------------------
    # Audit Operations
    # -------------------------------------------------------------------------
    
    def get_audit_logs(self, dataset_id: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Retrieve audit trail logs.
        
        Args:
            dataset_id: Optional dataset filter (returns all if None)
        
        Returns:
            List of audit log entries with timestamps, actions, and details
        
        Raises:
            APIError: If retrieval fails
        """
        if dataset_id:
            endpoint = f"/audit/{dataset_id}"
        else:
            endpoint = "/audit/"
        
        response = self._make_request("GET", endpoint)
        return response.json()
    
    # -------------------------------------------------------------------------
    # Analysis Operations
    # -------------------------------------------------------------------------
    
    def run_analysis(
        self,
        dataset_id: str,
        mode: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Execute statistical analysis on configured dataset.
        
        Performs correlation, multivariate, or auto-triage analysis based on
        the specified mode or the dataset's configured analysis mode.
        
        Args:
            dataset_id: Unique identifier for the dataset
            mode: Optional analysis mode override:
                - "correlation": Pairwise correlations
                - "multivariate": Regression modeling
                - "auto_triage": Anomaly detection and triage
            parameters: Optional configuration overrides:
                - selected_columns: list[str]
                - anchor_columns: list[str]
                - filters: dict[str, list]
                - max_variables: int
                - interaction_depth: int
                - include_interactions: bool
        
        Returns:
            Analysis result dictionary containing:
                - dataset_id: str
                - analysis_id: str (unique ID for this analysis run)
                - analysis_mode: str
                - configuration: dict (configuration used)
                - cached: bool (whether result was from cache)
                - result: dict (serialized analysis results with visualizations)
        
        Raises:
            APIError: If analysis fails, dataset not found, or validation errors
        
        Note:
            Results are cached by the backend. Identical configurations will
            return cached results with cached=True in the response.
        """
        payload: dict[str, Any] = {}
        
        if mode is not None:
            payload["mode"] = mode
        
        if parameters is not None:
            payload["parameters"] = parameters
        
        # Analysis can take time, use extended timeout
        response = self._make_request(
            "POST",
            f"/datasets/{dataset_id}/analyze",
            json=payload if payload else None,
            timeout=120  # 2 minute timeout for long-running analyses
        )
        return response.json()
    
    # -------------------------------------------------------------------------
    # Health & Status Operations
    # -------------------------------------------------------------------------
    
    def health_check(self) -> dict[str, Any]:
        """
        Check backend API health status.
        
        Returns:
            Health status dictionary with version info
        
        Raises:
            APIError: If health check fails
        """
        response = self._make_request("GET", "/health")
        return response.json()


def get_client() -> RelatAIClient:
    """
    Get or create the API client singleton instance.
    
    Uses Streamlit session state to cache the client instance
    across reruns within a user session.
    
    Returns:
        RelatAIClient: Configured API client instance
    """
    if "api_client" not in st.session_state:
        st.session_state.api_client = RelatAIClient()
    
    return st.session_state.api_client


def handle_api_error(error: APIError) -> None:
    """
    Display user-friendly error messages in the Streamlit UI.
    
    Args:
        error: APIError exception containing status code and details
    """
    if error.status_code == 404:
        st.error(f"❌ Not Found: {error.message}")
        st.info("The requested resource was not found. It may have been deleted.")
    
    elif error.status_code == 422:
        st.error("⚠️ Validation Error")
        st.write("Please check your input and try again:")
        
        # Display field-specific errors if available
        if "detail" in error.details and isinstance(error.details["detail"], list):
            for field_error in error.details["detail"]:
                field = field_error.get("loc", ["unknown"])[-1]
                msg = field_error.get("msg", "Invalid value")
                st.warning(f"**{field}:** {msg}")
        else:
            st.warning(error.message)
    
    elif error.status_code == 503:
        st.error("🔌 Cannot Connect to Backend")
        st.write(error.message)
        st.info(
            f"Please ensure the backend server is running at `{CONFIG.backend_url}`. "
            "You can start it with `make run` from the backend directory."
        )
    
    elif error.status_code == 408:
        st.error("⏱️ Request Timeout")
        st.write(f"The request took longer than {CONFIG.api_timeout} seconds.")
        st.info("Try again, or check if the backend is experiencing performance issues.")
    
    elif error.status_code >= 500:
        st.error(f"🔥 Server Error: {error.message}")
        st.write("An error occurred on the backend server.")
        
        if CONFIG.debug_mode:
            with st.expander("Technical Details (Debug Mode)"):
                st.json(error.details)
    
    else:
        st.error(f"❌ Error: {error.message}")
        
        if CONFIG.debug_mode and error.details:
            with st.expander("Error Details"):
                st.json(error.details)
