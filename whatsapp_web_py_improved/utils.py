"""
Utilități pentru biblioteca WhatsApp Web Python îmbunătățită.

Acest modul conține funcții utilitare pentru gestionarea conexiunii WebSocket,
generarea ID-urilor și alte funcționalități generale.
"""

import base64
import json
import logging
import random
import string
import time
import uuid
from typing import Dict, Any, Optional

# Configurare logger
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

# Generarea ID-urilor
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
    Generează un ID aleatoriu pentru diverse utilizări.
    
    Args:
        length: Lungimea ID-ului generat
        
    Returns:
        str: ID aleatoriu
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Utilități pentru conversia numerelor de telefon și ID-uri
def phone_number_to_jid(phone: str, is_group: bool = False) -> str:
    """
    Convertește un număr de telefon în format JID (Jabber ID).
    
    Args:
        phone: Numărul de telefon
        is_group: Dacă este un ID de grup
        
    Returns:
        str: JID-ul corespunzător
    """
    # Elimină tot ce nu este cifră
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    if is_group:
        return f"{clean_phone}@g.us"
    else:
        return f"{clean_phone}@s.whatsapp.net"

def jid_to_phone(jid: str) -> str:
    """
    Extrage numărul de telefon dintr-un JID.
    
    Args:
        jid: JID-ul din care se extrage numărul de telefon
        
    Returns:
        str: Numărul de telefon
    """
    if not jid:
        return ""
        
    parts = jid.split('@')
    if len(parts) != 2:
        return jid
        
    return parts[0]

# Utilități pentru codificare/decodificare JSON
def json_stringify(obj: Any) -> str:
    """
    Convertește un obiect Python în JSON string.
    
    Args:
        obj: Obiectul de convertit
        
    Returns:
        str: Reprezentarea JSON a obiectului
    """
    return json.dumps(obj, separators=(',', ':'))

def parse_json(text: str) -> Dict[str, Any]:
    """
    Parsează un string JSON în obiect Python.
    
    Args:
        text: String JSON
        
    Returns:
        dict: Obiectul Python rezultat
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Dacă nu este JSON valid, returnează un dicționar gol
        return {}

# Utilități pentru reconectare
class ReconnectionManager:
    """
    Manager pentru strategia de reconectare cu backoff exponențial.
    """
    
    def __init__(self, 
                 initial_delay_ms: int, 
                 max_delay_ms: int, 
                 max_attempts: int,
                 decay_factor: float = 1.5,
                 random_factor: float = 0.2):
        """
        Inițializează managerul de reconectare.
        
        Args:
            initial_delay_ms: Întârzierea inițială în milisecunde
            max_delay_ms: Întârzierea maximă în milisecunde
            max_attempts: Numărul maxim de încercări
            decay_factor: Factorul de creștere pentru backoff exponențial
            random_factor: Factorul aleatoriu pentru variație (jitter)
        """
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.max_attempts = max_attempts
        self.decay_factor = decay_factor
        self.random_factor = random_factor
        self.attempt_count = 0
        self.logger = get_logger("ReconnectionManager")
        
    def reset(self) -> None:
        """Resetează contorul de încercări."""
        self.attempt_count = 0
        
    def get_next_delay_seconds(self) -> float:
        """
        Calculează întârzierea pentru următoarea încercare în secunde.
        
        Returns:
            float: Întârzierea în secunde sau -1 dacă s-a depășit numărul maxim de încercări
        """
        if self.attempt_count >= self.max_attempts:
            return -1
            
        self.attempt_count += 1
        
        # Calculează întârzierea de bază cu backoff exponențial
        base_delay_ms = min(
            self.initial_delay_ms * (self.decay_factor ** (self.attempt_count - 1)),
            self.max_delay_ms
        )
        
        # Adăugăm factor aleatoriu (jitter)
        jitter = 1.0 + random.uniform(-self.random_factor, self.random_factor)
        delay_ms = base_delay_ms * jitter
        
        # Convertim la secunde
        delay_sec = delay_ms / 1000.0
        
        self.logger.info(f"Calculat întârziere reconectare: {delay_sec:.2f}s (încercarea {self.attempt_count}/{self.max_attempts})")
        return delay_sec
        
    def can_retry(self) -> bool:
        """
        Verifică dacă mai pot fi făcute încercări de reconectare.
        
        Returns:
            bool: True dacă se mai pot face încercări, False altfel
        """
        return self.attempt_count < self.max_attempts