"""
Media handling module for WhatsApp Web communications.

This module provides functionality for sending and receiving media files
like images, videos, documents, and audio through WhatsApp Web.
"""

import base64
import hashlib
import json
import logging
import mimetypes
import os
import requests
import time
from io import BytesIO
from typing import Dict, Optional, Tuple, Union, BinaryIO, Any

from .errors import WAMediaError
from .utils import generate_random_filename

logger = logging.getLogger(__name__)

class WAMedia:
    """
    WhatsApp Web media handler.
    
    This class handles the uploading, downloading, and processing of 
    media files for WhatsApp Web communications.
    """
    
    # Media types supported by WhatsApp
    MEDIA_IMAGE = "image"
    MEDIA_VIDEO = "video"
    MEDIA_AUDIO = "audio"
    MEDIA_DOCUMENT = "document"
    MEDIA_STICKER = "sticker"
    
    # MIME type mapping
    MIME_TYPES = {
        MEDIA_IMAGE: ["image/jpeg", "image/png", "image/gif"],
        MEDIA_VIDEO: ["video/mp4", "video/3gpp"],
        MEDIA_AUDIO: ["audio/aac", "audio/mp4", "audio/amr", "audio/mpeg", "audio/ogg"],
        MEDIA_DOCUMENT: ["application/pdf", "application/msword", "text/plain"],
        MEDIA_STICKER: ["image/webp"]
    }
    
    # Max file sizes (in bytes)
    MAX_SIZE = {
        MEDIA_IMAGE: 16 * 1024 * 1024,      # 16MB
        MEDIA_VIDEO: 16 * 1024 * 1024,      # 16MB
        MEDIA_AUDIO: 16 * 1024 * 1024,      # 16MB
        MEDIA_DOCUMENT: 100 * 1024 * 1024,  # 100MB
        MEDIA_STICKER: 1 * 1024 * 1024      # 1MB
    }
    
    def __init__(self, client):
        """
        Initialize the media handler.
        
        Args:
            client: The WhatsApp Web client instance
        """
        self.client = client
        self.upload_url = "https://mmg.whatsapp.net/upload"
        self.media_conn_info = None
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def determine_media_type(self, file_path: str) -> Tuple[str, str]:
        """
        Determine the media type and mime type based on file extension.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            tuple: (media_type, mime_type)
            
        Raises:
            WAMediaError: If the file type is not supported
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if not mime_type:
            raise WAMediaError(f"Could not determine MIME type for file: {file_path}")
        
        for media_type, mime_types in self.MIME_TYPES.items():
            if any(mime_type.startswith(m.split('/')[0]) for m in mime_types):
                return media_type, mime_type
                
        raise WAMediaError(f"Unsupported file type: {mime_type}")
    
    def prepare_media(self, file_path: str) -> Dict[str, Any]:
        """
        Prepare media for sending by calculating hashes and other metadata.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            dict: Media metadata including file size, hashes, etc.
            
        Raises:
            WAMediaError: If there's an error preparing the media
        """
        try:
            if not os.path.isfile(file_path):
                raise WAMediaError(f"File not found: {file_path}")
                
            file_size = os.path.getsize(file_path)
            media_type, mime_type = self.determine_media_type(file_path)
            
            if file_size > self.MAX_SIZE.get(media_type, 16 * 1024 * 1024):
                raise WAMediaError(f"File exceeds maximum size for {media_type}")
                
            # Calculate file hashes
            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                # Read and update hash in chunks to avoid loading large files into memory
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
                    
            file_hash = sha256_hash.hexdigest()
            
            media_key = os.urandom(32)
            media_key_base64 = base64.b64encode(media_key).decode('utf-8')
            
            return {
                "file_path": file_path,
                "file_size": file_size,
                "file_hash": file_hash,
                "media_key": media_key_base64,
                "media_type": media_type,
                "mime_type": mime_type
            }
            
        except Exception as e:
            logger.error(f"Error preparing media: {e}")
            raise WAMediaError(f"Failed to prepare media: {e}")
    
    def upload_media(self, file_path: str) -> Dict[str, Any]:
        """
        Upload media to WhatsApp servers.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            dict: Upload response including media URL
            
        Raises:
            WAMediaError: If there's an error uploading the media
        """
        try:
            # Prepare media metadata
            media_info = self.prepare_media(file_path)
            media_type = media_info["media_type"]
            mime_type = media_info["mime_type"]
            file_size = media_info["file_size"]
            
            # Request upload URL and credentials
            if not self.media_conn_info:
                # In a real implementation, this would get the media connection info
                # from the WhatsApp server through the client's connection
                raise WAMediaError("Media connection info not available")
                
            # Prepare upload request
            upload_url = f"{self.upload_url}/{media_type}"
            headers = {
                "Origin": "https://web.whatsapp.com",
                "Referer": "https://web.whatsapp.com/",
            }
            
            # This would include authentication tokens from media_conn_info
            auth_info = {}
            
            # Upload the file
            with open(file_path, 'rb') as f:
                for attempt in range(self.max_retries):
                    try:
                        logger.info(f"Uploading {media_type} file ({file_size} bytes)")
                        
                        # In a real implementation, this would use the actual
                        # WhatsApp upload endpoint and protocol
                        # This is a placeholder for the upload request
                        # response = requests.post(
                        #     upload_url,
                        #     headers=headers,
                        #     data=auth_info,
                        #     files={"file": (os.path.basename(file_path), f, mime_type)}
                        # )
                        
                        # # Check response
                        # if response.status_code == 200:
                        #     upload_result = response.json()
                        #     return {
                        #         "url": upload_result.get("url"),
                        #         "mimetype": mime_type,
                        #         "filehash": media_info["file_hash"],
                        #         "filesize": file_size,
                        #         "mediaKey": media_info["media_key"],
                        #         "type": media_type
                        #     }
                        # else:
                        #     logger.warning(f"Upload failed with status {response.status_code}")
                        
                        # Placeholder for successful upload result
                        # In a real implementation, this would be returned by the server
                        return {
                            "url": f"https://mmg.whatsapp.net/{media_type}/{media_info['file_hash']}",
                            "mimetype": mime_type,
                            "filehash": media_info["file_hash"],
                            "filesize": file_size,
                            "mediaKey": media_info["media_key"],
                            "type": media_type
                        }
                        
                    except Exception as e:
                        logger.error(f"Upload attempt {attempt+1} failed: {e}")
                        if attempt < self.max_retries - 1:
                            time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                        else:
                            raise
                            
            raise WAMediaError("All upload attempts failed")
            
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            raise WAMediaError(f"Failed to upload media: {e}")
    
    def download_media(self, message: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Download media from a received message.
        
        Args:
            message: Message containing media
            output_path: Optional path to save the media
            
        Returns:
            str: Path to the downloaded media file
            
        Raises:
            WAMediaError: If there's an error downloading the media
        """
        try:
            # Extract media info from message
            if not message.get("mediaUrl"):
                raise WAMediaError("Message does not contain media URL")
                
            media_url = message["mediaUrl"]
            media_key = message.get("mediaKey")
            mime_type = message.get("mimetype", "application/octet-stream")
            file_name = message.get("fileName")
            
            # Determine file extension from mime type
            extension = mimetypes.guess_extension(mime_type) or ""
            
            # Generate output filename if not provided
            if not output_path:
                if file_name:
                    output_path = file_name
                else:
                    output_path = generate_random_filename("media", extension)
                    
            # Download the file
            headers = {
                "Origin": "https://web.whatsapp.com",
                "Referer": "https://web.whatsapp.com/",
            }
            
            # This would include authentication info
            auth_info = {}
            
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Downloading media from {media_url}")
                    
                    # In a real implementation, this would use the actual
                    # WhatsApp download protocol
                    # This is a placeholder for the download request
                    # response = requests.get(
                    #     media_url,
                    #     headers=headers,
                    #     params=auth_info
                    # )
                    
                    # # Check response
                    # if response.status_code == 200:
                    #     # Decrypt media using media_key if available
                    #     content = response.content
                    #     if media_key:
                    #         # Decryption would be implemented here
                    #         pass
                            
                    #     # Save to file
                    #     with open(output_path, 'wb') as f:
                    #         f.write(content)
                            
                    #     return output_path
                    # else:
                    #     logger.warning(f"Download failed with status {response.status_code}")
                    
                    # Placeholder for successful download
                    # In a real implementation, this would actually download and save the file
                    with open(output_path, 'wb') as f:
                        f.write(b"Placeholder for media content")  # This would be the actual content
                        
                    return output_path
                    
                except Exception as e:
                    logger.error(f"Download attempt {attempt+1} failed: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise
                        
            raise WAMediaError("All download attempts failed")
            
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            raise WAMediaError(f"Failed to download media: {e}")
    
    def process_media_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a received media message to extract media information.
        
        Args:
            message: Received message data
            
        Returns:
            dict: Processed message with media information
            
        Raises:
            WAMediaError: If there's an error processing the media message
        """
        try:
            # Determine media type from message
            if "imageMessage" in message:
                media_msg = message["imageMessage"]
                media_type = self.MEDIA_IMAGE
            elif "videoMessage" in message:
                media_msg = message["videoMessage"]
                media_type = self.MEDIA_VIDEO
            elif "audioMessage" in message:
                media_msg = message["audioMessage"]
                media_type = self.MEDIA_AUDIO
            elif "documentMessage" in message:
                media_msg = message["documentMessage"]
                media_type = self.MEDIA_DOCUMENT
            elif "stickerMessage" in message:
                media_msg = message["stickerMessage"]
                media_type = self.MEDIA_STICKER
            else:
                return message  # Not a media message
                
            # Extract media information
            media_info = {
                "mediaType": media_type,
                "mimetype": media_msg.get("mimetype"),
                "mediaUrl": media_msg.get("url"),
                "mediaKey": media_msg.get("mediaKey"),
                "fileSize": media_msg.get("fileLength"),
                "fileName": media_msg.get("fileName"),
                "caption": media_msg.get("caption"),
            }
            
            # Add media info to the message
            message["mediaInfo"] = media_info
            
            return message
            
        except Exception as e:
            logger.error(f"Error processing media message: {e}")
            raise WAMediaError(f"Failed to process media message: {e}")
