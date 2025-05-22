"""
Constants for WhatsApp Web library - Îmbunătățit cu inspirație din Baileys.
"""

# WhatsApp Web WebSocket URL 
# Schimbat în URL-ul principal utilizat de Baileys
WA_WEBSOCKET_URL = "wss://web.whatsapp.com/ws"

# Alternative WebSocket URLs care ar putea funcționa
WA_ALTERNATIVE_WS_URLS = [
    "wss://web.whatsapp.com/ws/chat",
    "wss://web.whatsapp.com:5222",
    "wss://web.whatsapp.com/ws"
]

# Informații client WhatsApp - actualizate conform Baileys
WA_CLIENT_VERSION = "2.2402.7"
WA_CLIENT_TOKEN = ""  # Baileys nu folosește un token fix, ci generează unul dinamic

# Informații browser WhatsApp Web
WA_BROWSER_NAME = "Chrome"
WA_BROWSER_VERSION = "110.0.5481.177"

# HTTP origin pentru conexiunea WebSocket
WA_ORIGIN = "https://web.whatsapp.com"

# User agent pentru conexiunea WebSocket - actualizat la Chrome recent
WA_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.177 Safari/537.36"

# Format browser pentru WhatsApp
WA_BROWSER_DATA = f"{WA_BROWSER_NAME},{WA_BROWSER_VERSION}"

# Protocoale WebSocket
WA_WS_PROTOCOLS = ["chat"]

# Parametri conexiune
CONNECT_TIMEOUT_MS = 30000    # Timeout conexiune
KEEPALIVE_INTERVAL_MS = 20000 # Interval keepalive

# Setări reconectare - îmbunătățite cu backoff exponențial ca în Baileys
MAX_RECONNECT_ATTEMPTS = 10           # Crescut numărul de încercări
RECONNECT_DELAY_MS = 3000            # Întârziere inițială
MAX_RECONNECT_DELAY_MS = 60000       # Întârziere maximă
RECONNECT_DECAY_FACTOR = 1.5         # Factor de creștere pentru backoff exponențial
RECONNECT_RANDOM_FACTOR = 0.2        # Jitter pentru a preveni reconnect simultan

# QR code timeout (ms)
QR_CODE_TIMEOUT_MS = 60000

# Headere HTTP comune pentru conexiunea WebSocket
WA_DEFAULT_HEADERS = {
    "Origin": WA_ORIGIN,
    "User-Agent": WA_USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits"
}

# Message status types
class MessageStatus:
    """Constants for message status values"""
    ERROR = -1
    PENDING = 0
    SENT = 1
    DELIVERED = 2
    READ = 3

# Chat types
class ChatType:
    """Constants for chat types"""
    SOLO = 'solo'
    GROUP = 'group'
    BROADCAST = 'broadcast'
    
# Media types
class MediaType:
    """Constants for media types"""
    IMAGE = 'image'
    VIDEO = 'video'
    AUDIO = 'audio'
    DOCUMENT = 'document'
    STICKER = 'sticker'
    
# Connection states
class ConnectionState:
    """Constants for connection states"""
    DISCONNECTED = 'disconnected'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    RECONNECTING = 'reconnecting'
    DISCONNECTING = 'disconnecting'
    
# Comandă Keepalive - similară cu cea din Baileys
WA_KEEPALIVE_COMMAND = "?,,"