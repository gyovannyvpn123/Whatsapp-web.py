"""
Tests for cryptographic functionality.
"""

import pytest
import os
import json
import base64
import asyncio
from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

from whatsapp.crypto.signal import SignalProtocol
from whatsapp.crypto.keys import IdentityKeyPair, PreKeyBundle, SessionBuilder, Session
from whatsapp.exceptions import WAEncryptionError

# Create a temporary directory for test session
@pytest.fixture
def storage_path(tmpdir):
    """Create a temporary directory for test storage"""
    storage_path = tmpdir.mkdir("test_crypto")
    return str(storage_path)

# Test identity key pair generation and serialization
def test_identity_key_pair_generation():
    """Test generating and serializing identity key pair"""
    # Generate a new key pair
    key_pair = IdentityKeyPair.generate()
    
    # Check that keys were generated
    assert key_pair.private_key is not None
    assert key_pair.public_key is not None
    
    # Test to_json and from_json
    json_data = key_pair.to_json()
    
    # Check JSON structure
    assert "private" in json_data
    assert "public" in json_data
    
    # Reconstruct from JSON
    reconstructed = IdentityKeyPair.from_json(json_data)
    
    # Check that private key is the same type
    assert isinstance(reconstructed.private_key, Ed25519PrivateKey)
    assert isinstance(reconstructed.public_key, Ed25519PublicKey)

# Test signing and verification
def test_identity_key_signing():
    """Test signing and verifying with identity key"""
    key_pair = IdentityKeyPair.generate()
    
    # Test data
    test_data = b"test message to sign"
    
    # Sign data
    signature = key_pair.sign(test_data)
    
    # Verify signature
    assert key_pair.verify(signature, test_data) is True
    
    # Test with modified data (should fail verification)
    modified_data = b"modified message"
    assert key_pair.verify(signature, modified_data) is False

# Test PreKeyBundle serialization
def test_prekey_bundle_serialization():
    """Test PreKeyBundle serialization"""
    # Create test keys
    identity_key = Ed25519PrivateKey.generate().public_key()
    prekey = X25519PrivateKey.generate().public_key()
    signed_prekey = X25519PrivateKey.generate().public_key()
    
    # Create bundle
    bundle = PreKeyBundle(
        registration_id=12345,
        device_id=1,
        prekey_id=100,
        prekey_public=prekey,
        signed_prekey_id=200,
        signed_prekey_public=signed_prekey,
        signed_prekey_signature=b"test_signature",
        identity_key=identity_key
    )
    
    # Convert to JSON
    json_data = bundle.to_json()
    
    # Check JSON structure
    assert json_data["registrationId"] == 12345
    assert json_data["deviceId"] == 1
    assert json_data["prekeyId"] == 100
    assert json_data["signedPrekeyId"] == 200
    
    # Reconstruct from JSON
    reconstructed = PreKeyBundle.from_json(json_data)
    
    # Check reconstruction
    assert reconstructed.registration_id == 12345
    assert reconstructed.device_id == 1
    assert reconstructed.prekey_id == 100
    assert reconstructed.signed_prekey_id == 200
    assert isinstance(reconstructed.prekey_public, X25519PublicKey)
    assert isinstance(reconstructed.signed_prekey_public, X25519PublicKey)
    assert isinstance(reconstructed.identity_key, Ed25519PublicKey)

# Test SessionBuilder
def test_session_builder():
    """Test building a session"""
    # Create identity key pair
    identity_key_pair = IdentityKeyPair.generate()
    
    # Create session builder
    builder = SessionBuilder(identity_key_pair)
    
    # Create remote identity key and prekeys
    remote_identity = Ed25519PrivateKey.generate().public_key()
    remote_prekey = X25519PrivateKey.generate().public_key()
    remote_signed_prekey = X25519PrivateKey.generate().public_key()
    
    # Create prekey bundle
    bundle = PreKeyBundle(
        registration_id=67890,
        device_id=1,
        prekey_id=300,
        prekey_public=remote_prekey,
        signed_prekey_id=400,
        signed_prekey_public=remote_signed_prekey,
        signed_prekey_signature=b"remote_signature",
        identity_key=remote_identity
    )
    
    # Process bundle to create session
    session = builder.process(bundle)
    
    # Check session
    assert isinstance(session, Session)
    assert session.remote_identity_key is remote_identity
    assert session.local_identity_key_pair is identity_key_pair

