"""
Message model for WhatsApp Web.

This module defines the Message class for representing WhatsApp messages.
"""

import time
from typing import Dict, Optional, Any, List

class Message:
    """
    Represents a WhatsApp message
    """
    
    def __init__(
        self, 
        id: str,
        to: str,
        from_me: bool,
        text: str = "",
        media_type: Optional[str] = None,
        media_url: Optional[str] = None,
        quoted_message_id: Optional[str] = None,
        timestamp: Optional[int] = None,
        status: str = "pending"
    ):
        """
        Initialize a new message
        
        Args:
            id: Message ID
            to: Recipient (for outgoing) or sender (for incoming)
            from_me: True if message was sent by current user
            text: Message text content
            media_type: Type of media (image, video, audio, document)
            media_url: URL of media content
            quoted_message_id: ID of quoted message (if reply)
            timestamp: Message timestamp (epoch)
            status: Message status (pending, sent, delivered, read)
        """
        self.id = id
        self.to = to
        self.from_me = from_me
        self.text = text
        self.media_type = media_type
        self.media_url = media_url
        self.quoted_message_id = quoted_message_id
        self.timestamp = timestamp or int(time.time())
        self.status = status
        
    def __str__(self) -> str:
        """String representation of the message"""
        direction = "→" if self.from_me else "←"
        return f"Message {direction} {self.to}: {self.text[:30]}{'...' if len(self.text) > 30 else ''}"
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert message to dictionary
        
        Returns:
            Dict: Dictionary representation of message
        """
        return {
            "id": self.id,
            "to": self.to,
            "fromMe": self.from_me,
            "text": self.text,
            "mediaType": self.media_type,
            "mediaUrl": self.media_url,
            "quotedMessageId": self.quoted_message_id,
            "timestamp": self.timestamp,
            "status": self.status
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """
        Create message from dictionary
        
        Args:
            data: Dictionary representation of message
            
        Returns:
            Message: New message instance
        """
        return cls(
            id=data.get("id", ""),
            to=data.get("to", ""),
            from_me=data.get("fromMe", False),
            text=data.get("text", ""),
            media_type=data.get("mediaType"),
            media_url=data.get("mediaUrl"),
            quoted_message_id=data.get("quotedMessageId"),
            timestamp=data.get("timestamp"),
            status=data.get("status", "pending")
        )
        
    def is_media(self) -> bool:
        """
        Check if message contains media
        
        Returns:
            bool: True if message has media
        """
        return self.media_type is not None
        
    def is_reply(self) -> bool:
        """
        Check if message is a reply
        
        Returns:
            bool: True if message is a reply
        """
        return self.quoted_message_id is not None
