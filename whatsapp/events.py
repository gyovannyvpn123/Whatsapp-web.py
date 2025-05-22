"""
Event system for WhatsApp Web library.
"""

import asyncio
from enum import Enum, auto
from typing import Dict, Callable, List, Any, Set

class WAEventType(Enum):
    """
    WhatsApp event types
    """
    # Connection events
    CONNECTION_OPEN = auto()
    CONNECTION_CLOSE = auto()
    CONNECTION_ERROR = auto()
    
    # Authentication events
    QR_CODE = auto()
    AUTHENTICATED = auto()
    AUTH_FAILURE = auto()
    AUTH_RESPONSE = auto()
    LOGOUT = auto()
    
    # Message events
    MESSAGE = auto()
    MESSAGE_RECEIVED = auto()
    MESSAGE_SENT = auto()
    MESSAGE_DELIVERY = auto()
    MESSAGE_READ = auto()
    
    # Group events
    GROUP_CREATE = auto()
    GROUP_UPDATE = auto()
    GROUP_PARTICIPANT_ADD = auto()
    GROUP_PARTICIPANT_REMOVE = auto()
    GROUP_PARTICIPANT_PROMOTE = auto()
    GROUP_PARTICIPANT_DEMOTE = auto()
    
    # Status events
    STATUS_UPDATE = auto()
    PRESENCE_UPDATE = auto()
    
    # Other events
    NOTIFICATION = auto()
    BINARY_MESSAGE = auto()
    CHAT_NEW = auto()
    
    # Internal events
    INTERNAL_EVENT = auto()

class EventEmitter:
    """
    Asynchronous event emitter for WhatsApp events
    """
    
    def __init__(self):
        """Initialize the event emitter"""
        self._listeners: Dict[WAEventType, List[Callable]] = {}
        self._once_listeners: Dict[WAEventType, Set[Callable]] = {}
        
    def on(self, event_type: WAEventType, callback: Callable) -> None:
        """
        Register an event listener
        
        Args:
            event_type: Type of event to listen for
            callback: Async function to call when event occurs
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        if callback not in self._listeners[event_type]:
            self._listeners[event_type].append(callback)
            
    def once(self, event_type: WAEventType, callback: Callable) -> None:
        """
        Register a one-time event listener
        
        Args:
            event_type: Type of event to listen for
            callback: Async function to call when event occurs
        """
        if event_type not in self._once_listeners:
            self._once_listeners[event_type] = set()
            
        self._once_listeners[event_type].add(callback)
        
        # Also add to regular listeners
        self.on(event_type, callback)
        
    def off(self, event_type: WAEventType, callback: Callable) -> None:
        """
        Remove an event listener
        
        Args:
            event_type: Type of event
            callback: Callback function to remove
        """
        if event_type in self._listeners:
            if callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)
                
        if event_type in self._once_listeners:
            if callback in self._once_listeners[event_type]:
                self._once_listeners[event_type].remove(callback)
                
    def emit(self, event_type: WAEventType, data: Any) -> None:
        """
        Emit an event
        
        Args:
            event_type: Type of event to emit
            data: Data to pass to listeners
        """
        # Create a task to handle the event asynchronously
        asyncio.create_task(self._emit_async(event_type, data))
        
    async def _emit_async(self, event_type: WAEventType, data: Any) -> None:
        """
        Asynchronously emit an event
        
        Args:
            event_type: Type of event to emit
            data: Data to pass to listeners
        """
        callbacks = self._listeners.get(event_type, []).copy()
        
        for callback in callbacks:
            try:
                # Check if this is a one-time listener
                is_once = event_type in self._once_listeners and callback in self._once_listeners[event_type]
                
                # Call the callback
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
                    
                # Remove if it's a one-time listener
                if is_once:
                    self.off(event_type, callback)
                    
            except Exception as e:
                import logging
                logging.getLogger("whatsapp.EventEmitter").error(
                    f"Error in event listener for {event_type}: {str(e)}"
                )
                
    def remove_all_listeners(self, event_type: WAEventType = None) -> None:
        """
        Remove all listeners for an event type
        
        Args:
            event_type: Event type to clear, or None for all events
        """
        if event_type is None:
            # Clear all listeners
            self._listeners = {}
            self._once_listeners = {}
        else:
            # Clear listeners for specific event
            if event_type in self._listeners:
                del self._listeners[event_type]
            if event_type in self._once_listeners:
                del self._once_listeners[event_type]
                
    def listener_count(self, event_type: WAEventType) -> int:
        """
        Get the number of listeners for an event
        
        Args:
            event_type: Event type to count
            
        Returns:
            int: Number of listeners
        """
        return len(self._listeners.get(event_type, []))
