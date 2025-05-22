"""
WebSocket connection handler for WhatsApp Web.

This module handles establishing and maintaining a WebSocket connection to
WhatsApp Web servers, with improved reconnection logic and error handling.
"""

import json
import logging
import time
import websocket
import threading
import random
import base64
from typing import Callable, Dict, Optional, List, Any, Union
from urllib.parse import urlencode

from .errors import WAConnectionError, WAAuthenticationError
from .utils import generate_message_tag, generate_client_id

logger = logging.getLogger(__name__)

# Constants
WA_WEB_URL = "wss://web.whatsapp.com/ws"
WA_ORIGIN = "https://web.whatsapp.com"
WA_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.177 Safari/537.36"
WA_VERSION = "2.2402.7"
WA_WEB_BROWSER = "Chrome,110.0.5481.177"

class WAConnection:
    """
    WhatsApp WebSocket Connection Handler.
    
    This class manages the WebSocket connection to WhatsApp Web servers,
    with improved reconnection logic based on insights from @whiskeysockets/baileys.
    """
    
    def __init__(self):
        self.ws: Optional[websocket.WebSocketApp] = None
        self.connected = False
        self.authenticated = False
        self.client_id = generate_client_id()
        self.client_token = None
        self.server_token = None
        self.secret = None
        self.last_seen = None
        
        # Callbacks
        self.on_message_callback = None
        self.on_connect_callback = None
        self.on_close_callback = None
        self.on_error_callback = None
        
        # Connection parameters
        self.reconnect_interval = 3
        self.max_reconnect_interval = 60
        self.reconnect_decay = 1.5
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
        # Queues and locks
        self.pending_requests: Dict[str, Dict] = {}
        self.lock = threading.RLock()
        
        # Keepalive mechanism
        self.keepalive_thread = None
        self.keepalive_interval = 20

    def connect(self) -> bool:
        """
        Establish WebSocket connection to WhatsApp Web servers.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            logger.info("Connecting to WhatsApp Web...")
            
            # Create websocket connection
            query_params = {
                "version": "2.2319.9",
                "browser_data": "Chrome,91.0.4472.124",
                "clientId": self.client_id
            }
            
            url = f"{WA_WEB_URL}?{urlencode(query_params)}"
            
            self.ws = websocket.WebSocketApp(
                url,
                on_message=self._on_message,
                on_open=self._on_open,
                on_close=self._on_close,
                on_error=self._on_error,
                header={
                    "Origin": WA_ORIGIN,
                    "User-Agent": WA_USER_AGENT
                }
            )
            
            # Start WebSocket connection in a separate thread
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection to establish
            timeout = 30
            start_time = time.time()
            while not self.connected and time.time() - start_time < timeout:
                time.sleep(0.5)
            
            if not self.connected:
                logger.error("Failed to connect within timeout period")
                return False
                
            # Start keepalive mechanism
            self._start_keepalive()
            
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise WAConnectionError(f"Failed to connect: {e}")

    def disconnect(self) -> None:
        """
        Disconnect from WhatsApp Web servers.
        """
        try:
            logger.info("Disconnecting from WhatsApp Web...")
            
            # Stop keepalive thread
            if self.keepalive_thread and self.keepalive_thread.is_alive():
                self.keepalive_thread = None
            
            # Close WebSocket connection
            if self.ws:
                self.ws.close()
                self.ws = None
                
            self.connected = False
            self.authenticated = False
            
            logger.info("Disconnected from WhatsApp Web")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    def reconnect(self) -> bool:
        """
        Attempt to reconnect to WhatsApp Web servers with exponential backoff.
        
        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Maximum reconnection attempts reached")
            return False
        
        self.reconnect_attempts += 1
        wait_time = min(
            self.reconnect_interval * (self.reconnect_decay ** (self.reconnect_attempts - 1)),
            self.max_reconnect_interval
        )
        
        logger.info(f"Attempting to reconnect in {wait_time:.2f} seconds (attempt {self.reconnect_attempts})")
        time.sleep(wait_time)
        
        try:
            # Ensure old connection is closed
            if self.ws:
                try:
                    self.ws.close()
                except:
                    pass
                
            self.ws = None
            self.connected = False
            return self.connect()
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            return False

    def send_message(self, data: Union[Dict, List, str], tag: Optional[str] = None) -> str:
        """
        Send a message through the WebSocket connection.
        
        Args:
            data: Message data to send
            tag: Optional message tag for tracking the response
            
        Returns:
            str: Message tag used for the message
            
        Raises:
            WAConnectionError: If connection is not established
        """
        if not self.connected or not self.ws:
            raise WAConnectionError("Not connected to WhatsApp Web")
        
        tag = tag or generate_message_tag()
        
        if isinstance(data, (dict, list)):
            data = json.dumps(data)
        
        message = f"{tag},{data}"
        
        try:
            logger.debug(f"Sending message: {message[:100]}...")
            self.ws.send(message)
            return tag
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise WAConnectionError(f"Failed to send message: {e}")

    def register_callback(self, 
                          on_message: Optional[Callable] = None,
                          on_connect: Optional[Callable] = None,
                          on_close: Optional[Callable] = None,
                          on_error: Optional[Callable] = None) -> None:
        """
        Register callbacks for WebSocket events.
        
        Args:
            on_message: Callback for message events
            on_connect: Callback for connection events
            on_close: Callback for connection close events
            on_error: Callback for error events
        """
        if on_message:
            self.on_message_callback = on_message
        if on_connect:
            self.on_connect_callback = on_connect
        if on_close:
            self.on_close_callback = on_close
        if on_error:
            self.on_error_callback = on_error

    def _on_message(self, ws, message: str) -> None:
        """
        Internal WebSocket message handler.
        
        Args:
            ws: WebSocket instance
            message: Received message
        """
        try:
            if not message:
                return
                
            logger.debug(f"Received message: {message[:100]}...")
            
            # Parse message tag and data
            parts = message.split(",", 1)
            if len(parts) < 2:
                logger.warning(f"Received malformed message: {message[:50]}...")
                return
                
            tag = parts[0]
            data_str = parts[1]
            
            # Binary message handling
            if tag.startswith("pong"):
                logger.debug("Received pong message")
                return
                
            # Try to parse JSON data
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                data = data_str
            
            # Handle connection success message
            if tag == "s1" and isinstance(data, dict) and data.get("status") == 200:
                self.client_token = data.get("clientToken")
                self.server_token = data.get("serverToken")
                self.connected = True
                logger.info("Successfully connected to WhatsApp Web")
                
                if self.on_connect_callback:
                    self.on_connect_callback(self)
                return
            
            # Call user callback
            if self.on_message_callback:
                self.on_message_callback(tag, data)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_open(self, ws) -> None:
        """
        Internal WebSocket connection open handler.
        
        Args:
            ws: WebSocket instance
        """
        logger.info("WebSocket connection established")
        self.connected = True
        self.reconnect_attempts = 0
        
        # Initialize connection with server
        self._send_init_message()

    def _on_close(self, ws, close_status_code, close_reason) -> None:
        """
        Internal WebSocket connection close handler.
        
        Args:
            ws: WebSocket instance
            close_status_code: Status code for closure
            close_reason: Reason for closure
        """
        was_connected = self.connected
        self.connected = False
        
        logger.info(f"WebSocket connection closed: {close_status_code} - {close_reason}")
        
        if self.on_close_callback:
            self.on_close_callback(close_status_code, close_reason)
            
        # Attempt reconnection if the connection was previously established
        if was_connected:
            self.reconnect()

    def _on_error(self, ws, error) -> None:
        """
        Internal WebSocket error handler.
        
        Args:
            ws: WebSocket instance
            error: Error that occurred
        """
        logger.error(f"WebSocket error: {error}")
        
        if self.on_error_callback:
            self.on_error_callback(error)

    def _send_init_message(self) -> None:
        """
        Send initial connection message to WhatsApp Web servers.
        """
        init_message = {
            "clientId": self.client_id,
            "connectType": "WIFI_UNKNOWN",
            "connectReason": "USER_ACTIVATED",
            "userAgent": WA_USER_AGENT,
            "webVersion": "2.2319.9",
            "browserName": "Chrome"
        }
        
        if self.client_token and self.server_token:
            init_message["clientToken"] = self.client_token
            init_message["serverToken"] = self.server_token
            
        self.send_message(init_message, "admin")

    def _start_keepalive(self) -> None:
        """
        Start keepalive thread to maintain connection.
        """
        def keepalive_worker():
            while self.connected and self.ws:
                try:
                    logger.debug("Sending keepalive ping")
                    self.ws.send("?,,")
                    time.sleep(self.keepalive_interval)
                except Exception as e:
                    logger.error(f"Keepalive error: {e}")
                    break
        
        self.keepalive_thread = threading.Thread(target=keepalive_worker)
        self.keepalive_thread.daemon = True
        self.keepalive_thread.start()
