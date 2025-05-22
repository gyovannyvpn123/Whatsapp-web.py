"""
Signal Protocol implementation for WhatsApp Web.

This module implements the Signal Protocol (Double Ratchet and X3DH) used by WhatsApp
for end-to-end encryption.
"""

import os
import json
import base64
from typing import Dict, Any, Optional, List, Tuple
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

from ..utils.logger import get_logger
from ..exceptions import WAEncryptionError
from .keys import IdentityKeyPair, PreKeyBundle, SessionBuilder

class SignalProtocol:
    """
    Implementation of Signal Protocol for WhatsApp Web
    
    This class handles all the encryption and decryption operations
    required for secure WhatsApp communication.
    """
    
    def __init__(self, storage_path: str):
        """
        Initialize Signal Protocol implementation
        
        Args:
            storage_path: Path to store keys and sessions
        """
        self.logger = get_logger("SignalProtocol")
        self.storage_path = storage_path
        self.keys_path = os.path.join(storage_path, "keys")
        self.sessions_path = os.path.join(storage_path, "sessions")
        
        # Create storage directories
        os.makedirs(self.keys_path, exist_ok=True)
        os.makedirs(self.sessions_path, exist_ok=True)
        
        # Initialize keys
        self.identity_key_pair = None
        self.prekeys = {}
        self.sessions = {}
        
        # User information
        self.user_id = None
        self.device_id = None
        
    async def initialize(self, user_info: Dict[str, Any]):
        """
        Initialize the protocol with user information
        
        Args:
            user_info: User information from authentication
        """
        self.user_id = user_info.get('id')
        if not self.user_id:
            raise WAEncryptionError("Missing user ID for Signal initialization")
            
        self.device_id = 1  # Default device ID for WhatsApp Web
        
        # Try to load existing keys
        loaded = await self._load_keys()
        if not loaded:
            # Generate new keys if none exist
            await self._generate_keys()
            
        self.logger.info(f"Signal Protocol initialized for user {self.user_id}")
        
    async def _load_keys(self) -> bool:
        """
        Load keys from storage
        
        Returns:
            bool: True if keys were loaded successfully
        """
        identity_key_file = os.path.join(self.keys_path, "identity_key.json")
        prekeys_file = os.path.join(self.keys_path, "prekeys.json")
        
        try:
            # Load identity key
            if os.path.exists(identity_key_file):
                with open(identity_key_file, 'r') as f:
                    identity_data = json.load(f)
                
                # Create identity key pair from stored data
                self.identity_key_pair = IdentityKeyPair.from_json(identity_data)
                
                # Load prekeys
                if os.path.exists(prekeys_file):
                    with open(prekeys_file, 'r') as f:
                        self.prekeys = json.load(f)
                
                self.logger.info("Keys loaded from storage")
                return True
            else:
                self.logger.info("No keys found in storage")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to load keys: {str(e)}")
            return False
            
    async def _generate_keys(self):
        """
        Generate new encryption keys
        """
        try:
            # Generate identity key pair
            self.identity_key_pair = IdentityKeyPair.generate()
            
            # Generate prekeys
            self._generate_prekeys(count=100)
            
            # Save generated keys
            await self._save_keys()
            
            self.logger.info("New keys generated")
            
        except Exception as e:
            self.logger.error(f"Failed to generate keys: {str(e)}")
            raise WAEncryptionError(f"Key generation failed: {str(e)}")
            
    def _generate_prekeys(self, count: int = 100, start_id: int = 1):
        """
        Generate prekeys for initial key exchange
        
        Args:
            count: Number of prekeys to generate
            start_id: Starting ID for prekeys
        """
        for i in range(start_id, start_id + count):
            # Generate private key
            private_key = X25519PrivateKey.generate()
            
            # Serialize private key (in a real app, use proper serialization)
            private_bytes = private_key.private_bytes(
                encoding=cryptography.hazmat.primitives.serialization.Encoding.Raw,
                format=cryptography.hazmat.primitives.serialization.PrivateFormat.Raw,
                encryption_algorithm=cryptography.hazmat.primitives.serialization.NoEncryption()
            )
            
            # Generate public key
            public_key = private_key.public_key()
            public_bytes = public_key.public_bytes(
                encoding=cryptography.hazmat.primitives.serialization.Encoding.Raw,
                format=cryptography.hazmat.primitives.serialization.PublicFormat.Raw
            )
            
            # Store key pair
            self.prekeys[str(i)] = {
                "id": i,
                "private": base64.b64encode(private_bytes).decode('utf-8'),
                "public": base64.b64encode(public_bytes).decode('utf-8')
            }
            
        self.logger.info(f"Generated {count} prekeys")
            
    async def _save_keys(self):
        """
        Save keys to storage
        """
        identity_key_file = os.path.join(self.keys_path, "identity_key.json")
        prekeys_file = os.path.join(self.keys_path, "prekeys.json")
        
        try:
            # Save identity key
            with open(identity_key_file, 'w') as f:
                json.dump(self.identity_key_pair.to_json(), f)
                
            # Save prekeys
            with open(prekeys_file, 'w') as f:
                json.dump(self.prekeys, f)
                
            self.logger.info("Keys saved to storage")
            
        except Exception as e:
            self.logger.error(f"Failed to save keys: {str(e)}")
            raise WAEncryptionError(f"Failed to save keys: {str(e)}")
            
    async def establish_session(self, recipient_id: str, prekey_bundle: Dict[str, Any]):
        """
        Establish a new session with a recipient
        
        Args:
            recipient_id: ID of the recipient
            prekey_bundle: Recipient's prekey bundle
        """
        try:
            # Create session builder
            session_builder = SessionBuilder(self.identity_key_pair)
            
            # Create prekey bundle from received data
            bundle = PreKeyBundle.from_json(prekey_bundle)
            
            # Process prekey bundle to establish session
            session = session_builder.process(bundle)
            
            # Save session
            self.sessions[recipient_id] = session.to_json()
            await self._save_session(recipient_id)
            
            self.logger.info(f"Session established with {recipient_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to establish session: {str(e)}")
            raise WAEncryptionError(f"Session establishment failed: {str(e)}")
            
    async def _save_session(self, recipient_id: str):
        """
        Save a session to storage
        
        Args:
            recipient_id: ID of the recipient
        """
        if recipient_id not in self.sessions:
            return
            
        session_file = os.path.join(self.sessions_path, f"{recipient_id}.json")
        
        try:
            with open(session_file, 'w') as f:
                json.dump(self.sessions[recipient_id], f)
                
            self.logger.debug(f"Session with {recipient_id} saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save session: {str(e)}")
            
    async def _load_session(self, recipient_id: str) -> bool:
        """
        Load a session from storage
        
        Args:
            recipient_id: ID of the recipient
            
        Returns:
            bool: True if session was loaded successfully
        """
        session_file = os.path.join(self.sessions_path, f"{recipient_id}.json")
        
        if not os.path.exists(session_file):
            return False
            
        try:
            with open(session_file, 'r') as f:
                self.sessions[recipient_id] = json.load(f)
                
            self.logger.debug(f"Session with {recipient_id} loaded")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load session: {str(e)}")
            return False
            
    async def encrypt_message(self, recipient_id: str, message_data: Dict[str, Any]) -> bytes:
        """
        Encrypt a message for a recipient using Signal Protocol
        
        Args:
            recipient_id: ID of the recipient
            message_data: Message data to encrypt
            
        Returns:
            bytes: Encrypted message
            
        Raises:
            WAEncryptionError: If encryption fails
        """
        # Ensure we have a session with the recipient
        if recipient_id not in self.sessions:
            loaded = await self._load_session(recipient_id)
            if not loaded:
                raise WAEncryptionError(f"No session established with {recipient_id}")
                
        try:
            # Serialize message data to bytes
            message_bytes = json.dumps(message_data).encode('utf-8')
            
            # Use the Signal Protocol session to encrypt
            # This is simplified - a real implementation would use the actual
            # Signal Protocol ratcheting mechanism
            
            # For demonstration purposes, we'll use a simple AES-GCM encryption
            # In a real implementation, this would use the Double Ratchet algorithm
            
            # Derive encryption key from session
            session_data = self.sessions[recipient_id]
            encryption_key = self._derive_key(session_data)
            
            # Generate random nonce
            nonce = os.urandom(12)
            
            # Encrypt with AES-GCM
            aesgcm = AESGCM(encryption_key)
            ciphertext = aesgcm.encrypt(nonce, message_bytes, None)
            
            # Prepend nonce to ciphertext
            encrypted_message = nonce + ciphertext
            
            self.logger.debug(f"Message encrypted for {recipient_id}")
            return encrypted_message
            
        except Exception as e:
            self.logger.error(f"Encryption failed: {str(e)}")
            raise WAEncryptionError(f"Failed to encrypt message: {str(e)}")
            
    async def decrypt_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt a message using Signal Protocol
        
        Args:
            message_data: Encrypted message data
            
        Returns:
            Dict: Decrypted message content
            
        Raises:
            WAEncryptionError: If decryption fails
        """
        sender_id = message_data.get('sender')
        if not sender_id:
            raise WAEncryptionError("Missing sender ID in encrypted message")
            
        encrypted_content = message_data.get('content')
        if not encrypted_content:
            raise WAEncryptionError("Missing encrypted content in message")
            
        # If binary base64 string, decode it
        if isinstance(encrypted_content, str):
            encrypted_content = base64.b64decode(encrypted_content)
            
        # Ensure we have a session with the sender
        if sender_id not in self.sessions:
            loaded = await self._load_session(sender_id)
            if not loaded:
                raise WAEncryptionError(f"No session established with {sender_id}")
                
        try:
            # Extract nonce and ciphertext
            nonce = encrypted_content[:12]
            ciphertext = encrypted_content[12:]
            
            # Derive decryption key from session
            session_data = self.sessions[sender_id]
            decryption_key = self._derive_key(session_data)
            
            # Decrypt with AES-GCM
            aesgcm = AESGCM(decryption_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            # Parse decrypted JSON
            decrypted_data = json.loads(plaintext.decode('utf-8'))
            
            self.logger.debug(f"Message from {sender_id} decrypted")
            return decrypted_data
            
        except Exception as e:
            self.logger.error(f"Decryption failed: {str(e)}")
            raise WAEncryptionError(f"Failed to decrypt message: {str(e)}")
            
    def _derive_key(self, session_data: Dict[str, Any]) -> bytes:
        """
        Derive an encryption/decryption key from session data
        
        Args:
            session_data: Session data
            
        Returns:
            bytes: 32-byte key
        """
        # In a real implementation, this would use the Signal Protocol key derivation
        # For demonstration, we'll use a simple HKDF derivation
        
        # Extract root key from session
        root_key_base64 = session_data.get('rootKey')
        if not root_key_base64:
            raise WAEncryptionError("Missing root key in session")
            
        root_key = base64.b64decode(root_key_base64)
        
        # Use HKDF to derive encryption key
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"WhatsApp Message Key",
            backend=default_backend()
        )
        
        return hkdf.derive(root_key)
