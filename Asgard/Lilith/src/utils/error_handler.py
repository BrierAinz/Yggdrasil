"""
Enhanced error handling for Lilith v2.0
Provides user-friendly error messages and suggestions
"""

import re
import traceback
from typing import Any, Dict, Optional


class ErrorHandler:
    """Converts technical errors into user-friendly messages"""

    ERROR_PATTERNS = {
        r"Permission denied": {
            "message": "Permission denied. This usually means Lilith needs administrator privileges.",
            "suggestion": "Try running: Right-click -> Run as Administrator",
            "category": "permission",
        },
        r"File not found|No such file or directory": {
            "message": "File or directory not found.",
            "suggestion": "Check the path and ensure the file exists. Use @plan to search for files if needed.",
            "category": "not_found",
        },
        r"Command not found|is not recognized": {
            "message": "Command not found. The tool may not be installed or not in PATH.",
            "suggestion": "Ensure the tool is installed and added to your system PATH.",
            "category": "not_installed",
        },
        r"timeout|timed out": {
            "message": "Operation timed out. This step took too long to complete.",
            "suggestion": "Try increasing the timeout or breaking the task into smaller steps.",
            "category": "timeout",
        },
        r"Connection|network|internet": {
            "message": "Network connection issue.",
            "suggestion": "Check your internet connection and try again.",
            "category": "network",
        },
    }

    @staticmethod
    def process_error(
        error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Convert exception to user-friendly message"""

        error_str = str(error).lower()
        error_type = type(error).__name__

        # Find matching pattern
        for pattern, info in ErrorHandler.ERROR_PATTERNS.items():
            if re.search(pattern, error_str, re.IGNORECASE):
                return {
                    "error_type": error_type,
                    "category": info["category"],
                    "message": info["message"],
                    "suggestion": info["suggestion"],
                    "technical_details": str(error),
                }

        # Generic fallback
        return {
            "error_type": error_type,
            "category": "unknown",
            "message": f"An error occurred: {str(error)[:100]}...",
            "suggestion": "Check the logs for more details or try breaking the task into smaller steps.",
            "technical_details": str(error),
        }

    @staticmethod
    def format_execution_error(step_title: str, error_info: Dict[str, Any]) -> str:
        """Format error message for UI display"""

        return f"""âŒ **Step Failed: {step_title}**

Error Type: {error_info['error_type']}
Category: {error_info['category'].upper()}

{error_info['message']}

**Suggestion:** {error_info['suggestion']}

---
For technical details, check the logs: Backend/work_session_5_realtime.log
"""

    @staticmethod
    def log_error_to_file(error: Exception, step_id: str, log_path: str):
        """Write detailed error to log file"""
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"ERROR in step: {step_id}\n")
            f.write(f"Time: {__import__('datetime').datetime.now().isoformat()}\n")
            f.write(f"Error: {str(error)}\n")
            f.write(f"Traceback:\n{traceback.format_exc()}\n")
            f.write(f"{'='*60}\n")
