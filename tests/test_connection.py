"""
Tests for the WebSocket connection module of wawspy.
"""

import pytest
import time
import json
from unittest.mock import MagicMock, patch

from wawspy.connection import WAConnection
from wawspy.errors import WAConnectionError

class TestWAConnection:
    """Tests for the WAConnection class."""
    
    @pytest.fixture
    def connection(self):
        """Create a WAConnection instance for testing."""
        return WAConnection()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        mock_ws = MagicMock()
        mock_ws.run_forever = MagicMock()
        mock_ws.send = MagicMock()
        mock_ws.close = MagicMock()
        return mock_ws
    
    @patch('wawspy.connection.websocket.WebSocketApp')
    def test_connect(self, mock_websocket_app, connection, mock_websocket):
        """Test connecting to WhatsApp Web."""
        # Setup mock
        mock_websocket_app.return_value = mock_websocket
        
        # Make the _on_open method get called to set connected = True
        def side_effect(*args, **kwargs):
            connection._on_open(mock_websocket)
            return mock_websocket
            
        mock_websocket_app.side_effect = side_effect
        
        # Test connect
        result = connection.connect()
        
        # Verify
        assert result is True
        assert connection.connected is True
        assert mock_websocket_app.called
        assert mock_websocket.run_forever.called
    
    def test_disconnect(self, connection):
        """Test disconnecting from WhatsApp Web."""
        # Setup
        connection.ws = MagicMock()
        connection.connected = True
        
        # Test disconnect
        connection.disconnect()
        
        # Verify
        assert connection.connected is False
        assert connection.ws.close.called
    
    def test_send_message_not_connected(self, connection):
        """Test sending a message when not connected throws error."""
        # Setup
        connection.connected = False
        
        # Test & verify
        with pytest.raises(WAConnectionError):
            connection.send_message({"test": "message"})
    
    @patch('wawspy.connection.websocket.WebSocketApp')
    def test_send_message(self, mock_websocket_app, connection, mock_websocket):
        """Test sending a message."""
        # Setup
        connection.ws = mock_websocket
        connection.connected = True
        
        # Test
        tag = connection.send_message({"test": "message"})
        
        # Verify
        assert mock_websocket.send.called
        assert isinstance(tag, str)
    
    def test_on_message_success(self, connection):
        """Test handling a success message."""
        # Setup
        connection.on_connect_callback = MagicMock()
        
        # Test
        data = {"status": 200, "clientToken": "test_token", "serverToken": "server_token"}
        connection._on_message(None, f"s1,{json.dumps(data)}")
        
        # Verify
        assert connection.connected is True
        assert connection.client_token == "test_token"
        assert connection.server_token == "server_token"
        assert connection.on_connect_callback.called
    
    def test_register_callback(self, connection):
        """Test registering callbacks."""
        # Setup
        mock_callback = MagicMock()
        
        # Test
        connection.register_callback(
            on_message=mock_callback,
            on_connect=mock_callback,
            on_close=mock_callback,
            on_error=mock_callback
        )
        
        # Verify
        assert connection.on_message_callback == mock_callback
        assert connection.on_connect_callback == mock_callback
        assert connection.on_close_callback == mock_callback
        assert connection.on_error_callback == mock_callback
