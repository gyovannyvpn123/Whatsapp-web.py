"""
Constants for WhatsApp Web library.
"""

# WhatsApp Web WebSocket URL - Updated to match current WhatsApp Web
# From Content-Security-Policy headers, we can see several options
WA_WEBSOCKET_URL = "wss://web.whatsapp.com:5222"

# Alternative WebSocket URLs that might work
WA_ALTERNATIVE_WS_URLS = [
    "wss://web.whatsapp.com/ws",
    "wss://web.whatsapp.com/ws/chat"
]

# WhatsApp client info - update with newer versions
WA_CLIENT_VERSION = "2.2413.7"
WA_CLIENT_TOKEN = "1vj6lkgm06dd2nh1"  # Updated token

# WhatsApp Web browser info
WA_BROWSER_NAME = "Chrome"
WA_BROWSER_VERSION = "120.0.0.0"

# HTTP origin for WebSocket connection
WA_ORIGIN = "https://web.whatsapp.com"

# User agent for WebSocket connection - Updated to more recent Chrome
WA_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# WebSocket protocols
WA_WS_PROTOCOLS = ["chat"]

# Retry settings
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY_MS = 3000

# QR code timeout (ms)
QR_CODE_TIMEOUT_MS = 60000

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
