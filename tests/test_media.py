"""
Tests for the media handling module of wawspy.
"""

import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch

from wawspy.media import WAMedia
from wawspy.errors import WAMediaError

class TestWAMedia:
    """Tests for the WAMedia class."""
    
    @pytest.fixture
    def client_mock(self):
        """Create a mock client for testing."""
        return MagicMock()
    
    @pytest.fixture
    def media_handler(self, client_mock):
        """Create a WAMedia instance for testing."""
        return WAMedia(client_mock)
    
    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            f.write(b"Test file content")
            return f.name
    
    def teardown_method(self):
        """Clean up after tests."""
        for f in os.listdir('.'):
            if f.startswith('media') and f.endswith('.jpg'):
                try:
                    os.remove(f)
                except:
                    pass
    
    def test_determine_media_type_image(self, media_handler):
        """Test determining media type for an image."""
        # Test
        media_type, mime_type = media_handler.determine_media_type("test.jpg")
        
        # Verify
        assert media_type == "image"
        assert mime_type == "image/jpeg"
    
    def test_determine_media_type_video(self, media_handler):
        """Test determining media type for a video."""
        # Test
        media_type, mime_type = media_handler.determine_media_type("test.mp4")
        
        # Verify
        assert media_type == "video"
        assert mime_type == "video/mp4"
    
    def test_determine_media_type_document(self, media_handler):
        """Test determining media type for a document."""
        # Test
        media_type, mime_type = media_handler.determine_media_type("test.pdf")
        
        # Verify
        assert media_type == "document"
        assert mime_type == "application/pdf"
    
    def test_determine_media_type_unsupported(self, media_handler):
        """Test determining media type for an unsupported file."""
        # Test & verify
        with pytest.raises(WAMediaError):
            media_handler.determine_media_type("test.unsupported")
    
    @patch('os.path.isfile')
    @patch('os.path.getsize')
    @patch('wawspy.media.WAMedia.determine_media_type')
    def test_prepare_media(self, mock_determine_media_type, mock_getsize, mock_isfile, media_handler, temp_file):
        """Test preparing media for sending."""
        # Setup mocks
        mock_isfile.return_value = True
        mock_getsize.return_value = 1024
        mock_determine_media_type.return_value = ("image", "image/jpeg")
        
        # Test
        result = media_handler.prepare_media(temp_file)
        
        # Verify
        assert mock_isfile.called
        assert mock_getsize.called
        assert mock_determine_media_type.called
        assert "file_path" in result
        assert "file_size" in result
        assert "file_hash" in result
        assert "media_key" in result
        assert "media_type" in result
        assert "mime_type" in result
        assert result["media_type"] == "image"
        assert result["mime_type"] == "image/jpeg"
    
    @patch('wawspy.media.WAMedia.prepare_media')
    def test_upload_media(self, mock_prepare_media, media_handler, temp_file):
        """Test uploading media."""
        # Setup mock
        mock_prepare_media.return_value = {
            "file_path": temp_file,
            "file_size": 1024,
            "file_hash": "abc123",
            "media_key": "key123",
            "media_type": "image",
            "mime_type": "image/jpeg"
        }
        
        # Test
        result = media_handler.upload_media(temp_file)
        
        # Verify
        assert mock_prepare_media.called
        assert "url" in result
        assert "mimetype" in result
        assert "filehash" in result
        assert "filesize" in result
        assert "mediaKey" in result
        assert "type" in result
        assert result["type"] == "image"
        assert result["mimetype"] == "image/jpeg"
    
    def test_process_media_message_image(self, media_handler):
        """Test processing an image message."""
        # Setup
        message = {
            "imageMessage": {
                "url": "https://example.com/image.jpg",
                "mimetype": "image/jpeg",
                "caption": "Test image",
                "fileLength": 1024,
                "mediaKey": "key123"
            }
        }
        
        # Test
        result = media_handler.process_media_message(message)
        
        # Verify
        assert "mediaInfo" in result
        assert result["mediaInfo"]["mediaType"] == "image"
        assert result["mediaInfo"]["mediaUrl"] == "https://example.com/image.jpg"
        assert result["mediaInfo"]["mimetype"] == "image/jpeg"
        assert result["mediaInfo"]["caption"] == "Test image"
    
    def test_process_media_message_document(self, media_handler):
        """Test processing a document message."""
        # Setup
        message = {
            "documentMessage": {
                "url": "https://example.com/document.pdf",
                "mimetype": "application/pdf",
                "fileName": "test.pdf",
                "fileLength": 10240,
                "mediaKey": "key456"
            }
        }
        
        # Test
        result = media_handler.process_media_message(message)
        
        # Verify
        assert "mediaInfo" in result
        assert result["mediaInfo"]["mediaType"] == "document"
        assert result["mediaInfo"]["mediaUrl"] == "https://example.com/document.pdf"
        assert result["mediaInfo"]["mimetype"] == "application/pdf"
        assert result["mediaInfo"]["fileName"] == "test.pdf"
