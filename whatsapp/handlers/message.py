"""
Message handler for WhatsApp Web.

This module handles sending and receiving messages.
"""

import time
import asyncio
import uuid
from typing import Dict, Any, Optional, List, Union

from ..utils.logger import get_logger
from ..models.message import Message
from ..exceptions import WAMessageError
from ..events import WAEventType

class MessageHandler:
    """
    Handles sending and receiving WhatsApp messages
    """
    
    def __init__(self, client):
        """
        Initialize message handler
        
        Args:
            client: WAClient instance
        """
        self.logger = get_logger("MessageHandler")
        self.client = client
        self.pending_messages = {}
        
    async def send_text_message(self, to: str, text: str) -> Message:
        """
        Send a text message
        
        Args:
            to: Recipient phone number or group ID
            text: Message text
            
        Returns:
            Message: Sent message object
            
        Raises:
            WAMessageError: If sending fails
        """
        try:
            # Generate a unique message ID
            message_id = self._generate_message_id()
            
            # Create message object
            message = Message(
                id=message_id,
                to=to,
                from_me=True,
                text=text,
                timestamp=int(time.time())
            )
            
            # Store in pending messages
            self.pending_messages[message_id] = message
            
            # Prepare message payload
            payload = {
                "id": message_id,
                "type": "text",
                "to": to,
                "content": {
                    "text": text
                },
                "timestamp": message.timestamp
            }
            
            # Encrypt the message if needed
            if to.endswith("@c.us") or to.endswith("@g.us"):
                # This is a private chat or group
                # In a real implementation, we would encrypt this with Signal Protocol
                encrypted_payload = await self.client.crypto.encrypt_message(to, payload)
                
                # Send message through connection
                await self._send_message_packet(to, encrypted_payload, message_id)
            else:
                # For testing/debug, just send as-is
                await self._send_message_packet(to, payload, message_id)
            
            self.logger.info(f"Text message sent to {to}")
            
            # Emit message sent event
            self.client.event_emitter.emit(WAEventType.MESSAGE_SENT, message)
            
            return message
            
        except Exception as e:
            self.logger.error(f"Failed to send text message: {str(e)}")
            raise WAMessageError(f"Failed to send text message: {str(e)}")
    
    async def _send_message_packet(self, to: str, payload: Any, message_id: str):
        """
        Send message packet through WebSocket connection
        
        Args:
            to: Recipient
            payload: Message payload (encrypted or plain)
            message_id: Message ID
        """
        # Prepare WebSocket message packet
        packet = {
            "type": "message",
            "data": {
                "to": to,
                "id": message_id,
                "content": payload
            }
        }
        
        # Send through WebSocket connection
        await self.client.connection.send_json(packet)
    
    def parse_message(self, message_data: Dict[str, Any]) -> Message:
        """
        Parse a received message into a Message object
        
        Args:
            message_data: Raw message data
            
        Returns:
            Message: Parsed message object
        """
        try:
            # Extract basic message info
            message_id = message_data.get('id', '')
            sender = message_data.get('from', '')
            recipient = message_data.get('to', '')
            timestamp = message_data.get('timestamp', int(time.time()))
            
            # Determine if message is from current user
            from_me = sender == self.client.user_info.get('id') if self.client.user_info else False
            
            # Extract message content based on type
            content_data = message_data.get('content', {})
            message_type = message_data.get('type', 'unknown')
            
            if message_type == 'text':
                # Text message
                text = content_data.get('text', '')
                
                # Create message object
                message = Message(
                    id=message_id,
                    from_me=from_me,
                    to=recipient if from_me else sender,
                    text=text,
                    timestamp=timestamp
                )
                
            elif message_type == 'media':
                # Media message (image, video, audio, etc.)
                media_type = content_data.get('mediaType', 'unknown')
                caption = content_data.get('caption', '')
                
                # For now, we'll only handle the text caption
                message = Message(
                    id=message_id,
                    from_me=from_me,
                    to=recipient if from_me else sender,
                    text=caption,
                    media_type=media_type,
                    timestamp=timestamp
                )
                
            else:
                # Other message types
                self.logger.warning(f"Unsupported message type: {message_type}")
                
                # Create basic message object
                message = Message(
                    id=message_id,
                    from_me=from_me,
                    to=recipient if from_me else sender,
                    text="",
                    timestamp=timestamp
                )
            
            return message
            
        except Exception as e:
            self.logger.error(f"Failed to parse message: {str(e)}")
            # Return basic message object on error
            return Message(
                id=message_data.get('id', ''),
                from_me=False,
                to="",
                text="[Error parsing message]"
            )
    
    def _generate_message_id(self) -> str:
        """
        Generate a unique message ID
        
        Returns:
            str: Unique message ID
        """
        # Format: PREFIX.CURRENT_TIMESTAMP.RANDOM_UUID
        import time
        import uuid
        return f"WAPYLIB.{int(time.time() * 1000)}.{str(uuid.uuid4())}"
