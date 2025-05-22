"""
Modul de autentificare pentru WhatsApp Web.

Acest modul implementează metodele de autentificare pentru WhatsApp Web,
inclusiv scanarea codului QR și utilizarea codului de asociere (pairing code).
"""

import base64
import json
import os
import qrcode
import re
import time
from typing import Dict, Optional, Callable, Any, Tuple

from .utils import get_logger
from .exceptions import WAAuthenticationError

class WAAuthentication:
    """
    Manager pentru autentificarea cu WhatsApp Web.
    
    Această clasă gestionează mecanismele de autentificare, inclusiv
    scanarea codului QR și utilizarea codului de asociere.
    """
    
    def __init__(self):
        """Inițializează managerul de autentificare."""
        self.logger = get_logger("WAAuthentication")
        self.qr_code = None
        self.pairing_ref = None
        self.pairing_code = None
        self.authenticated = False
        self.auth_info = None
    
    def handle_qr_code(self, qr_data: str, callback: Optional[Callable] = None) -> str:
        """
        Gestionează datele codului QR pentru autentificare.
        
        Args:
            qr_data: Datele pentru generarea codului QR
            callback: Funcție opțională de callback pentru notificarea aplicației client
            
        Returns:
            str: Reprezentarea text a codului QR pentru terminal
        """
        self.qr_code = qr_data
        self.logger.info("Cod QR primit pentru autentificare")
        
        # Afișăm codul QR în terminal
        qr = qrcode.QRCode()
        qr.add_data(qr_data)
        qr_terminal = qr.get_matrix()
        
        # Convertim matricea în reprezentare text pentru terminal
        terminal_qr = ""
        for row in qr_terminal:
            line = ""
            for cell in row:
                if cell:
                    line += "██"  # Caracter plin pentru celulele active
                else:
                    line += "  "  # Spațiu pentru celulele inactive
            terminal_qr += line + "\n"
        
        # Notificăm aplicația client dacă este furnizat un callback
        if callback:
            callback(qr_data)
            
        return terminal_qr
    
    def request_pairing_code(self, phone_number: str) -> str:
        """
        Solicită un cod de asociere (pairing code) pentru autentificare.
        
        Aceasta este o metodă alternativă de autentificare care nu necesită scanarea
        unui cod QR, ci introduce un cod numeric pe telefonul mobil.
        
        Args:
            phone_number: Numărul de telefon în format internațional (ex: +40123456789)
            
        Returns:
            str: Referința pentru codul de asociere sau None dacă solicitarea eșuează
            
        Raises:
            WAAuthenticationError: Dacă apare o eroare la solicitarea codului
        """
        # Validăm formatul numărului de telefon
        if not re.match(r'^\+[1-9]\d{1,14}$', phone_number):
            raise WAAuthenticationError("Format invalid pentru numărul de telefon. Utilizați formatul internațional: +40123456789")
        
        # Eliminăm caracterul '+' de la început
        phone_number = phone_number.lstrip('+')
        
        self.logger.info(f"Solicitare cod de asociere pentru numărul {phone_number}")
        
        # În implementarea reală, aici s-ar trimite solicitarea către serverul WhatsApp
        # și s-ar primi referința pentru codul de asociere
        
        # Pentru simulare, generăm o referință aleatorie
        self.pairing_ref = "pairing_ref_" + str(int(time.time()))
        
        # Pairing code-ul va fi afișat pe telefonul utilizatorului
        # În implementarea reală, acest cod ar fi generat de WhatsApp și trimis pe telefonul utilizatorului
        self.pairing_code = "123456"  # simulare
        
        self.logger.info(f"Cod de asociere solicitat. Verificați telefonul pentru cod.")
        
        return self.pairing_ref
    
    def verify_pairing_code(self, code: str) -> bool:
        """
        Verifică un cod de asociere introdus de utilizator.
        
        Args:
            code: Codul de asociere de 6 cifre
            
        Returns:
            bool: True dacă codul este valid, False altfel
            
        Raises:
            WAAuthenticationError: Dacă nu există o solicitare activă pentru cod de asociere
        """
        if not self.pairing_ref:
            raise WAAuthenticationError("Nu există o solicitare activă pentru cod de asociere")
            
        # Validăm formatul codului
        if not re.match(r'^\d{6}$', code):
            raise WAAuthenticationError("Format invalid pentru codul de asociere. Trebuie să conțină 6 cifre.")
            
        # În implementarea reală, aici s-ar verifica codul cu serverul WhatsApp
        
        # Pentru simulare, verificăm cu codul generat anterior (în realitate codul e pe telefon)
        if code == self.pairing_code:
            self.logger.info("Cod de asociere valid. Autentificare reușită.")
            self.authenticated = True
            self.auth_info = {
                "method": "pairing_code",
                "pairing_ref": self.pairing_ref,
                "timestamp": time.time()
            }
            return True
        else:
            self.logger.warning("Cod de asociere invalid.")
            return False
    
    def handle_auth_success(self, auth_data: Dict[str, Any]) -> None:
        """
        Gestionează succesul autentificării.
        
        Args:
            auth_data: Datele de autentificare primite de la server
        """
        self.authenticated = True
        self.auth_info = auth_data
        self.logger.info("Autentificare reușită cu WhatsApp Web")
    
    def reset(self) -> None:
        """Resetează starea de autentificare."""
        self.qr_code = None
        self.pairing_ref = None
        self.pairing_code = None
        self.authenticated = False
        self.auth_info = None
        self.logger.info("Stare de autentificare resetată")