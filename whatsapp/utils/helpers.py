"""
Helper functions for WhatsApp Web library.
"""

from typing import Dict, Optional, Tuple, Any

def parse_jid(jid: str) -> Tuple[str, str]:
    """
    Parse a WhatsApp JID (Jabber ID) into user and server parts
    
    Args:
        jid: JID string (e.g., "1234567890@c.us")
        
    Returns:
        Tuple: (user, server) parts of the JID
    """
    if "@" not in jid:
        return jid, "c.us"  # Default to user contact
        
    user, server = jid.split("@", 1)
    return user, server

def format_jid(user: str, server: str = "c.us") -> str:
    """
    Format a user ID and server into a WhatsApp JID
    
    Args:
        user: User part (usually phone number)
        server: Server part (c.us for contacts, g.us for groups)
        
    Returns:
        str: Formatted JID
    """
    # Check if user already contains a server part
    if "@" in user:
        return user
        
    return f"{user}@{server}"

def is_group_id(jid: str) -> bool:
    """
    Check if a JID is a group
    
    Args:
        jid: JID to check
        
    Returns:
        bool: True if this is a group JID
    """
    _, server = parse_jid(jid)
    return server == "g.us"

def is_user_id(jid: str) -> bool:
    """
    Check if a JID is a user contact
    
    Args:
        jid: JID to check
        
    Returns:
        bool: True if this is a user contact JID
    """
    _, server = parse_jid(jid)
    return server == "c.us"

def normalize_phone_number(phone: str) -> str:
    """
    Normalize a phone number for WhatsApp
    
    Args:
        phone: Phone number to normalize
        
    Returns:
        str: Normalized phone number
    """
    # Remove any non-digit characters
    digits_only = ''.join(c for c in phone if c.isdigit())
    
    # Ensure it doesn't start with a leading 0
    if digits_only.startswith('0'):
        digits_only = digits_only[1:]
        
    return digits_only

def generate_message_id() -> str:
    """
    Generate a unique message ID
    
    Returns:
        str: Unique message ID in WhatsApp format
    """
    import time
    import uuid
    import random
    
    # WhatsApp message IDs have a specific format
    # This is a simplified version
    timestamp = int(time.time() * 1000)
    random_id = random.randint(1000, 9999)
    unique_id = str(uuid.uuid4()).replace('-', '')[:8]
    
    return f"{timestamp}.{random_id}.{unique_id}"
