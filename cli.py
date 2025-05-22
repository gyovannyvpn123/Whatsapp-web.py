#!/usr/bin/env python3
"""
Command-line interface for WhatsApp Web Python Library.

This module provides a simple CLI for interacting with WhatsApp Web,
allowing users to scan QR codes, send messages, and receive messages.
"""

import os
import sys
import asyncio
import logging
import argparse
import json
import time
from datetime import datetime
from io import BytesIO
from PIL import Image

# Import WhatsApp library
from whatsapp import WAClient, WAEventType
from whatsapp.utils.logger import setup_logging
from whatsapp.exceptions import (
    WAConnectionError,
    WAAuthenticationError,
    WAMessageError,
    WAEncryptionError,
    WAProtocolError
)

# ASCII art for terminal display
BANNER = r'''
 __      __.__            __          ___                   
/  \    /  \  |__ _____  |  | _______\_ |__ ______ ______  
\   \/\/   /  |  \\__  \ |  |/ /\__  \| __ \\____ \\____ \ 
 \        /|   Y  \/ __ \|    < / __ \| \_\ \  |_> >  |_> >
  \__/\  / |___|  (____  /__|_ \____  /___  /   __/|   __/ 
       \/       \/     \/     \/    \/    \/|__|   |__|    
                                                           
WhatsApp Web Python Library - CLI Tool
'''

