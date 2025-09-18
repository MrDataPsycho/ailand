import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class RetrySettings:
    """Configuration for retry mechanism."""
    max_attempts: int
    min_wait: int
    max_wait: int
    multiplier: int


class RetryConfig(Enum):
    """Predefined retry configurations for OpenAI API calls."""

    CONSERVATIVE = RetrySettings(max_attempts=3, min_wait=2, max_wait=30, multiplier=1)
    MODERATE = RetrySettings(max_attempts=4, min_wait=3, max_wait=45, multiplier=1)
    AGGRESSIVE = RetrySettings(max_attempts=6, min_wait=5, max_wait=60, multiplier=1)

    @property
    def settings(self) -> RetrySettings:
        """Get the retry settings for this configuration."""
        return self.value