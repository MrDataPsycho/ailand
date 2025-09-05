"""
Ailand package initialization.
"""
from ailand.__about__ import VERSION

# Import utils module to initialize logging configuration
import ailand.utils

def main() -> None:
    """
    Main entry point for the package.
    """
    print(f"Hello from ailand a Crafting Neuron blog! Version: {VERSION}")
