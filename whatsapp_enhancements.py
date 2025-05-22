"""
Îmbunătățiri pentru biblioteca WhatsApp Web Python

Acest modul conține îmbunătățiri pentru biblioteca whatsapp-web-py, inspirate din
implementarea @whiskeysockets/baileys, cu focus pe:
1. Mecanismul de conexiune WebSocket
2. Strategia de reconectare
3. Parametrii de conexiune actualizați
4. Gestionarea mesajelor și a media
"""

import asyncio
import base64
import json
import os
import time
import random
import logging
from typing import Dict, List, Optional, Union, Any, Callable, Tuple

# Parametri actualizați pentru conexiunea la WhatsApp Web
# Inspirați din implementarea modernă a @whiskeysockets/baileys
WA_WEB_PARAMS = {
    "version": "2.2402.7",         # Versiune actualizată a protocolului
    "browser_data": "Chrome,110.0.5481.177",
    "wa_web_url": "wss://web.whatsapp.com/ws",
    "origin": "https://web.whatsapp.com",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.177 Safari/537.36",
    "ws_protocols": ["chat"],
    "connect_timeout_ms": 30000,
    "keepalive_interval_ms": 20000,
    "alternative_urls": [
        "wss://web.whatsapp.com/ws",
        "wss://web.whatsapp.com/ws/chat"
    ]
}

# Metoda îmbunătățită de generare a ID-ului clientului, urmând tehnica din baileys
def generate_client_id() -> str:
    """
    Generează un ID client pentru WhatsApp Web, conform standardului baileys.
    
    Returns:
        str: ID client codificat base64
    """
    import uuid
    return base64.b64encode(uuid.uuid4().bytes).decode('utf-8')

# Clasă îmbunătățită pentru reconectare, inspirată din baileys
class ReconnectionStrategy:
    """
    Strategie de reconectare inspirată din baileys pentru stabilitatea conexiunii.
    
    Implementează backoff exponențial și încercări multiple pe URL-uri alternative.
    """
    
    def __init__(self, 
                 max_attempts: int = 10, 
                 initial_delay_ms: int = 3000, 
                 max_delay_ms: int = 60000, 
                 decay_factor: float = 1.5):
        """
        Inițializează strategia de reconectare.
        
        Args:
            max_attempts: Numărul maxim de încercări
            initial_delay_ms: Întârzierea inițială între încercări (ms)
            max_delay_ms: Întârzierea maximă între încercări (ms)
            decay_factor: Factorul de creștere pentru backoff exponențial
        """
        self.max_attempts = max_attempts
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.decay_factor = decay_factor
        self.attempt_count = 0
    
    def reset(self):
        """Resetează contorul de încercări."""
        self.attempt_count = 0
    
    def next_delay(self) -> float:
        """
        Calculează următoarea întârziere folosind backoff exponențial.
        
        Returns:
            float: Întârzierea în secunde
        """
        if self.attempt_count >= self.max_attempts:
            return -1  # Indică depășirea numărului maxim de încercări
            
        self.attempt_count += 1
        delay_ms = min(
            self.initial_delay_ms * (self.decay_factor ** (self.attempt_count - 1)),
            self.max_delay_ms
        )
        
        # Adăugăm un jitter (variație aleatoare) pentru a preveni efectul de "thundering herd"
        jitter = random.uniform(0.8, 1.2)
        delay_ms *= jitter
        
        return delay_ms / 1000.0  # Convertim la secunde
    
    def can_retry(self) -> bool:
        """
        Verifică dacă mai pot fi făcute încercări de reconectare.
        
        Returns:
            bool: True dacă se mai pot face încercări, False altfel
        """
        return self.attempt_count < self.max_attempts

