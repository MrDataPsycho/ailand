import logging
from typing import Type, TypeVar

from openai import AsyncAzureOpenAI, AzureOpenAI, RateLimitError
from pydantic import BaseModel
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from cnlib.core.clients.interfaces import BaseChatClient
from cnlib.core.clients.openai.catalog import APIVersion, ChatModelSelection
from cnlib.core.clients.retry import RetryConfig
from cnlib.utils.auth.azure_identity import get_cert_token_provider
from cnlib.utils.settings.core import AOAISettings, DEFAULT_COGNITIVE_SERVICE_ENDPOINT
from enum import Enum

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)


class AzureOpenAIChatClient(BaseChatClient):
    """
    Client for Azure OpenAI chat completions, supporting sync and async usage, retry logic, and tool selection.
    """
    def __init__(
        self,
        model: ChatModelSelection,
        api_version: APIVersion,
        endpoint: str | None = None,
        api_key: str | None = None,
        azure_ad_token: str | None = None,
        aoai_settings: AOAISettings | None = None,
        retry_config: RetryConfig = RetryConfig.CONSERVATIVE,
    ):
        """
        Initialize the AzureOpenAIChatClient.

        Args:
            model (ChatModelSelection): The chat model to use.
            api_version (APIVersion): The API version to use.
            endpoint (str): The Azure OpenAI endpoint URL.
            api_key (str, optional): API key for authentication. Defaults to None.
            azure_ad_token (str, optional): Azure AD token for authentication. Defaults to None.
            retry_config (RetryConfig, optional): Retry configuration. Defaults to RetryConfig.CONSERVATIVE.
            
        Note:
            If neither api_key nor azure_ad_token is provided, the client will use DefaultAzureCredential
            for RBAC authentication with Azure AD.
        """

        if aoai_settings is None and not endpoint:
            raise ValueError("Either aoai_settings or endpoint must be provided.")

        self.model = model
        self.api_version = api_version
        self.retry_config = retry_config
        self.aoai_settings = aoai_settings
        self.endpoint = endpoint or aoai_settings.OPENAI_API_BASE
        self.openai = self._build_client(api_key, azure_ad_token, sync=True)
        self.async_openai = self._build_client(api_key, azure_ad_token, sync=False)


    def _build_client(self, api_key: str | None, azure_ad_token: str | None, sync: bool = True):
        """
        Initialize the AzureOpenAI or AsyncAzureOpenAI client depending on credentials.

        Args:
            api_key (str, optional): API key for authentication.
            azure_ad_token (str, optional): Azure AD token for authentication.
            sync (bool, optional): Whether to use the synchronous client. If False, uses async client.

        Returns:
            AzureOpenAI or AsyncAzureOpenAI: The initialized client.
        """
        common_args = {
            "azure_endpoint": self.endpoint,
            "api_version": self.api_version,
        }

        if api_key:
            common_args["api_key"] = api_key
        elif azure_ad_token:
            common_args["azure_ad_token"] = azure_ad_token
        elif self.aoai_settings:
            common_args["azure_ad_token_provider"] = get_cert_token_provider(self.aoai_settings)
        else:
            try:
                token_provider = get_bearer_token_provider(DefaultAzureCredential(), DEFAULT_COGNITIVE_SERVICE_ENDPOINT)
                common_args["azure_ad_token_provider"] = token_provider
            except Exception as e:
                logger.error(f"Failed to get token provider could not get token for DefaultAzureCredential also no other token generation method is selected. You can try setting the API key or Azure AD token manually: {e}")
                raise

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

    def __repr__(self):
        """
        Return a string representation of the client.
        """
        return f"OpenAIClient(auth=***, model={self.model})"

    def __str__(self):
        """
        Return a string representation of the client (same as __repr__).
        """
        return self.__repr__()


if __name__ == "__main__":
    from cnlib.utils.settings.core import AOAISettings
    from pathlib import Path
    from pydantic import BaseModel

    class User(BaseModel):
        name: str
        id: str

    ENVFILE_PATH = Path(".envs").joinpath("local.env")
    aoai_settings = AOAISettings.from_env_file(ENVFILE_PATH)
    client = AzureOpenAIChatClient(model=ChatModelSelection.GPT4_1_MINI, api_version=APIVersion.LATEST, aoai_settings=aoai_settings)
    response = client.chat(
        messages=[
            {"role": "user", "content": "Hello, how are you?"}
        ]
    )
    print(response)

    response = client.parse(
        messages=[
            {"role": "system", "content": "You are special agent can parse structured information from provided content. User will provide unstructured content. If there is nothing to parse you should refuse to parse."},
            {"role": "user", "content": "There is nothing to parse."}
        ],
        response_format=User
    )
    print(response)
    print(type(response))

