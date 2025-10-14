"""Error handling utilities for user-friendly error messages.

Provides formatters and handlers for common error scenarios,
converting technical exceptions into actionable user guidance.
"""

import streamlit as st
from typing import Optional, Dict, Any, Callable
import traceback
import requests


class ErrorCategory:
    """Error category constants."""
    NETWORK = "network"
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    SERVER = "server"
    TIMEOUT = "timeout"
    PERMISSION = "permission"
    DATA = "data"
    UNKNOWN = "unknown"


class UserFriendlyError(Exception):
    """Exception with user-friendly message and recovery suggestions."""
    
    def __init__(
        self,
        message: str,
        category: str = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[list] = None,
        technical_details: Optional[str] = None
    ):
        self.message = message
        self.category = category
        self.details = details or {}
        self.suggestions = suggestions or []
        self.technical_details = technical_details
        super().__init__(self.message)


def format_error_message(error: Exception) -> Dict[str, Any]:
    """Format exception into user-friendly message components.
    
    Args:
        error: Exception to format
    
    Returns:
        Dictionary with message, category, suggestions, and technical details
    """
    if isinstance(error, UserFriendlyError):
        return {
            "message": error.message,
            "category": error.category,
            "suggestions": error.suggestions,
            "details": error.details,
            "technical": error.technical_details
        }
    
    # Handle requests exceptions
    if isinstance(error, requests.exceptions.ConnectionError):
        return {
            "message": "Cannot connect to backend server",
            "category": ErrorCategory.NETWORK,
            "suggestions": [
                "Check that the backend server is running",
                "Verify the backend URL in configuration",
                "Check your network connection",
                "Try refreshing the page"
            ],
            "technical": str(error)
        }
    
    if isinstance(error, requests.exceptions.Timeout):
        return {
            "message": "Request timed out",
            "category": ErrorCategory.TIMEOUT,
            "suggestions": [
                "Try again - the server may be temporarily busy",
                "Check if the dataset is very large (consider sampling)",
                "Verify server is responsive",
                "Contact administrator if problem persists"
            ],
            "technical": str(error)
        }
    
    if isinstance(error, requests.exceptions.HTTPError):
        status_code = error.response.status_code if error.response else 0
        
        if status_code == 404:
            return {
                "message": "Resource not found",
                "category": ErrorCategory.NOT_FOUND,
                "suggestions": [
                    "The dataset may have been deleted",
                    "Refresh the page to reload available datasets",
                    "Check the dataset ID is correct"
                ],
                "technical": f"HTTP 404: {error}"
            }
        
        elif status_code == 422:
            return {
                "message": "Validation error - invalid input",
                "category": ErrorCategory.VALIDATION,
                "suggestions": [
                    "Check that all required fields are filled",
                    "Verify data types match requirements",
                    "Review validation messages below",
                    "Try simplifying your configuration"
                ],
                "technical": f"HTTP 422: {error}"
            }
        
        elif status_code >= 500:
            return {
                "message": "Server error occurred",
                "category": ErrorCategory.SERVER,
                "suggestions": [
                    "Try again in a few moments",
                    "The issue may be temporary",
                    "If problem persists, contact support",
                    "Check server logs for details"
                ],
                "technical": f"HTTP {status_code}: {error}"
            }
    
    # Generic exception
    return {
        "message": f"An error occurred: {type(error).__name__}",
        "category": ErrorCategory.UNKNOWN,
        "suggestions": [
            "Try refreshing the page",
            "Check your inputs and try again",
            "Contact support if problem persists"
        ],
        "technical": f"{type(error).__name__}: {str(error)}\n{traceback.format_exc()}"
    }


def display_error(
    error: Exception,
    show_technical: bool = False,
    expandable_technical: bool = True
) -> None:
    """Display user-friendly error message in Streamlit.
    
    Args:
        error: Exception to display
        show_technical: Whether to show technical details by default
        expandable_technical: Whether to make technical details expandable
    """
    error_info = format_error_message(error)
    
    # Main error message
    icon = _get_category_icon(error_info['category'])
    st.error(f"{icon} **{error_info['message']}**")
    
    # Suggestions
    if error_info.get('suggestions'):
        st.markdown("**What you can do:**")
        for suggestion in error_info['suggestions']:
            st.markdown(f"- {suggestion}")
    
    # Technical details
    if error_info.get('technical'):
        if expandable_technical:
            with st.expander("🔧 Technical Details", expanded=show_technical):
                st.code(error_info['technical'], language="text")
        else:
            if show_technical:
                st.markdown("**Technical Details:**")
                st.code(error_info['technical'], language="text")


