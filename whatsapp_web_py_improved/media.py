"""
Modul de gestionare a fișierelor media pentru biblioteca WhatsApp Web Python îmbunătățită.

Acest modul se ocupă de încărcarea, descărcarea și procesarea fișierelor media
cum ar fi imagini, videoclipuri, documente, audio și stickere.
"""

import asyncio
import base64
import hashlib
import json
import logging
import mimetypes
import os
import random
import time
from io import BytesIO
from typing import Dict, List, Optional, Any, Union, Tuple, BinaryIO

import aiohttp
from PIL import Image

from .constants import MediaType
from .exceptions import WAMediaError
from .utils import get_logger, generate_random_id

class WAMedia:
    """
    Manager de media pentru WhatsApp Web.
    
    Această clasă gestionează operațiunile legate de fișierele media,
    cum ar fi încărcarea, descărcarea și procesarea acestora.
    """
    
    # Dimensiuni maxime pentru diferite tipuri de media (în bytes)
    MAX_SIZE = {
        MediaType.IMAGE: 16 * 1024 * 1024,      # 16MB
        MediaType.VIDEO: 16 * 1024 * 1024,      # 16MB
        MediaType.AUDIO: 16 * 1024 * 1024,      # 16MB
        MediaType.DOCUMENT: 100 * 1024 * 1024,  # 100MB
        MediaType.STICKER: 1 * 1024 * 1024      # 1MB
    }
    
    # MIME types acceptate pentru fiecare tip de media
    MIME_TYPES = {
        MediaType.IMAGE: ["image/jpeg", "image/png", "image/gif", "image/webp"],
        MediaType.VIDEO: ["video/mp4", "video/3gpp", "video/quicktime", "video/x-msvideo"],
        MediaType.AUDIO: ["audio/aac", "audio/mp4", "audio/amr", "audio/mpeg", "audio/ogg", "audio/wav"],
        MediaType.DOCUMENT: ["application/pdf", "application/msword", "application/vnd.ms-excel",
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                          "text/plain", "application/zip"],
        MediaType.STICKER: ["image/webp"]
    }
    
    def __init__(self, client: Any):
        """
        Inițializează managerul de media.
        
        Args:
            client: Clientul WhatsApp Web pentru comunicarea cu serverul
        """
        self.logger = get_logger("WAMedia")
        self.client = client
        self.upload_url = "https://mmg.whatsapp.net/v/t62.7118-24/upload"
        self.media_conn_info = None
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
    async def determine_media_type(self, file_path: str) -> Tuple[str, str]:
        """
        Determină tipul de media și MIME type-ul bazat pe extensia fișierului.
        
        Args:
            file_path: Calea către fișierul media
            
        Returns:
            tuple: (media_type, mime_type)
            
        Raises:
            WAMediaError: Dacă tipul de fișier nu este suportat
        """
        # Determinăm MIME type-ul bazat pe extensie
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if not mime_type:
            # Încercăm să determinăm tipul bazat pe conținutul fișierului
            try:
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    # Verificăm primii bytes pentru a determina tipul
                    with open(file_path, 'rb') as f:
                        header = f.read(12)
                        
                    # Verificăm semnăturile comune
                    if header.startswith(b'\xFF\xD8\xFF'):  # JPEG
                        mime_type = "image/jpeg"
                    elif header.startswith(b'\x89PNG\r\n\x1A\n'):  # PNG
                        mime_type = "image/png"
                    elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):  # GIF
                        mime_type = "image/gif"
                    elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':  # WEBP
                        mime_type = "image/webp"
                    elif header.startswith(b'%PDF'):  # PDF
                        mime_type = "application/pdf"
                    else:
                        # Determinare bazată pe extensie ca fallback
                        ext = os.path.splitext(file_path)[1].lower()
                        if ext == '.docx':
                            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        elif ext == '.xlsx':
                            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        elif ext == '.pptx':
                            mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                        elif ext == '.mp3':
                            mime_type = "audio/mpeg"
                        elif ext == '.mp4':
                            mime_type = "video/mp4"
                        elif ext == '.txt':
                            mime_type = "text/plain"
                        else:
                            mime_type = "application/octet-stream"
            except Exception as e:
                self.logger.error(f"Eroare la determinarea tipului de fișier: {e}")
                mime_type = "application/octet-stream"
        
        # Determinăm tipul de media bazat pe MIME type
        if mime_type:
            for media_type, types in self.MIME_TYPES.items():
                if mime_type in types or mime_type.split('/')[0] in [t.split('/')[0] for t in types]:
                    return media_type, mime_type
        
        # Default la document dacă nu putem determina tipul
        if mime_type:
            return MediaType.DOCUMENT, mime_type
            
        raise WAMediaError(f"Tip de fișier nesuportat: {os.path.basename(file_path)}")
    
    async def prepare_media(self, file_path: str) -> Dict[str, Any]:
        """
        Pregătește media pentru trimitere calculând hash-uri și alte metadate.
        
        Args:
            file_path: Calea către fișierul media
            
        Returns:
            dict: Metadatele media inclusiv dimensiunea fișierului, hash-uri etc.
            
        Raises:
            WAMediaError: Dacă apare o eroare la pregătirea media
        """
        try:
            if not os.path.isfile(file_path):
                raise WAMediaError(f"Fișierul nu a fost găsit: {file_path}")
                
            file_size = os.path.getsize(file_path)
            media_type, mime_type = await self.determine_media_type(file_path)
            
            # Verificăm dimensiunea maximă
            if file_size > self.MAX_SIZE.get(media_type, 16 * 1024 * 1024):
                raise WAMediaError(f"Fișierul depășește dimensiunea maximă pentru {media_type}")
                
            # Calculăm hash-urile fișierului
            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                # Citim și actualizăm hash-ul în chunks pentru a evita încărcarea fișierelor mari în memorie
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
                    
            file_hash = sha256_hash.hexdigest()
            
            # Generăm cheia media (folosită pentru criptare în WhatsApp)
            media_key = os.urandom(32)
            media_key_base64 = base64.b64encode(media_key).decode('utf-8')
            
            # Determinăm dimensiunile pentru imagini (necesare pentru WhatsApp)
            width = height = 0
            if media_type == MediaType.IMAGE or media_type == MediaType.STICKER:
                try:
                    with Image.open(file_path) as img:
                        width, height = img.size
                except Exception as e:
                    self.logger.warning(f"Nu s-au putut determina dimensiunile imaginii: {e}")
            
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_size": file_size,
                "file_hash": file_hash,
                "media_key": media_key_base64,
                "media_type": media_type,
                "mime_type": mime_type,
                "width": width,
                "height": height
            }
            
        except Exception as e:
            if isinstance(e, WAMediaError):
                raise
            self.logger.error(f"Eroare la pregătirea media: {e}")
            raise WAMediaError(f"Eroare la pregătirea media: {e}")
    
    async def upload_media(self, file_path: str) -> Dict[str, Any]:
        """
        Încarcă media pe serverele WhatsApp.
        Metoda este îmbunătățită cu abordarea din bibliotecile moderne.
        
        Args:
            file_path: Calea către fișierul media
            
        Returns:
            dict: Răspunsul de încărcare incluzând URL-ul media
            
        Raises:
            WAMediaError: Dacă apare o eroare la încărcarea media
        """
        try:
            # Pregătim metadatele media
            media_info = await self.prepare_media(file_path)
            media_type = media_info["media_type"]
            mime_type = media_info["mime_type"]
            file_size = media_info["file_size"]
            file_name = media_info["file_name"]
            
            # Obținem informațiile de conectare pentru media
            if not self.media_conn_info:
                # În implementarea reală, aici s-ar obține informațiile de conexiune 
                # de la serverul WhatsApp prin clientul conectat
                # Deoarece nu avem acces direct la conexiunea cu serverul,
                # vom presupune un scenariu placebo pentru ilustrare
                self.media_conn_info = {
                    "auth": "someAuthToken",
                    "ttl": 3600,
                    "uploadUrl": self.upload_url
                }
            
            # Pregătim URL-ul de încărcare
            upload_url = f"{self.upload_url}/{media_type}"
            
            # Pregătim headerele pentru încărcare
            headers = {
                "Origin": "https://web.whatsapp.com",
                "Referer": "https://web.whatsapp.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.177 Safari/537.36"
            }
            
            # În implementarea reală, aici s-ar încărca efectiv fișierul pe serverul WhatsApp
            # folosind informațiile de autentificare și URL-ul de încărcare.
            
            # Pentru ilustrare, vom simula un răspuns de succes
            # În implementarea reală, aici s-ar procesa răspunsul de la server
            simulated_response = {
                "url": f"https://mmg.whatsapp.net/{media_type}/{media_info['file_hash']}",
                "mimetype": mime_type,
                "filehash": media_info["file_hash"],
                "filesize": file_size,
                "mediaKey": media_info["media_key"],
                "type": media_type,
                "fileName": file_name
            }
            
            if media_type == MediaType.IMAGE or media_type == MediaType.STICKER:
                simulated_response["width"] = media_info["width"]
                simulated_response["height"] = media_info["height"]
                
            self.logger.info(f"Simulare încărcare media de tip {media_type} ({file_size} bytes): {file_name}")
            
            return simulated_response
            
        except Exception as e:
            if isinstance(e, WAMediaError):
                raise
            self.logger.error(f"Eroare la încărcarea media: {e}")
            raise WAMediaError(f"Eroare la încărcarea media: {e}")
    
    async def download_media(self, message: Dict[str, Any], output_path: Optional[str] = None) -> str:
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
            # Extragem informațiile despre media din mesaj
            if not message.get("mediaUrl"):
                raise WAMediaError("Mesajul nu conține URL media")
                
            media_url = message["mediaUrl"]
            media_key = message.get("mediaKey")
            mime_type = message.get("mimetype", "application/octet-stream")
            file_name = message.get("fileName")
            
            # Determinăm extensia fișierului din mime type
            extension = mimetypes.guess_extension(mime_type) or ""
            
            # Generăm numele fișierului de ieșire dacă nu este furnizat
            if not output_path:
                if file_name:
                    output_path = file_name
                else:
                    rand_id = generate_random_id(8)
                    output_path = f"media_{rand_id}{extension}"
                    
            # În implementarea reală, aici s-ar descărca efectiv fișierul de la URL-ul media
            # și s-ar decripta folosind cheia media dacă este disponibilă.
            
            # Pentru ilustrare, vom simula o descărcare reușită
            self.logger.info(f"Simulare descărcare media de la {media_url} către {output_path}")
            
            # Creăm un fișier gol pentru a simula descărcarea
            with open(output_path, 'wb') as f:
                f.write(b"Placeholder pentru conținutul media")  # În implementarea reală, aici ar fi conținutul real
                
            return output_path
            
        except Exception as e:
            if isinstance(e, WAMediaError):
                raise
            self.logger.error(f"Eroare la descărcarea media: {e}")
            raise WAMediaError(f"Eroare la descărcarea media: {e}")
    
    async def process_media_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesează un mesaj media primit pentru a extrage informațiile despre media.
        
        Args:
            message: Datele mesajului
            
        Returns:
            dict: Mesajul procesat cu informații despre media
            
        Raises:
            WAMediaError: Dacă apare o eroare la procesarea mesajului media
        """
        try:
            # Determinăm tipul de media din mesaj
            if "imageMessage" in message:
                media_msg = message["imageMessage"]
                media_type = MediaType.IMAGE
            elif "videoMessage" in message:
                media_msg = message["videoMessage"]
                media_type = MediaType.VIDEO
            elif "audioMessage" in message:
                media_msg = message["audioMessage"]
                media_type = MediaType.AUDIO
            elif "documentMessage" in message:
                media_msg = message["documentMessage"]
                media_type = MediaType.DOCUMENT
            elif "stickerMessage" in message:
                media_msg = message["stickerMessage"]
                media_type = MediaType.STICKER
            else:
                return message  # Nu este un mesaj media
                
            # Extragem informațiile despre media
            media_info = {
                "mediaType": media_type,
                "mimetype": media_msg.get("mimetype"),
                "mediaUrl": media_msg.get("url"),
                "mediaKey": media_msg.get("mediaKey"),
                "fileSize": media_msg.get("fileLength") or media_msg.get("fileSize"),
                "fileName": media_msg.get("fileName"),
                "caption": media_msg.get("caption"),
            }
            
            # Adăugăm informațiile despre dimensiune pentru imagini și stickere
            if media_type in [MediaType.IMAGE, MediaType.STICKER]:
                media_info["width"] = media_msg.get("width")
                media_info["height"] = media_msg.get("height")
            
            # Adăugăm informațiile despre media la mesaj
            message["mediaInfo"] = media_info
            
            return message
            
        except Exception as e:
            self.logger.error(f"Eroare la procesarea mesajului media: {e}")
            raise WAMediaError(f"Eroare la procesarea mesajului media: {e}")
            
    async def create_thumbnail(self, file_path: str, max_size: int = 100) -> Optional[bytes]:
        """
        Creează o miniatură pentru o imagine sau un videoclip.
        
        Args:
            file_path: Calea către fișierul pentru care se creează miniatura
            max_size: Dimensiunea maximă a miniaturii (în pixeli)
            
        Returns:
            bytes: Datele miniatură sau None dacă nu se poate crea
        """
        try:
            media_type, mime_type = await self.determine_media_type(file_path)
            
            # Pentru imagini, folosim PIL pentru a crea miniatura
            if media_type == MediaType.IMAGE:
                try:
                    with Image.open(file_path) as img:
                        # Păstrăm raportul de aspect
                        img.thumbnail((max_size, max_size))
                        
                        # Salvăm miniatura în format JPEG
                        buffer = BytesIO()
                        img.save(buffer, format="JPEG", quality=70)
                        return buffer.getvalue()
                except Exception as e:
                    self.logger.error(f"Eroare la crearea miniaturii pentru imagine: {e}")
                    return None
            
            # Pentru videoclipuri, în implementarea reală s-ar folosi ffmpeg sau o bibliotecă similară
            # Pentru ilustrare, vom returna None
            if media_type == MediaType.VIDEO:
                self.logger.info("Crearea miniaturilor pentru videoclipuri nu este implementată în acest exemplu")
                return None
                
            # Pentru alte tipuri de media, nu creăm miniaturi
            return None
            
        except Exception as e:
            self.logger.error(f"Eroare la crearea miniaturii: {e}")
            return None