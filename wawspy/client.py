"""
Client WhatsApp Web cu suport pentru protocol binar, criptare și autentificare avansată.

Acest modul furnizează interfața principală pentru interacțiunea cu WhatsApp Web,
cu focus pe stabilitatea conexiunii WebSocket și gestionarea media.
"""

import asyncio
import json
import logging
import os
import qrcode
import websocket
import time
from typing import Dict, List, Optional, Callable, Any, Union, Tuple

from .utils import get_logger, phone_number_to_jid, jid_to_phone, generate_message_tag
from .encryption import WAEncryption
from .auth import WAAuthentication
from .protocol import WANode
from .exceptions import (
    WAConnectionError,
    WAAuthenticationError,
    WAMessageError,
    WAMediaError,
    WATimeoutError
)

class WAClient:
    """
    Client WhatsApp Web cu suport pentru protocol binar, criptare și autentificare.
    
    Această clasă furnizează interfața principală pentru conectarea la WhatsApp Web și
    interacțiunea cu serviciul prin trimiterea și primirea mesajelor și media.
    """
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Inițializează clientul WhatsApp Web.
        
        Args:
            log_level: Nivelul de logging (implicit: INFO)
        """
        # Configurare logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        self.logger = get_logger("WAClient")
        self.ws = None
        self.authentication = WAAuthentication()
        self.encryption = WAEncryption()
        
        # State management
        self._connected = False
        self._authenticated = False
        
        # Callbacks
        self._on_message_callback = None
        self._on_qr_code_callback = None
        self._on_connected_callback = None
        self._on_disconnected_callback = None
        
        # Informații client
        self.user_info = None
        self.contacts = {}
        self.chats = {}
        
    @property
    def is_connected(self) -> bool:
        """Verifică dacă clientul este conectat la WhatsApp Web."""
        return self._connected and self.ws and self.ws.connected
        
    @property
    def is_authenticated(self) -> bool:
        """Verifică dacă clientul este autentificat cu WhatsApp Web."""
        return self._authenticated
        
    def connect(self) -> None:
        """
        Conectare la WhatsApp Web.
        
        Raises:
            WAConnectionError: Dacă apare o eroare la conexiune
        """
        if self.is_connected:
            self.logger.warning("Deja conectat la WhatsApp Web")
            return
            
        try:
            # URL-ul pentru conexiunea WebSocket
            websocket_url = "wss://web.whatsapp.com/ws"
            
            # Header-uri pentru conexiune
            headers = {
                "Origin": "https://web.whatsapp.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.177 Safari/537.36"
            }
            
            # Configurare WebSocket client
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp(
                websocket_url,
                header=headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Pornire conexiune WebSocket în thread separat
            self.logger.info("Conectare la WhatsApp Web...")
            self.ws.run_forever()
            
        except Exception as e:
            self.logger.error(f"Eroare la conexiune: {e}")
            raise WAConnectionError(f"Nu s-a putut stabili conexiunea: {e}")
    
    def disconnect(self) -> None:
        """
        Deconectare de la WhatsApp Web.
        """
        if not self.is_connected:
            self.logger.warning("Nu există o conexiune activă")
            return
            
        try:
            if self.ws:
                self.ws.close()
                
            self._connected = False
            self._authenticated = False
            self.logger.info("Deconectat de la WhatsApp Web")
            
        except Exception as e:
            self.logger.error(f"Eroare la deconectare: {e}")
    
    def wait_for_connection(self, timeout: int = 60) -> bool:
        """
        Așteaptă stabilirea conexiunii.
        
        Args:
            timeout: Timpul maxim de așteptare în secunde
            
        Returns:
            bool: True dacă s-a conectat în timpul specificat, False altfel
        """
        start_time = time.time()
        while not self.is_connected and time.time() - start_time < timeout:
            time.sleep(0.5)
        
        return self.is_connected
    
    def wait_for_authentication(self, timeout: int = 120) -> bool:
        """
        Așteaptă finalizarea autentificării.
        
        Args:
            timeout: Timpul maxim de așteptare în secunde
            
        Returns:
            bool: True dacă s-a autentificat în timpul specificat, False altfel
        """
        start_time = time.time()
        while not self.is_authenticated and time.time() - start_time < timeout:
            time.sleep(0.5)
        
        return self.is_authenticated
    
    def authenticate_with_qr(self, callback: Optional[Callable] = None) -> None:
        """
        Inițiază procesul de autentificare prin cod QR.
        
        Aceasta este metoda standard de autentificare cu WhatsApp Web,
        care necesită scanarea unui cod QR cu aplicația WhatsApp de pe telefon.
        
        Args:
            callback: Funcție opțională pentru primirea datelor codului QR
        """
        self._on_qr_code_callback = callback
        self.logger.info("Autentificare prin cod QR inițiată. Așteptând codul QR...")
    
    def authenticate_with_pairing_code(self, phone_number: str) -> str:
        """
        Inițiază procesul de autentificare prin cod de asociere (pairing code).
        
        Aceasta este o metodă alternativă de autentificare care nu necesită
        scanarea unui cod QR, ci introduce un cod numeric pe telefonul mobil.
        
        Args:
            phone_number: Numărul de telefon în format internațional (ex: +40123456789)
            
        Returns:
            str: Un mesaj care indică că procesul a fost inițiat
            
        Raises:
            WAAuthenticationError: Dacă apare o eroare la solicitarea codului
        """
        if not self.is_connected:
            raise WAConnectionError("Nu există o conexiune activă. Conectați-vă mai întâi")
            
        try:
            pairing_ref = self.authentication.request_pairing_code(phone_number)
            message = (
                f"Cod de asociere solicitat pentru numărul {phone_number}.\n"
                f"Veți primi un cod de 6 cifre pe telefonul dvs.\n"
                f"Utilizați metoda verify_pairing_code(cod) pentru a finaliza autentificarea."
            )
            self.logger.info(f"Autentificare prin cod de asociere inițiată pentru {phone_number}")
            return message
            
        except Exception as e:
            self.logger.error(f"Eroare la solicitarea codului de asociere: {e}")
            raise WAAuthenticationError(f"Nu s-a putut solicita codul de asociere: {e}")
    
    def verify_pairing_code(self, code: str) -> bool:
        """
        Verifică un cod de asociere introdus de utilizator.
        
        Args:
            code: Codul de asociere de 6 cifre
            
        Returns:
            bool: True dacă codul este valid și autentificarea a reușit, False altfel
            
        Raises:
            WAAuthenticationError: Dacă nu există o solicitare activă pentru cod de asociere
        """
        if not self.is_connected:
            raise WAConnectionError("Nu există o conexiune activă. Conectați-vă mai întâi")
            
        try:
            result = self.authentication.verify_pairing_code(code)
            
            if result:
                self._authenticated = True
                self.user_info = {
                    "auth_method": "pairing_code",
                    "timestamp": time.time()
                }
                
                self.logger.info("Autentificare reușită prin cod de asociere")
                
                # Notificăm callback-ul de conectare dacă există
                if self._on_connected_callback:
                    self._on_connected_callback(self.user_info)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Eroare la verificarea codului de asociere: {e}")
            raise WAAuthenticationError(f"Nu s-a putut verifica codul de asociere: {e}")
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Înregistrează un callback pentru un anumit tip de eveniment.
        
        Args:
            event_type: Tipul de eveniment ('message', 'qr_code', 'connected', 'disconnected')
            callback: Funcția de callback care va fi apelată la emiterea evenimentului
        """
        if event_type == 'message':
            self._on_message_callback = callback
        elif event_type == 'qr_code':
            self._on_qr_code_callback = callback
        elif event_type == 'connected':
            self._on_connected_callback = callback
        elif event_type == 'disconnected':
            self._on_disconnected_callback = callback
        else:
            self.logger.warning(f"Tip de eveniment necunoscut: {event_type}")
    
    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        """
        Trimite un mesaj text.
        
        Args:
            to: Numărul de telefon sau JID-ul destinatarului
            text: Textul mesajului de trimis
            
        Returns:
            dict: Informații despre mesajul trimis
            
        Raises:
            WAConnectionError: Dacă nu există o conexiune activă
            WAAuthenticationError: Dacă clientul nu este autentificat
            WAMessageError: Dacă apare o eroare la trimiterea mesajului
        """
        if not self.is_connected:
            raise WAConnectionError("Nu există o conexiune activă")
            
        if not self.is_authenticated:
            raise WAAuthenticationError("Clientul nu este autentificat")
            
        try:
            # Asigurăm că destinatarul este în format JID
            recipient = to if '@' in to else phone_number_to_jid(to)
            
            # Creăm nodul pentru mesaj
            message_node = WANode.create(
                "message",
                {
                    "id": generate_message_tag(),
                    "type": "text",
                    "to": recipient
                },
                WANode.create(
                    "body",
                    {},
                    text
                )
            )
            
            # Transformăm nodul în format binar și îl criptăm
            binary_data = WANode.encode(message_node)
            encrypted_data = self.encryption.encrypt_message(binary_data)
            
            # Trimitem mesajul
            tag = generate_message_tag()
            self.ws.send(f"{tag},{encrypted_data.hex()}")
            
            self.logger.info(f"Mesaj trimis către {recipient}")
            
            # Creăm un obiect cu informații despre mesajul trimis
            result = {
                "id": message_node["attrs"]["id"],
                "to": recipient,
                "text": text,
                "timestamp": time.time(),
                "status": "sent"
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea mesajului: {e}")
            raise WAMessageError(f"Nu s-a putut trimite mesajul: {e}")
    
    def _on_open(self, ws) -> None:
        """
        Handler pentru evenimentul de deschidere a conexiunii WebSocket.
        
        Args:
            ws: Obiectul WebSocket
        """
        self._connected = True
        self.logger.info("Conexiune WebSocket stabilită")
        
        # Trimitem mesajul de inițializare
        init_message = {
            "clientId": generate_message_tag(),
            "connectType": "WIFI_UNKNOWN",
            "connectReason": "USER_ACTIVATED",
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.177 Safari/537.36",
            "webVersion": "2.2402.7",
            "browserName": "Chrome",
            "browserVersion": "110.0.5481.177"
        }
        
        self.ws.send(f"admin,{json.dumps(init_message)}")
    
    def _on_message(self, ws, message) -> None:
        """
        Handler pentru mesajele primite prin WebSocket.
        
        Args:
            ws: Obiectul WebSocket
            message: Mesajul primit
        """
        try:
            # Parsăm mesajul în format tag,data
            parts = message.split(',', 1)
            if len(parts) < 2:
                self.logger.warning(f"Format mesaj neașteptat: {message[:50]}...")
                return
                
            tag = parts[0]
            data_str = parts[1]
            
            # Tratăm mesajele speciale
            
            # Mesaj de autentificare cu QR code
            if tag == "s1" and '"status":401' in data_str and '"ref":' in data_str:
                try:
                    data = json.loads(data_str)
                    qr_data = data.get("ref", "")
                    if qr_data:
                        qr_terminal = self.authentication.handle_qr_code(qr_data, self._on_qr_code_callback)
                        print("\nScanați codul QR de mai jos cu aplicația WhatsApp de pe telefonul dvs.:\n")
                        print(qr_terminal)
                except json.JSONDecodeError:
                    self.logger.error("Eroare la parsarea datelor QR")
                
            # Mesaj de succes la autentificare
            elif tag == "s1" and '"status":200' in data_str:
                try:
                    data = json.loads(data_str)
                    self._authenticated = True
                    self.authentication.handle_auth_success(data)
                    self.user_info = {
                        "auth_method": "qr_code",
                        "timestamp": time.time(),
                        "serverToken": data.get("serverToken"),
                        "clientToken": data.get("clientToken")
                    }
                    
                    self.logger.info("Autentificare reușită cu WhatsApp Web")
                    
                    # Notificăm callback-ul de conectare dacă există
                    if self._on_connected_callback:
                        self._on_connected_callback(self.user_info)
                        
                except json.JSONDecodeError:
                    self.logger.error("Eroare la parsarea datelor de autentificare")
            
            # Alte mesaje le trimitem către callback
            elif self._on_message_callback:
                try:
                    # Pentru mesajele criptate, le-am decripta aici
                    # În această implementare, tratăm doar mesajele în text
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        data = data_str
                        
                    self._on_message_callback({
                        "tag": tag,
                        "data": data
                    })
                except Exception as e:
                    self.logger.error(f"Eroare la procesarea mesajului pentru callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Eroare la procesarea mesajului: {e}")
    
    def _on_error(self, ws, error) -> None:
        """
        Handler pentru erori WebSocket.
        
        Args:
            ws: Obiectul WebSocket
            error: Eroarea primită
        """
        self.logger.error(f"Eroare WebSocket: {error}")
    
    def _on_close(self, ws, close_status_code, close_reason) -> None:
        """
        Handler pentru închiderea conexiunii WebSocket.
        
        Args:
            ws: Obiectul WebSocket
            close_status_code: Codul de status al închiderii
            close_reason: Motivul închiderii
        """
        self._connected = False
        close_info = f"Status: {close_status_code}, Motiv: {close_reason}" if close_status_code else "Fără informații"
        self.logger.info(f"Conexiune WebSocket închisă. {close_info}")
        
        # Resetăm starea de autentificare la deconectare
        if self._authenticated:
            self._authenticated = False
            self.authentication.reset()
            
        # Notificăm callback-ul de deconectare dacă există
        if self._on_disconnected_callback:
            self._on_disconnected_callback({
                "status_code": close_status_code,
                "reason": close_reason
            })