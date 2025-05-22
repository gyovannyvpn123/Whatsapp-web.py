"""
Tests for Protocol Buffer message handling.
"""

import pytest
import os
import json
from unittest.mock import MagicMock, patch

from google.protobuf.message import Message as ProtoMessage

from whatsapp.proto.message import parse_message, encode_message, encode_node, decode_node
from whatsapp.proto.definitions import message_types, NodeTypes, AttributeNames
from whatsapp.exceptions import WAProtocolError

# Test message type definitions
def test_message_type_definitions():
    """Test that message type definitions are properly set up"""
    # Check that message types are defined
    assert len(message_types) > 0
    
    # Check specific message types exist
    assert 0x01 in message_types  # Ping/Pong
    assert 0x02 in message_types  # Text messages
    assert 0x03 in message_types  # Media messages
    
    # Check node types are defined
    assert hasattr(NodeTypes, 'MESSAGE')
    assert hasattr(NodeTypes, 'PRESENCE')
    assert hasattr(NodeTypes, 'IQ')
    
    # Check attribute names are defined
    assert hasattr(AttributeNames, 'TYPE')
    assert hasattr(AttributeNames, 'FROM')
    assert hasattr(AttributeNames, 'TO')

# Mock protobuf classes for testing
class MockTextMessage:
    """Mock text message protobuf"""
    def __init__(self):
        self.text = ""
        self.to = ""
        self.from_user = ""
    
    def ParseFromString(self, data):
        """Mock parsing"""
        self.text = "Mock parsed text"
        self.to = "recipient@c.us"
        self.from_user = "sender@c.us"
    
    def SerializeToString(self):
        """Mock serialization"""
        return b"serialized_text_message"

class MockMediaMessage:
    """Mock media message protobuf"""
    def __init__(self):
        self.url = ""
        self.mimetype = ""
        self.caption = ""
    
    def ParseFromString(self, data):
        """Mock parsing"""
        self.url = "https://example.com/media.jpg"
        self.mimetype = "image/jpeg"
        self.caption = "Mock media caption"
    
    def SerializeToString(self):
        """Mock serialization"""
        return b"serialized_media_message"

# Test parsing binary message
@patch('whatsapp.proto.message.message_types')
def test_parse_message(mock_message_types):
    """Test parsing a binary protobuf message"""
    # Set up mock message types
    mock_text_message = MockTextMessage()
    mock_message_types.get.return_value = MockTextMessage
    
    # Create test binary data
    # First byte is message type (0x02 = text message)
    binary_data = b'\x02' + b'test binary data'
    
    # Parse message
    result = parse_message(binary_data)
    
    # Check that message type was identified and looked up
    mock_message_types.get.assert_called_with(0x02)
    
    # Check result includes message type info
    assert result["messageType"] == 0x02
    assert result["messageTypeName"] == "MockTextMessage"

# Test parsing unknown message type
@patch('whatsapp.proto.message.message_types')
def test_parse_unknown_message_type(mock_message_types):
    """Test parsing a message with unknown type"""
    # Set up mock to return None for unknown type
    mock_message_types.get.return_value = None
    
    # Create test binary data with unknown type (0xFF)
    binary_data = b'\xFF' + b'unknown data'
    
    # Parse message
    result = parse_message(binary_data)
    
    # Check that we get an 'unknown' result
    assert result["type"] == "unknown"
    assert result["typeId"] == 0xFF
    assert result["rawData"] == b'unknown data'

# Test parsing empty message
def test_parse_empty_message():
    """Test parsing an empty message"""
    with pytest.raises(WAProtocolError):
        parse_message(b'')

# Test encoding a message
@patch('whatsapp.proto.message.message_types')
def test_encode_message(mock_message_types):
    """Test encoding a message to binary format"""
    # Set up mock message types
    mock_text_message = MockTextMessage()
    mock_message_types.get.return_value = MockTextMessage
    
    # Create test message content
    message_content = {
        "text": "Hello, WhatsApp!",
        "to": "recipient@c.us",
        "from_user": "sender@c.us"
    }
    
    # Encode message
    result = encode_message(0x02, message_content)
    
    # Check result format
    assert result[0] == 0x02  # First byte should be message type
    assert result[1:] == b"serialized_text_message"  # Rest should be serialized data

# Test encoding unknown message type
@patch('whatsapp.proto.message.message_types')
def test_encode_unknown_message_type(mock_message_types):
    """Test encoding a message with unknown type"""
    # Set up mock to return None for unknown type
    mock_message_types.get.return_value = None
    
    # Create test message content
    message_content = {"test": "content"}
    
    # Try to encode message with unknown type
    with pytest.raises(WAProtocolError):
        encode_message(0xFF, message_content)

# Test encoding and decoding nodes
def test_encode_decode_node():
    """Test encoding and decoding protocol nodes"""
    # Create test node data
    tag = "message"
    attributes = {
        "id": "test_id",
        "type": "text",
        "to": "recipient@c.us",
        "from": "sender@c.us"
    }
    content = "Hello, WhatsApp!"
    
    # Encode node
    encoded = encode_node(tag, attributes, content)
    
    # Decode node
    decoded_tag, decoded_attrs, decoded_content = decode_node(encoded)
    
    # Check decoded data
    assert decoded_tag == tag
    assert decoded_attrs["id"] == attributes["id"]
    assert decoded_attrs["type"] == attributes["type"]
    assert decoded_attrs["to"] == attributes["to"]
    assert decoded_attrs["from"] == attributes["from"]
    assert decoded_content == content

# Test node encoding error handling
def test_node_encoding_error():
    """Test error handling during node encoding"""
    # Create a tag that will cause encoding to fail
    tag = object()  # Non-string object will cause error
    attributes = {"test": "attrs"}
    
    # Try to encode invalid node
    with pytest.raises(WAProtocolError):
        encode_node(tag, attributes)

# Test node decoding error handling
def test_node_decoding_error():
    """Test error handling during node decoding"""
    # Create invalid encoded data
    invalid_data = b'\x00\x01\x02\x03'  # Not a valid encoded node
    
    # Try to decode invalid data
    with pytest.raises(WAProtocolError):
        decode_node(invalid_data)
