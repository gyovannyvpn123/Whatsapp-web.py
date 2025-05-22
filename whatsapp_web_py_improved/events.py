"""
Sistem de evenimente pentru biblioteca WhatsApp Web Python îmbunătățită.

Acest modul furnizează un sistem de gestionare a evenimentelor pentru comunicarea
între diferitele componente ale bibliotecii și pentru notificarea aplicației client.
"""

import asyncio
import logging
from enum import Enum
from typing import Dict, List, Callable, Any, Optional, Set

from .utils import get_logger

class WAEventType(Enum):
    """Tipuri de evenimente utilizate în biblioteca WhatsApp Web."""
    
    # Evenimente de autentificare și conectare
    QR_CODE = "qr_code"                 # Cod QR pentru scanare
    CONNECTED = "connected"             # Conexiune stabilită cu succes
    AUTHENTICATED = "authenticated"     # Autentificare reușită
    CONNECTION_STATE = "conn_state"     # Schimbare de stare a conexiunii
    DISCONNECTED = "disconnected"       # Conexiune închisă
    
    # Evenimente pentru mesaje
    MESSAGE = "message"                 # Mesaj general
    MESSAGE_RECEIVED = "message_received"   # Mesaj nou primit
    MESSAGE_SENT = "message_sent"       # Mesaj trimis cu succes
    MESSAGE_DELIVERED = "message_delivered" # Mesaj livrat
    MESSAGE_READ = "message_read"       # Mesaj marcat ca citit
    MESSAGE_REACTION = "message_reaction"   # Reacție la mesaj
    
    # Evenimente pentru grupuri
    GROUP_UPDATE = "group_update"       # Actualizare informații grup
    GROUP_PARTICIPANT = "group_participant" # Schimbări participanți grup
    
    # Evenimente pentru media
    MEDIA_UPLOADED = "media_uploaded"   # Media încărcată cu succes
    MEDIA_DOWNLOAD = "media_download"   # Progres descărcare media
    
    # Alte evenimente
    PRESENCE_UPDATE = "presence_update" # Actualizare prezență contact
    CONTACT_UPDATE = "contact_update"   # Actualizare informații contact
    CHAT_UPDATE = "chat_update"         # Actualizare conversație
    STATUS_UPDATE = "status_update"     # Actualizare status
    ERROR = "error"                     # Eroare generală

