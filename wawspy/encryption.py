"""
Modul de criptare pentru comunicarea cu WhatsApp Web.

Acest modul implementează criptarea și decriptarea pentru comunicarea sigură
între client și serverele WhatsApp Web, conform protocolului Signal.
"""

import base64
import hashlib
import hmac
import json
import os
import logging
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from typing import Dict, List, Tuple, Any, Optional, Union, Callable

from .utils import get_logger

class WAEncryption:
    """
    Manager pentru criptarea și decriptarea mesajelor WhatsApp.
    
    Implementează algoritmii necesari pentru criptarea și decriptarea
    comunicării cu serverele WhatsApp Web, inclusiv gestionarea cheilor.
    """
    
    def __init__(self):
        """Inițializează managerul de criptare."""
        self.logger = get_logger("WAEncryption")
        self.backend = default_backend()
        
        # Chei pentru sesiune
        self.private_key = None
        self.public_key = None
        self.shared_key = None
        self.shared_secret = None
        self.server_public_key = None
        self.auth_key = None
        self.enc_key = None
        self.mac_key = None
        
    def generate_keys(self) -> Tuple[bytes, bytes]:
        """
        Generează perechea de chei pentru criptare.
        
        Returns:
            tuple: (cheie_privată, cheie_publică)
        """
        # În implementarea reală, aici s-ar genera o pereche de chei EC / Curve25519
        # Pentru simplificare, simulăm generarea cheilor
        self.private_key = os.urandom(32)
        self.public_key = os.urandom(32)  # În realitate, s-ar calcula din cheia privată
        
        return self.private_key, self.public_key
    
    def compute_shared_key(self, server_public_key: bytes) -> bytes:
        """
        Calculează cheia comună folosind algoritmul X25519 (Curve25519).
        
        Args:
            server_public_key: Cheia publică a serverului
            
        Returns:
            bytes: Cheia comună
        """
        if not self.private_key:
            raise ValueError("Nu s-a generat cheia privată")
            
        self.server_public_key = server_public_key
        
        # În implementarea reală, aici s-ar calcula cheia comună folosind X25519
        # Pentru simplificare, simulăm calculul cheii comune
        h = hashlib.sha256()
        h.update(self.private_key)
        h.update(self.server_public_key)
        self.shared_key = h.digest()
        
        return self.shared_key
    
    def derive_session_keys(self) -> Tuple[bytes, bytes, bytes]:
        """
        Derivă cheile de sesiune pentru criptare și autentificare.
        
        Returns:
            tuple: (cheie_autentificare, cheie_criptare, cheie_MAC)
        """
        if not self.shared_key:
            raise ValueError("Nu s-a calculat cheia comună")
            
        # Derivăm cheile folosind HKDF (HMAC-based Key Derivation Function)
        # În implementarea reală, s-ar folosi algoritmi specifici WhatsApp
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=80,
            salt=b"WhatsApp Salt",
            info=b"WhatsApp Derived Key",
            backend=self.backend
        )
        
        derived_key = hkdf.derive(self.shared_key)
        
        # Împărțim cheia derivată în cele trei componente
        self.auth_key = derived_key[0:32]   # Primii 32 de bytes pentru autentificare
        self.enc_key = derived_key[32:64]   # Următorii 32 pentru criptare
        self.mac_key = derived_key[64:80]   # Ultimii 16 pentru MAC
        
        return self.auth_key, self.enc_key, self.mac_key
    
    def encrypt_message(self, message: bytes) -> bytes:
        """
        Criptează un mesaj pentru transmitere.
        
        Args:
            message: Mesajul de criptat
            
        Returns:
            bytes: Mesajul criptat cu MAC
        """
        if not self.enc_key or not self.mac_key:
            raise ValueError("Cheile de sesiune nu au fost derivate")
            
        # Generăm un vector de inițializare (IV) aleator
        iv = os.urandom(16)
        
        # Aplicăm padding pentru AES
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(message) + padder.finalize()
        
        # Criptăm mesajul folosind AES-256-CBC
        cipher = Cipher(algorithms.AES(self.enc_key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # Calculăm MAC pentru autentificarea mesajului
        h = hmac.new(self.mac_key, digestmod=hashlib.sha256)
        h.update(iv + ciphertext)
        mac = h.digest()
        
        # Construim mesajul final: iv + ciphertext + mac
        encrypted_message = iv + ciphertext + mac
        
        return encrypted_message
    
    def decrypt_message(self, encrypted_message: bytes) -> bytes:
        """
        Decriptează un mesaj criptat.
        
        Args:
            encrypted_message: Mesajul criptat
            
        Returns:
            bytes: Mesajul decriptat
            
        Raises:
            ValueError: Dacă MAC-ul este invalid sau apare o eroare la decriptare
        """
        if not self.enc_key or not self.mac_key:
            raise ValueError("Cheile de sesiune nu au fost derivate")
            
        # Despărțim mesajul în componentele sale
        iv = encrypted_message[:16]
        mac_start = len(encrypted_message) - 32  # MAC-ul are 32 de bytes (SHA-256)
        ciphertext = encrypted_message[16:mac_start]
        received_mac = encrypted_message[mac_start:]
        
        # Verificăm MAC-ul
        h = hmac.new(self.mac_key, digestmod=hashlib.sha256)
        h.update(iv + ciphertext)
        calculated_mac = h.digest()
        
        if not hmac.compare_digest(calculated_mac, received_mac):
            raise ValueError("MAC invalid - mesaj posibil alterat")
            
        # Decriptăm mesajul
        cipher = Cipher(algorithms.AES(self.enc_key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Eliminăm padding-ul
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        
        return plaintext
    
    def encrypt_media_key(self, media_key: bytes) -> bytes:
        """
        Criptează o cheie media pentru transmisie.
        
        Args:
            media_key: Cheia media de criptat
            
        Returns:
            bytes: Cheia media criptată
        """
        if not self.enc_key:
            raise ValueError("Cheia de criptare nu a fost derivată")
            
        # Generăm un IV aleator
        iv = os.urandom(16)
        
        # Aplicăm padding pentru AES
        padder = padding.PKCS7(128).padder()
        padded_key = padder.update(media_key) + padder.finalize()
        
        # Criptăm cheia folosind AES-256-CBC
        cipher = Cipher(algorithms.AES(self.enc_key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        encrypted_key = encryptor.update(padded_key) + encryptor.finalize()
        
        # Returnăm IV + cheia criptată
        return iv + encrypted_key
    
    def decrypt_media_key(self, encrypted_key: bytes) -> bytes:
        """
        Decriptează o cheie media.
        
        Args:
            encrypted_key: Cheia media criptată
            
        Returns:
            bytes: Cheia media decriptată
        """
        if not self.enc_key:
            raise ValueError("Cheia de criptare nu a fost derivată")
            
        # Despărțim mesajul în componentele sale
        iv = encrypted_key[:16]
        ciphertext = encrypted_key[16:]
        
        # Decriptăm cheia
        cipher = Cipher(algorithms.AES(self.enc_key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        padded_key = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Eliminăm padding-ul
        unpadder = padding.PKCS7(128).unpadder()
        media_key = unpadder.update(padded_key) + unpadder.finalize()
        
        return media_key
    
    def compute_hmac(self, data: bytes) -> bytes:
        """
        Calculează un HMAC pentru date.
        
        Args:
            data: Datele pentru care se calculează HMAC
            
        Returns:
            bytes: HMAC-ul
        """
        if not self.mac_key:
            raise ValueError("Cheia MAC nu a fost derivată")
            
        h = hmac.new(self.mac_key, data, digestmod=hashlib.sha256)
        return h.digest()
    
    def verify_hmac(self, data: bytes, expected_hmac: bytes) -> bool:
        """
        Verifică un HMAC pentru date.
        
        Args:
            data: Datele pentru care se verifică HMAC
            expected_hmac: HMAC-ul așteptat
            
        Returns:
            bool: True dacă HMAC-ul este valid, False altfel
        """
        calculated_hmac = self.compute_hmac(data)
        return hmac.compare_digest(calculated_hmac, expected_hmac)