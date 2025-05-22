"""
Protocol binar pentru WhatsApp Web.

Acest modul implementează codificarea și decodificarea protocolului binar
utilizat de WhatsApp Web pentru comunicarea cu serverul.
"""

import base64
import json
import logging
import struct
import io
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Tuple, BinaryIO

from .utils import get_logger

class WANodeType(Enum):
    """Tipuri de noduri în protocolul WhatsApp."""
    LIST = 0
    STREAM = 1
    BINARY = 2
    DICTIONARY = 3
    JID = 4
    TEXT = 5
    

class WATag:
    """Taguri pentru protocolul WhatsApp Web Binary."""
    LIST_EMPTY = 0
    DICTIONARY_0 = 236
    DICTIONARY_1 = 237
    DICTIONARY_2 = 238
    DICTIONARY_3 = 239
    LIST_8 = 248
    LIST_16 = 249
    JID_PAIR = 250
    HEX_8 = 251
    BINARY_8 = 252
    BINARY_20 = 253
    BINARY_32 = 254
    NIBBLE_8 = 255
    SINGLE_BYTE_MAX = 256
    PACKED_MAX = 254

    # Tokens WhatsApp
    TOKENS = [
        None, None, None, None, None, "5", "6", "7", "8", "9", "10", None, "12", None, None, None,
        "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31",
        " ", "1", "2", "3", "4", "5", "6", "7", "8", "9", ":", ";", "<", "=", ">", "?",
        "@", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O",
        "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "[", "\\", "]", "^", "_",
        "`", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o",
        "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "{", "|", "}", "~", None,
        # Tokens single-byte pentru dicționar
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "-", ".", "0", "1", "2", "3",
        "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
        "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p",
        "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "À", "Á", "Â", "Ã", "Ä", "Å",
        "à", "á", "â", "ã", "ä", "å", "Ç", "È", "É", "Ê", "Ë", "ç", "è", "é", "ê", "ë",
        "Ì", "Í", "Î", "Ï", "ì", "í", "î", "ï", "Ò", "Ó", "Ô", "Õ", "Ö", "Ø", "ò", "ó",
        "ô", "õ", "ö", "ø", "Ù", "Ú", "Û", "Ü", "ù", "ú", "û", "ü", "ÿ", "Ñ", "ñ", None,
        
        # Double-byte tokens pentru dicționar
        "account", "ack", "action", "active", "add", "after", "all", "allow", "apple", "audio", "auth", "author", "available", "bad-protocol", "bad-request", "before", "bits", "broadcast", "cat", "category", "challenge", "chat", "clear", "code", "composing", "contacts", "count", "create", "creation", "default", "delay", "delete", "delivered", "deny", "device", "digest", "dir", "directives", "direct_path", "disable", "duplicate", "duration", "e2e_encrypted", "encoding", "encrypt", "error", "expiration", "expired", "fail", "failure", "false", "favorites", "feature", "features", "first", "forwarded", "from", "future", "g.us", "get", "google", "group", "groups", "groups_v2", "height", "host", "id", "identity", "image", "in", "index", "init", "intent", "internal-server-error", "ip", "ip_network", "iq", "jid", "kind", "last", "latest", "latitude", "length", "location", "log", "longitude", "max", "media", "message", "message-id", "message_type", "meta", "mime-type", "mode", "modify", "mute", "name", "notification", "notify", "off", "on", "outgoing", "owner", "participant", "paused", "picture", "ping", "platform", "played", "poll", "port", "presence", "preview", "profile", "props", "query", "raw", "read", "read-receipts", "reason", "receipt", "relay", "remote-server-error", "remove", "request", "required", "resource", "resource-conflict", "resource-constraint", "response", "result", "retry", "rim", "s.whatsapp.net", "seconds", "server", "server-error", "service-unavailable", "set", "silent", "size", "state", "status", "storage", "stream:error", "subject", "subscribe", "success", "sync", "t", "text", "timeout", "timestamp", "true", "type", "unavailable", "unsubscribe", "update", "uri", "url", "user", "user-not-found", "value", "version", "video", "web", "width", "xml", "xmpp-error", "xmlns", "xmlns:stream", "1.0"
    ]

    @classmethod
    def is_list(cls, tag: int) -> bool:
        """Verifică dacă tag-ul indică o listă."""
        return tag == cls.LIST_EMPTY or tag == cls.LIST_8 or tag == cls.LIST_16
    
    @classmethod
    def is_dict(cls, tag: int) -> bool:
        """Verifică dacă tag-ul indică un dicționar."""
        return tag >= cls.DICTIONARY_0 and tag <= cls.DICTIONARY_3


