"""
Exceptions for WhatsApp Web library.
"""

class WAException(Exception):
    """Base exception for all WhatsApp Web errors"""
    pass

class WAConnectionError(WAException):
    """Connection error"""
    pass

class WAAuthenticationError(WAException):
    """Authentication error"""
    pass

class WAMessageError(WAException):
    """Message sending/receiving error"""
    pass

class WAEncryptionError(WAException):
    """Encryption/decryption error"""
    pass

class WAProtocolError(WAException):
    """Protocol error"""
    pass
