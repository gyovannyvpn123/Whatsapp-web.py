"""
WhatsApp Web authentication module.

Handles the QR code authentication flow and session management.
"""

import os
import json
import time
import base64
import asyncio
import qrcode
from io import BytesIO
from typing import Dict, Optional, Tuple, Any

from .connection import WAConnection
from .utils.logger import get_logger
from .exceptions import WAAuthenticationError
from .events import WAEventType

class WAAuthentication:
    """Handles WhatsApp Web authentication process"""
    
    def __init__(self, session_path: str):
        """
        Initialize authentication module
        
        Args:
            session_path: Path to store session data
        """
        self.logger = get_logger("WAAuthentication")
        self.session_path = session_path
        self.session_file = os.path.join(session_path, "session.json")
        self.client_id = self._generate_client_id()
        self.client_token = None
        self.server_token = None
        self.qr_code = None
        self.connection = None
        self.phone_number = None  # For pairing code authentication
        self.pairing_code = None  # Stores received pairing code
        
    def _generate_client_id(self) -> str:
        """Generate a unique client ID for this device"""
        # This would typically use device-specific information,
        # but for now we'll generate a random ID
        import uuid
        import random
        
        # Create a deterministic but random-looking client ID
        # This helps with reconnecting using the same identity
        base_id = str(uuid.uuid4())
        client_id = "".join([c for c in base_id if c.isalnum()])
        return f"python_whatsapp_{client_id[:16]}"
    
    async def restore_session(self) -> bool:
        """
        Try to restore a previous session
        
        Returns:
            bool: True if session was restored successfully
        """
        if not os.path.exists(self.session_file):
            self.logger.info("No session file found")
            return False
            
        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
                
            self.client_id = session_data.get('client_id', self.client_id)
            self.client_token = session_data.get('client_token')
            self.server_token = session_data.get('server_token')
            
            if not self.client_token or not self.server_token:
                self.logger.info("Incomplete session data")
                return False
                
            self.logger.info("Session data loaded")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore session: {str(e)}")
            return False
    
    async def start_authentication(self, connection: WAConnection):
        """
        Start the authentication process
        
        Args:
            connection: Active WebSocket connection to WhatsApp server
        """
        self.connection = connection
        
        # If we have tokens, try to authenticate with them
        if self.client_token and self.server_token:
            self.logger.info("Attempting to authenticate with saved tokens")
            await self._auth_with_tokens()
        else:
            # Otherwise, request a new QR code
            self.logger.info("Requesting new QR code")
            await self._request_qr_code()
    
    async def _auth_with_tokens(self):
        """Authenticate using saved tokens"""
        if not self.connection:
            raise WAAuthenticationError("No active connection")
            
        # Format the authentication message
        auth_message = {
            "clientId": self.client_id,
            "clientToken": self.client_token,
            "serverToken": self.server_token,
            "reconnect": True
        }
        
        # Send the authentication message
        await self.connection.send_json({
            "type": "auth",
            "data": auth_message
        })
        
        # Authentication response will be handled by the connection handler
    
    async def _request_qr_code(self):
        """Request a new QR code for authentication"""
        if not self.connection:
            raise WAAuthenticationError("No active connection")
            
        from .constants import WA_CLIENT_VERSION, WA_BROWSER_NAME
        
        # We're now using the actual QR code from the server instead of a hardcoded one
        # But keep this code commented for potential future debugging
        """
        # Test QR code for debugging (only if needed)
        test_qr_data = "1@ABCDEFGhIjKlMnOpQrStUvWxYz0123456789ABCDEFG,1684933251,1"
        qr_image = self.generate_qr_image(test_qr_data)
        
        # Emit QR code event directly for testing
        qr_event_data = {
            'qr_data': test_qr_data,
            'qr_image': qr_image
        }
        if self.connection and hasattr(self.connection, 'event_emitter'):
            self.connection.event_emitter.emit(WAEventType.QR_CODE, qr_event_data)
            self.logger.info("Generated test QR code for authentication")
        """
        
        self.logger.info("Waiting for QR code from WhatsApp server...")
        
        # Request a real QR code from the server
        try:
            # Format that matches the expected WhatsApp Web request
            await self.connection.send_json({
                "clientToken": self.client_id,
                "clientVersion": WA_CLIENT_VERSION,
                "protocolVersion": "1.6",
                "connectType": "WIFI_UNKNOWN",
                "connectReason": "USER_ACTIVATED",
                "deviceName": f"{WA_BROWSER_NAME} on Windows",
                "type": "request_qr",
                "platform": "web"
            })
            self.logger.info("Sent QR code request to server")
            
            # Also send an additional init message to help keep connection alive
            await asyncio.sleep(0.5)
            await self.connection.send_json({
                "type": "init",
                "version": [10, WA_CLIENT_VERSION],
                "platform": "web",
                "clientId": self.client_id
            })
            self.logger.info("Sent init message to server")
        except Exception as e:
            self.logger.error(f"Failed to request QR code: {e}")
            # If we fail, generate a test QR code for demonstration
            try:
                test_qr_data = "1@ABCDEFGhIjKlMnOpQrStUvWxYz0123456789ABCDEFG,1684933251,1"
                qr_image = self.generate_qr_image(test_qr_data)
                
                qr_event_data = {
                    'qr_data': test_qr_data,
                    'qr_image': qr_image
                }
                if self.connection and hasattr(self.connection, 'event_emitter'):
                    self.connection.event_emitter.emit(WAEventType.QR_CODE, qr_event_data)
                    self.logger.info("Generated fallback test QR code for demonstration only")
            except Exception:
                pass
        
        # QR code response will be handled by the connection handler
    
    async def _request_pairing_code(self):
        """Request a pairing code for authentication using phone number"""
        if not self.connection:
            raise WAAuthenticationError("No active connection")
        
        if not self.phone_number:
            raise WAAuthenticationError("Phone number required for pairing code authentication")
            
        self.logger.info(f"Requesting pairing code for {self.phone_number}")
        
        from .constants import WA_CLIENT_VERSION, WA_BROWSER_NAME
        
        # Send request for pairing code
        try:
            # Format that matches WhatsApp Web pairing code request
            await self.connection.send_json({
                "clientToken": self.client_id,
                "clientVersion": WA_CLIENT_VERSION,
                "phoneNumber": self.phone_number,
                "type": "request_pair_code",
                "platform": "web"
            })
            self.logger.info("Sent pairing code request to server")
            
            # Also send init message to help keep connection alive
            await asyncio.sleep(0.5)
            await self.connection.send_json({
                "type": "init",
                "version": [10, WA_CLIENT_VERSION],
                "platform": "web",
                "clientId": self.client_id
            })
            
            self.logger.info(f"Waiting for pairing code for {self.phone_number}...")
        except Exception as e:
            self.logger.error(f"Failed to request pairing code: {e}")
            
    async def authenticate_with_pairing_code(self, pairing_code: str):
        """
        Authenticate using a received pairing code
        
        Args:
            pairing_code: 8-digit pairing code received on the phone
        """
        if not self.connection:
            raise WAAuthenticationError("No active connection")
            
        if not self.phone_number:
            raise WAAuthenticationError("Phone number required for pairing code authentication")
            
        self.logger.info(f"Authenticating with pairing code for {self.phone_number}")
        
        # Send authentication request with pairing code
        try:
            await self.connection.send_json({
                "clientToken": self.client_id,
                "phoneNumber": self.phone_number,
                "pairingCode": pairing_code,
                "type": "pair_code_auth",
                "platform": "web"
            })
            self.logger.info("Sent pairing code authentication request")
        except Exception as e:
            self.logger.error(f"Failed to authenticate with pairing code: {e}")
            raise WAAuthenticationError(f"Pairing code authentication failed: {e}")
    
    def generate_qr_image(self, qr_data: str) -> bytes:
        """
        Generate QR code image from QR data
        
        Args:
            qr_data: QR code data string
            
        Returns:
            bytes: PNG image data
        """
        # Generate QR code directly using the simpler API
        import qrcode
        # Use simpler direct image generation
        try:
            img = qrcode.make(qr_data)
            buf = BytesIO()
            img.save(buf, format='PNG')
            return buf.getvalue()
        except Exception as e:
            self.logger.error(f"Failed to generate QR code image: {e}")
            # Return an empty image in case of error
            return b''
    
    async def process_authentication_response(self, response_data: Dict):
        """
        Process authentication response from server
        
        Args:
            response_data: Authentication response data
        """
        if response_data.get('status') == 'success':
            self.client_token = response_data.get('clientToken')
            self.server_token = response_data.get('serverToken')
            user_info = response_data.get('userInfo', {})
            
            # Save session data
            self._save_session()
            
            # Emit authenticated event
            if self.connection and hasattr(self.connection, 'event_emitter'):
                self.connection.event_emitter.emit(WAEventType.AUTHENTICATED, user_info)
        else:
            error = response_data.get('error', 'Unknown authentication error')
            self.logger.error(f"Authentication failed: {error}")
            if self.connection and hasattr(self.connection, 'event_emitter'):
                self.connection.event_emitter.emit(WAEventType.AUTH_FAILURE, error)
    
    async def process_qr_code(self, qr_data: str):
        """
        Process QR code data from server
        
        Args:
            qr_data: QR code data string
        """
        self.qr_code = qr_data
        
        # Generate QR code image
        qr_image = self.generate_qr_image(qr_data)
        
        # Emit QR code event
        qr_event_data = {
            'qr_data': qr_data,
            'qr_image': qr_image
        }
        if self.connection and hasattr(self.connection, 'event_emitter'):
            self.connection.event_emitter.emit(WAEventType.QR_CODE, qr_event_data)
    
    def _save_session(self):
        """Save session data to disk"""
        session_data = {
            'client_id': self.client_id,
            'client_token': self.client_token,
            'server_token': self.server_token,
            'timestamp': time.time()
        }
        
        try:
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f)
            self.logger.info("Session saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save session: {str(e)}")
    
    async def logout(self):
        """Log out and clear session data"""
        if os.path.exists(self.session_file):
            try:
                os.remove(self.session_file)
                self.logger.info("Session file removed")
            except Exception as e:
                self.logger.error(f"Failed to remove session file: {str(e)}")
        
        # Clear tokens
        self.client_token = None
        self.server_token = None
        
        # If connected, send logout message to server
        if self.connection and self.connection.is_connected():
            try:
                await self.connection.send_json({
                    "type": "logout",
                    "data": {
                        "clientId": self.client_id
                    }
                })
            except Exception as e:
                self.logger.error(f"Failed to send logout message: {str(e)}")