class EventEmitter:
    """
    Manager de evenimente pentru WhatsApp Web.
    
    Această clasă permite înregistrarea de callback-uri pentru diverse tipuri de evenimente
    și emiterea de evenimente către callback-urile înregistrate.
    """
    
    def __init__(self):
        """Inițializează emițătorul de evenimente."""
        self.logger = get_logger("EventEmitter")
        self._listeners: Dict[str, List[Callable]] = {}
        self._once_listeners: Dict[str, List[Callable]] = {}
        
    def on(self, event_type: WAEventType, callback: Callable) -> None:
        """
        Înregistrează un callback pentru un anumit tip de eveniment.
        
        Args:
            event_type: Tipul de eveniment pentru care se înregistrează callback-ul
            callback: Funcția de callback care va fi apelată la emiterea evenimentului
        """
        event_name = event_type.value
        if event_name not in self._listeners:
            self._listeners[event_name] = []
            
        self._listeners[event_name].append(callback)
        self.logger.debug(f"Înregistrat callback pentru evenimentul {event_name}")
        
    def once(self, event_type: WAEventType, callback: Callable) -> None:
        """
        Înregistrează un callback care va fi apelat o singură dată pentru un anumit tip de eveniment.
        
        Args:
            event_type: Tipul de eveniment pentru care se înregistrează callback-ul
            callback: Funcția de callback care va fi apelată o singură dată la emiterea evenimentului
        """
        event_name = event_type.value
        if event_name not in self._once_listeners:
            self._once_listeners[event_name] = []
            
        self._once_listeners[event_name].append(callback)
        self.logger.debug(f"Înregistrat callback 'once' pentru evenimentul {event_name}")
        
    def off(self, event_type: WAEventType, callback: Optional[Callable] = None) -> None:
        """
        Elimină un callback pentru un anumit tip de eveniment.
        
        Args:
            event_type: Tipul de eveniment pentru care se elimină callback-ul
            callback: Funcția de callback de eliminat. Dacă este None, se elimină toate callback-urile pentru eveniment.
        """
        event_name = event_type.value
        
        # Elimină din listeners regulari
        if event_name in self._listeners:
            if callback is None:
                self._listeners[event_name] = []
                self.logger.debug(f"Eliminate toate callback-urile pentru evenimentul {event_name}")
            else:
                self._listeners[event_name] = [cb for cb in self._listeners[event_name] if cb != callback]
                self.logger.debug(f"Eliminat callback specific pentru evenimentul {event_name}")
                
        # Elimină din once listeners
        if event_name in self._once_listeners:
            if callback is None:
                self._once_listeners[event_name] = []
                self.logger.debug(f"Eliminate toate callback-urile 'once' pentru evenimentul {event_name}")
            else:
                self._once_listeners[event_name] = [cb for cb in self._once_listeners[event_name] if cb != callback]
                self.logger.debug(f"Eliminat callback 'once' specific pentru evenimentul {event_name}")
                
    def emit(self, event_type: WAEventType, data: Any = None) -> None:
        """
        Emite un eveniment către toate callback-urile înregistrate.
        
        Args:
            event_type: Tipul de eveniment de emis
            data: Datele asociate evenimentului
        """
        event_name = event_type.value
        self.logger.debug(f"Emitere eveniment {event_name}")
        
        # Apelează listeners regulari
        if event_name in self._listeners:
            for callback in self._listeners[event_name]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        # Pentru funcții asincrone, creăm un task
                        asyncio.create_task(callback(data))
                    else:
                        # Pentru funcții sincrone, apelăm direct
                        callback(data)
                except Exception as e:
                    self.logger.error(f"Eroare în callback pentru evenimentul {event_name}: {e}")
                    
        # Apelează once listeners și apoi îi elimină
        if event_name in self._once_listeners and self._once_listeners[event_name]:
            once_callbacks = self._once_listeners[event_name].copy()
            self._once_listeners[event_name] = []
            
            for callback in once_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        # Pentru funcții asincrone, creăm un task
                        asyncio.create_task(callback(data))
                    else:
                        # Pentru funcții sincrone, apelăm direct
                        callback(data)
                except Exception as e:
                    self.logger.error(f"Eroare în callback 'once' pentru evenimentul {event_name}: {e}")
                    
    def listeners(self, event_type: WAEventType) -> List[Callable]:
        """
        Obține lista de callback-uri înregistrate pentru un anumit tip de eveniment.
        
        Args:
            event_type: Tipul de eveniment pentru care se obțin callback-urile
            
        Returns:
            List[Callable]: Lista de callback-uri înregistrate
        """
        event_name = event_type.value
        regular = self._listeners.get(event_name, [])
        once = self._once_listeners.get(event_name, [])
        return regular + once
        
    def remove_all_listeners(self, event_type: Optional[WAEventType] = None) -> None:
        """
        Elimină toate callback-urile înregistrate.
        
        Args:
            event_type: Tipul de eveniment pentru care se elimină callback-urile.
                       Dacă este None, se elimină toate callback-urile pentru toate evenimentele.
        """
        if event_type is None:
            self._listeners = {}
            self._once_listeners = {}
            self.logger.debug("Eliminate toate callback-urile pentru toate evenimentele")
        else:
            event_name = event_type.value
            self._listeners[event_name] = []
            self._once_listeners[event_name] = []
            self.logger.debug(f"Eliminate toate callback-urile pentru evenimentul {event_name}")