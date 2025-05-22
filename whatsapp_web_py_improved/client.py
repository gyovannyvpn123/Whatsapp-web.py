"""
Client WhatsApp Web îmbunătățit.

Acest modul furnizează interfața principală pentru interacțiunea cu WhatsApp Web,
cu focus pe stabilitatea conexiunii WebSocket și gestionarea media.
"""

import asyncio
import json
import logging
import os
import qrcode
import tempfile
import time
from io import BytesIO
from typing import Dict, List, Optional, Callable, Any, Union, Tuple

from .connection import WAConnection
from .media import WAMedia
from .events import EventEmitter, WAEventType
from .constants import MediaType, ConnectionState, MessageStatus
from .exceptions import (
    WAConnectionError, 
    WAAuthenticationError, 
    WAMessageError, 
    WAMediaError
)
from .utils import (
    get_logger, 
    phone_number_to_jid, 
    jid_to_phone
)

class WAClient:
    """
    Client WhatsApp Web îmbunătățit cu conexiune WebSocket stabilă și gestionare media avansată.
    
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
        self.event_emitter = EventEmitter()
        self.connection = WAConnection(self.event_emitter)
        self.media = WAMedia(self)
        
        # Informații client
        self.user_info = None
        self.contacts = {}
        self.chats = {}
        
        # Stare autentificare
        self.qr_code = None
        self._authenticated = False
        
        # Configurare evenimente
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Configurează handler-ele pentru evenimente interne."""
        # Handler pentru cod QR
        self.event_emitter.on(WAEventType.QR_CODE, self._handle_qr_code)
        
        # Handler pentru autentificare
        self.event_emitter.on(WAEventType.AUTHENTICATED, self._handle_authentication)
        
        # Handler pentru mesaje
        self.event_emitter.on(WAEventType.MESSAGE_RECEIVED, self._handle_message)
        
        # Handler pentru starea conexiunii
        self.event_emitter.on(WAEventType.CONNECTION_STATE, self._handle_connection_state)
    
    async def connect(self) -> bool:
        """
        Conectare la WhatsApp Web.
        
        Returns:
            bool: True dacă conexiunea a fost stabilită cu succes, False altfel
            
        Raises:
            WAConnectionError: Dacă apare o eroare la conexiune
        """
        self.logger.info("Conectare la WhatsApp Web...")
        return await self.connection.connect()
    
    async def disconnect(self) -> None:
        """
        Deconectare de la WhatsApp Web.
        """
        self.logger.info("Deconectare de la WhatsApp Web...")
        await self.connection.disconnect()
    
    async def wait_for_connection(self, timeout: int = 60) -> bool:
        """
        Așteaptă stabilirea conexiunii.
        
        Args:
            timeout: Timpul maxim de așteptare în secunde
            
        Returns:
            bool: True dacă s-a conectat în timpul specificat, False altfel
        """
        start_time = time.time()
        while not self.connection.is_connected and time.time() - start_time < timeout:
            await asyncio.sleep(0.5)
        
        return self.connection.is_connected
    
    async def wait_for_authentication(self, timeout: int = 120) -> bool:
        """
        Așteaptă finalizarea autentificării.
        
        Args:
            timeout: Timpul maxim de așteptare în secunde
            
        Returns:
            bool: True dacă s-a autentificat în timpul specificat, False altfel
        """
        start_time = time.time()
        while not self._authenticated and time.time() - start_time < timeout:
            await asyncio.sleep(0.5)
        
        return self._authenticated
    
    def register_callback(self, event_type: WAEventType, callback: Callable) -> None:
        """
        Înregistrează un callback pentru un anumit tip de eveniment.
        
        Args:
            event_type: Tipul de eveniment pentru care se înregistrează callback-ul
            callback: Funcția de callback care va fi apelată la emiterea evenimentului
        """
        self.event_emitter.on(event_type, callback)
        self.logger.debug(f"Înregistrat callback pentru evenimentul {event_type.value}")
    
    def register_once_callback(self, event_type: WAEventType, callback: Callable) -> None:
        """
        Înregistrează un callback care va fi apelat o singură dată pentru un anumit tip de eveniment.
        
        Args:
            event_type: Tipul de eveniment pentru care se înregistrează callback-ul
            callback: Funcția de callback care va fi apelată o singură dată la emiterea evenimentului
        """
        self.event_emitter.once(event_type, callback)
        self.logger.debug(f"Înregistrat callback 'once' pentru evenimentul {event_type.value}")
    
    def unregister_callback(self, event_type: WAEventType, callback: Optional[Callable] = None) -> None:
        """
        Elimină un callback pentru un anumit tip de eveniment.
        
        Args:
            event_type: Tipul de eveniment pentru care se elimină callback-ul
            callback: Funcția de callback de eliminat. Dacă este None, se elimină toate callback-urile pentru eveniment.
        """
        self.event_emitter.off(event_type, callback)
        self.logger.debug(f"Eliminat callback pentru evenimentul {event_type.value}")
    
    async def send_message(self, to: str, text: str, quoted_msg_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Trimite un mesaj text.
        
        Args:
            to: Numărul de telefon sau JID-ul destinatarului
            text: Textul mesajului de trimis
            quoted_msg_id: ID-ul opțional al mesajului citat/răspuns
            
        Returns:
            dict: Informații despre mesajul trimis
            
        Raises:
            WAMessageError: Dacă apare o eroare la trimiterea mesajului
        """
        if not self._authenticated:
            raise WAMessageError("Nu sunteți autentificat")
        
        try:
            # Asigurăm că destinatarul este în format JID
            if '@' not in to:
                to = phone_number_to_jid(to)
            
            # Construim mesajul
            message = {
                "text": text,
                "to": to,
                "type": "text"
            }
            
            if quoted_msg_id:
                message["quotedMessageId"] = quoted_msg_id
            
            # Trimitem mesajul prin conexiunea WebSocket
            msg_id = f"msg_{int(time.time() * 1000)}"
            self.logger.info(f"Trimitere mesaj către {to}")
            
            # În implementarea reală, aici s-ar trimite efectiv mesajul prin conexiunea WebSocket
            # și s-ar aștepta confirmarea de la server
            
            # Pentru ilustrare, vom presupune că mesajul a fost trimis cu succes
            result = {
                "id": msg_id,
                "to": to,
                "text": text,
                "timestamp": time.time(),
                "status": MessageStatus.SENT
            }
            
            # Emitem evenimentul de mesaj trimis
            self.event_emitter.emit(WAEventType.MESSAGE_SENT, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea mesajului: {e}")
            raise WAMessageError(f"Eroare la trimiterea mesajului: {e}")
    
    async def send_image(self, to: str, image_path: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """
        Trimite un mesaj cu imagine.
        
        Args:
            to: Numărul de telefon sau JID-ul destinatarului
            image_path: Calea către fișierul imagine
            caption: Textul opțional pentru imagine
            
        Returns:
            dict: Informații despre mesajul trimis
            
        Raises:
            WAMediaError: Dacă apare o eroare cu media
            WAMessageError: Dacă apare o eroare la trimiterea mesajului
        """
        if not self._authenticated:
            raise WAMessageError("Nu sunteți autentificat")
        
        try:
            # Asigurăm că destinatarul este în format JID
            if '@' not in to:
                to = phone_number_to_jid(to)
            
            # Încărcăm media
            self.logger.info(f"Pregătire pentru trimiterea imaginii către {to}")
            media_info = await self.media.upload_media(image_path)
            
            # Construim mesajul
            message = {
                "to": to,
                "type": MediaType.IMAGE,
                "url": media_info["url"],
                "mimetype": media_info["mimetype"],
                "caption": caption,
                "mediaKey": media_info["mediaKey"],
                "filesize": media_info["filesize"]
            }
            
            # Adăugăm dimensiunile imaginii dacă sunt disponibile
            if "width" in media_info and "height" in media_info:
                message["width"] = media_info["width"]
                message["height"] = media_info["height"]
            
            # Trimitem mesajul prin conexiunea WebSocket
            msg_id = f"img_{int(time.time() * 1000)}"
            self.logger.info(f"Trimitere imagine către {to}")
            
            # În implementarea reală, aici s-ar trimite efectiv mesajul prin conexiunea WebSocket
            # și s-ar aștepta confirmarea de la server
            
            # Pentru ilustrare, vom presupune că mesajul a fost trimis cu succes
            result = {
                "id": msg_id,
                "to": to,
                "caption": caption,
                "type": MediaType.IMAGE,
                "media": media_info,
                "timestamp": time.time(),
                "status": MessageStatus.SENT
            }
            
            # Emitem evenimentul de mesaj trimis
            self.event_emitter.emit(WAEventType.MESSAGE_SENT, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea imaginii: {e}")
            if isinstance(e, WAMediaError):
                raise
            raise WAMessageError(f"Eroare la trimiterea imaginii: {e}")
    
    async def send_document(self, to: str, document_path: str, caption: Optional[str] = None, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Trimite un document.
        
        Args:
            to: Numărul de telefon sau JID-ul destinatarului
            document_path: Calea către fișierul document
            caption: Textul opțional pentru document
            filename: Numele opțional pentru fișier
            
        Returns:
            dict: Informații despre mesajul trimis
            
        Raises:
            WAMediaError: Dacă apare o eroare cu media
            WAMessageError: Dacă apare o eroare la trimiterea mesajului
        """
        if not self._authenticated:
            raise WAMessageError("Nu sunteți autentificat")
        
        try:
            # Asigurăm că destinatarul este în format JID
            if '@' not in to:
                to = phone_number_to_jid(to)
            
            # Utilizăm numele original al fișierului dacă nu este specificat
            if not filename:
                filename = os.path.basename(document_path)
            
            # Încărcăm media
            self.logger.info(f"Pregătire pentru trimiterea documentului către {to}")
            media_info = await self.media.upload_media(document_path)
            
            # Construim mesajul
            message = {
                "to": to,
                "type": MediaType.DOCUMENT,
                "url": media_info["url"],
                "mimetype": media_info["mimetype"],
                "caption": caption,
                "fileName": filename,
                "mediaKey": media_info["mediaKey"],
                "filesize": media_info["filesize"]
            }
            
            # Trimitem mesajul prin conexiunea WebSocket
            msg_id = f"doc_{int(time.time() * 1000)}"
            self.logger.info(f"Trimitere document către {to}")
            
            # În implementarea reală, aici s-ar trimite efectiv mesajul prin conexiunea WebSocket
            # și s-ar aștepta confirmarea de la server
            
            # Pentru ilustrare, vom presupune că mesajul a fost trimis cu succes
            result = {
                "id": msg_id,
                "to": to,
                "caption": caption,
                "filename": filename,
                "type": MediaType.DOCUMENT,
                "media": media_info,
                "timestamp": time.time(),
                "status": MessageStatus.SENT
            }
            
            # Emitem evenimentul de mesaj trimis
            self.event_emitter.emit(WAEventType.MESSAGE_SENT, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea documentului: {e}")
            if isinstance(e, WAMediaError):
                raise
            raise WAMessageError(f"Eroare la trimiterea documentului: {e}")
    
    async def send_video(self, to: str, video_path: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """
        Trimite un videoclip.
        
        Args:
            to: Numărul de telefon sau JID-ul destinatarului
            video_path: Calea către fișierul video
            caption: Textul opțional pentru videoclip
            
        Returns:
            dict: Informații despre mesajul trimis
            
        Raises:
            WAMediaError: Dacă apare o eroare cu media
            WAMessageError: Dacă apare o eroare la trimiterea mesajului
        """
        if not self._authenticated:
            raise WAMessageError("Nu sunteți autentificat")
        
        try:
            # Asigurăm că destinatarul este în format JID
            if '@' not in to:
                to = phone_number_to_jid(to)
            
            # Încărcăm media
            self.logger.info(f"Pregătire pentru trimiterea videoclipului către {to}")
            media_info = await self.media.upload_media(video_path)
            
            # Construim mesajul
            message = {
                "to": to,
                "type": MediaType.VIDEO,
                "url": media_info["url"],
                "mimetype": media_info["mimetype"],
                "caption": caption,
                "mediaKey": media_info["mediaKey"],
                "filesize": media_info["filesize"]
            }
            
            # Trimitem mesajul prin conexiunea WebSocket
            msg_id = f"vid_{int(time.time() * 1000)}"
            self.logger.info(f"Trimitere videoclip către {to}")
            
            # În implementarea reală, aici s-ar trimite efectiv mesajul prin conexiunea WebSocket
            # și s-ar aștepta confirmarea de la server
            
            # Pentru ilustrare, vom presupune că mesajul a fost trimis cu succes
            result = {
                "id": msg_id,
                "to": to,
                "caption": caption,
                "type": MediaType.VIDEO,
                "media": media_info,
                "timestamp": time.time(),
                "status": MessageStatus.SENT
            }
            
            # Emitem evenimentul de mesaj trimis
            self.event_emitter.emit(WAEventType.MESSAGE_SENT, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea videoclipului: {e}")
            if isinstance(e, WAMediaError):
                raise
            raise WAMessageError(f"Eroare la trimiterea videoclipului: {e}")
    
    async def send_audio(self, to: str, audio_path: str) -> Dict[str, Any]:
        """
        Trimite un mesaj audio.
        
        Args:
            to: Numărul de telefon sau JID-ul destinatarului
            audio_path: Calea către fișierul audio
            
        Returns:
            dict: Informații despre mesajul trimis
            
        Raises:
            WAMediaError: Dacă apare o eroare cu media
            WAMessageError: Dacă apare o eroare la trimiterea mesajului
        """
        if not self._authenticated:
            raise WAMessageError("Nu sunteți autentificat")
        
        try:
            # Asigurăm că destinatarul este în format JID
            if '@' not in to:
                to = phone_number_to_jid(to)
            
            # Încărcăm media
            self.logger.info(f"Pregătire pentru trimiterea audio către {to}")
            media_info = await self.media.upload_media(audio_path)
            
            # Construim mesajul
            message = {
                "to": to,
                "type": MediaType.AUDIO,
                "url": media_info["url"],
                "mimetype": media_info["mimetype"],
                "mediaKey": media_info["mediaKey"],
                "filesize": media_info["filesize"]
            }
            
            # Trimitem mesajul prin conexiunea WebSocket
            msg_id = f"aud_{int(time.time() * 1000)}"
            self.logger.info(f"Trimitere audio către {to}")
            
            # În implementarea reală, aici s-ar trimite efectiv mesajul prin conexiunea WebSocket
            # și s-ar aștepta confirmarea de la server
            
            # Pentru ilustrare, vom presupune că mesajul a fost trimis cu succes
            result = {
                "id": msg_id,
                "to": to,
                "type": MediaType.AUDIO,
                "media": media_info,
                "timestamp": time.time(),
                "status": MessageStatus.SENT
            }
            
            # Emitem evenimentul de mesaj trimis
            self.event_emitter.emit(WAEventType.MESSAGE_SENT, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea audio: {e}")
            if isinstance(e, WAMediaError):
                raise
            raise WAMessageError(f"Eroare la trimiterea audio: {e}")
    
    async def download_media_from_message(self, message: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Descarcă media dintr-un mesaj primit.
        
        Args:
            message: Mesajul conținând media
            output_path: Calea opțională pentru salvarea media
            
        Returns:
            str: Calea către fișierul media descărcat
            
        Raises:
            WAMediaError: Dacă apare o eroare la descărcarea media
        """
        try:
            # Procesăm mesajul pentru a ne asigura că informațiile media sunt disponibile
            processed_message = await self.media.process_media_message(message)
            
            # Descărcăm media
            if "mediaInfo" not in processed_message:
                raise WAMediaError("Mesajul nu conține media")
                
            return await self.media.download_media(processed_message["mediaInfo"], output_path)
            
        except Exception as e:
            self.logger.error(f"Eroare la descărcarea media: {e}")
            if isinstance(e, WAMediaError):
                raise
            raise WAMediaError(f"Eroare la descărcarea media: {e}")
    
    async def get_contacts(self) -> Dict[str, Dict[str, Any]]:
        """
        Obține lista de contacte.
        
        Returns:
            dict: Dicționar de contacte
            
        Raises:
            WAConnectionError: Dacă nu există o conexiune activă
        """
        if not self.connection.is_connected:
            raise WAConnectionError("Nu există o conexiune activă")
            
        if not self._authenticated:
            raise WAAuthenticationError("Nu sunteți autentificat")
            
        # În implementarea reală, aici s-ar obține efectiv lista de contacte de la server
        # Pentru ilustrare, vom returna dicționarul de contacte existent
        return self.contacts
    
    async def get_chats(self) -> Dict[str, Dict[str, Any]]:
        """
        Obține lista de conversații.
        
        Returns:
            dict: Dicționar de conversații
            
        Raises:
            WAConnectionError: Dacă nu există o conexiune activă
        """
        if not self.connection.is_connected:
            raise WAConnectionError("Nu există o conexiune activă")
            
        if not self._authenticated:
            raise WAAuthenticationError("Nu sunteți autentificat")
            
        # În implementarea reală, aici s-ar obține efectiv lista de conversații de la server
        # Pentru ilustrare, vom returna dicționarul de conversații existent
        return self.chats
    
    def _handle_qr_code(self, data: Dict[str, Any]) -> None:
        """
        Handler intern pentru evenimentul de cod QR.
        
        Args:
            data: Datele evenimentului
        """
        qr_data = data.get("qr", "")
        self.qr_code = qr_data
        self.logger.info("Cod QR primit pentru autentificare")
        
        # Afișăm codul QR în terminal dacă este disponibil
        if qr_data:
            qr = qrcode.QRCode()
            qr.add_data(qr_data)
            qr.print_ascii(invert=True)
            print(f"\nScanați acest cod QR cu WhatsApp pe telefonul dvs.")
            
        # Emitem evenimentul către callback-urile externe
        self.event_emitter.emit(WAEventType.QR_CODE, {
            "qrCode": qr_data
        })
    
    def _handle_authentication(self, data: Dict[str, Any]) -> None:
        """
        Handler intern pentru evenimentul de autentificare.
        
        Args:
            data: Datele evenimentului
        """
        self._authenticated = True
        self.user_info = data.get("user")
        self.logger.info("Autentificare reușită la WhatsApp Web")
        
        # Emitem evenimentul către callback-urile externe
        self.event_emitter.emit(WAEventType.AUTHENTICATED, {
            "user": self.user_info
        })
    
    def _handle_message(self, data: Dict[str, Any]) -> None:
        """
        Handler intern pentru evenimentul de mesaj primit.
        
        Args:
            data: Datele evenimentului
        """
        # În implementarea reală, aici s-ar procesa mesajul primit și s-ar actualiza
        # starea internă a conversațiilor și contactelor
        
        # Emitem evenimentul către callback-urile externe
        self.event_emitter.emit(WAEventType.MESSAGE_RECEIVED, data)
    
    def _handle_connection_state(self, data: Dict[str, Any]) -> None:
        """
        Handler intern pentru evenimentul de schimbare a stării conexiunii.
        
        Args:
            data: Datele evenimentului
        """
        old_state = data.get("old")
        new_state = data.get("new")
        
        self.logger.info(f"Stare conexiune schimbată: {old_state} -> {new_state}")
        
        # Gestionăm tranziții specifice de stare
        if new_state == ConnectionState.DISCONNECTED and self._authenticated:
            # Resetăm starea de autentificare la deconectare
            self._authenticated = False
            self.logger.info("Sesiune închisă, autentificare resetată")
        
        # Emitem evenimentul către callback-urile externe
        self.event_emitter.emit(WAEventType.CONNECTION_STATE, data)