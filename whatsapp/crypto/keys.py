"""
Key management for Signal Protocol in WhatsApp Web.

This module handles the various types of keys used in the Signal Protocol,
including identity keys, prekeys, and signed prekeys.
"""

import os
import base64
import json
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from ..utils.logger import get_logger
from ..exceptions import WAEncryptionError

logger = get_logger("SignalKeys")

class IdentityKeyPair:
    """
    Identity key pair for Signal Protocol
    
    Consists of a long-term Ed25519 key pair used for signing.
    """
    
    def __init__(self, private_key: Ed25519PrivateKey, public_key: Ed25519PublicKey):
        """
        Initialize identity key pair
        
        Args:
            private_key: Ed25519 private key
            public_key: Ed25519 public key
        """
        self.private_key = private_key
        self.public_key = public_key
        
    @classmethod
    def generate(cls) -> 'IdentityKeyPair':
        """
        Generate a new identity key pair
        
        Returns:
            IdentityKeyPair: New key pair
        """
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        return cls(private_key, public_key)
        
    def sign(self, data: bytes) -> bytes:
        """
        Sign data with the identity key
        
        Args:
            data: Data to sign
            
        Returns:
            bytes: Signature
        """
        return self.private_key.sign(data)
        
    def verify(self, signature: bytes, data: bytes) -> bool:
        """
        Verify a signature with the identity key
        
        Args:
            signature: Signature to verify
            data: Data that was signed
            
        Returns:
            bool: True if signature is valid
        """
        try:
            self.public_key.verify(signature, data)
            return True
        except Exception:
            return False
            
    def to_json(self) -> Dict[str, Any]:
        """
        Convert key pair to JSON-serializable dictionary
        
        Returns:
            Dict: JSON-serializable representation
        """
        # Serialize private key
        private_bytes = self.private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return {
            "private": base64.b64encode(private_bytes).decode('utf-8'),
            "public": base64.b64encode(public_bytes).decode('utf-8')
        }
        
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'IdentityKeyPair':
        """
        Create identity key pair from JSON data
        
        Args:
            data: JSON-serializable representation
            
        Returns:
            IdentityKeyPair: Reconstructed key pair
        """
        try:
            # Decode private key
            private_bytes = base64.b64decode(data["private"])
            private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
            
            # Decode public key
            public_bytes = base64.b64decode(data["public"])
            public_key = Ed25519PublicKey.from_raw_key_data(public_bytes)
            
            return cls(private_key, public_key)
            
        except Exception as e:
            logger.error(f"Failed to load identity key pair: {str(e)}")
            raise WAEncryptionError(f"Failed to load identity key pair: {str(e)}")


class PreKeyBundle:
    """
    PreKey bundle for Signal Protocol initial key exchange
    
    Contains the necessary keys for establishing a session.
    """
    
    def __init__(
        self, 
        registration_id: int,
        device_id: int,
        prekey_id: int,
        prekey_public: X25519PublicKey,
        signed_prekey_id: int,
        signed_prekey_public: X25519PublicKey,
        signed_prekey_signature: bytes,
        identity_key: Ed25519PublicKey
    ):
        """
        Initialize prekey bundle
        
        Args:
            registration_id: Registration ID
            device_id: Device ID
            prekey_id: PreKey ID
            prekey_public: PreKey public key
            signed_prekey_id: Signed prekey ID
            signed_prekey_public: Signed prekey public key
            signed_prekey_signature: Signature of signed prekey
            identity_key: Identity public key
        """
        self.registration_id = registration_id
        self.device_id = device_id
        self.prekey_id = prekey_id
        self.prekey_public = prekey_public
        self.signed_prekey_id = signed_prekey_id
        self.signed_prekey_public = signed_prekey_public
        self.signed_prekey_signature = signed_prekey_signature
        self.identity_key = identity_key
        
    def to_json(self) -> Dict[str, Any]:
        """
        Convert prekey bundle to JSON-serializable dictionary
        
        Returns:
            Dict: JSON-serializable representation
        """
        # Serialize public keys
        prekey_public_bytes = self.prekey_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        signed_prekey_public_bytes = self.signed_prekey_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        identity_key_bytes = self.identity_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return {
            "registrationId": self.registration_id,
            "deviceId": self.device_id,
            "prekeyId": self.prekey_id,
            "prekey": base64.b64encode(prekey_public_bytes).decode('utf-8'),
            "signedPrekeyId": self.signed_prekey_id,
            "signedPrekey": base64.b64encode(signed_prekey_public_bytes).decode('utf-8'),
            "signedPrekeySignature": base64.b64encode(self.signed_prekey_signature).decode('utf-8'),
            "identityKey": base64.b64encode(identity_key_bytes).decode('utf-8')
        }
        
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'PreKeyBundle':
        """
        Create prekey bundle from JSON data
        
        Args:
            data: JSON-serializable representation
            
        Returns:
            PreKeyBundle: Reconstructed prekey bundle
        """
        try:
            # Decode keys
            prekey_public_bytes = base64.b64decode(data["prekey"])
            prekey_public = X25519PublicKey.from_public_bytes(prekey_public_bytes)
            
            signed_prekey_public_bytes = base64.b64decode(data["signedPrekey"])
            signed_prekey_public = X25519PublicKey.from_public_bytes(signed_prekey_public_bytes)
            
            signed_prekey_signature = base64.b64decode(data["signedPrekeySignature"])
            
            identity_key_bytes = base64.b64decode(data["identityKey"])
            identity_key = Ed25519PublicKey.from_public_bytes(identity_key_bytes)
            
            return cls(
                registration_id=data["registrationId"],
                device_id=data["deviceId"],
                prekey_id=data["prekeyId"],
                prekey_public=prekey_public,
                signed_prekey_id=data["signedPrekeyId"],
                signed_prekey_public=signed_prekey_public,
                signed_prekey_signature=signed_prekey_signature,
                identity_key=identity_key
            )
            
        except Exception as e:
            logger.error(f"Failed to load prekey bundle: {str(e)}")
            raise WAEncryptionError(f"Failed to load prekey bundle: {str(e)}")


