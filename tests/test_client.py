"""
Tests for the WhatsApp Web client module of wawspy.
"""

import pytest
import os
import json
from unittest.mock import MagicMock, patch

from wawspy.client import WAClient
from wawspy.errors import WAConnectionError, WAMessageError, WAMediaError

class TestWAClient:
    """Tests for the WAClient class."""
    
    @pytest.fixture
    def client(self):
        """Create a WAClient instance for testing."""
        with patch('wawspy.client.logging'):
            return WAClient(log_level=0)  # Disable actual logging
    
    @patch('wawspy.connection.WAConnection.connect')
    def test_connect(self, mock_connect, client):
        """Test connecting to WhatsApp Web."""
        # Setup mock
        mock_connect.return_value = True
        
        # Test connect
        result = client.connect()
        
        # Verify
        assert result is True
        assert client.connected is True
        assert mock_connect.called
    
    @patch('wawspy.connection.WAConnection.disconnect')
    def test_disconnect(self, mock_disconnect, client):
        """Test disconnecting from WhatsApp Web."""
        # Setup
        client.connected = True
        client.authenticated = True
        
        # Test disconnect
        client.disconnect()
        
        # Verify
        assert client.connected is False
        assert client.authenticated is False
        assert mock_disconnect.called
    
    def test_send_message_not_authenticated(self, client):
        """Test sending a message when not authenticated throws error."""
        # Setup
        client.authenticated = False
        
        # Test & verify
        with pytest.raises(WAMessageError):
            client.send_message("1234567890", "Test message")
    
    @patch('wawspy.connection.WAConnection.send_message')
    @patch('wawspy.protocol.WAProtocol.create_text_message')
    def test_send_message(self, mock_create_msg, mock_send_msg, client):
        """Test sending a text message."""
        # Setup
        client.authenticated = True
        mock_msg = MagicMock()
        mock_msg.attributes = {"id": "test_id"}
        mock_msg.to_json.return_value = {"test": "message"}
        mock_create_msg.return_value = mock_msg
        mock_send_msg.return_value = "test_tag"
        
        # Test
        result = client.send_message("1234567890", "Test message")
        
        # Verify
        assert mock_create_msg.called
        assert mock_send_msg.called
        assert result["id"] == "test_id"
        assert result["text"] == "Test message"
        assert result["status"] == "sent"
    
    @patch('wawspy.media.WAMedia.upload_media')
    @patch('wawspy.connection.WAConnection.send_message')
    @patch('wawspy.protocol.WAProtocol.create_media_message')
    def test_send_image(self, mock_create_msg, mock_send_msg, mock_upload, client):
        """Test sending an image message."""
        # Setup
        client.authenticated = True
        
        mock_msg = MagicMock()
        mock_msg.attributes = {"id": "test_id"}
        mock_msg.to_json.return_value = {"test": "message"}
        mock_create_msg.return_value = mock_msg
        
        mock_send_msg.return_value = "test_tag"
        
        mock_upload.return_value = {
            "url": "https://example.com/image.jpg",
            "mimetype": "image/jpeg",
            "filehash": "abc123",
            "filesize": 1024,
            "mediaKey": "key123",
            "type": "image"
        }
        
        # Test
        result = client.send_image("1234567890", "/path/to/image.jpg", "Test caption")
        
        # Verify
        assert mock_upload.called
        assert mock_create_msg.called
        assert mock_send_msg.called
        assert result["id"] == "test_id"
        assert result["type"] == "image"
        assert result["caption"] == "Test caption"
        assert result["status"] == "sent"
        assert "media" in result
    
    def test_register_callback(self, client):
        """Test registering callbacks."""
        # Setup
        mock_msg_callback = MagicMock()
        mock_qr_callback = MagicMock()
        
        # Test
        client.register_callback(
            on_message=mock_msg_callback,
            on_qr_code=mock_qr_callback
        )
        
        # Verify
        assert client.message_callback == mock_msg_callback
        assert client.qr_callback == mock_qr_callback
    
    def test_on_message_qr(self, client):
        """Test handling a QR code message."""
        # Setup
        client.qr_callback = MagicMock()
        
        # Test
        client._on_message("qr", "test_qr_data")
        
        # Verify
        assert client.qr_code == "test_qr_data"
        assert client.qr_callback.called
    
    def test_on_message_success(self, client):
        """Test handling a success message."""
        # Setup
        user_info = {"id": "1234567890", "name": "Test User"}
        
        # Test
        client._on_message("success", {"user": user_info})
        
        # Verify
        assert client.authenticated is True
        assert client.user_info == user_info
