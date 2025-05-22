"""
Contact model for WhatsApp Web.

This module defines the Contact class for representing WhatsApp contacts.
"""

from typing import Dict, Optional, Any, List

class Contact:
    """
    Represents a WhatsApp contact
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        push_name: Optional[str] = None,
        short_name: Optional[str] = None,
        status: Optional[str] = None,
        profile_picture_url: Optional[str] = None,
        is_business: bool = False,
        is_enterprise: bool = False,
        verified_level: Optional[int] = None,
        is_blocked: bool = False
    ):
        """
        Initialize a new contact
        
        Args:
            id: Contact ID (usually phone number with @c.us suffix)
            name: Contact name (from address book)
            push_name: Name set by the contact themselves
            short_name: Shorter version of the name
            status: Contact's status message
            profile_picture_url: URL of profile picture
            is_business: Whether this is a business account
            is_enterprise: Whether this is an enterprise account
            verified_level: Verification level (0=none, 1=green, 2=blue)
            is_blocked: Whether contact is blocked by the user
        """
        self.id = id
        self.name = name
        self.push_name = push_name
        self.short_name = short_name
        self.status = status
        self.profile_picture_url = profile_picture_url
        self.is_business = is_business
        self.is_enterprise = is_enterprise
        self.verified_level = verified_level
        self.is_blocked = is_blocked
        
    def __str__(self) -> str:
        """String representation of the contact"""
        display_name = self.name or self.push_name or self.id
        return f"Contact: {display_name}"
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert contact to dictionary
        
        Returns:
            Dict: Dictionary representation of contact
        """
        return {
            "id": self.id,
            "name": self.name,
            "pushName": self.push_name,
            "shortName": self.short_name,
            "status": self.status,
            "profilePictureUrl": self.profile_picture_url,
            "isBusiness": self.is_business,
            "isEnterprise": self.is_enterprise,
            "verifiedLevel": self.verified_level,
            "isBlocked": self.is_blocked
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contact':
        """
        Create contact from dictionary
        
        Args:
            data: Dictionary representation of contact
            
        Returns:
            Contact: New contact instance
        """
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            push_name=data.get("pushName"),
            short_name=data.get("shortName"),
            status=data.get("status"),
            profile_picture_url=data.get("profilePictureUrl"),
            is_business=data.get("isBusiness", False),
            is_enterprise=data.get("isEnterprise", False),
            verified_level=data.get("verifiedLevel"),
            is_blocked=data.get("isBlocked", False)
        )
        
    def get_phone_number(self) -> Optional[str]:
        """
        Extract phone number from ID
        
        Returns:
            str: Phone number without WhatsApp suffix, or None if not a valid ID
        """
        if self.id and self.id.endswith("@c.us"):
            return self.id.split("@")[0]
        return None
        
    def get_display_name(self) -> str:
        """
        Get best available display name
        
        Returns:
            str: Best available name to display
        """
        if self.name:
            return self.name
        elif self.push_name:
            return self.push_name
        elif self.short_name:
            return self.short_name
        else:
            phone = self.get_phone_number()
            if phone:
                return phone
            return self.id
