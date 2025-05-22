"""
Tests for authentication functionality.
"""

import pytest
import os
import json
import asyncio
from unittest.mock import MagicMock, patch

from whatsapp.auth import WAAuthentication
from whatsapp.events import EventEmitter, WAEventType
from whatsapp.exceptions import WAAuthenticationError

# Create a temporary directory for test sessions
@pytest.fixture
def session_dir(tmpdir):
    """Create a temporary directory for test sessions"""
    session_path = tmpdir.mkdir("test_session")
    return str(session_path)

# Mock connection
@pytest.fixture
def mock_connection():
    """Create a mock connection object"""
    connection = MagicMock()
    connection.event_emitter = EventEmitter()
    connection.send_json = MagicMock()
    return connection

# Test authentication initialization
def test_init(session_dir):
    """Test authentication initialization"""
    auth = WAAuthentication(session_dir)
    assert auth.session_path == session_dir
    assert auth.session_file == os.path.join(session_dir, "session.json")
    assert auth.client_id is not None
    assert auth.client_token is None
    assert auth.server_token is None

# Test session restoration when no session file exists
@pytest.mark.asyncio
async def test_restore_session_no_file(session_dir):
    """Test restoring a session when no file exists"""
    auth = WAAuthentication(session_dir)
    result = await auth.restore_session()
    assert result is False

# Test session restoration with valid session file
@pytest.mark.asyncio
async def test_restore_session_with_file(session_dir):
    """Test restoring a session from a valid file"""
    # Create test session data
    session_data = {
        "client_id": "test_client_id",
        "client_token": "test_client_token",
        "server_token": "test_server_token",
        "timestamp": 1234567890
    }
    
    # Write test session file
    session_file = os.path.join(session_dir, "session.json")
    with open(session_file, 'w') as f:
        json.dump(session_data, f)
    
    # Test restoration
    auth = WAAuthentication(session_dir)
    result = await auth.restore_session()
    
    assert result is True
    assert auth.client_id == "test_client_id"
    assert auth.client_token == "test_client_token"
    assert auth.server_token == "test_server_token"

# Test session restoration with incomplete session file
@pytest.mark.asyncio
async def test_restore_session_incomplete(session_dir):
    """Test restoring a session from an incomplete file"""
    # Create incomplete test session data
    session_data = {
        "client_id": "test_client_id",
        # Missing tokens
        "timestamp": 1234567890
    }
    
    # Write test session file
    session_file = os.path.join(session_dir, "session.json")
    with open(session_file, 'w') as f:
        json.dump(session_data, f)
    
    # Test restoration
    auth = WAAuthentication(session_dir)
    result = await auth.restore_session()
    
    assert result is False
    assert auth.client_id == "test_client_id"
    assert auth.client_token is None
    assert auth.server_token is None

# Test authentication using tokens
@pytest.mark.asyncio
async def test_auth_with_tokens(session_dir, mock_connection):
    """Test authenticating with existing tokens"""
    auth = WAAuthentication(session_dir)
    auth.client_id = "test_client_id"
    auth.client_token = "test_client_token"
    auth.server_token = "test_server_token"
    
    await auth.start_authentication(mock_connection)
    
    # Check that it tried to authenticate with tokens
    mock_connection.send_json.assert_called_once()
    sent_data = mock_connection.send_json.call_args[0][0]
    
    assert sent_data["type"] == "auth"
    assert sent_data["data"]["clientId"] == "test_client_id"
    assert sent_data["data"]["clientToken"] == "test_client_token"
    assert sent_data["data"]["serverToken"] == "test_server_token"
    assert sent_data["data"]["reconnect"] is True

# Test requesting QR code
@pytest.mark.asyncio
async def test_request_qr_code(session_dir, mock_connection):
    """Test requesting a QR code for authentication"""
    auth = WAAuthentication(session_dir)
    auth.client_id = "test_client_id"
    auth.client_token = None
    auth.server_token = None
    
    await auth.start_authentication(mock_connection)
    
    # Check that it requested a QR code
    mock_connection.send_json.assert_called_once()
    sent_data = mock_connection.send_json.call_args[0][0]
    
    assert sent_data["type"] == "request_qr"
    assert sent_data["data"]["clientId"] == "test_client_id"

# Test QR code generation
def test_generate_qr_image(session_dir):
    """Test generating a QR code image"""
    auth = WAAuthentication(session_dir)
    qr_data = "1@abcdefghijklmnopqrstuvwxyz0123456789"
    
    qr_image = auth.generate_qr_image(qr_data)
    
    # Check that it generated a PNG image
    assert isinstance(qr_image, bytes)
    assert qr_image.startswith(b'\x89PNG')

# Test authentication response processing
@pytest.mark.asyncio
async def test_process_authentication_response(session_dir, mock_connection):
    """Test processing a successful authentication response"""
    auth = WAAuthentication(session_dir)
    auth.connection = mock_connection
    
    # Create test response data
    response_data = {
        "status": "success",
        "clientToken": "new_client_token",
        "serverToken": "new_server_token",
        "userInfo": {
            "id": "1234567890",
            "name": "Test User"
        }
    }
    
    # Process response
    await auth.process_authentication_response(response_data)
    
    # Check that tokens were updated
    assert auth.client_token == "new_client_token"
    assert auth.server_token == "new_server_token"
    
    # Check that authenticated event was emitted
    events = [call.args[0] for call in mock_connection.event_emitter.emit._mock_mock_calls]
    assert WAEventType.AUTHENTICATED in events

# Test failed authentication response
@pytest.mark.asyncio
async def test_process_failed_authentication(session_dir, mock_connection):
    """Test processing a failed authentication response"""
    auth = WAAuthentication(session_dir)
    auth.connection = mock_connection
    
    # Create test failure response data
    response_data = {
        "status": "failure",
        "error": "Invalid credentials"
    }
    
    # Process response
    await auth.process_authentication_response(response_data)
    
    # Check that failure event was emitted
    events = [call.args[0] for call in mock_connection.event_emitter.emit._mock_mock_calls]
    assert WAEventType.AUTH_FAILURE in events

# Test saving and loading session
@pytest.mark.asyncio
async def test_save_and_load_session(session_dir):
    """Test saving and loading a session"""
    auth = WAAuthentication(session_dir)
    auth.client_id = "test_client_id"
    auth.client_token = "test_client_token"
    auth.server_token = "test_server_token"
    
    # Save session
    auth._save_session()
    
    # Create a new auth instance
    auth2 = WAAuthentication(session_dir)
    
    # Load session
    result = await auth2.restore_session()
    
    # Check that session was loaded correctly
    assert result is True
    assert auth2.client_id == "test_client_id"
    assert auth2.client_token == "test_client_token"
    assert auth2.server_token == "test_server_token"

# Test logout
@pytest.mark.asyncio
async def test_logout(session_dir):
    """Test logging out"""
    auth = WAAuthentication(session_dir)
    auth.client_id = "test_client_id"
    auth.client_token = "test_client_token"
    auth.server_token = "test_server_token"
    
    # Save session
    auth._save_session()
    
    # Verify file exists
    session_file = os.path.join(session_dir, "session.json")
    assert os.path.exists(session_file)
    
    # Logout
    await auth.logout()
    
    # Check that tokens were cleared
    assert auth.client_token is None
    assert auth.server_token is None
    
    # Check that session file was deleted
    assert not os.path.exists(session_file)
