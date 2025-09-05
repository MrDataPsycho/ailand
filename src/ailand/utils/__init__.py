"""
Utility module initialization.
Sets up logging configuration based on environment variables.
"""

# Import and initialize logging configuration
from .logging import (
    AZURE_VERBOSE_LOGGERS,
    configure_azure_logging, 
    get_log_level_from_env,
    initialize_logging,
    set_quiet_mode, 
    set_verbose_mode
)

# Initialize logging when the module is imported
initialize_logging()

# Export public API
__all__ = [
    "AZURE_VERBOSE_LOGGERS",
    "configure_azure_logging", 
    "get_log_level_from_env",
    "initialize_logging",
    "set_quiet_mode", 
    "set_verbose_mode"
]