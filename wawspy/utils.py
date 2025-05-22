"""
Utilități pentru biblioteca WhatsApp Web Python.

Acest modul conține funcții utilitare pentru diverse componente ale bibliotecii.
"""

import base64
import json
import logging
import random
import string
import time
import uuid
from typing import Dict, Any, Optional, List, Callable, Union

def get_logger(name: str) -> logging.Logger:
    """
    Obține un logger configurat pentru modulul specificat.
    
    Args:
        name: Numele modulului
        
    Returns:
        logging.Logger: Logger configurat
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def generate_message_tag() -> str:
    """
    Generează un tag unic pentru mesajele WhatsApp.
    
    Returns:
        str: Tag de mesaj
    """
    return str(time.time()).replace(".", "") + str(random.randint(10000, 99999))

def generate_client_id() -> str:
    """
    Generează un ID client pentru WhatsApp Web.
    Metodă similară cu cea din Baileys.
    
    Returns:
        str: ID-ul clientului
    """
    return base64.b64encode(uuid.uuid4().bytes).decode('utf-8')

def generate_random_id(length: int = 16) -> str:
    """
    Generează un ID aleator.
    
    Args:
        length: Lungimea ID-ului
        
    Returns:
        str: ID-ul generat
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def phone_number_to_jid(phone: str) -> str:
    """
    Convertește un număr de telefon în format JID (Jabber ID).
    
    Args:
        phone: Numărul de telefon
        
    Returns:
        str: JID-ul corespunzător
    """
    phone = phone.lstrip('+')
    return f"{phone}@s.whatsapp.net"

def jid_to_phone(jid: str) -> str:
    """
    Extrage numărul de telefon dintr-un JID.
    
    Args:
        jid: JID-ul
        
    Returns:
        str: Numărul de telefon
    """
    if '@' not in jid:
        return jid
    
    return jid.split('@')[0]

class ReconnectionManager:
    """
    Manager pentru strategia de reconectare la WhatsApp Web.
    
    Implementează backoff exponențial și gestionarea tentativelor de reconectare.
    """
    
    def __init__(self, initial_delay_ms: int = 3000, 
                 max_delay_ms: int = 60000, 
                 max_attempts: int = 10,
                 decay_factor: float = 1.5,
                 random_factor: float = 0.2):
        """
        Inițializează managerul de reconectare.
        
        Args:
            initial_delay_ms: Întârzierea inițială între încercări (ms)
            max_delay_ms: Întârzierea maximă între încercări (ms)
            max_attempts: Numărul maxim de încercări
            decay_factor: Factorul de creștere pentru backoff exponențial
            random_factor: Factorul aleator pentru evitarea coliziunilor
        """
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.max_attempts = max_attempts
        self.decay_factor = decay_factor
        self.random_factor = random_factor
        
        self.attempt_count = 0
        
    def reset(self) -> None:
        """Resetează contorul de încercări."""
        self.attempt_count = 0
        
    def get_next_delay_seconds(self) -> float:
        """
        Calculează următoarea întârziere folosind backoff exponențial.
        
        Returns:
            float: Întârzierea în secunde sau -1 dacă s-a depășit numărul maxim de încercări
        """
        if not self.can_retry():
            return -1
            
        # Incrementăm contorul de încercări
        self.attempt_count += 1
        
        # Calculăm întârzierea de bază cu backoff exponențial
        delay_ms = min(
            self.initial_delay_ms * (self.decay_factor ** (self.attempt_count - 1)),
            self.max_delay_ms
        )
        
        # Adăugăm un factor aleator pentru a evita reconectările sincronizate
        if self.random_factor > 0:
            jitter = random.uniform(-self.random_factor, self.random_factor)
            delay_ms = delay_ms * (1 + jitter)
            
        # Convertim la secunde
        return delay_ms / 1000
        
    def can_retry(self) -> bool:
        """
        Verifică dacă mai pot fi făcute încercări de reconectare.
        
        Returns:
            bool: True dacă se mai pot face încercări, False altfel
        """
        return self.attempt_count < self.max_attempts