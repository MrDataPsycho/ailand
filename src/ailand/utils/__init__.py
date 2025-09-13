"""
Utility module initialization.
Sets up logging configuration based on environment variables.
"""

# Import and initialize logging configuration
from .logging import (
    VERBOSE_LOGGERS,
    configure_third_party_logging, 
    get_log_level_from_env,
    initialize_logging,
    set_quiet_mode_for_third_party_logging,
    set_verbose_mode_for_third_party_logging
)

# Initialize logging when the module is imported
initialize_logging()

# Export public API
__all__ = [
    "VERBOSE_LOGGERS",
    "configure_third_party_logging", 
    "get_log_level_from_env",
    "initialize_logging",
    "set_quiet_mode_for_third_party_logging", 
    "set_verbose_mode_for_third_party_logging"
]