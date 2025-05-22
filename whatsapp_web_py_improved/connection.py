"""
Modul de conexiune WebSocket pentru biblioteca WhatsApp Web Python îmbunătățită.

Acest modul gestionează conexiunea WebSocket la serverele WhatsApp Web cu 
mecanisme îmbunătățite pentru stabilitate și reconectare.
"""

import asyncio
import json
import logging
import random
import time
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union
import websockets
from urllib.parse import urlparse, parse_qs, urlencode

from .constants import (
    WA_WEBSOCKET_URL, WA_ORIGIN, WA_USER_AGENT, WA_WS_PROTOCOLS,
    WA_ALTERNATIVE_WS_URLS, WA_BROWSER_NAME, WA_BROWSER_VERSION,
    WA_CLIENT_VERSION, CONNECT_TIMEOUT_MS, KEEPALIVE_INTERVAL_MS,
    MAX_RECONNECT_ATTEMPTS, RECONNECT_DELAY_MS, MAX_RECONNECT_DELAY_MS,
    RECONNECT_DECAY_FACTOR, RECONNECT_RANDOM_FACTOR, WA_DEFAULT_HEADERS,
    ConnectionState, WA_KEEPALIVE_COMMAND, WA_BROWSER_DATA
)
from .utils import (
    get_logger, generate_message_tag, generate_client_id, 
    generate_random_id, ReconnectionManager
)
from .events import EventEmitter, WAEventType
from .exceptions import WAConnectionError

