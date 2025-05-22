"""
WhatsApp Web WebSocket connection module.

Handles the WebSocket connection to WhatsApp Web servers.
"""

import json
import time
import asyncio
import websockets
from typing import Dict, Optional, Any, List, Union

from .utils.logger import get_logger
from .events import EventEmitter, WAEventType
from .constants import (
    WA_WEBSOCKET_URL, WA_ORIGIN, WA_USER_AGENT, WA_WS_PROTOCOLS, 
    WA_CLIENT_VERSION, WA_CLIENT_TOKEN, WA_ALTERNATIVE_WS_URLS,
    WA_BROWSER_NAME, WA_BROWSER_VERSION
)
from .exceptions import WAConnectionError

class WAConnection:
    """
    Manages WebSocket connection to WhatsApp Web servers
    """
    
    def __init__(self, event_emitter: EventEmitter):
        """
        Initialize connection manager
        
        Args:
            event_emitter: Event emitter for triggering events
        """
        self.logger = get_logger("WAConnection")
        self.event_emitter = event_emitter
        self.ws = None
        self._connected = False
        self._listener_task = None
        
    async def connect(self):
        """
        Connect to WhatsApp Web WebSocket server
        
        Raises:
            WAConnectionError: If connection fails
        """
        if self._connected:
            self.logger.warning("Already connected")
            return
            
        # Try the primary WebSocket URL first
        primary_ws_url = f"{WA_WEBSOCKET_URL}?v={WA_CLIENT_VERSION}&appVersion={WA_CLIENT_VERSION}&platform=web&clientToken={WA_CLIENT_TOKEN}"
        self.logger.info(f"Trying primary WebSocket URL: {primary_ws_url}")
        
        # Create list of all URLs to try (primary first, then alternatives)
        all_urls = [primary_ws_url]
        for alt_url in WA_ALTERNATIVE_WS_URLS:
            formatted_alt_url = f"{alt_url}?v={WA_CLIENT_VERSION}&appVersion={WA_CLIENT_VERSION}&platform=web&clientToken={WA_CLIENT_TOKEN}"
            all_urls.append(formatted_alt_url)
        
        # Common connection headers
        headers = {
            "Origin": WA_ORIGIN,
            "User-Agent": WA_USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits"
        }
        
        # Try each URL until one works
        last_error = None
        for ws_url in all_urls:
            try:
                self.logger.info(f"Attempting to connect to {ws_url}")
                
                # Connect to WhatsApp Web WebSocket server
                self.ws = await websockets.connect(
                    ws_url,
                    additional_headers=headers,
                    max_size=None,  # Don't limit message size
                    ping_interval=20,  # Send ping every 20 seconds
                    ping_timeout=10,   # Wait 10 seconds for pong
                    close_timeout=5    # Wait 5 seconds for close
                )
                
                self._connected = True
                self.logger.info(f"Successfully connected to {ws_url}")
                
                # Send initial hello message required by WhatsApp protocol
                await self._send_hello_message()
                
                # Start listener for incoming messages
                self._listener_task = asyncio.create_task(self._listen())
                
                # Emit connection open event
                self.event_emitter.emit(WAEventType.CONNECTION_OPEN, {"connected": True})
                
                # Successfully connected, no need to try other URLs
                return
                
            except Exception as e:
                self.logger.warning(f"Failed to connect to {ws_url}: {str(e)}")
                last_error = e
                # Continue to try next URL
        
        # If we got here, all connection attempts failed
        self._connected = False
        error_msg = f"All connection attempts failed. Last error: {str(last_error)}"
        self.logger.error(error_msg)
        raise WAConnectionError(error_msg)
    
    async def disconnect(self):
        """Disconnect from WhatsApp Web server"""
        if not self._connected:
            return
            
        self.logger.info("Disconnecting from WhatsApp Web server")
        
        # Cancel listener task
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        
        # Close WebSocket connection
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                self.logger.error(f"Error closing WebSocket: {str(e)}")
            self.ws = None
        
        self._connected = False
        
        # Emit connection close event
        self.event_emitter.emit(WAEventType.CONNECTION_CLOSE, None)
    
    async def _listen(self):
        """
        Listen for incoming WebSocket messages
        """
        reconnect_attempts = 0
        max_reconnect_attempts = 3
        
        try:
            while self._connected:
                if not self.ws:
                    self.logger.error("WebSocket connection lost")
                    
                    # Try to reconnect
                    if reconnect_attempts < max_reconnect_attempts:
                        reconnect_attempts += 1
                        self.logger.info(f"Attempting to reconnect (attempt {reconnect_attempts}/{max_reconnect_attempts})")
                        try:
                            # Use the last successful URL
                            await self.connect()
                            self.logger.info("Successfully reconnected")
                            reconnect_attempts = 0  # Reset counter on successful reconnect
                            continue
                        except Exception as e:
                            self.logger.error(f"Failed to reconnect: {str(e)}")
                    
                    break
                
                # Wait for next message with a timeout
                try:
                    message = await asyncio.wait_for(self.ws.recv(), timeout=30)
                    # Reset reconnect attempts on successful message
                    reconnect_attempts = 0
                    await self._process_message(message)
                except asyncio.TimeoutError:
                    # No message received in timeout period, send a ping to keep connection alive
                    self.logger.debug("No message received, sending ping")
                    try:
                        pong_waiter = await self.ws.ping()
                        await asyncio.wait_for(pong_waiter, timeout=10)
                        self.logger.debug("Received pong response")
                    except Exception as e:
                        self.logger.warning(f"Ping failed: {str(e)}")
                        # Connection might be dead, try to reconnect
                except websockets.exceptions.ConnectionClosed as e:
                    self.logger.error(f"WebSocket connection closed: {str(e)}")
                    break
                except Exception as e:
                    self.logger.error(f"Error receiving message: {str(e)}")
                    # Continue listening for next message
        
        finally:
            # Ensure we're marked as disconnected
            self._connected = False
            self.event_emitter.emit(WAEventType.CONNECTION_CLOSE, None)
    
    async def _process_message(self, message: Union[str, bytes]):
        """
        Process incoming WebSocket message
        
        Args:
            message: Raw message from WebSocket
        """
        # Determine if this is a binary or text message
        if isinstance(message, bytes):
            # Binary message (protobuf)
            await self._handle_binary_message(message)
        else:
            # Text message (JSON) - ensure it's a string
            await self._handle_text_message(str(message))
    
    async def _handle_text_message(self, message: Union[str, bytearray, memoryview]):
        """
        Handle JSON text message from WebSocket
        
        Args:
            message: JSON string message or convertible to string
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            msg_data = data.get('data', {})
            
            self.logger.info(f"Received message type: {msg_type}")
            self.logger.debug(f"Message data: {msg_data}")
            
            # Route message to appropriate handler based on type
            if msg_type == 'qr':
                # QR code for authentication
                qr_data = msg_data.get('qrCode')
                if qr_data:
                    # Generate QR image from the received data
                    from .auth import WAAuthentication
                    auth = WAAuthentication("./whatsapp_session")
                    qr_image = auth.generate_qr_image(qr_data)
                    
                    # Emit QR code event with both data and image
                    qr_event_data = {
                        'qr_data': qr_data,
                        'qr_image': qr_image
                    }
                    self.event_emitter.emit(WAEventType.QR_CODE, qr_event_data)
                    self.logger.info("Received and processed QR code from server")
                else:
                    self.logger.warning("Received QR message but no QR code data")
            
            elif msg_type == 'auth':
                # Authentication response
                self.logger.info(f"Received authentication response: {msg_data}")
                self.event_emitter.emit(WAEventType.AUTH_RESPONSE, msg_data)
            
            elif msg_type == 'message':
                # Regular message
                self.event_emitter.emit(WAEventType.MESSAGE_RECEIVED, msg_data)
            
            elif msg_type == 'presence':
                # Presence update (online/offline)
                self.event_emitter.emit(WAEventType.PRESENCE_UPDATE, msg_data)
            
            elif msg_type == 'group':
                # Group update
                self.event_emitter.emit(WAEventType.GROUP_UPDATE, msg_data)
            
            elif msg_type == 'notification':
                # General notification
                self.event_emitter.emit(WAEventType.NOTIFICATION, msg_data)
            
            # Add handler for more message types
            elif msg_type == 'conn':
                # Connection status update
                self.logger.info(f"Connection status update: {msg_data}")
                # This might contain information about connection state
                
            elif msg_type == 'challenge':
                # Security challenge that might need to be responded to
                self.logger.info("Received security challenge")
                # Handle challenge response here
                
            elif msg_type == 'stream':
                # Stream-related message
                self.logger.info("Received stream event")
                
            else:
                # Unknown message type - log it for debugging
                self.logger.warning(f"Unknown message type: {msg_type}")
                self.logger.debug(f"Unknown message content: {data}")
        
        except json.JSONDecodeError:
            self.logger.error("Failed to decode JSON message")
            self.logger.debug(f"Raw message: {message}")
        except Exception as e:
            self.logger.error(f"Error handling text message: {str(e)}")
    
    async def _handle_binary_message(self, message: bytes):
        """
        Handle binary message (usually protobuf encoded)
        
        Args:
            message: Binary message data
        """
        # For now, just emit the raw binary message
        # Later, this will be processed through the protobuf parser
        self.event_emitter.emit(WAEventType.BINARY_MESSAGE, message)
    
    async def send_json(self, data: Dict):
        """
        Send JSON data over WebSocket
        
        Args:
            data: Dictionary to send as JSON
            
        Raises:
            WAConnectionError: If sending fails
        """
        if not self._connected or not self.ws:
            raise WAConnectionError("Not connected")
        
        try:
            await self.ws.send(json.dumps(data))
        except Exception as e:
            self.logger.error(f"Failed to send message: {str(e)}")
            raise WAConnectionError(f"Failed to send message: {str(e)}")
    
    async def send_binary(self, data: bytes):
        """
        Send binary data over WebSocket
        
        Args:
            data: Binary data to send
            
        Raises:
            WAConnectionError: If sending fails
        """
        if not self._connected or not self.ws:
            raise WAConnectionError("Not connected")
        
        try:
            await self.ws.send(data)
        except Exception as e:
            self.logger.error(f"Failed to send binary message: {str(e)}")
            raise WAConnectionError(f"Failed to send binary message: {str(e)}")
    
    async def _send_hello_message(self):
        """
        Send initial hello message to the WhatsApp server.
        This is required to establish the connection properly.
        """
        try:
            # Format close to what WhatsApp Web actually sends
            hello_msg = {
                "clientToken": WA_CLIENT_TOKEN,
                "clientVersion": WA_CLIENT_VERSION,
                "connectType": "WIFI_UNKNOWN",
                "connectReason": "USER_ACTIVATED",
                "deviceName": f"{WA_BROWSER_NAME} on Desktop",
                "features": {
                    "documentEditor": {
                        "enabled": False
                    },
                    "communityAnnouncements": {
                        "enabled": True
                    },
                    "hfmCompression": {
                        "enabled": True
                    },
                    "md_migration": {
                        "enabled": True
                    }
                },
                "passive": False,
                "pushName": "WhatsAppWebPy",
                "type": "hello",
                "platform": "WEB",
                "userAgent": {
                    "appVersion": WA_CLIENT_VERSION,
                    "browser": WA_BROWSER_NAME,
                    "browser_version": WA_BROWSER_VERSION,
                    "os": "Windows",
                    "os_version": "10.0"
                },
                "webInfo": {
                    "timestamp": str(int(time.time())),
                    "expiration": "86400",
                    "status": "healthy"
                }
            }
            
            self.logger.info("Sending hello message to server")
            await self.send_json(hello_msg)
            
            # Send a follow-up message for authentication
            auth_init_msg = {
                "type": "init",
                "version": [10, WA_CLIENT_VERSION],
                "platform": "web"
            }
            await asyncio.sleep(0.5)
            self.logger.info("Sending authentication initialization message")
            await self.send_json(auth_init_msg)
            
        except Exception as e:
            self.logger.error(f"Failed to send hello message: {str(e)}")
            
    def is_connected(self) -> bool:
        """
        Check if currently connected
        
        Returns:
            bool: True if connected to WhatsApp Web server
        """
        return self._connected and self.ws is not None
