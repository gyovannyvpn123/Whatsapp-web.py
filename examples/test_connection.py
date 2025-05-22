#!/usr/bin/env python3
"""
Script de test pentru verificarea conectării la serverele WhatsApp Web.

Acest script demonstrează conectarea la serverele WhatsApp Web și
autentificarea folosind fie codul QR, fie codul de asociere (pairing code).
"""

import argparse
import logging
import os
import sys
import time

# Adăugăm directorul părinte în calea de căutare pentru a putea importa modulul wawspy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wawspy import WAClient, WAConnectionError, WAAuthenticationError

def on_qr_code(qr_data):
    """Callback pentru primirea codului QR."""
    print("\nPrimire cod QR pentru autentificare. Scanați cu aplicația WhatsApp de pe telefon.\n")
    print(f"Date cod QR: {qr_data[:20]}...\n")

def on_connected(user_info):
    """Callback pentru conectare și autentificare reușită."""
    print(f"\nConectat cu succes la WhatsApp Web!")
    print(f"Informații utilizator: {user_info}\n")

def on_message(message):
    """Callback pentru mesaje primite."""
    print(f"\nMesaj primit: {message}\n")

def on_disconnected(info):
    """Callback pentru deconectare."""
    print(f"\nDeconectat de la WhatsApp Web. Motiv: {info.get('reason')}\n")

def main():
    """Funcția principală care demonstrează conexiunea la WhatsApp Web."""
    
    # Configurare argumente linie de comandă
    parser = argparse.ArgumentParser(description="Testare conectare la WhatsApp Web")
    parser.add_argument("--phone", type=str, help="Numărul de telefon pentru autentificare cu pairing code (ex: +40123456789)")
    parser.add_argument("--debug", action="store_true", help="Activează logging detaliat")
    args = parser.parse_args()
    
    # Configurare nivel logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    
    # Inițializare client WhatsApp
    client = WAClient(log_level=log_level)
    
    # Înregistrare callbacks
    client.register_callback("qr_code", on_qr_code)
    client.register_callback("connected", on_connected)
    client.register_callback("message", on_message)
    client.register_callback("disconnected", on_disconnected)
    
    try:
        print("Conectare la serverele WhatsApp Web...")
        
        # Pornire thread pentru conexiune
        import threading
        connection_thread = threading.Thread(target=client.connect)
        connection_thread.daemon = True
        connection_thread.start()
        
        # Așteptăm stabilirea conexiunii
        if not client.wait_for_connection(timeout=30):
            print("Nu s-a putut conecta la serverele WhatsApp Web în timpul specificat")
            return
            
        print("Conexiune stabilită cu serverele WhatsApp Web!")
        
        # Alegem metoda de autentificare în funcție de argumentele primite
        if args.phone:
            # Autentificare cu pairing code
            print(f"Solicitare cod de asociere pentru numărul {args.phone}...")
            result = client.authenticate_with_pairing_code(args.phone)
            print(result)
            
            # Solicităm codul de asociere de la utilizator
            pairing_code = input("Introduceți codul de asociere primit pe telefon (6 cifre): ")
            print(f"Verificare cod de asociere: {pairing_code}")
            
            if client.verify_pairing_code(pairing_code):
                print("Autentificare reușită cu codul de asociere!")
            else:
                print("Autentificare eșuată. Cod de asociere invalid.")
                return
        else:
            # Autentificare cu cod QR
            print("Inițiere autentificare cu cod QR...")
            client.authenticate_with_qr()
        
        # Așteptăm autentificarea
        if not client.wait_for_authentication(timeout=120):
            print("Autentificare eșuată sau timeout.")
            return
            
        print("Autentificare reușită!")
        
        # Testăm trimiterea unui mesaj dacă suntem autentificați
        if client.is_authenticated:
            recipient = input("\nIntroduceți numărul de telefon pentru a trimite un mesaj de test (ex: +40123456789): ")
            message = "Acesta este un mesaj de test trimis prin biblioteca wawspy!"
            
            try:
                result = client.send_message(recipient, message)
                print(f"Mesaj trimis cu succes: {result}")
            except Exception as e:
                print(f"Eroare la trimiterea mesajului: {e}")
        
        # Menținem conexiunea activă pentru a primi mesaje
        print("\nConexiune activă. Apăsați Ctrl+C pentru a încheia.")
        while client.is_connected:
            time.sleep(1)
            
    except WAConnectionError as e:
        print(f"Eroare de conexiune: {e}")
    except WAAuthenticationError as e:
        print(f"Eroare de autentificare: {e}")
    except KeyboardInterrupt:
        print("\nÎntrerupere de la tastatură. Deconectare...")
    except Exception as e:
        print(f"Eroare neașteptată: {e}")
    finally:
        # Deconectare la final
        if client.is_connected:
            client.disconnect()
            print("Deconectat de la WhatsApp Web.")

if __name__ == "__main__":
    main()