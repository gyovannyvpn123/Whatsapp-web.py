#!/usr/bin/env python3
"""
Client WhatsApp Web simplificat, optimizat pentru Replit.

Acest script demonstrează o implementare simplificată care se poate conecta 
la WhatsApp Web, emulând un browser real, dar fără a depinde de biblioteci externe
complexe care pot cauza probleme de compatibilitate.
"""

import base64
import json
import logging
import os
import sys
import time
import uuid
import websocket
import threading
import requests
from typing import Dict, Any, Callable
import qrcode
from PIL import Image

# Adăugăm directorul părinte în path pentru a importa modulele proprii
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Parametri pentru conexiunea WhatsApp Web
WA_WEB_PARAMS = {
    "WS_URL": "wss://web.whatsapp.com/ws/chat",
    "ORIGIN": "https://web.whatsapp.com",
    "WEBSITE_URL": "https://web.whatsapp.com/",
    "WA_VERSION": "2.2423.9", 
    "BROWSER_VERSION": "Chrome,124.0.6367.91",
    "UA": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.91 Safari/537.36",
    "WS_PROTOCOLS": ["v-rvosdlz7cqwcpv6tpg6qn6y", "chat"],
}

class SimpleWhatsAppClient:
    """
    Client simplu pentru WhatsApp Web care demonstrează conexiunea
    cu un număr minim de dependențe externe.
    """
    
    def __init__(self, log_level=logging.INFO):
        """Inițializează clientul simplu WhatsApp Web."""
        # Configurare logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("SimpleWhatsAppClient")
        
        # Conexiune WebSocket
        self.ws = None
        self.connected = False
        self.authenticated = False
        
        # Generare ID client unic
        self.client_id = self._generate_client_id()
        self.logger.info(f"Client ID generat: {self.client_id}")
        
        # Callbacks pentru evenimente
        self.callbacks = {
            "qr_code": None,
            "message": None,
            "connected": None
        }
    
    def _generate_client_id(self) -> str:
        """Generează un ID client pentru conectare."""
        return base64.b64encode(uuid.uuid4().bytes).decode('utf-8')
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Înregistrează un callback pentru un anumit tip de eveniment.
        
        Args:
            event_type: Tipul de eveniment ('qr_code', 'message', 'connected')
            callback: Funcția de callback care va fi apelată când apare evenimentul
        """
        if event_type in self.callbacks:
            self.callbacks[event_type] = callback
        else:
            self.logger.warning(f"Tip de eveniment necunoscut: {event_type}")
    
    def _on_message(self, ws, message) -> None:
        """Handler pentru mesajele primite de la WhatsApp Web."""
        self.logger.debug(f"Mesaj primit: {message[:100]}...")
        
        try:
            # Verificăm dacă mesajul conține un cod QR pentru autentificare
            if "\"type\":\"qr\"" in message:
                data = json.loads(message.split(",", 1)[1])
                if data.get("type") == "qr":
                    qr_data = data["data"]
                    self.logger.info("Cod QR primit pentru scanare")
                    
                    # Generăm și afișăm imaginea QR
                    self._generate_and_display_qr(qr_data)
                    
                    # Notificăm aplicația prin callback
                    if self.callbacks["qr_code"]:
                        self.callbacks["qr_code"](qr_data)
            
            # Verificăm dacă este un mesaj normal
            elif "\"type\":\"message\"" in message:
                data = json.loads(message.split(",", 1)[1])
                if self.callbacks["message"]:
                    self.callbacks["message"](data)
        
        except Exception as e:
            self.logger.error(f"Eroare la procesarea mesajului: {e}")
    
    def _on_error(self, ws, error) -> None:
        """Handler pentru erori WebSocket."""
        self.logger.error(f"Eroare WebSocket: {error}")
    
    def _on_close(self, ws, close_status_code, close_reason) -> None:
        """Handler pentru închiderea conexiunii WebSocket."""
        self.logger.info(f"Conexiune WebSocket închisă. Cod: {close_status_code}, Motiv: {close_reason}")
        self.connected = False
    
    def _on_open(self, ws) -> None:
        """Handler pentru deschiderea conexiunii WebSocket."""
        self.logger.info("Conexiune WebSocket stabilită")
        self.connected = True
        
        # Trimitem mesajul de inițializare pentru a începe sesiunea
        self._send_init_message()
    
    def _send_init_message(self) -> None:
        """Trimite mesajul de inițializare pentru sesiunea WhatsApp Web."""
        init_message = {
            "clientId": self.client_id,
            "connectType": "WIFI_UNKNOWN",
            "connectReason": "USER_ACTIVATED",
            "connectAttempt": 1,
            "isNewLogin": True,
            "passive": False,
            "userAgent": WA_WEB_PARAMS["UA"],
            "webVersion": WA_WEB_PARAMS["WA_VERSION"],
            "browserName": "Chrome",
            "browserVersion": "124.0.6367.91"
        }
        
        # Trimitem mesajul serialized ca JSON cu prefix "admin"
        self._send_json("admin", init_message)
    
    def _send_json(self, tag: str, data: Any) -> None:
        """
        Trimite date JSON prin WebSocket.
        
        Args:
            tag: Tag-ul mesajului (ex: "admin", "message")
            data: Datele pentru trimitere
        """
        if not self.ws or not self.connected:
            self.logger.error("Nu există o conexiune WebSocket activă")
            return
            
        # Serializăm datele ca JSON
        json_data = json.dumps(data, separators=(',', ':'))
        
        # Construim mesajul complet
        message = f"{tag},{json_data}"
        
        try:
            self.ws.send(message)
            self.logger.debug(f"Mesaj trimis: {tag}")
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea mesajului: {e}")
    
    def _generate_and_display_qr(self, qr_data: str) -> None:
        """
        Generează și afișează un cod QR în consolă.
        
        Args:
            qr_data: Datele pentru codul QR
        """
        # Generăm codul QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=4,  # ERROR_CORRECT_H
            box_size=10,
            border=4
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Afișăm codul QR în consolă în format ASCII
        self._display_qr_terminal(qr_image)
    
    def _display_qr_terminal(self, qr_image: Image.Image) -> None:
        """
        Afișează un cod QR în terminal.
        
        Args:
            qr_image: Imaginea codului QR
        """
        # Convertim imaginea la alb/negru
        qr_image = qr_image.convert('RGB')
        width, height = qr_image.size
        
        # Afișăm imaginea în terminal
        print("\n" + "-" * 50)
        print("SCANAȚI ACEST COD QR CU WHATSAPP PE TELEFON")
        print("-" * 50)
        
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
        
        print("-" * 50)
        print("Notă: Codul QR expiră după 20 de secunde.")
        print("Dacă nu reușiți să îl scanați, așteptați un nou cod.")
        print("-" * 50 + "\n")
    
    def connect(self) -> None:
        """
        Inițiază conexiunea la serverele WhatsApp Web.
        
        Această metodă simulează comportamentul unui browser real pentru a
        asigura acceptarea conexiunii de către serverele WhatsApp.
        """
        if self.connected:
            self.logger.warning("Clientul este deja conectat")
            return
            
        self.logger.info("Conectare la serverele WhatsApp Web...")
        
        try:
            # Dezactivăm trace WebSocket pentru a reduce zgomotul în log
            websocket.enableTrace(False)
            
            # Simulăm sesiunea de browser prin efectuarea unui request HTTP inițial
            session = requests.Session()
            headers = {
                "User-Agent": WA_WEB_PARAMS["UA"],
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Cache-Control": "max-age=0"
            }
            
            # Facem un request inițial pentru a obține cookies
            try:
                resp = session.get(WA_WEB_PARAMS["WEBSITE_URL"], headers=headers)
                if resp.status_code != 200:
                    self.logger.warning(f"Acces inițial website returnat status {resp.status_code}")
            except Exception as e:
                self.logger.warning(f"Eroare la request HTTP inițial: {e}")
            
            # Generăm un ID de browser aleator
            browser_id = uuid.uuid4().hex[:8]
            
            # Construim URL-ul cu toți parametrii necesari
            browser_data = json.dumps({
                "actual_browser": "Chrome",
                "actual_version": "124.0.6367.91"
            })
            
            ws_url = f"{WA_WEB_PARAMS['WS_URL']}?v={WA_WEB_PARAMS['WA_VERSION']}&browser={WA_WEB_PARAMS['BROWSER_VERSION']}&browser_data={browser_data}&clientId={self.client_id}&browser_id={browser_id}"
            
            # Obținem și adăugăm cookie-urile din sesiunea HTTP
            cookies = "; ".join([f"{k}={v}" for k, v in session.cookies.items()])
            
            # Construim headerele pentru WebSocket
            ws_headers = {
                "Origin": WA_WEB_PARAMS["ORIGIN"],
                "User-Agent": WA_WEB_PARAMS["UA"]
            }
            
            if cookies:
                ws_headers["Cookie"] = cookies
            
            self.logger.info(f"Conectare WebSocket la: {ws_url}")
            
            # Creăm conexiunea WebSocket
            self.ws = websocket.WebSocketApp(
                ws_url,
                header=ws_headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                subprotocols=WA_WEB_PARAMS["WS_PROTOCOLS"]
            )
            
            # Rulăm WebSocket într-un thread separat
            websocket_thread = threading.Thread(
                target=lambda: self.ws.run_forever(ping_interval=25, ping_timeout=10)
            )
            websocket_thread.daemon = True
            websocket_thread.start()
            
        except Exception as e:
            self.logger.error(f"Eroare la conectare: {e}")
            self.connected = False
    
    def disconnect(self) -> None:
        """Deconectare de la serverele WhatsApp Web."""
        if not self.connected:
            self.logger.warning("Clientul este deja deconectat")
            return
            
        self.logger.info("Deconectare de la serverele WhatsApp Web...")
        
        try:
            if self.ws:
                self.ws.close()
                
            self.connected = False
            self.authenticated = False
            
        except Exception as e:
            self.logger.error(f"Eroare la deconectare: {e}")
    
    def wait_for_qr_code(self, timeout: int = 60) -> bool:
        """
        Așteaptă primirea unui cod QR pentru autentificare.
        
        Args:
            timeout: Timpul maxim de așteptare în secunde
            
        Returns:
            bool: True dacă s-a primit un cod QR, False altfel
        """
        qr_event = threading.Event()
        
        def on_qr_update(qr_data):
            qr_event.set()
        
        # Înregistrăm callback-ul temporar
        old_callback = self.callbacks.get("qr_code")
        self.callbacks["qr_code"] = on_qr_update
        
        # Așteptăm evenimentul sau timeout
        result = qr_event.wait(timeout)
        
        # Restaurăm callback-ul original
        self.callbacks["qr_code"] = old_callback
        
        if result:
            self.logger.info("Cod QR primit cu succes!")
        else:
            self.logger.warning(f"Timeout la așteptarea codului QR după {timeout} secunde")
            
        return result


def main():
    """Funcția principală pentru demonstrarea clientului simplificat."""
    # Configurare nivel logging
    log_level = logging.INFO
    
    # Inițializare client
    client = SimpleWhatsAppClient(log_level=log_level)
    
    # Definim callback-uri pentru evenimente
    def on_qr_code(qr_data):
        print(f"\nCod QR primit! Datele QR: {qr_data[:30]}...\n")
    
    def on_message(message):
        print(f"\nMesaj primit: {message}\n")
    
    def on_connected(info):
        print(f"\nConectat cu succes la WhatsApp! Info: {info}\n")
    
    # Înregistrăm callback-urile
    client.register_callback("qr_code", on_qr_code)
    client.register_callback("message", on_message)
    client.register_callback("connected", on_connected)
    
    try:
        print("\n=== Demonstrație Client Simplificat WhatsApp Web ===")
        print(">>> Conectare la serverele WhatsApp...")
        client.connect()
        
        # Așteptăm primirea codului QR
        print(">>> Așteptăm primirea codului QR...")
        client.wait_for_qr_code(timeout=30)
        
        # Menținem conexiunea activă pentru a permite scanarea QR
        print("\n>>> Conexiune activă. Apăsați Ctrl+C pentru a încheia.")
        print(">>> Scanați codul QR cu aplicația WhatsApp de pe telefonul dvs.\n")
        
        # Bucla principală
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n>>> Întrerupere de la tastatură. Deconectare...")
    except Exception as e:
        print(f">>> Eroare: {e}")
    finally:
        # Deconectare la final
        if client:
            client.disconnect()
        print(">>> Deconectat de la WhatsApp.")

if __name__ == "__main__":
    main()