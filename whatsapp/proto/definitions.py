"""
Protocol Buffer message type definitions for WhatsApp Web.

This module defines the mapping between message type IDs and protobuf message classes.
"""

from typing import Dict, Type, Any

# Simplified placeholder for WhatsApp protobuf message types
# In a real implementation, these would be the actual generated protobuf classes
class WAPingMessage:
    """Placeholder for ping message protobuf class"""
    pass

class WATextMessage:
    """Placeholder for text message protobuf class"""
    pass

class WAMediaMessage:
    """Placeholder for media message protobuf class"""
    pass

class WAGroupMessage:
    """Placeholder for group info message protobuf class"""
    pass

class WAContactMessage:
    """Placeholder for contact message protobuf class"""
    pass

class WAPresenceMessage:
    """Placeholder for presence update message protobuf class"""
    pass

class WANotificationMessage:
    """Placeholder for notification message protobuf class"""
    pass

class WAStatusMessage:
    """Placeholder for status message protobuf class"""
    pass

# Mapping of message type IDs to protobuf classes
message_types: Dict[int, Type[Any]] = {
    0x01: WAPingMessage,            # Ping/Pong messages
    0x02: WATextMessage,            # Text messages
    0x03: WAMediaMessage,           # Media messages (images, video, etc.)
    0x04: WAGroupMessage,           # Group-related messages
    0x05: WAContactMessage,         # Contact-related messages
    0x06: WAPresenceMessage,        # Online/offline status updates
    0x07: WANotificationMessage,    # Various notifications
    0x08: WAStatusMessage,          # Status updates (stories)
}

# WhatsApp message node types
class NodeTypes:
    """Constants for common WhatsApp node types"""
    MESSAGE = "message"
    PRESENCE = "presence"
    IQ = "iq"  # Info/Query
    IB = "ib"  # Identity-based
    NOTIFICATION = "notification"
    RECEIPT = "receipt"
    STREAM = "stream"
    SUCCESS = "success"
    FAILURE = "failure"
    IBS = "ibs"  # Identity-based stream
    
# Common WhatsApp message attributes
class AttributeNames:
    """Constants for common WhatsApp message attributes"""
    TYPE = "type"
    FROM = "from"
    TO = "to"
    ID = "id"
    PARTICIPANT = "participant"
    NOTIFY = "notify"
    TIMESTAMP = "t"
    AUTHOR = "author"
