"""
Excepții pentru biblioteca WhatsApp Web Python.

Acest modul definește ierarhia de excepții utilizate în bibliotecă pentru a gestiona
mai precis erorile specifice diferitelor componente.
"""

class WABaseError(Exception):
    """
    Excepție de bază pentru toate erorile din biblioteca WhatsApp Web.
    
    Toate celelalte excepții specifice extind această clasă.
    """
    pass

class WAConnectionError(WABaseError):
    """
    Excepție pentru erori de conexiune WebSocket.
    
    Se ridică atunci când apar probleme la stabilirea sau menținerea conexiunii
    WebSocket cu serverele WhatsApp Web.
    """
    pass

class WAAuthenticationError(WABaseError):
    """
    Excepție pentru erori de autentificare.
    
    Se ridică atunci când apar probleme în procesul de autentificare
    cu WhatsApp Web, cum ar fi QR code invalid sau expirat, sau pairing code invalid.
    """
    pass

class WAMessageError(WABaseError):
    """
    Excepție pentru erori la trimiterea sau primirea mesajelor.
    
    Se ridică atunci când apar probleme la trimiterea sau procesarea mesajelor.
    """
    pass

class WAMediaError(WABaseError):
    """
    Excepție pentru erori la gestionarea fișierelor media.
    
    Se ridică atunci când apar probleme la încărcarea, descărcarea sau
    procesarea fișierelor media (imagini, videoclipuri, documente etc.).
    """
    pass

class WAProtocolError(WABaseError):
    """
    Excepție pentru erori de protocol.
    
    Se ridică atunci când apar probleme la nivel de protocol WhatsApp,
    cum ar fi mesaje neașteptate sau erori de parsare.
    """
    pass

class WATimeoutError(WABaseError):
    """
    Excepție pentru depășiri de timp.
    
    Se ridică atunci când o operațiune durează mai mult decât timpul maxim alocat,
    cum ar fi așteptarea unui răspuns de la server.
    """
    pass

class WADecryptionError(WABaseError):
    """
    Excepție pentru erori de decriptare.
    
    Se ridică atunci când apar probleme la decriptarea mesajelor sau a datelor media.
    """
    pass