class SessionBuilder:
    """
    Builder for Signal Protocol sessions
    
    Handles the X3DH key agreement protocol for establishing sessions.
    """
    
    def __init__(self, identity_key_pair: IdentityKeyPair):
        """
        Initialize session builder
        
        Args:
            identity_key_pair: Local identity key pair
        """
        self.identity_key_pair = identity_key_pair
        
    def process(self, prekey_bundle: PreKeyBundle) -> 'Session':
        """
        Process a prekey bundle to establish a session
        
        Args:
            prekey_bundle: Recipient's prekey bundle
            
        Returns:
            Session: Established session
        """
        try:
            # Generate ephemeral key pair
            ephemeral_key = X25519PrivateKey.generate()
            ephemeral_public = ephemeral_key.public_key()
            
            # Calculate shared secrets using X3DH
            # DH1 = Identity Key × Signed PreKey
            dh1 = self._calculate_agreement(
                self.identity_key_pair.private_key, 
                prekey_bundle.signed_prekey_public
            )
            
            # DH2 = Ephemeral Key × Identity Key
            dh2 = self._calculate_agreement(
                ephemeral_key,
                prekey_bundle.identity_key
            )
            
            # DH3 = Ephemeral Key × Signed PreKey
            dh3 = self._calculate_agreement(
                ephemeral_key,
                prekey_bundle.signed_prekey_public
            )
            
            # DH4 = Ephemeral Key × One-time PreKey (if available)
            dh4 = self._calculate_agreement(
                ephemeral_key,
                prekey_bundle.prekey_public
            ) if prekey_bundle.prekey_public else b""
            
            # Concatenate shared secrets
            shared_secret = dh1 + dh2 + dh3 + dh4
            
            # Create session
            session = Session.from_shared_secret(
                shared_secret,
                self.identity_key_pair,
                prekey_bundle.identity_key,
                ephemeral_key,
                ephemeral_public
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to establish session: {str(e)}")
            raise WAEncryptionError(f"Failed to establish session: {str(e)}")
            
    def _calculate_agreement(self, private_key: Any, public_key: Any) -> bytes:
        """
        Calculate Diffie-Hellman agreement
        
        Args:
            private_key: Local private key
            public_key: Remote public key
            
        Returns:
            bytes: Shared secret
        """
        # This is simplified - a real implementation would handle the
        # correct key types and perform the appropriate calculation
        
        # For demonstration purposes, we'll return a placeholder
        # In a real implementation, this would use X25519 key agreement
        return os.urandom(32)  # 32 random bytes as placeholder


class Session:
    """
    Signal Protocol session
    
    Represents an established messaging session with a contact.
    """
    
    def __init__(
        self,
        session_id: str,
        remote_identity_key: Ed25519PublicKey,
        local_identity_key_pair: IdentityKeyPair,
        root_key: bytes,
        chain_key: bytes
    ):
        """
        Initialize session
        
        Args:
            session_id: Unique session identifier
            remote_identity_key: Remote identity public key
            local_identity_key_pair: Local identity key pair
            root_key: Root key for deriving chain keys
            chain_key: Current chain key
        """
        self.session_id = session_id
        self.remote_identity_key = remote_identity_key
        self.local_identity_key_pair = local_identity_key_pair
        self.root_key = root_key
        self.chain_key = chain_key
        
        # Messaging state
        self.sending_chain_key = None
        self.receiving_chain_key = None
        self.message_keys = {}
        
    @classmethod
    def from_shared_secret(
        cls,
        shared_secret: bytes,
        local_identity_key_pair: IdentityKeyPair,
        remote_identity_key: Ed25519PublicKey,
        ephemeral_private_key: X25519PrivateKey,
        ephemeral_public_key: X25519PublicKey
    ) -> 'Session':
        """
        Create session from shared secret
        
        Args:
            shared_secret: Shared secret from X3DH
            local_identity_key_pair: Local identity key pair
            remote_identity_key: Remote identity public key
            ephemeral_private_key: Local ephemeral private key
            ephemeral_public_key: Local ephemeral public key
            
        Returns:
            Session: New session
        """
        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # Derive initial keys
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
        
        # Derive root key
        kdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"WhatsApp Root Key",
            backend=default_backend()
        )
        root_key = kdf.derive(shared_secret)
        
        # Derive chain key
        kdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"WhatsApp Chain Key",
            backend=default_backend()
        )
        chain_key = kdf.derive(shared_secret)
        
        return cls(
            session_id=session_id,
            remote_identity_key=remote_identity_key,
            local_identity_key_pair=local_identity_key_pair,
            root_key=root_key,
            chain_key=chain_key
        )
        
    def to_json(self) -> Dict[str, Any]:
        """
        Convert session to JSON-serializable dictionary
        
        Returns:
            Dict: JSON-serializable representation
        """
        # Serialize keys
        remote_identity_key_bytes = self.remote_identity_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return {
            "sessionId": self.session_id,
            "remoteIdentityKey": base64.b64encode(remote_identity_key_bytes).decode('utf-8'),
            "localIdentityKey": self.local_identity_key_pair.to_json(),
            "rootKey": base64.b64encode(self.root_key).decode('utf-8'),
            "chainKey": base64.b64encode(self.chain_key).decode('utf-8')
        }
