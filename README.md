# WhatsApp Web Python Library

O bibliotecă Python pură pentru comunicarea cu WhatsApp Web, cu suport complet pentru criptarea Signal Protocol.

## Caracteristici

- Autentificare prin cod QR
- Autentificare prin cod de asociere (pairing code)
- Conexiune WebSocket la serverele WhatsApp Web
- Criptare completă Signal Protocol (Double Ratchet, X3DH)
- Suport pentru parsarea/serializarea Protobuf binară
- Trimiterea/primirea de mesaje text
- Arhitectură bazată pe evenimente pentru evenimente în timp real

## Instalare

```bash
pip install whatsapp-web-py
```

## Exemplu rapid

```python
import asyncio
from whatsapp import WAClient, WAEventType

async def on_message_received(message_data):
    print(f"Mesaj nou primit: {message_data}")

async def on_qr_code_received(qr_data):
    print(f"Scanează acest cod QR cu WhatsApp: {qr_data}")

async def main():
    # Creează clientul
    client = WAClient(session_path="./whatsapp_session")
    
    # Configurează handlerii de evenimente
    client.set_qr_callback(on_qr_code_received)
    client.on(WAEventType.MESSAGE, on_message_received)
    
    # Conectează
    await client.connect()
    
    # Așteaptă autentificarea
    while not client.authenticated:
        await asyncio.sleep(1)
    
    # Trimite un mesaj
    await client.send_message("+1234567890", "Salut de la WhatsApp Web Python!")
    
    # Menține rularea
    await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
```

## Licență

MIT License

## Autor

gyovannyvpn123
