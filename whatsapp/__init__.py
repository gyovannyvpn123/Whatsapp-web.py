"""
WhatsApp Web Python Library

A pure Python library for WhatsApp Web communication with full Signal Protocol encryption support.
This library provides core functionality similar to what Baileys offers in Node.js, 
including authentication, encryption, message parsing, and event handling.
"""

__version__ = "0.1.0"
__author__ = "WhatsApp Python Library Contributors"

# Import main components for easy access
from .client import WAClient
from .exceptions import (
    WAConnectionError,
    WAAuthenticationError,
    WAMessageError,
    WAEncryptionError,
    WAProtocolError
)
from .events import WAEventType

# Define what is publicly accessible
__all__ = [
    "WAClient",
    "WAConnectionError",
    "WAAuthenticationError",
    "WAMessageError",
    "WAEncryptionError",
    "WAProtocolError",
    "WAEventType"
]
