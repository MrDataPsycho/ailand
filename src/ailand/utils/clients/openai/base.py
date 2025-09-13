import logging
from typing import Any, Dict, Optional
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI, AzureOpenAI
from ailand.utils.settings.core import AOAICerteSettings, DEFAULT_COGNITIVE_SERVICE_ENDPOINT
from ailand.utils.auth.azure_identity import get_cert_token_provider

logger = logging.getLogger(__name__)


class BaseOpenAIClient:
    """
    Base class for OpenAI clients with common functionality.
    """
    pass

    def _resolve_authentication(self, api_key: Optional[str] = None, azure_ad_token: Optional[str] = None, aoai_cert_setting: Optional[AOAICerteSettings] = None) -> Dict[str, Any]:
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

        if aoai_cert_setting:
            try:
                return {"azure_ad_token_provider": get_cert_token_provider(aoai_cert_setting)}
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
        
    def _build_client(self, api_key: Optional[str], azure_ad_token: Optional[str], aoai_cert_settings: Optional[AOAICerteSettings], sync: bool = True):
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
        auth_args = self._resolve_authentication(api_key, azure_ad_token, aoai_cert_settings)
        common_args.update(auth_args)

        # Create appropriate client type
        client_class = AzureOpenAI if sync else AsyncAzureOpenAI
        return client_class(**common_args)