def handle_error(
    func: Callable,
    *args,
    on_error: Optional[Callable] = None,
    show_technical: bool = False,
    **kwargs
) -> Any:
    """Execute function with error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments for function
        on_error: Optional callback to execute on error
        show_technical: Whether to show technical details
        **kwargs: Keyword arguments for function
    
    Returns:
        Function result or None if error occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        display_error(e, show_technical=show_technical)
        
        if on_error:
            try:
                on_error(e)
            except:
                pass  # Don't let error handler fail
        
        return None


def validate_and_execute(
    func: Callable,
    validations: list[tuple[Callable, str]],
    *args,
    **kwargs
) -> Any:
    """Execute function with pre-execution validations.
    
    Args:
        func: Function to execute
        validations: List of (validation_func, error_message) tuples
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function
    
    Returns:
        Function result or None if validation failed
    """
    # Run validations
    for validation_func, error_message in validations:
        try:
            if not validation_func():
                st.error(f"⚠️ {error_message}")
                return None
        except Exception as e:
            st.error(f"⚠️ Validation error: {error_message}")
            display_error(e, expandable_technical=True)
            return None
    
    # Execute function
    return handle_error(func, *args, **kwargs)


def create_retry_handler(
    func: Callable,
    max_retries: int = 3,
    retry_message: str = "Retrying..."
) -> Callable:
    """Create a retry wrapper for a function.
    
    Args:
        func: Function to wrap
        max_retries: Maximum number of retry attempts
        retry_message: Message to display during retry
    
    Returns:
        Wrapped function with retry logic
    """
    def wrapper(*args, **kwargs):
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if attempt < max_retries - 1:
                    st.warning(f"{retry_message} (Attempt {attempt + 2}/{max_retries})")
                    # Could add exponential backoff here
                else:
                    display_error(e)
        
        return None
    
    return wrapper


def _get_category_icon(category: str) -> str:
    """Get icon for error category.
    
    Args:
        category: Error category
    
    Returns:
        Emoji icon
    """
    icons = {
        ErrorCategory.NETWORK: "🌐",
        ErrorCategory.VALIDATION: "⚠️",
        ErrorCategory.NOT_FOUND: "🔍",
        ErrorCategory.SERVER: "🔥",
        ErrorCategory.TIMEOUT: "⏱️",
        ErrorCategory.PERMISSION: "🔒",
        ErrorCategory.DATA: "📊",
        ErrorCategory.UNKNOWN: "❌"
    }
    
    return icons.get(category, "❌")


# Common validation error creators
def create_validation_error(
    field: str,
    issue: str,
    expected: Optional[str] = None
) -> UserFriendlyError:
    """Create a validation error.
    
    Args:
        field: Field name that failed validation
        issue: Description of the issue
        expected: What was expected (optional)
    
    Returns:
        UserFriendlyError instance
    """
    message = f"Invalid {field}: {issue}"
    
    suggestions = [f"Check the {field} value and try again"]
    if expected:
        suggestions.append(f"Expected: {expected}")
    
    return UserFriendlyError(
        message=message,
        category=ErrorCategory.VALIDATION,
        suggestions=suggestions,
        details={"field": field, "issue": issue, "expected": expected}
    )


def create_data_error(
    issue: str,
    affected: Optional[str] = None
) -> UserFriendlyError:
    """Create a data-related error.
    
    Args:
        issue: Description of the data issue
        affected: What data is affected
    
    Returns:
        UserFriendlyError instance
    """
    message = f"Data issue: {issue}"
    
    suggestions = [
        "Check your data quality",
        "Review preprocessing options",
        "Consider filtering problematic rows/columns"
    ]
    
    if affected:
        suggestions.insert(0, f"Affected: {affected}")
    
    return UserFriendlyError(
        message=message,
        category=ErrorCategory.DATA,
        suggestions=suggestions,
        details={"issue": issue, "affected": affected}
    )
