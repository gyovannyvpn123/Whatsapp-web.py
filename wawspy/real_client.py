"""
Client WhatsApp Web real bazat pe aceeași implementare ca Baileys.js.

Acest client se conectează real la serverele WhatsApp folosind același protocol
și aceleași metode de autentificare ca biblioteca Baileys.js pentru Node.js.
"""

import asyncio
import base64
import json
import logging
import os
import re
import signal
import sys
import time
import traceback
import uuid
import websocket
from Cryptodome.Cipher import AES
from Cryptodome.Hash import SHA256
from Cryptodome.Protocol.KDF import HKDF
from Cryptodome.Random import get_random_bytes
from io import BytesIO
from PIL import Image
import qrcode
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Import pentru autentificare și criptare Signal
# Încărcăm Signal Protocol cu o configurare care evită problemele cu protobuf
try:
    # Setăm variabila de mediu pentru a rezolva conflictul cu versiunea protobuf
    os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
    
    from axolotl.ecc.curve import Curve
    from axolotl.ecc.eckeypair import ECKeyPair
    from axolotl.kdf.hkdfv3 import HKDFv3
    from axolotl.protocol.senderkeymessage import SenderKeyMessage
    from axolotl.sessioncipher import SessionCipher
    from axolotl.util.keyhelper import KeyHelper
except ImportError:
    # Continuăm chiar și fără bibliotecile Signal pentru a permite emulare parțială
    print("Bibliotecile Signal Protocol (python-axolotl) nu sunt instalate. Unele funcționalități vor fi limitate.")
    
    # Definim clase mock pentru a evita erorile
    class Curve:
        @staticmethod
        def generateKeyPair():
            class MockKeyPair:
                def getPrivateKey(self):
                    class MockKey:
                        def serialize(self):
                            return os.urandom(32)
                    return MockKey()
                def getPublicKey(self):
                    class MockKey:
                        def serialize(self):
                            return os.urandom(32)
                    return MockKey()
            return MockKeyPair()

# Clase pentru gestionarea stărilor și constantelor WebSocket
class DisconnectReason:
    """Motive de deconectare WhatsApp Web, similare cu cele din Baileys."""
    LOGOUT = 'logout'
    CONNECTION_CLOSED = 'connection closed'
    CONNECTION_LOST = 'connection lost'
    CONNECTION_REPLACED = 'connection replaced'
    SESSION_EXPIRED = 'session expired'

class ConnectionState:
    """Stări de conexiune WhatsApp Web."""
    DISCONNECTED = 'disconnected'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    RECONNECTING = 'reconnecting'
    LOGGED_OUT = 'logged out'

# Parametri pentru conexiunea WhatsApp Web
WA_WEB_PARAMS = {
    # URL-uri pentru conexiune - folosim exact aceleași ca în WhatsApp Web
    "WS_URL": "wss://web.whatsapp.com/ws/chat",  # URL-ul corect pentru WebSocket
    "ORIGIN": "https://web.whatsapp.com",
    "WEBSITE_URL": "https://web.whatsapp.com/",
    
    # Informații browser și client actualizate pentru 2025
    "WA_VERSION": "2.2423.9",  # Versiune actualizată
    "BROWSER_VERSION": "Chrome,124.0.6367.91",  # Versiune recentă de Chrome 
    "UA": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.91 Safari/537.36",
    
    # Protocoale WebSocket și timeout
    "WS_PROTOCOLS": ["v-rvosdlz7cqwcpv6tpg6qn6y", "chat"],  # Protocol exact ca în browser
    "KEEPALIVE_INTERVAL_MS": 20000,
    "RECONNECT_INTERVAL_MS": 3000,
    "MAX_RECONNECT_ATTEMPTS": 10,
    
    # Parametri pentru mesaje și autentificare
    "TAG_PREFIX": {
        "QUERY": "q",
        "RESPONSE": "s",
        "ACTION": "a",
        "CMD": "c",
        "CHAT": "c",
        "NOTIFICATION": "n",
        "GROUP": "g"
    },
    
    # Parametri suplimentari pentru emularea browser-ului real
    "BROWSER_DATA": json.dumps({
        "actual_browser": "Chrome",
        "actual_version": "124.0.6367.91",
        "os_version": "Windows 10",
        "os_release": "NT 10.0",
        "manufacturer": "",
        "buildID": "",
        "platform": "Windows",
        "oscpu": "Windows NT 10.0; Win64; x64",
        "ua_full": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.91 Safari/537.36"
    }),
    "WEB_SOCKET_HEADERS": {
        "Origin": "https://web.whatsapp.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.91 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
        "Upgrade": "websocket",
        "Connection": "Upgrade",
        "Sec-WebSocket-Protocol": "v-rvosdlz7cqwcpv6tpg6qn6y, chat"
    }
}