class WABinaryDecoder:
    """
    Decodificator pentru protocolul binar WhatsApp.
    
    Acest decodificator transformă datele binare WhatsApp în structuri de date Python.
    """
    
    def __init__(self, buffer: Union[bytes, BinaryIO]):
        """
        Inițializează decodificatorul.
        
        Args:
            buffer: Buffer-ul de date binare sau un obiect file-like cu date binare
        """
        self.logger = get_logger("WABinaryDecoder")
        
        if isinstance(buffer, bytes):
            self.buffer = io.BytesIO(buffer)
        else:
            self.buffer = buffer
            
        self.dict_offset_index = 0
    
    def read_byte(self) -> int:
        """Citește un byte din buffer."""
        return struct.unpack("!B", self.buffer.read(1))[0]
    
    def read_int16(self) -> int:
        """Citește un int de 16 biți din buffer."""
        return struct.unpack("!H", self.buffer.read(2))[0]
    
    def read_int20(self) -> int:
        """Citește un int de 20 biți din buffer."""
        b1 = self.read_byte()
        b2 = self.read_byte()
        b3 = self.read_byte()
        
        # Combinăm cei 20 de biți
        val = ((b1 & 0x0F) << 16) | (b2 << 8) | b3
        return val
    
    def read_int32(self) -> int:
        """Citește un int de 32 biți din buffer."""
        return struct.unpack("!I", self.buffer.read(4))[0]
    
    def read_string(self, length: int) -> str:
        """
        Citește un string de lungime specificată.
        
        Args:
            length: Lungimea string-ului în bytes
            
        Returns:
            str: String-ul citit
        """
        return self.buffer.read(length).decode('utf-8')
    
    def read_list_size(self, tag: int) -> int:
        """
        Citește dimensiunea unei liste.
        
        Args:
            tag: Tag-ul listei
            
        Returns:
            int: Dimensiunea listei
        """
        if tag == WATag.LIST_EMPTY:
            return 0
        elif tag == WATag.LIST_8:
            return self.read_byte()
        elif tag == WATag.LIST_16:
            return self.read_int16()
        else:
            raise ValueError(f"Invalid list tag: {tag}")
    
    def decode_nibble(self, string_tag: int) -> str:
        """
        Decodifică un nibble (4 biți).
        
        Args:
            string_tag: Tag-ul string-ului
            
        Returns:
            str: String-ul decodificat
        """
        if string_tag >= 0 and string_tag < WATag.SINGLE_BYTE_MAX:
            if string_tag >= 0 and string_tag < len(WATag.TOKENS):
                token = WATag.TOKENS[string_tag]
                if token:
                    return token
            
            self.logger.warning(f"Token invalid la nibble: {string_tag}")
            return ""
        
        throw = False
        switch = string_tag & 0xF0
        
        if switch == WATag.NIBBLE_8:
            length = self.read_byte()
            buffer = self.buffer.read(length // 2)
            
            # Decodare nibble 4 biți per caracter
            res = ""
            for b in buffer:
                # Primul nibble
                val = (b & 0xF0) >> 4
                if val > 9:
                    val = 10 + (val - 10)
                res += chr(val + ord('0'))
                
                # Al doilea nibble (dacă nu este padding)
                val = b & 0x0F
                if val > 9:
                    val = 10 + (val - 10)
                res += chr(val + ord('0'))
                
            return res
        
        elif switch == WATag.HEX_8:
            length = self.read_byte()
            return self.buffer.read(length).hex()
        
        throw = True
        if throw:
            raise ValueError(f"Invalid string tag: {string_tag}")
    
    def decode_packed_bits(self, string_tag: int) -> str:
        """
        Decodifică biți împachetați.
        
        Args:
            string_tag: Tag-ul string-ului
            
        Returns:
            str: String-ul decodificat
        """
        value = ""
        start_byte = self.read_byte()
        for i in range(string_tag & 0x7F):
            value += WATag.TOKENS[(0xFF & start_byte) + self.dict_offset_index]
            start_byte = self.read_byte()
        
        return value
    
    def get_token_double_byte(self, index: int) -> str:
        """
        Obține un token double-byte.
        
        Args:
            index: Indexul tokenului
            
        Returns:
            str: Tokenul
        """
        # Ajustăm indexul pentru a obține tokenul corect
        adjusted_index = index - WATag.SINGLE_BYTE_MAX
        if 0 <= adjusted_index < len(WATag.TOKENS) - WATag.SINGLE_BYTE_MAX:
            token = WATag.TOKENS[WATag.SINGLE_BYTE_MAX + adjusted_index]
            if token:
                return token
        
        self.logger.warning(f"Token invalid la double-byte: {index}")
        return ""
    
    def read_packed_bytes(self, tag: int) -> bytes:
        """
        Citește bytes împachetați.
        
        Args:
            tag: Tag-ul datelor
            
        Returns:
            bytes: Datele citite
        """
        if tag == WATag.BINARY_8:
            size = self.read_byte()
            return self.buffer.read(size)
        elif tag == WATag.BINARY_20:
            size = self.read_int20()
            return self.buffer.read(size)
        elif tag == WATag.BINARY_32:
            size = self.read_int32()
            return self.buffer.read(size)
        else:
            raise ValueError(f"Invalid binary tag: {tag}")
    
    def decode_jid(self, tag: int) -> str:
        """
        Decodifică un JID (Jabber ID).
        
        Args:
            tag: Tag-ul JID-ului
            
        Returns:
            str: JID-ul decodificat
        """
        if tag == WATag.JID_PAIR:
            user = self.read_string(self.read_byte())
            server = self.read_string(self.read_byte())
            return f"{user}@{server}"
        else:
            raise ValueError(f"Invalid JID tag: {tag}")
    
    def next_node(self) -> Dict[str, Any]:
        """
        Citește următorul nod din buffer.
        
        Returns:
            dict: Nodul citit
        """
        list_size = 0
        tag = self.read_byte()
        
        if tag == WATag.LIST_EMPTY:
            list_size = 0
        elif tag == WATag.LIST_8:
            list_size = self.read_byte()
        elif tag == WATag.LIST_16:
            list_size = self.read_int16()
        else:
            if tag == WATag.STREAM:
                attributes = {}
                tag = self.read_byte()
                list_size = self.read_list_size(tag)
                for _ in range(list_size):
                    attributes[self.read_string(self.read_byte())] = self.read_string(self.read_byte())
                
                return {
                    "tag": "stream",
                    "attrs": attributes
                }
            else:
                raise ValueError(f"Expecting list but got: {tag}")
        
        if list_size == 0:
            return None
        
        # Citim descrierea nodului
        desc_type = self.read_byte()
        descriptor_len = 0
        
        if WATag.is_list(desc_type):
            descriptor_len = self.read_list_size(desc_type)
        else:
            raise ValueError(f"Invalid descriptor: {desc_type}")
        
        if descriptor_len == 0:
            return None
        
        # Tipul de nod
        type_str = None
        type_byte = self.read_byte()
        
        if type_byte == WATag.JID_PAIR:
            type_str = self.decode_jid(type_byte)
        elif type_byte < WATag.DICTIONARY_0:
            if type_byte == 0:
                type_str = "0"
            else:
                type_str = self.decode_nibble(type_byte)
        else:
            switch = type_byte & 0xF0
            
            if switch == WATag.DICTIONARY_0 or switch == WATag.DICTIONARY_1 or switch == WATag.DICTIONARY_2 or switch == WATag.DICTIONARY_3:
                # Calculăm offsetul dicționarului
                self.dict_offset_index = (type_byte & 0x0F) * 256
                type_byte = self.read_byte()
                dict_index = type_byte | self.dict_offset_index
                
                if 0 <= dict_index < len(WATag.TOKENS):
                    token = WATag.TOKENS[dict_index]
                    if token:
                        type_str = token
        
        if type_str is None:
            raise ValueError(f"Invalid node type: {type_byte}")
        
        # Citim atributele
        attrs = {}
        attrs_len = descriptor_len - 1
        
        for _ in range(attrs_len // 2):
            key_byte = self.read_byte()
            key = None
            
            if key_byte == WATag.JID_PAIR:
                key = self.decode_jid(key_byte)
            elif WATag.is_dict(key_byte):
                switch = key_byte & 0xF0
                
                if switch == WATag.DICTIONARY_0 or switch == WATag.DICTIONARY_1 or switch == WATag.DICTIONARY_2 or switch == WATag.DICTIONARY_3:
                    self.dict_offset_index = (key_byte & 0x0F) * 256
                    key_byte = self.read_byte()
                    dict_index = key_byte | self.dict_offset_index
                    
                    if 0 <= dict_index < len(WATag.TOKENS):
                        token = WATag.TOKENS[dict_index]
                        if token:
                            key = token
            else:
                if key_byte == 0:
                    key = "0"
                else:
                    key = self.decode_nibble(key_byte)
            
            if key is None:
                raise ValueError(f"Invalid attribute key: {key_byte}")
            
            # Citim valoarea atributului
            value_byte = self.read_byte()
            value = None
            
            if value_byte == WATag.JID_PAIR:
                value = self.decode_jid(value_byte)
            elif WATag.is_dict(value_byte):
                switch = value_byte & 0xF0
                
                if switch == WATag.DICTIONARY_0 or switch == WATag.DICTIONARY_1 or switch == WATag.DICTIONARY_2 or switch == WATag.DICTIONARY_3:
                    self.dict_offset_index = (value_byte & 0x0F) * 256
                    value_byte = self.read_byte()
                    dict_index = value_byte | self.dict_offset_index
                    
                    if 0 <= dict_index < len(WATag.TOKENS):
                        token = WATag.TOKENS[dict_index]
                        if token:
                            value = token
            elif value_byte == WATag.BINARY_8 or value_byte == WATag.BINARY_20 or value_byte == WATag.BINARY_32:
                value = self.read_packed_bytes(value_byte)
            else:
                if value_byte == 0:
                    value = "0"
                else:
                    value = self.decode_nibble(value_byte)
            
            if value is None:
                raise ValueError(f"Invalid attribute value: {value_byte}")
            
            attrs[key] = value
        
        # Citim conținutul nodului (copiii)
        content = None
        if list_size > 1:
            content_type = self.read_byte()
            
            if content_type == WATag.LIST_EMPTY or content_type == WATag.LIST_8 or content_type == WATag.LIST_16:
                content_size = self.read_list_size(content_type)
                children = []
                
                for _ in range(content_size):
                    child = self.next_node()
                    if child:
                        children.append(child)
                
                content = children
            elif content_type == WATag.BINARY_8 or content_type == WATag.BINARY_20 or content_type == WATag.BINARY_32:
                content = self.read_packed_bytes(content_type)
            elif content_type == WATag.JID_PAIR:
                content = self.decode_jid(content_type)
            else:
                content = self.decode_nibble(content_type)
        
        # Construim nodul final
        return {
            "tag": type_str,
            "attrs": attrs,
            "content": content
        }
    
    def decode(self) -> Dict[str, Any]:
        """
        Decodifică buffer-ul complet.
        
        Returns:
            dict: Mesajul decodificat
        """
        try:
            return self.next_node()
        except Exception as e:
            self.logger.error(f"Eroare la decodificare: {e}")
            raise


class WABinaryEncoder:
    """
    Codificator pentru protocolul binar WhatsApp.
    
    Acest codificator transformă structuri de date Python în date binare WhatsApp.
    """
    
    def __init__(self):
        """Inițializează codificatorul."""
        self.logger = get_logger("WABinaryEncoder")
        self.buffer = bytearray()
        self.dict_offset_index = 0
    
    def write_byte(self, value: int) -> None:
        """
        Scrie un byte în buffer.
        
        Args:
            value: Valoarea de scris
        """
        self.buffer.extend(struct.pack("!B", value & 0xFF))
    
    def write_int16(self, value: int) -> None:
        """
        Scrie un int de 16 biți în buffer.
        
        Args:
            value: Valoarea de scris
        """
        self.buffer.extend(struct.pack("!H", value & 0xFFFF))
    
    def write_int20(self, value: int) -> None:
        """
        Scrie un int de 20 biți în buffer.
        
        Args:
            value: Valoarea de scris
        """
        b1 = (value >> 16) & 0x0F
        b2 = (value >> 8) & 0xFF
        b3 = value & 0xFF
        
        self.write_byte(b1)
        self.write_byte(b2)
        self.write_byte(b3)
    
    def write_int32(self, value: int) -> None:
        """
        Scrie un int de 32 biți în buffer.
        
        Args:
            value: Valoarea de scris
        """
        self.buffer.extend(struct.pack("!I", value & 0xFFFFFFFF))
    
    def write_string(self, value: str) -> None:
        """
        Scrie un string în buffer.
        
        Args:
            value: String-ul de scris
        """
        self.buffer.extend(value.encode('utf-8'))
    
    def write_jid(self, value: str) -> None:
        """
        Scrie un JID în buffer.
        
        Args:
            value: JID-ul de scris (format user@server)
        """
        if '@' not in value:
            raise ValueError(f"Invalid JID: {value}")
        
        user, server = value.split('@', 1)
        
        self.write_byte(WATag.JID_PAIR)
        self.write_byte(len(user))
        self.write_string(user)
        self.write_byte(len(server))
        self.write_string(server)
    
    def write_bytes(self, value: bytes) -> None:
        """
        Scrie bytes în buffer.
        
        Args:
            value: Bytes de scris
        """
        size = len(value)
        
        if size < 256:
            self.write_byte(WATag.BINARY_8)
            self.write_byte(size)
        elif size < (1 << 20):
            self.write_byte(WATag.BINARY_20)
            self.write_int20(size)
        else:
            self.write_byte(WATag.BINARY_32)
            self.write_int32(size)
            
        self.buffer.extend(value)
    
    def write_list_start(self, size: int) -> None:
        """
        Scrie începutul unei liste.
        
        Args:
            size: Dimensiunea listei
        """
        if size == 0:
            self.write_byte(WATag.LIST_EMPTY)
        elif size < 256:
            self.write_byte(WATag.LIST_8)
            self.write_byte(size)
        else:
            self.write_byte(WATag.LIST_16)
            self.write_int16(size)
    
    def find_token_index(self, token: str) -> int:
        """
        Găsește indexul unui token în lista de tokens.
        
        Args:
            token: Tokenul de căutat
            
        Returns:
            int: Indexul tokenului sau 256 dacă nu este găsit
        """
        try:
            return WATag.TOKENS.index(token)
        except ValueError:
            return 256
    
    def write_token(self, token: str) -> None:
        """
        Scrie un token în buffer.
        
        Args:
            token: Tokenul de scris
        """
        if not token:
            self.write_byte(0)
            return
        
        index = self.find_token_index(token)
        
        if index < WATag.SINGLE_BYTE_MAX:
            self.write_byte(index)
        elif index < 256 * 4 + WATag.SINGLE_BYTE_MAX:
            index -= WATag.SINGLE_BYTE_MAX
            index_high = index // 256
            index_low = index % 256
            
            dict_index = WATag.DICTIONARY_0 + index_high
            self.write_byte(dict_index)
            self.write_byte(index_low)
        else:
            # Scriem ca string normal
            self.write_nibble(token)
    
    def write_nibble(self, value: str) -> None:
        """
        Scrie un string ca nibble.
        
        Args:
            value: String-ul de scris
        """
        # Dacă string-ul conține doar cifre, folosim NIBBLE_8
        if value.isdigit():
            self.write_byte(WATag.NIBBLE_8)
            # Calculăm lungimea (fiecare caracter este 4 biți)
            length = len(value)
            if length % 2 == 1:
                length += 1
            
            self.write_byte(length)
            
            # Împachetăm cifrele în nibbles
            i = 0
            while i < len(value):
                digit1 = int(value[i])
                digit2 = 0xF  # padding
                
                if i + 1 < len(value):
                    digit2 = int(value[i + 1])
                
                byte = (digit1 << 4) | digit2
                self.write_byte(byte)
                i += 2
        else:
            # Altfel, codificăm ca bytes simple
            bytes_val = value.encode('utf-8')
            size = len(bytes_val)
            
            if size < 256:
                self.write_byte(WATag.BINARY_8)
                self.write_byte(size)
            elif size < (1 << 20):
                self.write_byte(WATag.BINARY_20)
                self.write_int20(size)
            else:
                self.write_byte(WATag.BINARY_32)
                self.write_int32(size)
                
            self.buffer.extend(bytes_val)
    
    def encode_node(self, node: Dict[str, Any]) -> None:
        """
        Codifică un nod în buffer.
        
        Args:
            node: Nodul de codificat
        """
        if not node:
            self.write_list_start(0)
            return
        
        # Calculăm numărul de atribute care trebuie scrise
        attrs_count = 0
        if node.get("attrs"):
            attrs_count = len(node["attrs"])
        
        # Calculăm numărul total de elemente care trebuie scrise
        list_size = 1  # pentru tag
        list_size += attrs_count * 2  # câte 2 pentru fiecare atribut (cheie și valoare)
        
        # Dacă există conținut, adăugăm 1
        has_content = "content" in node and node["content"] is not None
        if has_content:
            list_size += 1
        
        # Scriem începutul listei
        self.write_list_start(list_size)
        
        # Scriem descrierea nodului (tag + atributele)
        attrs_list_size = 1 + attrs_count * 2
        self.write_list_start(attrs_list_size)
        
        # Scriem tag-ul
        if '@' in node["tag"]:
            self.write_jid(node["tag"])
        else:
            self.write_token(node["tag"])
        
        # Scriem atributele
        if attrs_count > 0:
            for key, value in node["attrs"].items():
                # Scriem cheia
                self.write_token(key)
                
                # Scriem valoarea
                if isinstance(value, str):
                    if '@' in value and ('jid' in key.lower() or key.lower() == 'participant'):
                        self.write_jid(value)
                    else:
                        self.write_token(value)
                elif isinstance(value, bytes):
                    self.write_bytes(value)
                elif isinstance(value, int):
                    self.write_token(str(value))
                elif isinstance(value, bool):
                    self.write_token("true" if value else "false")
                else:
                    self.logger.warning(f"Tip de atribut nesuportat: {type(value)}")
                    self.write_token(str(value))
        
        # Scriem conținutul
        if has_content:
            content = node["content"]
            
            if isinstance(content, str):
                if '@' in content:
                    self.write_jid(content)
                else:
                    self.write_token(content)
            elif isinstance(content, bytes):
                self.write_bytes(content)
            elif isinstance(content, list):
                # Lista de noduri copil
                children = content
                self.write_list_start(len(children))
                
                for child in children:
                    self.encode_node(child)
            else:
                self.logger.warning(f"Tip de conținut nesuportat: {type(content)}")
                self.write_token(str(content))
    
    def encode(self, node: Dict[str, Any]) -> bytes:
        """
        Codifică un nod complet.
        
        Args:
            node: Nodul de codificat
            
        Returns:
            bytes: Datele binare codificate
        """
        try:
            self.buffer = bytearray()
            self.encode_node(node)
            return bytes(self.buffer)
        except Exception as e:
            self.logger.error(f"Eroare la codificare: {e}")
            raise


class WANode:
    """
    Clasa pentru manipularea nodurilor de protocol WhatsApp.
    
    Această clasă furnizează metode helper pentru construirea și manipularea
    nodurilor de protocol în format simplu.
    """
    
    @staticmethod
    def create(tag: str, attrs: Optional[Dict[str, Any]] = None, content: Any = None) -> Dict[str, Any]:
        """
        Creează un nod nou.
        
        Args:
            tag: Tag-ul nodului
            attrs: Atributele nodului (opțional)
            content: Conținutul nodului (opțional)
            
        Returns:
            dict: Nodul creat
        """
        return {
            "tag": tag,
            "attrs": attrs or {},
            "content": content
        }
    
    @staticmethod
    def add_child(node: Dict[str, Any], child: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adaugă un nod copil la un nod părinte.
        
        Args:
            node: Nodul părinte
            child: Nodul copil
            
        Returns:
            dict: Nodul părinte actualizat
        """
        if "content" not in node:
            node["content"] = []
        
        if not isinstance(node["content"], list):
            # Convertim conținutul existent într-o listă
            node["content"] = [node["content"]]
        
        node["content"].append(child)
        return node
    
    @staticmethod
    def encode(node: Dict[str, Any]) -> bytes:
        """
        Codifică un nod în format binar.
        
        Args:
            node: Nodul de codificat
            
        Returns:
            bytes: Datele binare
        """
        encoder = WABinaryEncoder()
        return encoder.encode(node)
    
    @staticmethod
    def decode(data: Union[bytes, BinaryIO]) -> Dict[str, Any]:
        """
        Decodifică date binare într-un nod.
        
        Args:
            data: Datele binare
            
        Returns:
            dict: Nodul decodificat
        """
        decoder = WABinaryDecoder(data)
        return decoder.decode()