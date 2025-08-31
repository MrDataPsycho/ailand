import resource
from typing import Callable
from azure.identity import CertificateCredential
from ailand.utils.settings.core import AOAISettings


def get_cert_token_provider(settings: AOAISettings) -> Callable[[], str]:
    """Returns a callable that provides a bearer token using certificate-based authentication.

    This function creates a token provider that can be used directly with AzureOpenAI client.
    
    Example:
        ```python
        from azure.identity import CertificateCredential
        from cnlib.core.clients.auth.certificate_provider import get_cert_token_provider
        
        token_provider = get_cert_token_provider(
            tenant_id="your-tenant-id",
            client_id="your-client-id",
            certificate_data="your-certificate-data",
        )
        
        # Then use with AzureOpenAI client
        client = AzureOpenAI(
            azure_endpoint="https://your-endpoint.openai.azure.com",
            api_version="2023-05-15",
            azure_ad_token_provider=token_provider
        )
        ```

    Args:
        tenant_id: The Azure AD tenant ID
        client_id: The Azure AD client ID
        certificate_data: The certificate data in PEM format
        resource: The resource to request token for, defaults to Azure OpenAI

    Returns:
        A callable that returns a bearer token when invoked
    """
    # Create the certificate credential
    credential = CertificateCredential(
        tenant_id=settings.TENANT_ID,
        client_id=settings.CLIENT_ID,
        certificate_data=settings.certificate_string
    )
    
    # Define the token provider function
    def token_provider() -> str:
        # Get a fresh token when called
        token = credential.get_token(settings.RESOURCE)
        return token.token
    
    return token_provider