# Test Session serialization
def test_session_serialization():
    """Test session serialization"""
    # Create identity key pair
    identity_key_pair = IdentityKeyPair.generate()
    
    # Create remote identity
    remote_identity = Ed25519PrivateKey.generate().public_key()
    
    # Create session
    session = Session(
        session_id="test_session_id",
        remote_identity_key=remote_identity,
        local_identity_key_pair=identity_key_pair,
        root_key=b"test_root_key",
        chain_key=b"test_chain_key"
    )
    
    # Convert to JSON
    json_data = session.to_json()
    
    # Check JSON structure
    assert json_data["sessionId"] == "test_session_id"
    assert "rootKey" in json_data
    assert "chainKey" in json_data
    assert "remoteIdentityKey" in json_data
    assert "localIdentityKey" in json_data

# Test SignalProtocol initialization
@pytest.mark.asyncio
async def test_signal_protocol_init(storage_path):
    """Test initializing the Signal Protocol"""
    protocol = SignalProtocol(storage_path)
    
    # Check directory creation
    assert os.path.exists(os.path.join(storage_path, "keys"))
    assert os.path.exists(os.path.join(storage_path, "sessions"))
    
    # Initialize with user info
    user_info = {"id": "1234567890@c.us"}
    await protocol.initialize(user_info)
    
    # Check keys were generated
    assert protocol.identity_key_pair is not None
    assert protocol.user_id == "1234567890@c.us"

# Test key generation and storage
@pytest.mark.asyncio
async def test_key_generation_and_storage(storage_path):
    """Test generating and storing keys"""
    protocol = SignalProtocol(storage_path)
    
    # Initialize with user info
    user_info = {"id": "1234567890@c.us"}
    await protocol.initialize(user_info)
    
    # Check key files were created
    identity_key_file = os.path.join(storage_path, "keys", "identity_key.json")
    prekeys_file = os.path.join(storage_path, "keys", "prekeys.json")
    
    assert os.path.exists(identity_key_file)
    assert os.path.exists(prekeys_file)
    
    # Load keys from storage
    with open(identity_key_file, 'r') as f:
        identity_data = json.load(f)
    
    with open(prekeys_file, 'r') as f:
        prekeys_data = json.load(f)
    
    # Check data structure
    assert "private" in identity_data
    assert "public" in identity_data
    assert len(prekeys_data) > 0

# Test message encryption and decryption
@pytest.mark.asyncio
async def test_message_encryption_decryption(storage_path):
    """Test encrypting and decrypting messages"""
    # Create two protocols (sender and recipient)
    sender_protocol = SignalProtocol(os.path.join(storage_path, "sender"))
    recipient_protocol = SignalProtocol(os.path.join(storage_path, "recipient"))
    
    # Initialize protocols
    sender_info = {"id": "sender@c.us"}
    recipient_info = {"id": "recipient@c.us"}
    
    await sender_protocol.initialize(sender_info)
    await recipient_protocol.initialize(recipient_info)
    
    # Manually create a session between them
    # In a real scenario, this would involve exchanging prekey bundles
    
    # Create a fake session in the sender's sessions
    session_data = {
        "sessionId": "test_session",
        "remoteIdentityKey": base64.b64encode(b"recipient_key").decode('utf-8'),
        "localIdentityKey": sender_protocol.identity_key_pair.to_json(),
        "rootKey": base64.b64encode(b"test_root_key").decode('utf-8'),
        "chainKey": base64.b64encode(b"test_chain_key").decode('utf-8')
    }
    
    sender_protocol.sessions["recipient@c.us"] = session_data
    
    # Create the same session for the recipient
    recipient_protocol.sessions["sender@c.us"] = session_data
    
    # Test message
    test_message = {
        "type": "text",
        "content": "Hello, WhatsApp!",
        "timestamp": 1234567890
    }
    
    # Encrypt message
    encrypted_message = await sender_protocol.encrypt_message("recipient@c.us", test_message)
    
    # Create message data structure for decryption
    message_data = {
        "sender": "sender@c.us",
        "content": base64.b64encode(encrypted_message).decode('utf-8')
    }
    
    # Decrypt message
    decrypted_message = await recipient_protocol.decrypt_message(message_data)
    
    # Check decrypted content
    assert decrypted_message["type"] == "text"
    assert decrypted_message["content"] == "Hello, WhatsApp!"
    assert decrypted_message["timestamp"] == 1234567890

# Test error handling
@pytest.mark.asyncio
async def test_encryption_error_handling(storage_path):
    """Test error handling during encryption/decryption"""
    protocol = SignalProtocol(storage_path)
    
    # Initialize protocol
    user_info = {"id": "test@c.us"}
    await protocol.initialize(user_info)
    
    # Try to encrypt without a session
    with pytest.raises(WAEncryptionError):
        await protocol.encrypt_message("nonexistent@c.us", {"test": "message"})
    
    # Try to decrypt with invalid data
    with pytest.raises(WAEncryptionError):
        await protocol.decrypt_message({"content": "invalid"})
    
    # Try to decrypt without sender ID
    with pytest.raises(WAEncryptionError):
        await protocol.decrypt_message({"content": "data"})
