import logging
from typing import Optional, Type, TypeVar
from openai import  RateLimitError
from pydantic import BaseModel


from ailand.core.clients.interfaces import BaseChatClient
from ailand.core.clients.openai.catalog import APIVersion, ChatModelSelection
from ailand.core.clients.retry import RetryConfig
from ailand.utils.settings.core import AOAICerteSettings
from ailand.core.clients.openai.base import BaseOpenAIClient

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)





class AzureOpenAIChatClient(BaseChatClient, BaseOpenAIClient):
    """
    Enhanced client for Azure OpenAI chat completions, supporting:
    - Multiple endpoint types (standard, semantic network)
    - Flexible authentication methods
    - Automatic settings discovery
    - Factory methods for easier initialization
    - Context manager support
    - Improved error handling
    """
    def __init__(
        self,
        model: ChatModelSelection,
        api_version: APIVersion,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        azure_ad_token: Optional[str] = None,
        aoai_cert_settings: Optional[AOAICerteSettings] = None,
        retry_config: RetryConfig = RetryConfig.CONSERVATIVE,
    ):
        """
        Initialize the AzureOpenAIChatClient with enhanced configuration options.

        Args:
            model (ChatModelSelection): The chat model to use.
            api_version (APIVersion): The API version to use.
            endpoint (str, optional): Direct endpoint URL override (highest priority).
            api_key (str, optional): API key for authentication.
            azure_ad_token (str, optional): Azure AD token for authentication.
            aoai_settings (AOAISettings, optional): Settings object with endpoints and auth config.
            endpoint_type (str, optional): Which endpoint type to use from settings.
                Use EndpointSelector.STANDARD or EndpointSelector.SEMANTIC_NETWORK.
            retry_config (RetryConfig, optional): Retry configuration.
                When False (default), suppresses detailed HTTP logs from Azure services.
            
        Notes:
            - Authentication priority: api_key > azure_ad_token > certificate > DefaultAzureCredential
            - Endpoint priority: direct endpoint > selected from settings > error
        """
            
        # Determine endpoint (direct endpoint has priority)
        self.endpoint = endpoint
        if not self.endpoint:
            raise ValueError(
                "Endpoint must be provided either directly or via settings. "
                "Check that your settings object contains the required endpoint fields."
            )
        
        # Store configuration
        self.model = model
        self.api_version = api_version
        self.retry_config = retry_config
        self.aoai_cert_settings = aoai_cert_settings

        # Create clients
        self.openai = self._build_client(api_key, azure_ad_token, aoai_cert_settings, sync=True)
        self.async_openai = self._build_client(api_key, azure_ad_token, aoai_cert_settings, sync=False)


    def chat(self, messages: list[dict], temperature=0, config: dict = {}) -> str:
        """
        Chat with the OpenAI API (synchronous).

        Args:
            messages (list[dict]): List of chat messages (OpenAI format).
            temperature (float, optional): Sampling temperature. Defaults to 0.
            config (dict, optional): Additional OpenAI API parameters. Defaults to {}.

        Returns:
            str: The response content from the model.
        """

        @self._get_retry_decorator(exception=RateLimitError)
        def _chat_with_retry():
            response = self.openai.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=messages,
                **config,
            )
            logger.info(f"[SYNC] Model={self.model}")
            return response.choices[0].message.content.strip()

        return _chat_with_retry()

    async def chat_async(self, messages: list[dict], temperature=0, config: dict = {}) -> str:
        """
        Chat with the OpenAI API (asynchronous).

        Args:
            messages (list[dict]): List of chat messages (OpenAI format).
            temperature (float, optional): Sampling temperature. Defaults to 0.
            config (dict, optional): Additional OpenAI API parameters. Defaults to {}.

        Returns:
            str: The response content from the model.
        """

        @self._get_retry_decorator(exception=RateLimitError)
        async def _chat_async_with_retry():
            response = await self.async_openai.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=messages,
                **config,
            )
            logger.info(f"[ASYNC] Model={self.model}")
            return response.choices[0].message.content.strip()

        return await _chat_async_with_retry()

    def select_tool(self, messages: list[dict], temperature=0, tools=[], config={}):
        """
        Select a tool using the OpenAI API (synchronous).

        Args:
            messages (list[dict]): List of messages to send to OpenAI API.
            temperature (float, optional): Sampling temperature. Defaults to 0.
            tools (list, optional): List of tools to provide to the model. Defaults to [].
            config (dict, optional): Additional OpenAI API parameters. Defaults to {}.

        Returns:
            Any: Tool call(s) selected by the model.
        """

        @self._get_retry_decorator(exception=RateLimitError)
        def _select_tool_with_retry():
            response = self.openai.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=messages,
                tools=tools or None,
                **config,
            )
            tool = response.choices[0].message.tool_calls
            return tool
        
        return _select_tool_with_retry()
    
    async def select_tool_async(self, messages: list[dict], temperature=0, tools=[], config={}):
        """
        Select a tool using the OpenAI API (asynchronous).

        Args:
            messages (list[dict]): List of messages to send to OpenAI API.
            temperature (float, optional): Sampling temperature. Defaults to 0.
            tools (list, optional): List of tools to provide to the model. Defaults to [].
            config (dict, optional): Additional OpenAI API parameters. Defaults to {}.

        Returns:
            Any: Tool call(s) selected by the model.
        """
        @self._get_retry_decorator(exception=RateLimitError)        
        async def _select_tool_async_with_retry():
            response = await self.async_openai.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=messages,
                tools=tools or None,
                **config,
            )
            tool = response.choices[0].message.tool_calls
            return tool
        return await _select_tool_async_with_retry()

    def parse(self, messages: list[dict], response_format: Type[T], temperature=0, config={}):
        """
        Parse the response from the OpenAI API (synchronous).

        Args:
            messages (list[dict]): List of chat messages (OpenAI format).
            response_format (Type[T]): The Pydantic BaseModel class (not instance) to parse the response into.
            temperature (float, optional): Sampling temperature. Defaults to 0.
            config (dict, optional): Additional OpenAI API parameters. Defaults to {}.

        Returns:
            Any: The parsed response object or refusal message.
        """

        @self._get_retry_decorator(exception=RateLimitError)
        def _parse_with_retry():
            response = self.openai.chat.completions.parse(
                model=self.model,
                temperature=temperature,
                messages=messages,
                response_format=response_format,
                **config,
            )
            logger.info(f"[SYNC] Model={self.model}")
            message = response.choices[0].message
            if hasattr(message, "refusal") and message.refusal:
                logger.warning(f"Refusal: {message.refusal}")
                return message.refusal
            else:
                logger.info(f"Parsed: {message.parsed}")
                return message.parsed

        return _parse_with_retry()

    async def parse_async(self, messages: list[dict], response_format: Type[T] = str, temperature=0, config={}):
        """
        Parse the response from the OpenAI API (asynchronous).

        Args:
            messages (list[dict]): List of chat messages (OpenAI format).
            response_format (Type[T]): The Pydantic BaseModel class (not instance) to parse the response into.
            temperature (float, optional): Sampling temperature. Defaults to 0.
            config (dict, optional): Additional OpenAI API parameters. Defaults to {}.

        Returns:
            Any: The parsed response object or refusal message.
        """

        @self._get_retry_decorator(exception=RateLimitError)
        async def _parse_async_with_retry():
            response = await self.async_openai.chat.completions.parse(
                model=self.model,
                temperature=temperature,
                messages=messages,
                response_format=response_format,
                **config,
            )
            logger.info(f"[ASYNC] Model={self.model}")
            message = response.choices[0].message
            if hasattr(message, "refusal") and message.refusal:
                logger.warning(f"Refusal: {message.refusal}")
                return message.refusal
            else:
                logger.info(f"Parsed: {message.parsed}")
                return message.parsed

        return await _parse_async_with_retry()
        
    def __enter__(self):
        """
        Context manager support.
        """
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up resources when exiting context.
        """
        # Currently no cleanup needed
        pass

    def __repr__(self):
        """
        Return a string representation of the client.
        """
        return f"AzureOpenAIChatClient(model={self.model}, endpoint={self.endpoint})"

    def __str__(self):
        """
        Return a string representation of the client (same as __repr__).
        """
        return self.__repr__()


if __name__ == "__main__":
    from ailand.utils.settings.core import AOAIEndpointSettings
    from pathlib import Path
    from pydantic import BaseModel
    import logging
    import asyncio

    logger = logging.getLogger(__name__)

    class User(BaseModel):
        name: str
        id: str

    aoai_settings = AOAIEndpointSettings.from_runtime_env()
    aoai_cert_settings = AOAICerteSettings.from_runtime_env()
    
    # Client with default logging (verbose logging disabled)
    client1 = AzureOpenAIChatClient(
        model=ChatModelSelection.GPT4_1_MINI, 
        api_version=APIVersion.DEFAULT,
        endpoint=aoai_settings.OPENAI_API_BASE_DEFAULT,
        aoai_cert_settings=aoai_cert_settings,
    )

    response = client1.chat(messages=[{"role": "user", "content": "Hello, how are you?"}])
    logger.info(f"Response with default logging {response}")

    response = client1.parse(
        messages=[{"role": "user", "content": "Generate a user with name Alice and id 123"}],
        response_format=User
    )
    logger.info(f"Parsed user: {response}")


    # Example with context manager and quiet logging
    with AzureOpenAIChatClient(
        model=ChatModelSelection.GPT4_1_MINI, 
        api_version=APIVersion.DEFAULT,
        endpoint=aoai_settings.OPENAI_API_BASE_ALT,
        aoai_cert_settings=aoai_cert_settings,
    ) as client3:
        response = client3.chat(
            messages=[{"role": "user", "content": "What is the capital of France?"}]
        )
        print("Response with context manager:", response)
        response = asyncio.run(client3.chat_async(
            messages=[{"role": "user", "content": "Hello, how are you?"}]
        ))

        logger.info(f"Async response with verbose logging: {response}")