#!/usr/bin/env python
"""
Example script for handling media with WhatsApp using wawspy.

This script demonstrates how to send and receive different types of media
like images, documents, and videos using the improved WhatsApp Web Python library.
"""

import argparse
import logging
import os
import sys
import time

# Add parent directory to path to import wawspy when running from examples directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wawspy import WAClient, WAConnectionError, WAMessageError, WAMediaError

def main():
    """Main function to demonstrate media handling with WhatsApp."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Send media through WhatsApp')
    parser.add_argument('--to', '-t', help='Phone number to send the media to', required=True)
    parser.add_argument('--file', '-f', help='Path to the file to send', required=True)
    parser.add_argument('--caption', '-c', help='Caption for the media (optional)')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Validate file exists
    if not os.path.isfile(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create client
    client = WAClient(log_level=log_level)
    
    try:
        # Set up message callback to handle media messages
        def on_message(message):
            try:
                print(f"\nReceived message: {message}")
                
                # Check if it's a media message
                if any(key in message for key in ["imageMessage", "videoMessage", 
                                                 "audioMessage", "documentMessage"]):
                    print("This is a media message!")
                    
                    # Process and download the media
                    output_path = client.download_media_from_message(message)
                    print(f"Media downloaded to: {output_path}")
            except Exception as e:
                print(f"Error handling message: {e}")
            
        # Register callback
        client.register_callback(on_message=on_message)
        
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
        
        # Determine file type and send accordingly
        recipient = args.to
        file_path = args.file
        caption = args.caption
        
        _, file_ext = os.path.splitext(file_path.lower())
        
        # Send different types of media based on file extension
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
            print(f"Sending image to {recipient}")
            result = client.send_image(recipient, file_path, caption)
            media_type = "Image"
        elif file_ext in ['.mp4', '.3gp', '.mov']:
            print(f"Sending video to {recipient}")
            result = client.send_video(recipient, file_path, caption)
            media_type = "Video"
        elif file_ext in ['.mp3', '.ogg', '.m4a', '.wav']:
            print(f"Sending audio to {recipient}")
            result = client.send_audio(recipient, file_path)
            media_type = "Audio"
        else:
            print(f"Sending document to {recipient}")
            result = client.send_document(recipient, file_path, caption)
            media_type = "Document"
            
        print(f"{media_type} sent successfully. ID: {result['id']}")
        
        # Wait for messages (including potential media responses)
        print("\nWaiting for messages (press Ctrl+C to exit)...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nExiting message loop")
        
    except WAConnectionError as e:
        print(f"Connection error: {e}")
    except WAMessageError as e:
        print(f"Message error: {e}")
    except WAMediaError as e:
        print(f"Media error: {e}")
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
