#!/usr/bin/env python3
"""
Script de test pentru verificarea conexiunii reale la serverele WhatsApp.

Acest script demonstrează conectarea la serverele WhatsApp folosind implementarea
bazată pe protocolul real, similar cu Baileys.js.
"""

import argparse
import logging
import os
import sys
import time

# Adăugăm directorul părinte în calea de căutare
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importăm clientul real
from wawspy.real_client import WAClient

def on_qr_code(qr_data):
    """Callback pentru primirea codului QR."""
    print(f"\nPrimire cod QR pentru autentificare. Scanați cu aplicația WhatsApp!")
    print(f"Date cod QR: {qr_data[:30]}...\n")

def on_connection_update(update):
    """Callback pentru actualizări de conexiune."""
    print(f"Actualizare conexiune: {update}")
    
    # Verificăm dacă avem un cod de asociere
    if update.get("pairingCode"):
        print(f"\nCod de asociere primit: {update['pairingCode']}")
        print("Introduceți acest cod pe telefonul dvs. în Setări > Dispozitive conectate > Conectare dispozitiv")

def on_connected(info):
    """Callback pentru conectare reușită."""
    print(f"\nConectat cu succes la WhatsApp!")
    print(f"Informații sesiune: {info}")

def on_message(message):
    """Callback pentru mesaje primite."""
    print(f"\nMesaj primit: {message}")

def on_disconnected(info):
    """Callback pentru deconectare."""
    print(f"\nDeconectat de la WhatsApp. Motiv: {info}")

def main():
    """Funcția principală pentru testarea clientului real."""
    
    # Configurare argumente linie de comandă
    parser = argparse.ArgumentParser(description="Test conectare reală la WhatsApp")
    parser.add_argument("--phone", type=str, help="Numărul de telefon pentru autentificare cu pairing code")
    parser.add_argument("--debug", action="store_true", help="Activează logging detaliat")
    args = parser.parse_args()
    
    # Configurare nivel logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    
    # Inițializare client WhatsApp real
    client = WAClient(log_level=log_level)
    
    # Înregistrare callbacks
    client.register_callback("qr_code", on_qr_code)
    client.register_callback("connection_update", on_connection_update)
    client.register_callback("connected", on_connected)
    client.register_callback("message", on_message)
    client.register_callback("disconnected", on_disconnected)
    
    try:
        print("Conectare la serverele WhatsApp...")
        client.connect()
        
        # Dacă s-a specificat un număr de telefon, folosim autentificarea cu pairing code
        if args.phone:
            print(f"Solicitare cod de asociere pentru numărul {args.phone}...")
            client.request_pairing_code(args.phone)
        
        # Menținem conexiunea activă
        print("\nConexiune activă. Apăsați Ctrl+C pentru a încheia.")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nÎntrerupere de la tastatură. Deconectare...")
    except Exception as e:
        print(f"Eroare: {e}")
    finally:
        # Deconectare la final
        client.disconnect()
        print("Deconectat de la WhatsApp.")

if __name__ == "__main__":
    main()