from ailand.utils.settings.base import ABCBaseSettings


# Default Azure Cognitive Services resource endpoint without /.default suffix
# This will be automatically appended in model_post_init if needed
DEFAULT_COGNITIVE_SERVICE_ENDPOINT = "https://cognitiveservices.azure.com"

class AOAIEndpointSettings(ABCBaseSettings):
    OPENAI_API_BASE_DEFAULT: str
    OPENAI_API_BASE_ALT: str


class AOAICerteSettings(ABCBaseSettings):
    TENANT_ID: str
    CLIENT_ID: str
    NO_PROXY: str
    RESOURCE: str = DEFAULT_COGNITIVE_SERVICE_ENDPOINT
    PUBLIC_CERT_KEY: str
    PRIVATE_CERT_KEY: str

    def model_post_init(self, __context):
        """
        Post-initialization processing called by Pydantic after model initialization.
        
        Args:
            __context: Pydantic validation context (unused but required by Pydantic's
                      model lifecycle hooks)
                      
        Behavior:
        - Ensures RESOURCE ends with /.default for proper Azure authentication
        - Properly concatenates the base URL with /.default using string operations
        - Handles any trailing slashes in the base URL to avoid duplicate slashes
        """
        if not self.RESOURCE.endswith("/.default"):
            # Remove trailing slash if present
            resource_base = self.RESOURCE.rstrip("/")
            # Append /.default
            self.RESOURCE = f"{resource_base}/.default"

    @property
    def certificate_string(self) -> str:
        return self.PRIVATE_CERT_KEY.encode() + b"\n" + self.PUBLIC_CERT_KEY.encode()



class AOAIEndpointSettings(ABCBaseSettings):
    OPENAI_API_BASE_DEFAULT: str
    OPENAI_API_BASE_ALT: str


class AOAIKeySettings(ABCBaseSettings):
    OPENAI_API_BASE_DEFAULT: str
    OPENAI_API_BASE_ALT: str



if __name__ == "__main__":
    aoai_endpoint_settings = AOAIEndpointSettings.from_runtime_env()
    print(aoai_endpoint_settings.model_dump_json(indent=2))
    aoai_cert_settings = AOAICerteSettings.from_runtime_env()
    print(aoai_cert_settings.model_dump_json(indent=2))
    aoai_key_settings = AOAIKeySettings.from_runtime_env()
    print(aoai_key_settings.model_dump_json(indent=2))