class WhatsAppCLI:
    """Command-line interface for WhatsApp Web"""
    
    def __init__(self, session_path=None, log_level=logging.INFO):
        """
        Initialize WhatsApp CLI
        
        Args:
            session_path: Path to store session data
            log_level: Logging level
        """
        self.session_path = session_path or os.path.join(os.getcwd(), "whatsapp_session")
        os.makedirs(self.session_path, exist_ok=True)
        
        # Configure logging
        setup_logging(level=log_level)
        self.logger = logging.getLogger("whatsapp.cli")
        
        # Initialize client
        self.client = None
        self.running = False
        self.message_queue = asyncio.Queue()
        
        # Message history for display
        self.message_history = []
        self.max_history = 100
        
    async def initialize(self):
        """Initialize the WhatsApp client"""
        self.client = WAClient(session_path=self.session_path)
        
        # Set up event handlers
        self.client.set_qr_callback(self.handle_qr_code)
        self.client.on(WAEventType.MESSAGE, self.handle_message)
        self.client.on(WAEventType.AUTHENTICATED, self.handle_authenticated)
        self.client.on(WAEventType.AUTH_FAILURE, self.handle_auth_failure)
        self.client.on(WAEventType.CONNECTION_OPEN, self.handle_connection_open)
        self.client.on(WAEventType.CONNECTION_CLOSE, self.handle_connection_close)
        self.client.on(WAEventType.MESSAGE_SENT, self.handle_message_sent)
        
        print(BANNER)
        print("\nInitializing WhatsApp Web client...")
    
    async def connect(self):
        """Connect to WhatsApp Web"""
        try:
            print("Connecting to WhatsApp Web servers...")
            await self.client.connect()
            self.running = True
            return True
        except WAConnectionError as e:
            print(f"Connection error: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return False
    
    async def run(self):
        """Run the CLI main loop"""
        # Start consumer task
        consumer_task = asyncio.create_task(self.message_consumer())
        
        # Main input loop
        while self.running:
            try:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, self.get_user_input
                )
                
                # Process input
                await self.process_input(user_input)
                
            except asyncio.CancelledError:
                break
            except KeyboardInterrupt:
                print("\nExiting...")
                self.running = False
                break
            except Exception as e:
                print(f"Error processing input: {str(e)}")
        
        # Cancel consumer task
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        
        # Disconnect client
        if self.client:
            await self.client.disconnect()
    
    def get_user_input(self):
        """Get user input from console"""
        return input("\n> ")
    
    async def process_input(self, user_input):
        """
        Process user input
        
        Args:
            user_input: Command or message from user
        """
        if not user_input.strip():
            return
        
        if user_input.startswith("/"):
            # Command
            await self.process_command(user_input[1:])
        else:
            # Check if we have an active recipient
            if hasattr(self, 'current_recipient') and self.current_recipient:
                # Send message to current recipient
                await self.send_message(self.current_recipient, user_input)
            else:
                print("No active chat. Use '/chat <phone_number>' to start a chat, or '/send <phone_number> <message>' to send a message.")
    
    async def process_command(self, command):
        """
        Process a CLI command
        
        Args:
            command: Command string without the leading slash
        """
        parts = command.strip().split(" ", 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "help":
            self.show_help()
        
        elif cmd == "quit" or cmd == "exit":
            print("Exiting...")
            self.running = False
        
        elif cmd == "chat":
            if not args:
                print("Usage: /chat <phone_number>")
                return
            
            # Set current recipient
            self.current_recipient = args.strip()
            print(f"Chat active with {self.current_recipient}")
            
            # Show recent messages
            matching_messages = [
                msg for msg in self.message_history 
                if msg['to'] == self.current_recipient or msg['from'] == self.current_recipient
            ]
            if matching_messages:
                print("\nRecent messages:")
                for msg in matching_messages[-5:]:
                    direction = ">>>" if msg['from_me'] else "<<<"
                    print(f"{direction} {msg['text']}")
            else:
                print("No message history with this contact.")
        
        elif cmd == "send":
            parts = args.split(" ", 1)
            if len(parts) < 2:
                print("Usage: /send <phone_number> <message>")
                return
            
            recipient = parts[0].strip()
            message = parts[1].strip()
            
            await self.send_message(recipient, message)
        
        elif cmd == "status":
            self.show_status()
        
        elif cmd == "scan":
            if not self.client.authenticated:
                print("Requesting new QR code...")
                # This is simplified - in a real implementation,
                # we would request a new QR code from the server
                print("Please reconnect to get a new QR code.")
            else:
                print("Already authenticated.")
        
        elif cmd == "logout":
            if self.client and self.client.authenticated:
                await self.client.logout()
                print("Logged out successfully.")
            else:
                print("Not logged in.")
        
        elif cmd == "reconnect":
            if self.client:
                await self.client.disconnect()
                time.sleep(1)
                await self.client.connect()
            else:
                print("Client not initialized.")
        
        else:
            print(f"Unknown command: {cmd}")
            self.show_help()
    
    def show_help(self):
        """Show help information"""
        print("\nAvailable commands:")
        print("  /help               - Show this help message")
        print("  /chat <phone>       - Start or switch to a chat with a contact")
        print("  /send <phone> <msg> - Send a message to a specific contact")
        print("  /status             - Show connection status")
        print("  /scan               - Request a new QR code")
        print("  /logout             - Log out from WhatsApp Web")
        print("  /reconnect          - Reconnect to WhatsApp Web")
        print("  /quit or /exit      - Exit the application")
        print("\nDirect messages:")
        print("  When a chat is active, you can type messages directly")
    
    def show_status(self):
        """Show current status"""
        if not self.client:
            print("Client not initialized.")
            return
            
        status = "Authenticated" if self.client.authenticated else "Not authenticated"
        connection = "Connected" if self.client.connection.is_connected() else "Disconnected"
        
        print("\nStatus:")
        print(f"  Connection: {connection}")
        print(f"  Authentication: {status}")
        
        if self.client.authenticated and self.client.user_info:
            print(f"  User: {self.client.user_info.get('name', 'Unknown')}")
            print(f"  Phone: {self.client.user_info.get('phone', 'Unknown')}")
        
        if hasattr(self, 'current_recipient') and self.current_recipient:
            print(f"  Active chat: {self.current_recipient}")
    
    async def send_message(self, recipient, text):
        """
        Send a message to a recipient
        
        Args:
            recipient: Phone number or group ID
            text: Message text
        """
        if not self.client or not self.client.authenticated:
            print("Not authenticated. Please scan the QR code first.")
            return
        
        try:
            print(f"Sending message to {recipient}...")
            message = await self.client.send_message(recipient, text)
            
            # Store in history
            self.message_history.append({
                'id': message.id,
                'to': message.to,
                'from': self.client.user_info.get('id', 'me'),
                'from_me': True,
                'text': message.text,
                'timestamp': message.timestamp
            })
            
            # Trim history if needed
            if len(self.message_history) > self.max_history:
                self.message_history = self.message_history[-self.max_history:]
            
        except WAMessageError as e:
            print(f"Failed to send message: {str(e)}")
        except Exception as e:
            print(f"Unexpected error while sending message: {str(e)}")
    
    async def handle_qr_code(self, qr_data):
        """
        Handle QR code event
        
        Args:
            qr_data: QR code data dictionary
        """
        print("\n\nScan this QR code with your WhatsApp app:")
        
        # Try to display QR code in terminal
        try:
            qr_image = qr_data.get('qr_image')
            if qr_image:
                # Save QR code to file
                with open(os.path.join(self.session_path, "qrcode.png"), "wb") as f:
                    f.write(qr_image)
                
                print(f"QR code saved to {os.path.join(self.session_path, 'qrcode.png')}")
                
                # Try to display in terminal using ASCII art
                img = Image.open(BytesIO(qr_image))
                
                # Convert image to ASCII art
                width, height = img.size
                aspect_ratio = height/width
                
                # Resize image, maintaining aspect ratio
                new_width = 40
                new_height = int(aspect_ratio * new_width * 0.5)
                img = img.resize((new_width, new_height))
                
                # Convert to grayscale and then to ASCII
                img = img.convert('L')
                pixels = list(img.getdata())
                
                # ASCII art - simplistic
                chars = ["  ", "░░", "▒▒", "▓▓", "██"]
                
                # Print the ASCII art
                for i in range(0, len(pixels), new_width):
                    line = "".join([chars[min(len(chars)-1, pixel // 51)] for pixel in pixels[i:i+new_width]])
                    print(line)
                
            else:
                # If can't convert to image, print data for manual QR generation
                print(f"QR Data: {qr_data.get('qr_data')}")
                print("Use an online QR code generator to visualize this data.")
            
        except Exception as e:
            print(f"Could not display QR code image: {str(e)}")
            print(f"QR Data: {qr_data.get('qr_data')}")
    
    async def handle_message(self, message):
        """
        Handle incoming message event
        
        Args:
            message: Message object
        """
        # Add to queue for processing
        await self.message_queue.put(message)
    
    async def message_consumer(self):
        """Consumer task for processing incoming messages"""
        while self.running:
            try:
                # Get message from queue
                message = await self.message_queue.get()
                
                # Process message
                sender = message.to if message.from_me else message.to
                direction = ">>>" if message.from_me else "<<<"
                
                # Store in history
                self.message_history.append({
                    'id': message.id,
                    'to': message.to,
                    'from': sender,
                    'from_me': message.from_me,
                    'text': message.text,
                    'timestamp': message.timestamp
                })
                
                # Trim history if needed
                if len(self.message_history) > self.max_history:
                    self.message_history = self.message_history[-self.max_history:]
                
                # Only show if we're in a chat with this contact
                if (hasattr(self, 'current_recipient') and 
                    self.current_recipient and 
                    (self.current_recipient == message.to or self.current_recipient == sender)):
                    timestamp = datetime.fromtimestamp(message.timestamp).strftime('%H:%M:%S')
                    print(f"\n[{timestamp}] {direction} {message.text}")
                    print("> ", end="", flush=True)  # Restore prompt
                
                # Mark as done
                self.message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
    
    async def handle_authenticated(self, user_info):
        """
        Handle authentication success event
        
        Args:
            user_info: User information
        """
        print(f"\nAuthenticated as {user_info.get('name', 'user')}")
        print(f"Phone: {user_info.get('phone', 'unknown')}")
        print("\nType /help for available commands.")
    
    async def handle_auth_failure(self, error):
        """
        Handle authentication failure event
        
        Args:
            error: Error information
        """
        print(f"\nAuthentication failed: {error}")
    
    async def handle_connection_open(self, data):
        """
        Handle connection open event
        
        Args:
            data: Connection data
        """
        print("\nConnection established with WhatsApp servers.")
    
    async def handle_connection_close(self, data):
        """
        Handle connection close event
        
        Args:
            data: Close information
        """
        print("\nConnection closed.")
    
    async def handle_message_sent(self, message):
        """
        Handle message sent event
        
        Args:
            message: Sent message object
        """
        # We already handle this in send_message, no need to duplicate
        pass

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="WhatsApp Web Python CLI")
    parser.add_argument(
        "--session", 
        help="Path to session directory",
        default=os.path.join(os.getcwd(), "whatsapp_session")
    )
    parser.add_argument(
        "--log-level", 
        help="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO"
    )
    
    args = parser.parse_args()
    
    # Convert log level string to constant
    log_level = getattr(logging, args.log_level)
    
    # Create CLI
    cli = WhatsAppCLI(session_path=args.session, log_level=log_level)
    
    try:
        # Initialize and connect
        await cli.initialize()
        connected = await cli.connect()
        
        if connected:
            # Run main loop
            await cli.run()
        else:
            print("Failed to connect. Exiting.")
            
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")
    finally:
        # Ensure the client is disconnected
        if cli.client:
            await cli.client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
