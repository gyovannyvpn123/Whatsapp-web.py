"""
Simple WhatsApp Web client example.

This example demonstrates how to use the WhatsApp Web library to create
a simple client that can authenticate, receive QR codes, and send/receive messages.
"""

import os
import asyncio
import logging
from PIL import Image
from io import BytesIO

from whatsapp import WAClient, WAEventType
from whatsapp.utils.logger import setup_logging

async def print_qr_code(qr_data):
    """
    Display QR code for authentication
    
    Args:
        qr_data: QR code data
    """
    print("\nScan this QR code with your WhatsApp app:\n")
    
    # Try to display QR code image in terminal
    try:
        qr_image = qr_data.get('qr_image')
        if qr_image:
            img = Image.open(BytesIO(qr_image))
            
            # Convert image to ASCII art
            # This is a very simple implementation
            width, height = img.size
            aspect_ratio = height/width
            
            # Resize image, maintaining aspect ratio
            new_width = 80
            new_height = int(aspect_ratio * new_width * 0.5)
            img = img.resize((new_width, new_height))
            
            # Convert to grayscale and then to ASCII
            img = img.convert('L')
            pixels = list(img.getdata())
            
            # ASCII art - simplistic
            chars = ["  ", "░░", "▒▒", "▓▓", "██"]
            
            # Print the ASCII art
            ascii_art = ""
            for i, pixel in enumerate(pixels):
                if i % new_width == 0:
                    ascii_art += "\n"
                ascii_art += chars[min(len(chars)-1, pixel // 51)]
                
            print(ascii_art)
            
        else:
            # If can't convert to image, print data for manual QR generation
            print(f"QR Data: {qr_data.get('qr_data')}")
            print("Use an online QR code generator to visualize this data.")
            
    except Exception as e:
        print(f"Could not display QR code image: {str(e)}")
        print(f"QR Data: {qr_data.get('qr_data')}")

async def on_message(message):
    """
    Handle incoming messages
    
    Args:
        message: Message object
    """
    print(f"\nNew message from {message.to}: {message.text}")

async def on_authenticated(user_info):
    """
    Handle successful authentication
    
    Args:
        user_info: User information
    """
    print(f"\nAuthenticated as {user_info.get('name', 'user')}")
    print(f"Phone: {user_info.get('phone', 'unknown')}")

async def on_auth_failure(error):
    """
    Handle authentication failure
    
    Args:
        error: Error information
    """
    print(f"\nAuthentication failed: {error}")

async def on_connection_close(data):
    """
    Handle connection close
    
    Args:
        data: Close information
    """
    print("\nConnection closed")

async def run_client():
    """Run the WhatsApp Web client example"""
    # Create session directory if it doesn't exist
    session_path = os.path.join(os.getcwd(), "whatsapp_session")
    os.makedirs(session_path, exist_ok=True)
    
    # Create the client
    client = WAClient(session_path=session_path, log_level=logging.INFO)
    
    # Set up event handlers
    client.set_qr_callback(print_qr_code)
    client.on(WAEventType.MESSAGE, on_message)
    client.on(WAEventType.AUTHENTICATED, on_authenticated)
    client.on(WAEventType.AUTH_FAILURE, on_auth_failure)
    client.on(WAEventType.CONNECTION_CLOSE, on_connection_close)
    
    try:
        # Connect to WhatsApp Web
        print("Connecting to WhatsApp Web...")
        await client.connect()
        
        # Wait for authentication
        while not client.authenticated:
            print("Waiting for authentication...")
            await asyncio.sleep(5)
        
        print("\nWhatsApp Web client is ready!")
        
        # Auto-test sending a message (uncomment and modify with a real number to test)
        # try:
        #     test_number = "+1234567890"  # Replace with an actual number to test
        #     test_message = "Hello from WhatsApp Web Python Library!"
        #     print(f"\nAuto-testing message sending to {test_number}...")
        #     await client.send_message(test_number, test_message)
        #     print("Test message sent successfully!")
        # except Exception as e:
        #     print(f"Test message sending failed: {str(e)}")
        
        print("\nType a message to send, or 'exit' to quit")
        print("Format: [phone_number or group_id] [message]")
        print("Example: +1234567890 Hello, World!")
        
        # Simple command loop
        while True:
            user_input = await asyncio.get_running_loop().run_in_executor(
                None, input, "\n> "
            )
            
            if user_input.lower() == 'exit':
                break
                
            # Parse input
            parts = user_input.split(" ", 1)
            if len(parts) != 2:
                print("Invalid format. Use: [phone_number] [message]")
                continue
                
            recipient, message = parts
            
            try:
                # Send message
                print(f"Sending message to {recipient}...")
                await client.send_message(recipient, message)
                print("Message sent!")
            except Exception as e:
                print(f"Failed to send message: {str(e)}")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Disconnect properly
        print("Disconnecting...")
        await client.disconnect()
        print("Disconnected")

def main():
    """Main entry point"""
    # Set up logging
    setup_logging(level=logging.INFO)
    
    # Run the client
    asyncio.run(run_client())

if __name__ == "__main__":
    main()
