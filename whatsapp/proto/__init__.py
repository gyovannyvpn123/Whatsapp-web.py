"""
WhatsApp Protocol Buffer message handling.

This module contains the implementation for handling WhatsApp's protobuf-encoded messages.
"""

from .message import ProtoMessage, parse_message, encode_message
from .definitions import message_types

__all__ = [
    "ProtoMessage",
    "parse_message",
    "encode_message",
    "message_types"
]
