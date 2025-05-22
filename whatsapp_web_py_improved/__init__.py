"""
whatsapp-web-py îmbunătățit

O bibliotecă îmbunătățită pentru WhatsApp Web cu focus pe mecanismul de conexiune WebSocket
și funcționalitățile media, inspirată din principiile tehnice ale implementării @whiskeysockets/baileys.

Această bibliotecă oferă o interfață Python pentru WhatsApp Web, permițând trimiterea
și primirea mesajelor, gestionarea media și autentificarea prin cod QR.
"""

__version__ = "0.2.0"
__author__ = "Developer"
__license__ = "MIT"

# Importuri pentru facilitatea utilizării
from .constants import (
    MediaType,
    MessageStatus,
    ChatType,
    ConnectionState
)

from .exceptions import (
    WABaseError,
    WAConnectionError,
    WAAuthenticationError,
    WAMessageError,
    WAMediaError,
    WAGroupError,
    WAProtocolError,
    WATimeoutError,
    WADecryptionError
)

from .events import (
    WAEventType,
    EventEmitter
)

from .client import WAClient

__all__ = [
    # Clase principale
    "WAClient",
    "EventEmitter",
    
    # Tipuri de evenimente
    "WAEventType",
    
    # Tipuri și constante
    "MediaType",
    "MessageStatus",
    "ChatType",
    "ConnectionState",
    
    # Excepții
    "WABaseError",
    "WAConnectionError",
    "WAAuthenticationError",
    "WAMessageError",
    "WAMediaError",
    "WAGroupError",
    "WAProtocolError",
    "WATimeoutError",
    "WADecryptionError"
]