# Clasă pentru îmbunătățirea parametrilor de conectare la WebSocket
class EnhancedWebSocketParams:
    """
    Gestionează parametrii de conectare la WebSocket, inspirați din baileys.
    
    Furnizează URL-uri și headere actualizate pentru conexiunea la WhatsApp Web.
    """
    
    @staticmethod
    def get_connection_urls(client_id: Optional[str] = None) -> List[str]:
        """
        Generează lista de URL-uri pentru conexiunea WebSocket cu parametrii actualizați.
        
        Args:
            client_id: ID-ul clientului (opțional)
            
        Returns:
            List[str]: Lista de URL-uri pentru conectare
        """
        if not client_id:
            client_id = generate_client_id()
            
        # Parametrii query inspirați din baileys
        query_params = {
            "version": WA_WEB_PARAMS["version"],
            "browser_data": WA_WEB_PARAMS["browser_data"],
            "clientId": client_id
        }
        
        # Construim query string-ul
        query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
        
        # Adăugăm parametrii la fiecare URL
        urls = []
        for url in [WA_WEB_PARAMS["wa_web_url"]] + WA_WEB_PARAMS["alternative_urls"]:
            urls.append(f"{url}?{query_string}")
            
        return urls
    
    @staticmethod
    def get_connection_headers() -> Dict[str, str]:
        """
        Generează headerele pentru conexiunea WebSocket, inspirate din baileys.
        
        Returns:
            Dict[str, str]: Headerele pentru conexiunea WebSocket
        """
        return {
            "Origin": WA_WEB_PARAMS["origin"],
            "User-Agent": WA_WEB_PARAMS["user_agent"],
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits"
        }

# Exemplu de implementare îmbunătățită pentru keepalive
class KeepAliveManager:
    """
    Manager pentru menținerea conexiunii active, inspirat din baileys.
    
    Trimite periodic mesaje de ping pentru a menține conexiunea deschisă.
    """
    
    def __init__(self, interval_ms: int = WA_WEB_PARAMS["keepalive_interval_ms"]):
        """
        Inițializează managerul keepalive.
        
        Args:
            interval_ms: Intervalul între mesaje de ping (ms)
        """
        self.interval_sec = interval_ms / 1000.0
        self.task = None
        self.running = False
        self.logger = logging.getLogger("KeepAliveManager")
    
    async def start(self, send_callback: Callable[[], Awaitable[None]]):
        """
        Pornește task-ul de keepalive.
        
        Args:
            send_callback: Funcția callback pentru trimiterea mesajului de ping
        """
        if self.running:
            return
            
        self.running = True
        self.task = asyncio.create_task(self._keepalive_loop(send_callback))
        self.logger.debug(f"Started keepalive task (interval: {self.interval_sec}s)")
    
    async def stop(self):
        """Oprește task-ul de keepalive."""
        if not self.running:
            return
            
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        
        self.logger.debug("Stopped keepalive task")
    
    async def _keepalive_loop(self, send_callback: Callable[[], Awaitable[None]]):
        """
        Bucla principală pentru trimiterea mesajelor de ping.
        
        Args:
            send_callback: Funcția callback pentru trimiterea mesajului de ping
        """
        try:
            while self.running:
                try:
                    await send_callback()
                    self.logger.debug("Sent keepalive ping")
                except Exception as e:
                    self.logger.error(f"Error sending keepalive: {e}")
                
                await asyncio.sleep(self.interval_sec)
        except asyncio.CancelledError:
            self.logger.debug("Keepalive task cancelled")
            raise

# Exemplu de îmbunătățire a inițializării conexiunii, inspirată din baileys
def enhance_connection_init_message(client_id: str) -> Dict[str, Any]:
    """
    Generează un mesaj îmbunătățit de inițializare a conexiunii, inspirat din baileys.
    
    Args:
        client_id: ID-ul clientului
        
    Returns:
        Dict[str, Any]: Mesajul de inițializare
    """
    return {
        "clientId": client_id,
        "connectType": "WIFI_UNKNOWN",
        "connectReason": "USER_ACTIVATED",
        "userAgent": WA_WEB_PARAMS["user_agent"],
        "webVersion": WA_WEB_PARAMS["version"],
        "browserName": WA_WEB_PARAMS["browser_data"].split(',')[0]
    }

# Aceste îmbunătățiri pot fi integrate în biblioteca whatsapp-web-py
# pentru a îmbunătăți conectivitatea și stabilitatea