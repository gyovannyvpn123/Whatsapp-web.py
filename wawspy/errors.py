"""
Error classes for the wawspy library.
"""

class WABaseError(Exception):
    """Base error class for all wawspy errors."""
    pass

class WAConnectionError(WABaseError):
    """Error during WebSocket connection."""
    pass

class WAAuthenticationError(WABaseError):
    """Error during authentication process."""
    pass

class WAMessageError(WABaseError):
    """Error related to message sending/receiving."""
    pass

class WAMediaError(WABaseError):
    """Error related to media handling."""
    pass

class WAProtocolError(WABaseError):
    """Error related to protocol handling."""
    pass