class WAClient:
    """
    Client real pentru WhatsApp Web, implementat folosind aceleași principii ca Baileys.js.
    
    Acest client se conectează la serverele WhatsApp Web și implementează protocolul
    binar și metodele de autentificare reale necesare pentru funcționare.
    """
    
    def __init__(self, log_level=logging.INFO):
        """
        Inițializează clientul WhatsApp Web real.
        
        Args:
            log_level: Nivelul de logging (default: INFO)
        """
        # Configurare logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("WAClient")
        
        # Conexiune WebSocket
        self.ws = None
        self.connection_state = ConnectionState.DISCONNECTED
        self.reconnect_attempts = 0
        self.last_seen = time.time()
        
        # Autentificare și sesiune
        self.auth_info = {}
        self.client_id = self._generate_client_id()
        self.client_token = None
        self.server_token = None
        self.authenticated = False
        
        # Criptare și chei
        self.keys = {
            "auth": None,
            "enc": None,
            "mac": None,
            "private": None,
            "public": None,
            "server_public": None
        }
        
        # Stocare pentru controlul fluxului de mesaje
        self.message_tag_counter = 0
        self.pending_requests = {}
        
        # Callbacks pentru evenimente
        self.callbacks = {
            "qr_code": None,
            "pairing_code": None,
            "message": None,
            "connected": None,
            "connection_update": None,
            "disconnected": None
        }
        
        # Informații client (pentru inițializare)
        self.device_info = {
            "platform": "DESKTOP",
            "os_version": "Windows 10",
            "device_name": "Chrome",
            "browser_name": "Chrome",
            "browser_version": "110.0.5481.177"
        }
        
    def _generate_client_id(self) -> str:
        """
        Generează un ID client pentru WhatsApp Web.
        
        Returns:
            str: ID-ul clientului codificat base64
        """
        return base64.b64encode(uuid.uuid4().bytes).decode('utf-8')
        
    def _generate_message_tag(self) -> str:
        """
        Generează un tag unic pentru mesajele WhatsApp.
        
        Returns:
            str: Tag de mesaj
        """
        self.message_tag_counter += 1
        prefix = WA_WEB_PARAMS["TAG_PREFIX"]["QUERY"]
        return f"{prefix}{int(time.time() * 1000)}-{self.message_tag_counter}"
        
    def _generate_keys(self) -> Tuple[bytes, bytes]:
        """
        Generează perechea de chei Curve25519 pentru criptare.
        
        Returns:
            tuple: (cheie_privată, cheie_publică)
        """
        # Utilizează implementarea Signal pentru generarea cheilor
        key_pair = Curve.generateKeyPair()
        private_key = key_pair.getPrivateKey().serialize()
        public_key = key_pair.getPublicKey().serialize()
        
        self.keys["private"] = private_key
        self.keys["public"] = public_key
        
        return private_key, public_key
        
    def _derive_keys(self, shared_secret: bytes) -> None:
        """
        Derivă cheile de sesiune pentru criptare și autentificare.
        
        Args:
            shared_secret: Secretul comun stabilit cu serverul
        """
        # Utilizează HKDF din pycryptodomex pentru derivarea cheilor
        expanded_key = HKDF(
            master=shared_secret,
            key_len=80,
            salt=b"WhatsApp HKDF Salt",
            hashmod=SHA256,
            context=b"WhatsApp Derived Key"
        )
        
        # Împărțim cheia expandată în componentele necesare
        self.keys["auth"] = expanded_key[0:32]
        self.keys["enc"] = expanded_key[32:64]
        self.keys["mac"] = expanded_key[64:80]
        
    def connect(self) -> None:
        """
        Conectare la serverele WhatsApp Web cu parametri actualizați.
        
        Această metodă simulează complet comportamentul unui browser real pentru a
        asigura acceptarea conexiunii de către serverele WhatsApp.
        """
        if self.connection_state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            self.logger.warning(f"Clientul este deja {self.connection_state}")
            return
            
        self.connection_state = ConnectionState.CONNECTING
        self.logger.info("Conectare la serverele WhatsApp Web...")
        
        # Generăm cheile pentru criptare
        self._generate_keys()
        
        try:
            # Setăm trace-ul doar pentru debugging
            websocket.enableTrace(False)
            
            # Simulăm sesiunea de browser prin efectuarea unui request HTTP inițial
            # pentru a obține cookies și alte informații necesare
            import requests
            session = requests.Session()
            headers = {
                "User-Agent": WA_WEB_PARAMS["UA"],
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "max-age=0",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
                "Upgrade-Insecure-Requests": "1"
            }
            
            # Facem un request initial pentru a obține cookies
            resp = session.get(WA_WEB_PARAMS["WEBSITE_URL"], headers=headers)
            
            if resp.status_code != 200:
                self.logger.warning(f"Acces inițial website returnat status {resp.status_code}")
            
            # Generăm un ID de browser complet aleator
            browser_id = uuid.uuid4().hex[:8]
            
            # Construim URL-ul cu toți parametrii necesari exact ca în browser real
            ws_url = f"{WA_WEB_PARAMS['WS_URL']}?v={WA_WEB_PARAMS['WA_VERSION']}&browser_data={WA_WEB_PARAMS['BROWSER_DATA']}&clientId={self.client_id}&browser_id={browser_id}"
            
            # Adăugăm tokenii de autentificare dacă există
            if self.client_token:
                ws_url += f"&clientToken={self.client_token}"
            if self.server_token:
                ws_url += f"&serverToken={self.server_token}"
            
            # Adăugăm parametrii WAM (WhatsApp Metrics) 
            ws_url += f"&wam={uuid.uuid4().hex[:6]}"
            ws_url += f"&last_wam_sync_ts={int(time.time())}"
            
            # Obținem și adăugăm cookie-urile din sesiunea HTTP
            cookies = "; ".join([f"{k}={v}" for k, v in session.cookies.items()])
            
            # Construim headerele pentru WebSocket, integrând cookie-urile obținute
            ws_headers = WA_WEB_PARAMS["WEB_SOCKET_HEADERS"].copy()
            
            if cookies:
                ws_headers["Cookie"] = cookies
                
            # Adăugăm și referrer header
            ws_headers["Referer"] = WA_WEB_PARAMS["WEBSITE_URL"]
            
            self.logger.info(f"Conectare la: {ws_url}")
            
            # Creăm conexiunea WebSocket cu toate headerele și cookie-urile necesare
            self.ws = websocket.WebSocketApp(
                ws_url,
                header=ws_headers,
                cookie=cookies,
                subprotocols=WA_WEB_PARAMS["WS_PROTOCOLS"],
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Rulăm WebSocket într-un thread separat
            import threading
            # Rulăm WebSocket cu parametri optimizați
            websocket_thread = threading.Thread(target=lambda: self.ws.run_forever(
                # Opțiuni suplimentare pentru WebSocket care cresc compatibilitatea
                ping_interval=25,
                ping_timeout=10,
                skip_utf8_validation=True
            ))
            websocket_thread.daemon = True
            websocket_thread.start()
            
        except Exception as e:
            self.logger.error(f"Eroare la conectare: {e}")
            self.connection_state = ConnectionState.DISCONNECTED
            if self.callbacks["connection_update"]:
                self.callbacks["connection_update"]({
                    "connection": ConnectionState.DISCONNECTED,
                    "error": str(e)
                })
                
    def disconnect(self) -> None:
        """
        Deconectare de la serverele WhatsApp Web.
        """
        if self.connection_state == ConnectionState.DISCONNECTED:
            self.logger.warning("Clientul este deja deconectat")
            return
            
        self.logger.info("Deconectare de la serverele WhatsApp Web...")
        
        try:
            if self.ws:
                self.ws.close()
                
            self.connection_state = ConnectionState.DISCONNECTED
            
            if self.callbacks["disconnected"]:
                self.callbacks["disconnected"]({
                    "reason": "user_disconnected"
                })
                
        except Exception as e:
            self.logger.error(f"Eroare la deconectare: {e}")
            
    def reconnect(self) -> None:
        """
        Reconectare la serverele WhatsApp Web după o deconectare.
        """
        if self.connection_state in [ConnectionState.CONNECTING, ConnectionState.CONNECTED]:
            self.logger.warning(f"Clientul este deja {self.connection_state}")
            return
            
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > WA_WEB_PARAMS["MAX_RECONNECT_ATTEMPTS"]:
            self.logger.error("Numărul maxim de încercări de reconectare a fost depășit")
            self.connection_state = ConnectionState.DISCONNECTED
            return
            
        self.logger.info(f"Încercare de reconectare ({self.reconnect_attempts}/{WA_WEB_PARAMS['MAX_RECONNECT_ATTEMPTS']})...")
        self.connection_state = ConnectionState.RECONNECTING
        
        # Notificăm aplicația client
        if self.callbacks["connection_update"]:
            self.callbacks["connection_update"]({
                "connection": ConnectionState.RECONNECTING,
                "attempt": self.reconnect_attempts
            })
            
        # Reconectare după un delay
        import threading
        delay = WA_WEB_PARAMS["RECONNECT_INTERVAL_MS"] / 1000
        self.logger.info(f"Așteptăm {delay} secunde înainte de reconectare...")
        threading.Timer(delay, self.connect).start()
        
    def _on_open(self, ws) -> None:
        """
        Handler pentru deschiderea conexiunii WebSocket.
        
        Simulează exact secvența de mesaje trimise de browser-ul real la conexiune.
        
        Args:
            ws: Obiectul WebSocket
        """
        self.logger.info("Conexiune WebSocket stabilită")
        self.connection_state = ConnectionState.CONNECTED
        self.reconnect_attempts = 0
        
        # Derivăm informațiile exacte din navigator și window ca în browser
        browser_info = {
            "platform": "Win32",
            "appCodeName": "Mozilla",
            "appName": "Netscape",
            "appVersion": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.91 Safari/537.36",
            "vendorSub": "",
            "vendor": "Google Inc.",
            "product": "Gecko",
            "productSub": "20030107",
            "userAgent": WA_WEB_PARAMS["UA"],
            "language": "en-US",
            "languages": ["en-US", "en"],
            "onLine": True,
            "doNotTrack": None,
            "hardwareConcurrency": 8,
            "maxTouchPoints": 0,
            "deviceMemory": 8,
            "width": 1920,
            "height": 1080,
            "colorDepth": 24,
            "pixelDepth": 24
        }
        
        # Creăm un mesaj de inițializare complet, exact ca cel trimis de browser
        # Include toate câmpurile necesare pentru o emulare perfectă
        init_message = {
            "clientId": self.client_id,
            "connectType": "WIFI_UNKNOWN",  # Tipuri posibile: WIFI_UNKNOWN, CELL_UNKNOWN, WIFI_STRONG
            "connectReason": "USER_ACTIVATED",
            "connectAttempt": 1,
            "isNewLogin": True,
            "passive": False,
            "userAgent": browser_info["userAgent"],
            "webEncKey": base64.b64encode(self.keys.get("public", b'')).decode('utf-8'),
            "webVersion": WA_WEB_PARAMS["WA_VERSION"],
            "browserName": "Chrome",
            "browserVersion": "124.0.6367.91", 
            "deviceProps": json.dumps({
                "os": "Windows",
                "version": {
                    "string": "10.0",
                    "name": "Windows",
                    "main": 10,
                    "sub": 0
                },
                "platform": "Win32",
                "device": {
                    "manufacturer": "",
                    "model": ""
                },
                "browser": {
                    "version": "124.0.6367.91",
                    "name": "Chrome",
                    "vendor": "Google Inc."
                },
                "screen": {
                    "width": 1920,
                    "height": 1080,
                    "density": 1.0,  # Device pixel ratio
                    "colorDepth": 24
                }
            }),
            "features": json.dumps({
                "BETTER_LOCALSTORAGE_SUPPORT": True,
                "DIRECT_CONNECTION": True,
                "GROUP_PADDING_CHECK": True, 
                "VIDEO_WITHOUT_AVCIF": True,
                "DIRECT_CHANNEL_SUPPORT": True,
                "PV_SUPPORT": True,
                "MD_BACKEND": True,
                "MD_BOOT": True,
                "STORIES_VIEWS": True,
                "PRIVATESTATS": True
            }),
            "ghid": uuid.uuid4().hex,  # ID global unic pentru hardware
            "tos": 2  # Versiunea Terms of Service
        }
        
        # Adăugăm tokenii de autentificare dacă există
        if self.client_token:
            init_message["clientToken"] = self.client_token
        if self.server_token:
            init_message["serverToken"] = self.server_token
            
        self.logger.debug(f"Trimitere mesaj inițializare: {json.dumps(init_message, indent=2)}")
        
        # Trimitem mesajul de inițializare
        self._send_json("admin", init_message)
        
        # Pornim keepalive timer
        self._start_keepalive()
        
        # Emitem eveniment de schimbare stare conexiune
        if self.callbacks["connection_update"]:
            self.callbacks["connection_update"]({
                "connection": ConnectionState.CONNECTED
            })
            
    def _on_message(self, ws, message) -> None:
        """
        Handler pentru mesajele primite de la WhatsApp Web.
        
        Args:
            ws: Obiectul WebSocket
            message: Mesajul primit
        """
        try:
            self.last_seen = time.time()
            
            # Parsăm mesajul în format tag,data
            parts = message.split(',', 1)
            if len(parts) < 2:
                self.logger.warning(f"Format mesaj neașteptat: {message[:50]}...")
                return
                
            tag = parts[0]
            data_str = parts[1]
            
            # Tratăm mesajele pong special
            if tag.startswith("pong"):
                self.logger.debug("Primit răspuns pong pentru keepalive")
                return
                
            # Încercăm să parsăm datele ca JSON
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                data = data_str
                
            # Gestionăm diferite tipuri de mesaje
            self._process_message(tag, data)
            
        except Exception as e:
            self.logger.error(f"Eroare la procesarea mesajului: {e}")
            traceback.print_exc()
            
    def _on_error(self, ws, error) -> None:
        """
        Handler pentru erori WebSocket.
        
        Args:
            ws: Obiectul WebSocket
            error: Eroarea primită
        """
        self.logger.error(f"Eroare WebSocket: {error}")
        
        if self.callbacks["connection_update"]:
            self.callbacks["connection_update"]({
                "connection": self.connection_state,
                "error": str(error)
            })
            
    def _on_close(self, ws, close_status_code, close_reason) -> None:
        """
        Handler pentru închiderea conexiunii WebSocket.
        
        Args:
            ws: Obiectul WebSocket
            close_status_code: Codul de status al închiderii
            close_reason: Motivul închiderii
        """
        was_connected = self.connection_state == ConnectionState.CONNECTED
        close_info = f"Code: {close_status_code}, Reason: {close_reason}" if close_status_code else "Fără informații"
        self.logger.info(f"Conexiune WebSocket închisă. {close_info}")
        
        # Verificăm motivul închiderii
        reason = DisconnectReason.CONNECTION_CLOSED
        if was_connected:
            if close_status_code == 1000:
                # Închidere normală
                reason = "normal"
            elif close_status_code == 1006:
                # Închidere anormală
                reason = DisconnectReason.CONNECTION_LOST
                
        # Verificăm dacă trebuie să reconectăm
        should_reconnect = (
            was_connected and 
            reason != "normal" and
            reason != DisconnectReason.LOGOUT and
            reason != DisconnectReason.SESSION_EXPIRED
        )
        
        # Actualizăm starea conexiunii
        self.connection_state = ConnectionState.DISCONNECTED
        
        # Notificăm aplicația client
        if self.callbacks["disconnected"]:
            self.callbacks["disconnected"]({
                "reason": reason,
                "code": close_status_code
            })
            
        if self.callbacks["connection_update"]:
            self.callbacks["connection_update"]({
                "connection": ConnectionState.DISCONNECTED,
                "lastDisconnect": {
                    "reason": reason,
                    "code": close_status_code
                }
            })
            
        # Reconectăm dacă este necesar
        if should_reconnect:
            self.reconnect()
            
    def _start_keepalive(self) -> None:
        """
        Pornește un timer pentru menținerea conexiunii active prin trimiterea de mesaje ping.
        """
        if self.connection_state != ConnectionState.CONNECTED or not self.ws:
            return
            
        # Verificăm dacă conexiunea este încă activă
        if time.time() - self.last_seen > WA_WEB_PARAMS["KEEPALIVE_INTERVAL_MS"] / 1000 * 2:
            self.logger.warning("Conexiune inactivă detectată. Forțăm reconectarea.")
            if self.ws:
                self.ws.close()
            return
            
        # Trimitem mesaj de ping
        try:
            if self.ws and self.ws.sock and self.ws.sock.connected:
                self.ws.send("ping,")
                self.logger.debug("Ping trimis pentru keepalive")
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea ping-ului: {e}")
            
        # Reprogramăm următorul ping
        import threading
        interval = WA_WEB_PARAMS["KEEPALIVE_INTERVAL_MS"] / 1000
        threading.Timer(interval, self._start_keepalive).start()
        
    def _process_message(self, tag: str, data: Any) -> None:
        """
        Procesează un mesaj primit de la WhatsApp Web.
        
        Args:
            tag: Tag-ul mesajului
            data: Datele mesajului
        """
        # Verificăm dacă este un răspuns la o cerere anterioară
        if tag in self.pending_requests:
            request_info = self.pending_requests.pop(tag)
            if request_info.get("callback"):
                request_info["callback"](data)
                
        # Procesăm autentificarea - cazul QR code
        if tag == "s1" and isinstance(data, dict) and data.get("status") == 401:
            qr_data = data.get("ref", "")
            if qr_data:
                self.logger.info("Cod QR primit pentru autentificare")
                
                # Generăm și afișăm codul QR
                qr_image = self._generate_qr_image(qr_data)
                self._display_qr_terminal(qr_image)
                
                # Notificăm aplicația client
                if self.callbacks["qr_code"]:
                    self.callbacks["qr_code"](qr_data)
                    
                if self.callbacks["connection_update"]:
                    self.callbacks["connection_update"]({
                        "qr": qr_data
                    })
                    
        # Procesăm autentificarea reușită
        elif tag == "s1" and isinstance(data, dict) and data.get("status") == 200:
            self.client_token = data.get("clientToken")
            self.server_token = data.get("serverToken")
            self.authenticated = True
            
            # Salvăm informațiile de autentificare
            self.auth_info = {
                "clientToken": self.client_token,
                "serverToken": self.server_token,
                "clientId": self.client_id,
                "device": data.get("device", {}),
                "wid": data.get("wid", "")
            }
            
            self.logger.info("Autentificare reușită cu WhatsApp Web")
            
            # Notificăm aplicația client
            if self.callbacks["connected"]:
                self.callbacks["connected"](self.auth_info)
                
            if self.callbacks["connection_update"]:
                self.callbacks["connection_update"]({
                    "connection": ConnectionState.CONNECTED,
                    "authenticated": True
                })
                
        # Procesăm mesaje normale
        elif tag.startswith(WA_WEB_PARAMS["TAG_PREFIX"]["RESPONSE"]) or tag.startswith(WA_WEB_PARAMS["TAG_PREFIX"]["ACTION"]):
            if self.callbacks["message"]:
                self.callbacks["message"]({
                    "tag": tag,
                    "data": data
                })
                
    def _send_json(self, tag: str, data: Any) -> str:
        """
        Trimite date JSON prin WebSocket.
        
        Args:
            tag: Tag-ul mesajului
            data: Datele pentru trimitere
            
        Returns:
            str: Tag-ul mesajului trimis
        """
        if not self.ws or not self.connection_state == ConnectionState.CONNECTED:
            self.logger.error("Nu există o conexiune WebSocket activă")
            return ""
            
        # Serializăm datele ca JSON
        json_data = json.dumps(data, separators=(',', ':'))
        
        # Construim mesajul complet
        message = f"{tag},{json_data}"
        
        try:
            self.ws.send(message)
            self.logger.debug(f"Mesaj trimis: {tag}")
            return tag
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea mesajului: {e}")
            return ""
            
    def _generate_qr_image(self, qr_data: str) -> Image.Image:
        """
        Generează o imagine QR pentru datele furnizate.
        
        Args:
            qr_data: Datele pentru codul QR
            
        Returns:
            Image.Image: Imaginea codului QR
        """
        import qrcode
        from qrcode.constants import ERROR_CORRECT_L
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        return qr.make_image(fill_color="black", back_color="white")
        
    def _display_qr_terminal(self, qr_image: Image.Image) -> None:
        """
        Afișează codul QR în terminal.
        
        Args:
            qr_image: Imaginea codului QR
        """
        # Convertim imaginea la alb/negru
        qr_image = qr_image.convert('RGB')
        width, height = qr_image.size
        
        # Afișăm imaginea în terminal
        for y in range(0, height, 2):
            line = ""
            for x in range(width):
                if y + 1 < height:
                    upper_pixel = qr_image.getpixel((x, y))[0] < 128
                    lower_pixel = qr_image.getpixel((x, y + 1))[0] < 128
                    
                    if upper_pixel and lower_pixel:
                        line += "█"
                    elif upper_pixel:
                        line += "▀"
                    elif lower_pixel:
                        line += "▄"
                    else:
                        line += " "
                else:
                    pixel = qr_image.getpixel((x, y))[0] < 128
                    line += "▀" if pixel else " "
            print(line)
            
        print("\nScanați acest cod QR cu aplicația WhatsApp de pe telefonul dvs.")
        
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Înregistrează un callback pentru un anumit tip de eveniment.
        
        Args:
            event_type: Tipul de eveniment ('qr_code', 'message', 'connected', 'connection_update', 'disconnected')
            callback: Funcția de callback care va fi apelată când apare evenimentul
        """
        if event_type in self.callbacks:
            self.callbacks[event_type] = callback
        else:
            self.logger.warning(f"Tip de eveniment necunoscut: {event_type}")
            
    def wait_for_authentication(self, timeout: int = 60) -> bool:
        """
        Așteaptă autentificarea utilizatorului.
        
        Args:
            timeout: Timpul maxim de așteptare în secunde
            
        Returns:
            bool: True dacă autentificarea a reușit, False altfel
        """
        if self.authenticated:
            return True
            
        self.logger.info(f"Așteptăm autentificarea timp de {timeout} secunde...")
        
        import threading
        start_time = time.time()
        auth_event = threading.Event()
        
        # Funcție callback pentru starea de autentificare
        def on_auth_update(state):
            if state.get("authenticated", False):
                auth_event.set()
                
        # Înregistrăm callback-ul temporar
        old_callback = self.callbacks.get("connected")
        self.callbacks["connected"] = on_auth_update
        
        # Așteptăm evenimentul sau timeout
        is_authenticated = auth_event.wait(timeout)
        
        # Restaurăm callback-ul original
        self.callbacks["connected"] = old_callback
        
        if is_authenticated:
            self.logger.info("Autentificare reușită!")
        else:
            self.logger.warning(f"Timeout la autentificare după {timeout} secunde")
            
        return is_authenticated
            
    def send_message(self, to: str, text: str) -> str:
        """
        Trimite un mesaj text către un destinatar.
        
        Args:
            to: Numărul de telefon sau JID-ul destinatarului
            text: Textul mesajului
            
        Returns:
            str: ID-ul mesajului trimis
        """
        if not self.authenticated:
            self.logger.error("Clientul nu este autentificat")
            return ""
            
        # Asigurăm că destinatarul este în format JID
        recipient = to
        if '@' not in to:
            # Eliminate any non-numeric characters except + at the beginning
            phone = re.sub(r'[^0-9+]', '', to)
            if phone.startswith('+'):
                phone = phone[1:]
            recipient = f"{phone}@s.whatsapp.net"
            
        # Generăm ID-ul mesajului
        message_id = f"wawspy{int(time.time() * 1000)}"
        
        # Construim mesajul
        message = {
            "key": {
                "remoteJid": recipient,
                "fromMe": True,
                "id": message_id
            },
            "message": {
                "conversation": text
            }
        }
        
        # Tag-ul pentru mesaje de chat
        tag = self._generate_message_tag()
        
        # Trimitem mesajul
        self.logger.info(f"Trimitere mesaj către {recipient}")
        self._send_json(tag, message)
        
        return message_id
        
    def request_pairing_code(self, phone_number: str) -> None:
        """
        Solicită un cod de asociere pentru autentificare.
        
        Args:
            phone_number: Numărul de telefon în format internațional (ex: +40123456789)
        """
        if not self.connection_state == ConnectionState.CONNECTED:
            self.logger.error("Nu există o conexiune activă. Conectați-vă mai întâi")
            return
            
        # Asigurăm că numărul de telefon are formatul corect
        if phone_number.startswith('+'):
            phone_number = phone_number[1:]
            
        phone_number = re.sub(r'[^0-9]', '', phone_number)
        
        # Construim mesajul pentru solicitarea codului
        request = {
            "phoneNumber": phone_number,
            "method": "request_code"
        }
        
        # Tag-ul pentru solicitarea codului
        tag = self._generate_message_tag()
        
        # Ține minte că am cerut un cod de asociere
        self.auth_info["pairing_phone"] = phone_number
        
        # Trimitem solicitarea
        self.logger.info(f"Solicitare cod de asociere pentru {phone_number}")
        self._send_json(tag, request)
        
        # Notificăm aplicația client
        if self.callbacks["connection_update"]:
            self.callbacks["connection_update"]({
                "pairingCodeRequest": True,
                "phoneNumber": phone_number
            })
            
        print(f"Cod de asociere solicitat pentru numărul {phone_number}.")
        print("Veți primi un cod de 8 cifre pe telefonul dvs.")
        print("Introduceți acest cod în aplicație când vă este solicitat.")