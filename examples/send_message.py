#!/usr/bin/env python
"""
Example script for sending WhatsApp messages using wawspy.

This script demonstrates how to authenticate and send text messages
using the improved WhatsApp Web Python library.
"""

import argparse
import logging
import os
import sys
import time

# Add parent directory to path to import wawspy when running from examples directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wawspy import WAClient, WAConnectionError, WAMessageError

def main():
    """Main function to demonstrate sending a WhatsApp message."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Send a WhatsApp message')
    parser.add_argument('--to', '-t', help='Phone number to send the message to', required=True)
    parser.add_argument('--message', '-m', help='Message text to send', required=True)
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create client
    client = WAClient(log_level=log_level)
    
    try:
        # Set up custom QR callback (optional)
        def on_qr_code(qr_data):
            print("\nScan this QR code with WhatsApp on your phone:")
            print(f"QR data: {qr_data}")
            # Here you could also use a library to generate a QR code image
            # or save the data to display it in another way
        
        # Set up message callback (optional)
        def on_message(message):
            print(f"\nReceived message: {message.get('body', 'No body')}")
            print(f"From: {message.get('from', 'Unknown')}")
            
        # Register callbacks
        client.register_callback("qr_code", on_qr_code)
        client.register_callback("message", on_message)
        
        # Connect to WhatsApp Web
        print("Connecting to WhatsApp Web...")
        client.connect()
        
        # Wait for authentication
        print("Please authenticate by scanning the QR code with WhatsApp on your phone")
        authenticated = client.wait_for_authentication(timeout=120)
        
        if not authenticated:
            print("Authentication failed or timed out")
            sys.exit(1)
            
        print("Authentication successful!")
        
        # Send message
        recipient = args.to
        message_text = args.message
        
        print(f"Sending message to {recipient}: {message_text}")
        result = client.send_message(recipient, message_text)
        
        print(f"Message sent successfully. ID: {result['id']}")
        
        # Wait a bit to make sure message is delivered
        print("Waiting for message delivery...")
        time.sleep(5)
        
    except WAConnectionError as e:
        print(f"Connection error: {e}")
    except WAMessageError as e:
        print(f"Message error: {e}")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Disconnect
        print("Disconnecting...")
        if client:
            client.disconnect()
        print("Done.")

if __name__ == "__main__":
    main()
