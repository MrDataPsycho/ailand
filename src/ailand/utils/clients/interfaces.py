
from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar

from pydantic import BaseModel
from tenacity import (retry, retry_if_exception_type, stop_after_attempt, wait_exponential)

T = TypeVar('T', bound=BaseModel)


class BaseChatClient(ABC):
	"""
	Abstract base class for chat clients supporting chat, parse, and tool call methods (sync and async).
	"""

	@abstractmethod
	def chat(self, messages: list[dict], temperature: float = 0, config: dict = {}) -> str:
		"""
		Synchronous chat method.
		"""
		pass

	@abstractmethod
	def parse(self, messages: list[dict], response_format: Type[T], temperature: float = 0, config: dict = {}) -> Any:
		"""
		Synchronous parse method.
		"""
		pass

	@abstractmethod
	async def parse_async(self, messages: list[dict], response_format: Type[T], temperature: float = 0, config: dict = {}) -> Any:
		"""
		Asynchronous parse method.
		"""
		pass

	@abstractmethod
	async def chat_async(self, messages: list[dict], temperature: float = 0, config: dict = {}) -> str:
		"""
		Asynchronous chat method.
		"""
		pass



	@abstractmethod
	def select_tool(self, messages: list[dict], temperature: float = 0, tools: list = [], config: dict = {}) -> Any:
		"""
		Synchronous tool selection method.
		"""
		pass

	@abstractmethod
	async def select_tool_async(self, messages: list[dict], temperature: float = 0, tools: list = [], config: dict = {}) -> Any:
		"""
		Asynchronous tool selection method.
		"""
		pass

	def _get_retry_decorator(self, exception: Type[Exception] = ValueError) -> Any:
		"""
		Get retry decorator with current configuration.

        Returns:
            Callable: A tenacity retry decorator configured for RateLimitError.
        """
		settings = self.retry_config.settings
		return retry(
			retry=retry_if_exception_type(exception),
			wait=wait_exponential(multiplier=settings.multiplier, min=settings.min_wait, max=settings.max_wait),
			stop=stop_after_attempt(settings.max_attempts),
			reraise=True,
)
