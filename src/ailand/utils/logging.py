"""
Logging utilities for managing Azure SDK and other libraries' log levels.

These utilities provide convenient functions to control logging verbosity
for Azure SDK components which can be noisy in production environments.
"""
import logging
import os
from typing import Dict, List, Optional

# Azure SDK loggers that can be quite verbose
AZURE_VERBOSE_LOGGERS = [
    "azure.core.pipeline.policies.http_logging_policy",
    "azure.identity",
    "azure.core.pipeline",
    "msal",
    "urllib3.connectionpool"
]

# Log level mapping
LOG_LEVEL_MAP: Dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

DEFAULT_LOG_LEVEL = "INFO"


def get_log_level_from_env(default_level: int = logging.WARNING) -> int:
    """
    Get the log level from the LOG_LEVEL environment variable.
    
    Args:
        default_level: The default log level to use if the environment variable is not set
                      or has an invalid value.
                      
    Returns:
        The log level as an integer (e.g., logging.INFO, logging.DEBUG)
    """
    log_level_name = os.environ.get("LOG_LEVEL", "").upper()
    return LOG_LEVEL_MAP.get(log_level_name, default_level)


def initialize_logging() -> None:
    """
    Initialize logging configuration based on environment variables.
    
    This function:
    1. Reads LOG_LEVEL environment variable (defaults to WARNING)
    2. Configures the root logger with that level
    3. Sets Azure SDK loggers to appropriate levels to reduce verbosity
    """
    # Get log level from environment variable with fallback to default
    log_level_name = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    log_level = LOG_LEVEL_MAP.get(log_level_name, logging.WARNING)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    logger = logging.getLogger(__name__)
    logger.debug(f"Initialized logging with level: {log_level_name}")

    # Set Azure SDK loggers to a higher level to reduce verbosity
    # unless LOG_LEVEL=DEBUG is explicitly set
    if log_level > logging.DEBUG:
        for logger_name in AZURE_VERBOSE_LOGGERS:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
        logger.debug("Azure SDK verbose logging disabled (set LOG_LEVEL=DEBUG to enable)")
    else:
        logger.debug("Azure SDK verbose logging enabled")


def configure_azure_logging(
    enable_verbose: bool = False, 
    log_level: int = logging.WARNING,
    verbose_log_level: int = logging.INFO,
    logger_names: Optional[List[str]] = None
) -> None:
    """
    Configure logging levels for Azure SDK components.
    
    This function allows toggling verbose logging from Azure SDK components that
    can be noisy in production environments.
    
    Args:
        enable_verbose: When True, enables detailed logging from Azure components
                        When False, sets them to the specified log_level (default: WARNING)
        log_level: The log level to use when verbose logging is disabled (default: WARNING)
        verbose_log_level: The log level to use when verbose logging is enabled (default: INFO)
        logger_names: Custom list of logger names to configure.
                     If None, uses the AZURE_VERBOSE_LOGGERS list
    """
    logger_names = logger_names or AZURE_VERBOSE_LOGGERS
    
    # Set log level based on verbose flag
    level = verbose_log_level if enable_verbose else log_level
    
    # Configure each logger
    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        
        # Optional: also configure handlers if needed
        for handler in logger.handlers:
            handler.setLevel(level)
            
    if enable_verbose:
        logging.info(f"Enabled verbose logging for: {', '.join(logger_names)}")
    else:
        logging.info(f"Disabled verbose logging for: {', '.join(logger_names)}")


def set_quiet_mode() -> None:
    """
    Shorthand to quickly disable verbose Azure logging.
    """
    configure_azure_logging(enable_verbose=False, log_level=logging.WARNING)
    
    
def set_verbose_mode() -> None:
    """
    Shorthand to quickly enable verbose Azure logging for debugging.
    """
    configure_azure_logging(enable_verbose=True, verbose_log_level=logging.DEBUG)
