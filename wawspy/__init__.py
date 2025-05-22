"""
wawspy - O bibliotecă îmbunătățită pentru WhatsApp Web

Această bibliotecă oferă o interfață Python pentru conectarea la WhatsApp Web,
cu focus pe un mecanism de conexiune WebSocket robust și gestionare avansată a media.
"""

__version__ = "0.2.0"
__author__ = "Developer"
__license__ = "MIT"

# Importuri pentru facilitatea utilizării
from .client import WAClient
from .exceptions import (
    WABaseError,
    WAConnectionError,
    WAAuthenticationError,
    WAMessageError,
    WAMediaError,
    WAProtocolError,
    WATimeoutError,
    WADecryptionError
)

__all__ = [
    # Clasa principală
    "WAClient",
    
    # Excepții
    "WABaseError",
    "WAConnectionError",
    "WAAuthenticationError",
    "WAMessageError",
    "WAMediaError",
    "WAProtocolError",
    "WATimeoutError",
    "WADecryptionError"
]