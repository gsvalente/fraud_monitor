"""
Media Downloader - Phase 3 OCR Implementation
Handles downloading of images and media files from Telegram
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from colorama import Fore, Style

logger = logging.getLogger(__name__)

class MediaDownloader:
    """Handles downloading media files from Telegram messages"""
    
    def __init__(self, download_path: str = "downloads"):
        """
        Initialize the media downloader
        
        Args:
            download_path: Directory to store downloaded files
        """
        self.download_path = Path(download_path)
        self.download_path.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.images_path = self.download_path / "images"
        self.documents_path = self.download_path / "documents"
        self.images_path.mkdir(exist_ok=True)
        self.documents_path.mkdir(exist_ok=True)
        
        logger.info(f"Media downloader initialized - Path: {self.download_path}")
    
    async def download_image(self, client: TelegramClient, message, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Download image from Telegram message
        
        Args:
            client: Telegram client instance
            message: Telegram message object
            message_id: Unique message identifier
            
        Returns:
            Dictionary with download information or None if failed
        """
        try:
            if isinstance(message.media, MessageMediaPhoto):
                # Handle photo messages
                file_extension = "jpg"
                download_dir = self.images_path
                media_type = "photo"
                
            elif isinstance(message.media, MessageMediaDocument):
                # Handle document messages (images as documents)
                document = message.media.document
                if not document.mime_type or not document.mime_type.startswith('image/'):
                    logger.debug(f"Skipping non-image document: {document.mime_type}")
                    return None
                
                # Get file extension from mime type
                mime_to_ext = {
                    'image/jpeg': 'jpg',
                    'image/png': 'png',
                    'image/gif': 'gif',
                    'image/webp': 'webp',
                    'image/bmp': 'bmp'
                }
                file_extension = mime_to_ext.get(document.mime_type, 'jpg')
                download_dir = self.images_path
                media_type = "document_image"
                
            else:
                logger.debug(f"Unsupported media type for OCR: {type(message.media)}")
                return None
            
            # Generate filename
            filename = f"msg_{message_id}_{message.id}.{file_extension}"
            file_path = download_dir / filename
            
            # Download the file
            logger.info(f"{Fore.YELLOW}📥 Downloading image: {filename}")
            downloaded_path = await client.download_media(message.media, file=str(file_path))
            
            if downloaded_path:
                file_size = os.path.getsize(downloaded_path)
                logger.info(f"{Fore.GREEN}✅ Downloaded: {filename} ({file_size} bytes)")
                
                return {
                    'local_path': str(downloaded_path),
                    'filename': filename,
                    'file_size': file_size,
                    'media_type': media_type,
                    'file_extension': file_extension,
                    'mime_type': getattr(message.media.document, 'mime_type', f'image/{file_extension}') if hasattr(message.media, 'document') else f'image/{file_extension}'
                }
            else:
                logger.error(f"{Fore.RED}❌ Failed to download: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"{Fore.RED}❌ Error downloading media: {e}")
            return None
    
    def get_download_stats(self) -> Dict[str, Any]:
        """Get download statistics"""
        try:
            images_count = len(list(self.images_path.glob("*")))
            documents_count = len(list(self.documents_path.glob("*")))
            
            total_size = 0
            for path in [self.images_path, self.documents_path]:
                for file_path in path.glob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
            
            return {
                'images_downloaded': images_count,
                'documents_downloaded': documents_count,
                'total_files': images_count + documents_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'download_path': str(self.download_path)
            }
        except Exception as e:
            logger.error(f"Error getting download stats: {e}")
            return {}
    
    def cleanup_old_files(self, days_old: int = 7):
        """
        Clean up files older than specified days
        
        Args:
            days_old: Remove files older than this many days
        """
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days_old * 24 * 60 * 60)
            
            removed_count = 0
            for path in [self.images_path, self.documents_path]:
                for file_path in path.glob("*"):
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        removed_count += 1
            
            logger.info(f"Cleaned up {removed_count} old files (older than {days_old} days)")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0