import logging
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI, AzureOpenAI, RateLimitError
from pydantic import BaseModel
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                     wait_exponential)

from ailand.core.clients.interfaces import BaseChatClient
from ailand.core.clients.openai.catalog import APIVersion, ChatModelSelection
from ailand.core.clients.openai.endpoint_selector import EndpointSelector
from ailand.core.clients.retry import RetryConfig
from ailand.utils.auth.azure_identity import get_cert_token_provider
from ailand.utils.settings.core import AOAISettings, DEFAULT_COGNITIVE_SERVICE_ENDPOINT

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)


class AzureOpenAIChatClient(BaseChatClient):
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
        aoai_settings: Optional[AOAISettings] = None,
        endpoint_type: str = EndpointSelector.DEFAULT,
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
            
        Notes:
            - Authentication priority: api_key > azure_ad_token > certificate > DefaultAzureCredential
            - Endpoint priority: direct endpoint > selected from settings > error
        """
            
        # Determine endpoint (direct endpoint has priority)
        self.endpoint = endpoint
        if aoai_settings:
            self.endpoint = EndpointSelector.get_endpoint(aoai_settings, endpoint_type)
        if not self.endpoint:
            raise ValueError(
                "Endpoint must be provided either directly or via settings. "
                "Check that your settings object contains the required endpoint fields."
            )
        
        # Store configuration
        self.model = model
        self.api_version = api_version
        self.retry_config = retry_config
        self.aoai_settings = aoai_settings
        
        # Create clients
        self.openai = self._build_client(api_key, azure_ad_token, sync=True)
        self.async_openai = self._build_client(api_key, azure_ad_token, sync=False)
        
        logger.info(f"Initialized AzureOpenAIChatClient with model={model}, endpoint={self.endpoint}")

    @classmethod
    def from_aoai_settings(
        cls,
        aoai_settings: AOAISettings,
        model: ChatModelSelection = ChatModelSelection.DEFAULT,
        api_version: APIVersion = APIVersion.DEFAULT,
        endpoint_type: str = EndpointSelector.DEFAULT,
        **kwargs
    ) -> "AzureOpenAIChatClient":
        """
        Factory method to create a client with simpler configuration.
        
        Args:
            model: The model to use
            api_version: API version (defaults to latest)
            endpoint_type: Which endpoint type to use (standard or semantic_network)
            settings_path: Optional path to settings file
            **kwargs: Additional arguments passed to the constructor
            
        Returns:
            Configured AzureOpenAIChatClient
        """
        # Load settings if path provided
        return cls(
            model=model,
            api_version=api_version,
            aoai_settings=aoai_settings,
            endpoint_type=endpoint_type,
            **kwargs
        )

    def _resolve_authentication(self, api_key: Optional[str], azure_ad_token: Optional[str]) -> Dict[str, Any]:
        """
        Resolve authentication credentials in order of priority.
        
        Args:
            api_key: API key if available
            azure_ad_token: Azure AD token if available
            
        Returns:
            Dict with the appropriate authentication credentials
            
        Raises:
            ValueError: If no valid authentication method can be determined
        """
        if api_key:
            return {"api_key": api_key}
            
        if azure_ad_token:
            return {"azure_ad_token": azure_ad_token}
            
        if self.aoai_settings:
            try:
                return {"azure_ad_token_provider": get_cert_token_provider(self.aoai_settings)}
            except Exception as e:
                logger.warning(f"Failed to create certificate token provider: {e}")
                # Fall through to next method
        
        try:
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), 
                DEFAULT_COGNITIVE_SERVICE_ENDPOINT
            )
            return {"azure_ad_token_provider": token_provider}
        except Exception as e:
            logger.error(
                f"Failed to get any token provider. Could not authenticate. "
                f"Set API_KEY, AZURE_AD_TOKEN, or ensure AZURE credentials are available: {e}"
            )
            raise ValueError(f"No valid authentication method available: {e}")

    def _build_client(self, api_key: Optional[str], azure_ad_token: Optional[str], sync: bool = True):
        """
        Initialize the AzureOpenAI or AsyncAzureOpenAI client with appropriate authentication.

        Args:
            api_key: API key for authentication.
            azure_ad_token: Azure AD token for authentication.
            sync: Whether to use the synchronous client. If False, uses async client.

        Returns:
            AzureOpenAI or AsyncAzureOpenAI: The initialized client.
        """
        # Base configuration common to both sync and async clients
        common_args = {
            "azure_endpoint": self.endpoint,
            "api_version": self.api_version,
        }

        # Resolve authentication and update args
        auth_args = self._resolve_authentication(api_key, azure_ad_token)
        common_args.update(auth_args)

        # Create appropriate client type
        client_class = AzureOpenAI if sync else AsyncAzureOpenAI
        return client_class(**common_args)

    def _get_retry_decorator(self):
        """
        Get retry decorator with current configuration.

        Returns:
            Callable: A tenacity retry decorator configured for RateLimitError.
        """
        settings = self.retry_config.settings
        return retry(
            retry=retry_if_exception_type(RateLimitError),
            wait=wait_exponential(multiplier=settings.multiplier, min=settings.min_wait, max=settings.max_wait),
            stop=stop_after_attempt(settings.max_attempts),
            reraise=True,
        )

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

        @self._get_retry_decorator()
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

        @self._get_retry_decorator()
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
        
        @self._get_retry_decorator()        
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
        @self._get_retry_decorator()        
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

        @self._get_retry_decorator()
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

        @self._get_retry_decorator()
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
    from ailand.utils.settings.core import AOAISettings
    from pathlib import Path
    from pydantic import BaseModel
    import logging

    logging.basicConfig(level=logging.INFO)

    class User(BaseModel):
        name: str
        id: str

    ENVFILE_PATH = Path(".envs").joinpath("local.env")
    aoai_settings = AOAISettings.from_env_file(ENVFILE_PATH)
    client1 = AzureOpenAIChatClient(
        model=ChatModelSelection.GPT4_1_MINI, 
        api_version=APIVersion.DEFAULT, 
        aoai_settings=aoai_settings
    )

    response = client1.chat(messages=[{"role": "user", "content": "Hello, how are you?"}])
    print(response)

    # Example with context manager
    with AzureOpenAIChatClient.from_aoai_settings(
        aoai_settings=aoai_settings,
    ) as client2:
        response = client2.chat(
            messages=[{"role": "user", "content": "Hello, how are you?"}]
        )
        print(response)
