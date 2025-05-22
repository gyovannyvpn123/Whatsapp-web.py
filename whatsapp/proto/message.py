"""
Protocol Buffer message handling for WhatsApp Web.

This module handles parsing and generating binary protobuf messages for the WhatsApp protocol.
"""

import struct
from typing import Dict, Any, Optional, Union, Tuple
from google.protobuf.message import Message as ProtoMessage
from google.protobuf.json_format import MessageToDict, Parse

from .definitions import message_types
from ..utils.logger import get_logger
from ..exceptions import WAProtocolError

logger = get_logger("ProtoMessage")

def parse_message(binary_data: bytes) -> Dict[str, Any]:
    """
    Parse a binary protobuf message from WhatsApp Web
    
    Args:
        binary_data: Raw binary protobuf message
        
    Returns:
        Dict: Parsed message content
    
    Raises:
        WAProtocolError: If parsing fails
    """
    try:
        # The first byte typically indicates the message type
        if not binary_data:
            raise WAProtocolError("Empty binary message")
            
        message_type = binary_data[0]
        message_data = binary_data[1:]
        
        # Look up the appropriate protobuf message type
        proto_class = message_types.get(message_type)
        if not proto_class:
            logger.warning(f"Unknown message type: {message_type}")
            return {
                "type": "unknown",
                "typeId": message_type,
                "rawData": message_data
            }
        
        # Parse the binary data with the protobuf class
        proto_msg = proto_class()
        proto_msg.ParseFromString(message_data)
        
        # Convert to Python dictionary
        result = MessageToDict(
            proto_msg, 
            preserving_proto_field_name=True,
            including_default_value_fields=True
        )
        
        # Add message type information
        result["messageType"] = message_type
        result["messageTypeName"] = proto_class.__name__
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to parse protobuf message: {str(e)}")
        raise WAProtocolError(f"Protobuf parsing error: {str(e)}")

def encode_message(message_type: int, message_content: Dict[str, Any]) -> bytes:
    """
    Encode a message to binary protobuf format
    
    Args:
        message_type: Numeric ID of the message type
        message_content: Message content as a dictionary
        
    Returns:
        bytes: Binary protobuf message
        
    Raises:
        WAProtocolError: If encoding fails
    """
    try:
        # Look up the appropriate protobuf message type
        proto_class = message_types.get(message_type)
        if not proto_class:
            raise WAProtocolError(f"Unknown message type: {message_type}")
        
        # Convert dictionary to protobuf message
        proto_msg = proto_class()
        Parse(str(message_content), proto_msg)
        
        # Serialize to binary
        message_data = proto_msg.SerializeToString()
        
        # Prepend the message type byte
        full_message = bytes([message_type]) + message_data
        
        return full_message
        
    except Exception as e:
        logger.error(f"Failed to encode protobuf message: {str(e)}")
        raise WAProtocolError(f"Protobuf encoding error: {str(e)}")

def encode_node(tag: str, attributes: Dict[str, Any], content: Any = None) -> bytes:
    """
    Encode a WhatsApp protocol node
    
    Args:
        tag: Node tag name
        attributes: Node attributes
        content: Node content (optional)
        
    Returns:
        bytes: Encoded node
    """
    # This is a simplified implementation.
    # WhatsApp's actual protocol uses a custom binary format for nodes.
    
    try:
        node = {
            "tag": tag,
            "attrs": attributes
        }
        
        if content is not None:
            node["content"] = content
            
        # For now, we'll use JSON as a placeholder
        # In a real implementation, this would use the proper binary format
        return str(node).encode('utf-8')
        
    except Exception as e:
        logger.error(f"Failed to encode node: {str(e)}")
        raise WAProtocolError(f"Node encoding error: {str(e)}")

def decode_node(data: bytes) -> Tuple[str, Dict[str, Any], Any]:
    """
    Decode a WhatsApp protocol node
    
    Args:
        data: Encoded node data
        
    Returns:
        Tuple: (tag, attributes, content)
    """
    # This is a simplified implementation.
    # WhatsApp's actual protocol uses a custom binary format for nodes.
    
    try:
        # For now, we'll assume JSON as a placeholder
        # In a real implementation, this would parse the proper binary format
        node_str = data.decode('utf-8')
        
        # Very simplified parsing
        import ast
        node = ast.literal_eval(node_str)
        
        tag = node.get("tag", "")
        attributes = node.get("attrs", {})
        content = node.get("content", None)
        
        return (tag, attributes, content)
        
    except Exception as e:
        logger.error(f"Failed to decode node: {str(e)}")
        raise WAProtocolError(f"Node decoding error: {str(e)}")
