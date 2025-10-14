"""Configuration settings for the Streamlit frontend application."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Application configuration with backend API settings and UI preferences."""
    
    # Backend API Configuration
    backend_url: str
    api_timeout: int  # seconds
    
    # UI Configuration
    page_title: str
    page_icon: str
    layout: str
    
    # Upload Configuration
    max_upload_size_mb: int
    allowed_extensions: tuple[str, ...]
    
    # Performance Settings
    preview_row_limit: int
    chart_render_timeout: int  # seconds
    
    # Feature Flags
    enable_ai_summary: bool
    enable_export: bool
    debug_mode: bool


def load_config() -> AppConfig:
    """
    Load configuration from environment variables with sensible defaults.
    
    Returns:
        AppConfig: Application configuration instance.
    
    Environment Variables:
        BACKEND_URL: Base URL for the RelatAI backend API (default: http://localhost:8000)
        API_TIMEOUT: Timeout for API requests in seconds (default: 30)
        PAGE_TITLE: Application title (default: RelatAI)
        MAX_UPLOAD_SIZE_MB: Maximum upload file size (default: 100)
        PREVIEW_ROW_LIMIT: Maximum rows in preview tables (default: 50)
        ENABLE_AI_SUMMARY: Enable AI summarization features (default: False)
        ENABLE_EXPORT: Enable export functionality (default: True)
        DEBUG_MODE: Enable debug utilities and logging (default: False)
    """
    return AppConfig(
        # Backend settings - read from environment or use localhost default
        backend_url=os.getenv("BACKEND_URL", "http://localhost:8000"),
        api_timeout=int(os.getenv("API_TIMEOUT", "30")),
        
        # UI settings
        page_title=os.getenv("PAGE_TITLE", "RelatAI"),
        page_icon="📊",
        layout="wide",
        
        # Upload settings
        max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "100")),
        allowed_extensions=("csv", "xlsx", "xls", "parquet"),
        
        # Performance settings
        preview_row_limit=int(os.getenv("PREVIEW_ROW_LIMIT", "50")),
        chart_render_timeout=int(os.getenv("CHART_RENDER_TIMEOUT", "10")),
        
        # Feature flags
        enable_ai_summary=os.getenv("ENABLE_AI_SUMMARY", "false").lower() == "true",
        enable_export=os.getenv("ENABLE_EXPORT", "true").lower() == "true",
        debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
    )


# Global configuration instance
CONFIG = load_config()