class WAConnection:
    """
    Manager îmbunătățit de conexiune WebSocket pentru WhatsApp Web.
    
    Această clasă gestionează conexiunea WebSocket la serverele WhatsApp Web,
    cu mecanisme îmbunătățite pentru stabilitate și reconectare.
    """
    
    def __init__(self, event_emitter: EventEmitter):
        """
        Inițializează managerul de conexiune.
        
        Args:
            event_emitter: Emițătorul de evenimente pentru notificări
        """
        self.logger = get_logger("WAConnection")
        self.event_emitter = event_emitter
        self.ws = None
        self.client_id = generate_client_id()
        self.reconnect_manager = ReconnectionManager(
            initial_delay_ms=RECONNECT_DELAY_MS,
            max_delay_ms=MAX_RECONNECT_DELAY_MS,
            max_attempts=MAX_RECONNECT_ATTEMPTS,
            decay_factor=RECONNECT_DECAY_FACTOR,
            random_factor=RECONNECT_RANDOM_FACTOR
        )
        
        # State management
        self._state = ConnectionState.DISCONNECTED
        self._authenticated = False
        self._closing = False
        self._listener_task = None
        self._keepalive_task = None
        
        # Tracking pentru conexiune
        self.last_seen = time.time()
        self.server_token = None
        self.client_token = None
        
    @property
    def state(self) -> str:
        """Starea curentă a conexiunii."""
        return self._state
        
    @property
    def is_connected(self) -> bool:
        """Verifică dacă conexiunea este activă."""
        return self._state == ConnectionState.CONNECTED
        
    @property
    def is_authenticated(self) -> bool:
        """Verifică dacă clientul este autentificat."""
        return self._authenticated
        
    def _update_state(self, new_state: str) -> None:
        """
        Actualizează starea conexiunii și emite eveniment de schimbare.
        
        Args:
            new_state: Noua stare a conexiunii
        """
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            self.logger.info(f"Stare conexiune schimbată: {old_state} -> {new_state}")
            
            # Emit connection state change event
            self.event_emitter.emit(WAEventType.CONNECTION_STATE, {
                "old": old_state,
                "new": new_state
            })
    
    async def connect(self) -> bool:
        """
        Conectare la serverele WhatsApp Web cu strategie îmbunătățită.
        
        Returns:
            bool: True dacă conexiunea a fost stabilită cu succes, False altfel
            
        Raises:
            WAConnectionError: Dacă apare o eroare la conexiune
        """
        if self.is_connected:
            self.logger.warning("Deja conectat la serverele WhatsApp Web")
            return True
            
        if self._state == ConnectionState.CONNECTING:
            self.logger.warning("Conexiune în curs...")
            return False
            
        self._update_state(ConnectionState.CONNECTING)
        self.reconnect_manager.reset()
        
        # Construiește lista de URL-uri de încercat
        urls_to_try = self._get_connection_urls()
        self.logger.info(f"Încercarea de conectare la WhatsApp Web cu {len(urls_to_try)} URL-uri posibile")
        
        # Încercăm fiecare URL până reușim sau epuizăm lista
        for ws_url in urls_to_try:
            try:
                self.logger.info(f"Încercare conexiune la: {ws_url}")
                
                # Construim headerele de conexiune
                headers = WA_DEFAULT_HEADERS.copy()
                
                # Stabilim conexiunea WebSocket
                self.ws = await websockets.connect(
                    ws_url,
                    extra_headers=headers,
                    subprotocols=WA_WS_PROTOCOLS,
                    ping_interval=None,  # Vom gestiona manual keepalive
                    ping_timeout=None,
                    max_size=None,  # Fără limită pentru dimensiunea mesajelor
                    close_timeout=5,
                    compression=None
                )
                
                # Dacă am ajuns aici, conexiunea a reușit
                self.logger.info(f"Conexiune WebSocket stabilită cu succes la {ws_url}")
                self._update_state(ConnectionState.CONNECTED)
                
                # Pornește ascultătorul de mesaje
                self._start_listener()
                
                # Pornește mecanismul de keepalive
                self._start_keepalive()
                
                # Inițiază conexiunea cu serverul
                await self._send_init_message()
                
                return True
                
            except Exception as e:
                self.logger.error(f"Eroare la conexiunea la {ws_url}: {e}")
                # Continuăm cu următorul URL
        
        # Dacă am ajuns aici, toate încercările au eșuat
        self._update_state(ConnectionState.DISCONNECTED)
        raise WAConnectionError("Nu s-a putut stabili conexiunea la niciunul dintre serverele WhatsApp Web")
    
    async def disconnect(self) -> None:
        """
        Închide conexiunea WebSocket în mod controlat.
        """
        if not self.is_connected:
            self.logger.warning("Nu există o conexiune activă de închis")
            return
            
        self._update_state(ConnectionState.DISCONNECTING)
        self._closing = True
        
        # Oprim task-urile de menținere a conexiunii
        await self._stop_keepalive()
        
        # Oprim ascultătorul de mesaje
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        
        # Închidem conexiunea WebSocket
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                self.logger.error(f"Eroare la închiderea WebSocket: {e}")
            finally:
                self.ws = None
                
        self._closing = False
        self._update_state(ConnectionState.DISCONNECTED)
        self._authenticated = False
        self.logger.info("Deconectat de la serverele WhatsApp Web")
        
    async def reconnect(self) -> bool:
        """
        Încearcă reconectarea la serverele WhatsApp Web cu backoff exponențial.
        
        Returns:
            bool: True dacă reconectarea a reușit, False altfel
        """
        if self._closing:
            self.logger.warning("Se închide conexiunea, nu se poate reconecta")
            return False
            
        if self.is_connected:
            self.logger.warning("Deja conectat, nu este necesară reconectarea")
            return True
            
        self._update_state(ConnectionState.RECONNECTING)
        
        # Verifică dacă mai pot fi făcute încercări de reconectare
        if not self.reconnect_manager.can_retry():
            self.logger.error(f"S-a depășit numărul maxim de încercări de reconectare ({MAX_RECONNECT_ATTEMPTS})")
            self._update_state(ConnectionState.DISCONNECTED)
            return False
            
        # Calculează întârzierea pentru următoarea încercare
        delay_sec = self.reconnect_manager.get_next_delay_seconds()
        if delay_sec < 0:
            self.logger.error("Nu se mai pot face încercări de reconectare")
            self._update_state(ConnectionState.DISCONNECTED)
            return False
            
        self.logger.info(f"Așteptăm {delay_sec:.2f} secunde înainte de reconectare (încercarea {self.reconnect_manager.attempt_count})")
        await asyncio.sleep(delay_sec)
        
        try:
            # Închide orice conexiune existentă
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
                
            # Încearcă conectarea
            return await self.connect()
            
        except Exception as e:
            self.logger.error(f"Eroare la reconectare: {e}")
            # Vom încerca din nou la următorul ciclu de reconectare
            return False
    
    async def send_message(self, data: Union[Dict, List, str], tag: Optional[str] = None) -> str:
        """
        Trimite un mesaj prin conexiunea WebSocket.
        
        Args:
            data: Datele de trimis
            tag: Tag-ul mesajului pentru corelarea cu răspunsul
            
        Returns:
            str: Tag-ul mesajului
            
        Raises:
            WAConnectionError: Dacă nu există o conexiune activă
        """
        if not self.is_connected or not self.ws:
            raise WAConnectionError("Nu există o conexiune WebSocket activă")
            
        # Generează un tag dacă nu a fost furnizat
        tag = tag or generate_message_tag()
        
        # Convertește la JSON dacă este dicționar sau listă
        if isinstance(data, (dict, list)):
            data = json.dumps(data, separators=(',', ':'))
            
        # Construiește mesajul în formatul așteptat de WhatsApp
        message = f"{tag},{data}"
        
        try:
            self.logger.debug(f"Trimitere mesaj: {message[:100]}...")
            await self.ws.send(message)
            self.last_seen = time.time()
            return tag
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea mesajului: {e}")
            raise WAConnectionError(f"Eroare la trimiterea mesajului: {e}")
            
    def _get_connection_urls(self) -> List[str]:
        """
        Generează lista de URL-uri pentru conexiune cu parametri.
        
        Returns:
            List[str]: Lista de URL-uri pentru încercare
        """
        # Parametrii comuni pentru toate URL-urile
        query_params = {
            "v": WA_CLIENT_VERSION,
            "browser_data": WA_BROWSER_DATA,
            "clientId": self.client_id
        }
        
        # Adaugă token-urile de client și server dacă există
        if self.client_token:
            query_params["clientToken"] = self.client_token
        if self.server_token:
            query_params["serverToken"] = self.server_token
            
        # Construiește query string-ul
        query_string = urlencode(query_params)
        
        # Aplică la toate URL-urile
        urls = []
        
        # Adăugăm URL-ul principal
        urls.append(f"{WA_WEBSOCKET_URL}?{query_string}")
        
        # Adăugăm URL-urile alternative
        for alt_url in WA_ALTERNATIVE_WS_URLS:
            if alt_url != WA_WEBSOCKET_URL:  # Evităm duplicatele
                urls.append(f"{alt_url}?{query_string}")
                
        return urls
        
    async def _send_init_message(self) -> None:
        """
        Trimite mesajul de inițializare a conexiunii.
        Similar cu modelul din baileys.
        """
        init_message = {
            "clientId": self.client_id,
            "connectType": "WIFI_UNKNOWN",
            "connectReason": "USER_ACTIVATED",
            "userAgent": WA_USER_AGENT,
            "webVersion": WA_CLIENT_VERSION,
            "browserName": WA_BROWSER_NAME,
            "browserVersion": WA_BROWSER_VERSION
        }
        
        # Adaugă token-urile de client și server dacă există
        if self.client_token:
            init_message["clientToken"] = self.client_token
        if self.server_token:
            init_message["serverToken"] = self.server_token
            
        await self.send_message(init_message, "admin")
        self.logger.info("Mesaj de inițializare trimis")
        
    def _start_listener(self) -> None:
        """
        Pornește task-ul de ascultare a mesajelor WebSocket.
        """
        if self._listener_task:
            self._listener_task.cancel()
            
        self._listener_task = asyncio.create_task(self._listen_for_messages())
        
    async def _listen_for_messages(self) -> None:
        """
        Ascultă mesajele primite prin WebSocket și le procesează.
        """
        if not self.ws:
            self.logger.error("Nu există o conexiune WebSocket activă pentru ascultare")
            return
            
        self.logger.info("Pornit ascultătorul de mesaje WebSocket")
        
        try:
            async for message in self.ws:
                self.last_seen = time.time()
                
                try:
                    # Parsare mesaj în format tag,data
                    parts = message.split(',', 1)
                    if len(parts) < 2:
                        self.logger.warning(f"Mesaj primit în format neașteptat: {message[:50]}...")
                        continue
                        
                    tag = parts[0]
                    data_str = parts[1]
                    
                    # Tratăm mesajele pong special
                    if tag.startswith("pong"):
                        self.logger.debug("Primit mesaj pong")
                        continue
                        
                    # Încercăm să parsăm JSON
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        data = data_str
                        
                    # Procesăm mesajul
                    await self._process_message(tag, data)
                    
                except Exception as e:
                    self.logger.error(f"Eroare la procesarea mesajului: {e}")
                    
        except asyncio.CancelledError:
            self.logger.info("Ascultătorul de mesaje oprit")
            raise
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.error(f"Conexiunea WebSocket închisă: {e}")
            if not self._closing:
                self._handle_connection_closed()
        except Exception as e:
            self.logger.error(f"Eroare în ascultătorul de mesaje: {e}")
            if not self._closing:
                self._handle_connection_closed()
                
    def _handle_connection_closed(self) -> None:
        """
        Gestionează închiderea neașteptată a conexiunii.
        """
        if self._closing:
            return  # Ignorăm dacă închiderea a fost inițiată de noi
            
        self._update_state(ConnectionState.DISCONNECTED)
        
        # Oprim task-urile de menținere a conexiunii
        asyncio.create_task(self._stop_keepalive())
        
        # Emitem eveniment de deconectare
        self.event_emitter.emit(WAEventType.DISCONNECTED, {
            "reason": "connection_closed"
        })
        
        # Inițiem reconectarea dacă este cazul
        if not self._closing:
            asyncio.create_task(self.reconnect())
    
    async def _process_message(self, tag: str, data: Any) -> None:
        """
        Procesează mesajele primite de la server.
        
        Args:
            tag: Tag-ul mesajului
            data: Datele mesajului
        """
        # Procesăm mesajele speciale
        
        # Mesaj de succes pentru conectare
        if tag == "s1" and isinstance(data, dict) and data.get("status") == 200:
            self.client_token = data.get("clientToken")
            self.server_token = data.get("serverToken")
            self.logger.info("Conexiune autentificată cu succes la WhatsApp Web")
            
            # Emitem evenimentul de conectare
            self.event_emitter.emit(WAEventType.CONNECTED, {
                "clientToken": self.client_token,
                "serverToken": self.server_token
            })
            return
            
        # Mesaj de QR code pentru scanare
        if tag == "s1" and isinstance(data, dict) and data.get("status") == 401:
            qr_code = data.get("ref", "")
            if qr_code:
                self.logger.info("Cod QR primit pentru autentificare")
                
                # Emitem evenimentul de QR code
                self.event_emitter.emit(WAEventType.QR_CODE, {
                    "qr": qr_code
                })
            return
            
        # Alte mesaje le trimitem către handler-ul general
        self.event_emitter.emit(WAEventType.MESSAGE, {
            "tag": tag,
            "data": data
        })
        
    def _start_keepalive(self) -> None:
        """
        Pornește task-ul de keepalive pentru menținerea conexiunii active.
        Similar cu implementarea din baileys.
        """
        if self._keepalive_task:
            self._keepalive_task.cancel()
            
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        self.logger.info(f"Pornit task-ul keepalive (interval: {KEEPALIVE_INTERVAL_MS/1000}s)")
        
    async def _stop_keepalive(self) -> None:
        """
        Oprește task-ul de keepalive.
        """
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None
            self.logger.info("Task-ul keepalive oprit")
            
    async def _keepalive_loop(self) -> None:
        """
        Bucla de trimitere a mesajelor keepalive pentru menținerea conexiunii active.
        """
        try:
            while self.is_connected and self.ws:
                try:
                    # Verificăm dacă conexiunea este încă activă
                    if time.time() - self.last_seen > KEEPALIVE_INTERVAL_MS/1000 * 2:
                        self.logger.warning("Nu s-a primit niciun răspuns la mesajele keepalive. Posibilă conexiune inactivă.")
                        # Vom forța o reconectare
                        raise WAConnectionError("Keepalive timeout")
                        
                    # Trimitem comanda keepalive
                    await self.ws.send(WA_KEEPALIVE_COMMAND)
                    self.logger.debug("Mesaj keepalive trimis")
                    
                    # Așteptăm intervalul
                    await asyncio.sleep(KEEPALIVE_INTERVAL_MS/1000)
                    
                except Exception as e:
                    if not isinstance(e, asyncio.CancelledError):
                        self.logger.error(f"Eroare în bucla keepalive: {e}")
                        # Forțăm o reconectare
                        if not self._closing:
                            self._handle_connection_closed()
                        break
                        
        except asyncio.CancelledError:
            self.logger.info("Bucla keepalive oprită")
            raise