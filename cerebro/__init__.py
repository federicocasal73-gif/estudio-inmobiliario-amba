"""Cerebro de Prompts - Sistema de extracción y gestión de prompts para IA.

Extrae prompts de videos de Instagram/TikTok sobre propiedades inmobiliarias
y los almacena para usar en generación de imágenes con Fooocus/Stable Diffusion.
"""

from cerebro.prompt_database import PromptDatabase
from cerebro.cerebro import Cerebro

__version__ = "1.0.0"
__all__ = ["PromptDatabase", "Cerebro"]
