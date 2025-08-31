"""
Endpoint selector for Azure OpenAI services.
Provides a way to select different regional endpoints from settings.
"""
from ailand.utils.settings.core import AOAISettings


class EndpointSelector:
    """
    Utility class for selecting different geographic endpoint locations from settings.
    
    Usage:
        endpoint = EndpointSelector.get_endpoint(settings, EndpointSelector.SWITZERLAND)
    """
    DEFAULT = "sweden"  # Uses OPENAI_API_BASE (Sweden region by default)
    SWITZERLAND = "switzerland"  # Uses OPENAI_API_BASE_SN (Switzerland region)
    
    @staticmethod
    def get_endpoint(settings: AOAISettings, endpoint_type: str = DEFAULT) -> str:
        """
        Get the appropriate endpoint based on the selected geographic region.
        
        Args:
            settings: AOAISettings object containing endpoint configurations
            endpoint_type: Geographic region to select (use class constants)
            
        Returns:
            str: The selected regional endpoint URL
            
        Raises:
            ValueError: If the settings object is None or the endpoint isn't available
        """
        if not settings:
            raise ValueError("Settings must be provided to select an endpoint")
            
        if endpoint_type == EndpointSelector.SWITZERLAND:
            if not hasattr(settings, "OPENAI_API_BASE_SN") or not settings.OPENAI_API_BASE_SN:
                raise ValueError("OPENAI_API_BASE_SN (Switzerland region) not available in settings")
            return settings.OPENAI_API_BASE_SN
            
        # Default to Sweden region
        if not hasattr(settings, "OPENAI_API_BASE") or not settings.OPENAI_API_BASE:
            raise ValueError("OPENAI_API_BASE (Default Sweden region) not available in settings")
        return settings.OPENAI_API_BASE
