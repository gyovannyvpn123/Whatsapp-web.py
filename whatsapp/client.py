"""
Main WhatsApp client implementation. This is the primary class users will interact with.
"""

import asyncio
import json
import os
import logging
from typing import Callable, Dict, List, Optional, Union, Any, Set

from .auth import WAAuthentication
from .connection import WAConnection
from .crypto.signal import SignalProtocol
from .handlers.message import MessageHandler
from .handlers.group import GroupHandler
from .models.message import Message
from .utils.logger import get_logger
from .events import EventEmitter, WAEventType
from .exceptions import WAConnectionError, WAAuthenticationError

class WAClient:
    """
    WhatsApp Web Client - Main entry point for the library.
    Handles the coordination between connection, authentication, encryption,
    and message handling components.
    """
    
    def __init__(self, session_path: Optional[str] = None, log_level: int = logging.INFO):
        """
        Initialize a new WhatsApp Web client.
        
        Args:
            session_path: Path to store session data for reusing authentication
            log_level: Logging level for the client
        """
        self.logger = get_logger("WAClient", log_level)
        self.logger.info("Initializing WhatsApp Web client")
        
        self.session_path = session_path or os.path.join(os.getcwd(), "whatsapp_session")
        os.makedirs(self.session_path, exist_ok=True)
        
        self.authenticated = False
        self.qr_callback = None
        
        # Initialize components
        self.event_emitter = EventEmitter()
        self.auth = WAAuthentication(self.session_path)
        self.connection = WAConnection(self.event_emitter)
        self.crypto = SignalProtocol(self.session_path)
        self.message_handler = MessageHandler(self)
        self.group_handler = GroupHandler(self)
        
        # Set up internal event handlers
        self._setup_internal_handlers()
        
        self.user_info = None  # Will be populated after authentication

    def _setup_internal_handlers(self):
        """Set up the internal event handlers"""
        self.event_emitter.on(WAEventType.CONNECTION_OPEN, self._on_connection_open)
        self.event_emitter.on(WAEventType.CONNECTION_CLOSE, self._on_connection_close)
        self.event_emitter.on(WAEventType.QR_CODE, self._on_qr_code)
        self.event_emitter.on(WAEventType.AUTHENTICATED, self._on_authenticated)
        self.event_emitter.on(WAEventType.MESSAGE_RECEIVED, self._on_message_received)

    async def _on_connection_open(self, data):
        """Handle connection open event"""
        self.logger.info("Connection to WhatsApp servers established")
        await self.auth.start_authentication(self.connection)

    async def _on_connection_close(self, data):
        """Handle connection close event"""
        self.logger.info("Connection to WhatsApp servers closed")
        self.authenticated = False

    async def _on_qr_code(self, qr_data):
        """Handle QR code event"""
        self.logger.info("QR code received from server")
        if self.qr_callback:
            await self.qr_callback(qr_data)

    async def _on_authenticated(self, user_info):
        """Handle authentication success event"""
        self.logger.info(f"Authentication successful for {user_info.get('name', 'user')}")
        self.authenticated = True
        self.user_info = user_info
        
        # Initialize the crypto protocol with the user credentials
        await self.crypto.initialize(user_info)

    async def _on_message_received(self, message_data):
        """Handle incoming message event"""
        # Decrypt the message using Signal Protocol
        try:
            decrypted_data = await self.crypto.decrypt_message(message_data)
            parsed_message = self.message_handler.parse_message(decrypted_data)
            self.event_emitter.emit(WAEventType.MESSAGE, parsed_message)
        except Exception as e:
            self.logger.error(f"Failed to process message: {str(e)}")

    async def connect(self):
        """
        Connect to WhatsApp Web servers and authenticate.
        This will either use stored session or generate a new QR code.
        """
        self.logger.info("Connecting to WhatsApp Web")
        
        try:
            # Try to restore session if possible
            restored = await self.auth.restore_session()
            if restored:
                self.logger.info("Session restored, reconnecting")
                self.authenticated = True
            
            # Connect to the WebSocket server
            await self.connection.connect()
            
            # If we couldn't restore the session, authentication will 
            # start automatically via the connection_open event
            
        except Exception as e:
            self.logger.error(f"Failed to connect: {str(e)}")
            raise WAConnectionError(f"Connection failed: {str(e)}")

    async def disconnect(self):
        """Disconnect from WhatsApp Web servers"""
        self.logger.info("Disconnecting from WhatsApp Web")
        await self.connection.disconnect()

    def on(self, event_type: WAEventType, callback: Callable):
        """
        Register event listeners
        
        Args:
            event_type: Type of event to listen for
            callback: Async callback function to call when event occurs
        """
        self.event_emitter.on(event_type, callback)

    def set_qr_callback(self, callback: Callable):
        """
        Set callback for QR code events
        
        Args:
            callback: Async function that takes QR code data
        """
        self.qr_callback = callback

    async def send_message(self, to: str, text: str) -> Message:
        """
        Send a text message to a contact or group
        
        Args:
            to: Phone number (with country code) or group ID
            text: Message text content
            
        Returns:
            Message object for the sent message
        """
        if not self.authenticated:
            # Not raising exception here - we'll check connection and try to reconnect
            self.logger.warning("Not authenticated, attempting to reconnect...")
            try:
                await self.connect()
                # Give it 5 seconds to authenticate
                for _ in range(10):
                    if self.authenticated:
                        break
                    await asyncio.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Failed to reconnect: {e}")
                raise WAAuthenticationError("Not authenticated and reconnection failed")
                
            if not self.authenticated:
                raise WAAuthenticationError("Not authenticated after reconnection attempt")
        
        # Format the phone number if needed (ensure it has country code and proper format)
        if not to.startswith("@g.us") and not to.endswith("@c.us"):
            # Remove any non-digit characters from phone number except + at the beginning
            if to.startswith("+"):
                clean_number = "+" + ''.join(filter(str.isdigit, to[1:]))
            else:
                clean_number = ''.join(filter(str.isdigit, to))
                
            # Add WhatsApp suffix if not a group ID
            to = f"{clean_number}@c.us" if "@" not in clean_number else clean_number
        
        self.logger.info(f"Sending message to {to}: {text[:20]}{'...' if len(text) > 20 else ''}")
        
        import time
        
        # Create the message object
        message = Message(
            id="temp_" + str(int(time.time())),  # Temporary ID until server assigns one
            to=to,
            from_me=True,
            text=text,
            timestamp=int(time.time())  # Add current timestamp
        )
        
        try:
            # Let the message handler process and send the message
            sent_message = await self.message_handler.send_text_message(to, text)
            self.logger.info(f"Message sent successfully to {to}")
            
            # Emit message sent event
            self.event_emitter.emit(WAEventType.MESSAGE_SENT, sent_message)
            
            return sent_message
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {str(e)}")
            # Emit error event
            error_data = {
                "message": message,
                "error": str(e)
            }
            self.event_emitter.emit(WAEventType.MESSAGE_DELIVERY, error_data)
            raise

    async def logout(self):
        """Log out and clear session data"""
        self.logger.info("Logging out from WhatsApp Web")
        await self.auth.logout()
        await self.connection.disconnect()
        self.authenticated = False
        self.user_info = None
