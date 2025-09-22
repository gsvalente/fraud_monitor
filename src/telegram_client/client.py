from typing import Dict, Any
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from colorama import Fore, Style, init
import os
import sys
from dotenv import load_dotenv

# Add database imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.simplified_database import SimplifiedDatabaseManager
from src.fraud_detection.keyword_manager import KeywordManager
from src.fraud_detection.detector import FraudDetector
from src.alerts.alert_manager import AlertManager, AlertContext
from src.media.downloader import MediaDownloader
from src.media.ocr_processor import OCRProcessor

# Initialize colorama for colored console output
init(autoreset=True)

# Load environment variables
load_dotenv()

class TelegramFraudMonitor:
    def __init__(self):
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        self.phone_number = os.getenv('PHONE_NUMBER')
        self.target_groups = os.getenv('TARGET_GROUPS', '').split(',')
        
        # Initialize Clean Code components
        self.keyword_manager = KeywordManager()
        self.fraud_detector = FraudDetector(self.keyword_manager)
        
        # Initialize alert system (will be set after client connection)
        self.alert_manager = None
        print(f"{Fore.CYAN}🚨 Alert system will be initialized after connection...")
        
        # Initialize media processing components
        self.media_downloader = MediaDownloader()
        self.ocr_processor = OCRProcessor()
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize Telegram client
        self.client = TelegramClient('fraud_monitor_session', self.api_id, self.api_hash)
        
        # Initialize database
        self.db = SimplifiedDatabaseManager()
        
        # Statistics
        self.message_count = 0
        self.image_count = 0
        self.fraud_alerts = 0
        self.current_session = None
        
    async def start(self):
        """Start the Telegram client and begin monitoring"""
        try:
            # Initialize database (tables are created in constructor)
            print(f"{Fore.CYAN}🗄️  Database initialized...")
            
            # Create monitoring session
            session_name = f"Monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.current_session = self.db.start_monitoring_session(session_name, self.target_groups)
            
            # Check if running in Docker (no interactive terminal)
            is_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER') == 'true'
            
            if is_docker:
                print(f"{Fore.YELLOW}🐳 Docker environment detected")
                # Check if session file exists
                session_file = 'fraud_monitor_session.session'
                if not os.path.exists(session_file):
                    print(f"{Fore.RED}❌ No session file found in Docker container!")
                    print(f"{Fore.YELLOW}📋 To fix this issue:")
                    print(f"{Fore.WHITE}   1. Run the application locally first to authenticate:")
                    print(f"{Fore.WHITE}      python main.py")
                    print(f"{Fore.WHITE}   2. Copy the generated '{session_file}' to your Docker volume")
                    print(f"{Fore.WHITE}   3. Or mount it as a volume: -v ./fraud_monitor_session.session:/app/fraud_monitor_session.session")
                    print(f"{Fore.RED}🛑 Stopping application...")
                    return
                else:
                    print(f"{Fore.GREEN}✅ Session file found: {session_file}")
            
            try:
                await self.client.start(phone=self.phone_number)
                self.logger.info(f"{Fore.GREEN}✅ Successfully connected to Telegram!")
            except EOFError as e:
                if is_docker:
                    print(f"{Fore.RED}❌ Authentication failed in Docker environment")
                    print(f"{Fore.YELLOW}📋 This usually means:")
                    print(f"{Fore.WHITE}   • The session file is corrupted or invalid")
                    print(f"{Fore.WHITE}   • You need to re-authenticate locally first")
                    print(f"{Fore.WHITE}   • Run 'python main.py' on your local machine to create a new session")
                else:
                    print(f"{Fore.RED}❌ Authentication failed: {e}")
                    print(f"{Fore.YELLOW}💡 Please ensure you can receive SMS/calls for verification")
                raise
            except Exception as auth_error:
                print(f"{Fore.RED}❌ Authentication error: {auth_error}")
                if "AUTH_KEY" in str(auth_error):
                    print(f"{Fore.YELLOW}💡 Session may be expired. Try deleting the session file and re-authenticating.")
                raise
            
            # Initialize alert system after successful connection
            alert_chat_id = os.getenv('ALERT_CHAT_ID', 'me')  # Default to saved messages if not set
            enable_desktop_notifications = os.getenv('ENABLE_DESKTOP_NOTIFICATIONS', 'true').lower() == 'true'
            enable_sound_alerts = os.getenv('ENABLE_SOUND_ALERTS', 'true').lower() == 'true'
            bot_token = os.getenv('BOT_TOKEN')
            bot_alert_chat_id = os.getenv('BOT_ALERT_CHAT_ID')
            
            self.alert_manager = AlertManager(
                telegram_client=self.client, 
                alert_chat_id=alert_chat_id,
                enable_desktop_notifications=enable_desktop_notifications,
                enable_sound_alerts=enable_sound_alerts,
                bot_token=bot_token,
                bot_alert_chat_id=bot_alert_chat_id
            )
            
            print(f"{Fore.CYAN}🚨 Alert system initialized - notifications enabled!")
            if enable_desktop_notifications:
                print(f"{Fore.GREEN}🔔 Desktop notifications: ENABLED")
            else:
                print(f"{Fore.YELLOW}🔔 Desktop notifications: DISABLED")
            
            if enable_sound_alerts:
                print(f"{Fore.GREEN}🔊 Sound alerts: ENABLED")
            else:
                print(f"{Fore.YELLOW}🔊 Sound alerts: DISABLED")
                
            if bot_token and bot_alert_chat_id:
                print(f"{Fore.GREEN}🤖 Bot alerts: ENABLED (Chat: {bot_alert_chat_id})")
            else:
                print(f"{Fore.YELLOW}🤖 Bot alerts: DISABLED (No bot token or chat ID configured)")
                
            if alert_chat_id != 'me':
                print(f"{Fore.CYAN}📤 Alerts will be sent to: {alert_chat_id}")
            else:
                print(f"{Fore.YELLOW}📤 Alerts will be sent to Saved Messages (set ALERT_CHAT_ID to change)")
            
            # Get user info
            me = await self.client.get_me()
            print(f"{Fore.CYAN}🤖 Logged in as: {me.first_name} (@{me.username})")
            
            # Setup event handlers
            self.setup_handlers()
            
            # Display monitoring info
            print(f"{Fore.YELLOW}📡 Monitoring groups: {', '.join(self.target_groups)}")
            print(f"{Fore.MAGENTA}🔍 Fraud monitoring started... Press Ctrl+C to stop")
            print(f"{Fore.BLUE}💾 Database: {os.getenv('DATABASE_PATH', 'fraud_monitor_simplified.db')}")
            
            # Keep the client running
            await self.client.run_until_disconnected()
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}🛑 Received stop signal")
        except EOFError:
            print(f"\n{Fore.RED}❌ EOF Error - Cannot read input in this environment")
            print(f"{Fore.YELLOW}💡 If running in Docker, ensure you have a valid session file")
        except Exception as e:
            self.logger.error(f"{Fore.RED}❌ Error starting client: {e}")
            raise
    
    def setup_handlers(self):
        """Setup event handlers for different message types"""
        
        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            try:
                # Get chat info
                chat = await event.get_chat()
                chat_title = getattr(chat, 'title', 'Private Chat')
                
                # Check if message is from target groups
                if self.target_groups and chat_title not in self.target_groups:
                    return
                
                self.message_count += 1
                
                # Get sender info
                sender = await event.get_sender()
                sender_name = getattr(sender, 'first_name', 'Unknown')
                sender_username = getattr(sender, 'username', 'No username')
                
                # Process message
                await self.process_message(event, chat_title, sender_name, sender_username)
                
            except Exception as e:
                self.logger.error(f"{Fore.RED}Error handling message: {e}")
    
    async def process_message(self, event, chat_title, sender_name, sender_username):
        """Process individual messages"""
        message = event.message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Basic message info
        print(f"\n{Fore.CYAN}📨 New Message #{self.message_count}")
        print(f"{Fore.WHITE}🏷️  Group: {chat_title}")
        print(f"{Fore.YELLOW}🆔 Chat ID: {event.chat_id}")
        print(f"{Fore.WHITE}👤 Sender: {sender_name} (@{sender_username})")
        print(f"{Fore.WHITE}🕐 Time: {timestamp}")
        
        # Prepare message data for database
        message_data = {
            'message_id': str(message.id),
            'group_id': str(event.chat_id),
            'group_name': chat_title,
            'sender_id': str(message.sender_id),
            'sender_username': sender_username,
            'sender_first_name': sender_name,
            'text_content': message.text,
            'sent_at': message.date,
            'has_media': bool(message.media),
            'message_type': 'text'
        }
        
        # Process text message
        fraud_detected = False
        detected_keywords = []
        
        if message.text:
            print(f"{Fore.GREEN}💬 Text: {message.text[:100]}{'...' if len(message.text) > 100 else ''}")
            
            # Use Clean Code fraud detection system
            fraud_result = await self.detect_fraud(message.text)
            
            if fraud_result['is_suspicious']:
                fraud_detected = True
                detected_keywords = fraud_result['detected_keywords']
                fraud_score = fraud_result['fraud_score']
                print(f"{Fore.RED}🚨 FRAUD ALERT! Keywords: {', '.join(detected_keywords)} (Score: {fraud_score:.2f})")
                print(f"{Fore.RED}🎯 Risk Level: {fraud_result.get('risk_level', 'Unknown')}")
                print(f"{Fore.RED}🔍 Confidence: {fraud_result.get('confidence_level', 'Unknown')}")
                self.fraud_alerts += 1
                
                # Send alert notification
                await self.send_fraud_alert(message, chat_title, fraud_result, None)
        
        # Process media (images/documents) and extract text
        extracted_text = ""
        media_info = None
        if message.media:
            extracted_text, media_info = await self.process_media(message, chat_title)
            message_data['message_type'] = 'media'
            
            # Add OCR extracted text to message data if available
            if extracted_text:
                # Combine original text with extracted text
                combined_text = message.text or ""
                if combined_text and extracted_text:
                    combined_text += f"\n[OCR_EXTRACTED]: {extracted_text}"
                elif extracted_text:
                    combined_text = f"[OCR_EXTRACTED]: {extracted_text}"
                
                message_data['text_content'] = combined_text
                message_data['ocr_text'] = extracted_text
                
                # Also check for fraud in the extracted text if we haven't found any yet
                if not fraud_detected and extracted_text.strip():
                    ocr_fraud_result = await self.detect_fraud(extracted_text)
                    if ocr_fraud_result['is_suspicious']:
                        fraud_detected = True
                        fraud_result = ocr_fraud_result
                        detected_keywords = ocr_fraud_result['detected_keywords']
                        fraud_score = ocr_fraud_result['fraud_score']
                        print(f"{Fore.RED}🚨 FRAUD DETECTED IN OCR TEXT! Keywords: {', '.join(detected_keywords)} (Score: {fraud_score:.2f})")
                        self.fraud_alerts += 1
                        
                        # Send alert notification for OCR fraud
                        await self.send_fraud_alert(message, chat_title, ocr_fraud_result, extracted_text)
        
        try:
            # Save message to database (with fraud detection if any)
            fraud_result_data = fraud_result if fraud_detected else None
            saved_message_id = self.db.save_message(message_data, fraud_result_data)
            
            # Update session statistics
            if self.current_session:
                self.db.update_session_stats(
                    self.current_session, 
                    messages_processed=1,
                    fraud_alerts=1 if fraud_detected else 0
                )
            
            print(f"{Fore.GREEN}💾 Message saved to database")
            
        except Exception as e:
            self.logger.error(f"{Fore.RED}❌ Error saving to database: {e}")
        
        print(f"{Fore.BLUE}{'='*60}")
    
    async def detect_fraud(self, message_text: str) -> Dict[str, Any]:
        """
        Detect fraud using the Clean Code fraud detection system
        
        Args:
            message_text: Text content to analyze
            
        Returns:
            Dict containing detection results
        """
        if not message_text or not message_text.strip():
            return {
                'is_suspicious': False,
                'fraud_score': 0.0,
                'detected_keywords': [],
                'detection_method': 'none'
            }
        
        # Use the Clean Code fraud detector
        result = self.fraud_detector.detect_fraud(message_text)
        
        return {
            'is_suspicious': result.is_suspicious,
            'fraud_score': result.fraud_score,
            'detected_keywords': result.detected_keywords,
            'detection_method': result.detection_method,
            'risk_level': result.risk_level,
            'confidence_level': result.confidence_level
        }
    
    async def process_media(self, message, chat_title):
        """Process media messages (images, documents) with OCR text extraction"""
        extracted_text = ""
        media_info = None
        
        if isinstance(message.media, MessageMediaPhoto):
            self.image_count += 1
            print(f"{Fore.YELLOW}🖼️  Image detected (#{self.image_count})")
            
            # Download and process image
            try:
                # Download the image
                media_info = await self.media_downloader.download_image(
                    self.client, message, message.id
                )
                
                if media_info and media_info.get('local_path'):
                    print(f"{Fore.CYAN}📥 Downloaded: {media_info['filename']}")
                    
                    # Extract text using OCR
                    print(f"{Fore.CYAN}🔍 Extracting text from image...")
                    ocr_result = self.ocr_processor.extract_text(
                        media_info['local_path']
                    )
                    
                    if ocr_result.get('text') and ocr_result['text'].strip():
                        extracted_text = ocr_result['text'].strip()
                        confidence = ocr_result.get('confidence', 0.0)
                        print(f"{Fore.GREEN}📝 Text extracted (confidence: {confidence:.1f}%)")
                        print(f"{Fore.WHITE}Text: {extracted_text[:100]}{'...' if len(extracted_text) > 100 else ''}")
                        
                        # Check for fraud in extracted text
                        fraud_result = await self.detect_fraud(extracted_text)
                        if fraud_result.get('is_suspicious'):
                            detected_keywords = fraud_result['detected_keywords']
                            fraud_score = fraud_result['fraud_score']
                            print(f"{Fore.RED}🚨 FRAUD DETECTED IN IMAGE! Keywords: {', '.join(detected_keywords)} (Score: {fraud_score:.2f})")
                            self.fraud_alerts += 1
                    else:
                        print(f"{Fore.YELLOW}⚠️  No text found in image")
                        
            except Exception as e:
                print(f"{Fore.RED}❌ Error processing image: {e}")
                self.logger.error(f"Image processing error: {e}")
            
        elif isinstance(message.media, MessageMediaDocument):
            document = message.media.document
            if document.mime_type and document.mime_type.startswith('image/'):
                self.image_count += 1
                print(f"{Fore.YELLOW}🖼️  Image document detected (#{self.image_count})")
                
                # Download and process image document
                try:
                    # Download the image document
                    media_info = await self.media_downloader.download_image(
                        self.client, message, message.id
                    )
                    
                    if media_info and media_info.get('local_path'):
                        print(f"{Fore.CYAN}📥 Downloaded: {media_info['filename']}")
                        
                        # Extract text using OCR
                        print(f"{Fore.CYAN}🔍 Extracting text from image document...")
                        ocr_result = self.ocr_processor.extract_text(
                            media_info['local_path']
                        )
                        
                        if ocr_result.get('text') and ocr_result['text'].strip():
                            extracted_text = ocr_result['text'].strip()
                            confidence = ocr_result.get('confidence', 0.0)
                            print(f"{Fore.GREEN}📝 Text extracted (confidence: {confidence:.1f}%)")
                            print(f"{Fore.WHITE}Text: {extracted_text[:100]}{'...' if len(extracted_text) > 100 else ''}")
                            
                            # Check for fraud in extracted text
                            fraud_result = await self.detect_fraud(extracted_text)
                            if fraud_result.get('is_suspicious'):
                                detected_keywords = fraud_result['detected_keywords']
                                fraud_score = fraud_result['fraud_score']
                                print(f"{Fore.RED}🚨 FRAUD DETECTED IN IMAGE! Keywords: {', '.join(detected_keywords)} (Score: {fraud_score:.2f})")
                                self.fraud_alerts += 1
                                
                                # Send alert notification for image fraud
                                await self.send_fraud_alert(message, "Unknown Chat", fraud_result, extracted_text)
                        else:
                            print(f"{Fore.YELLOW}⚠️  No text found in image document")
                            
                except Exception as e:
                    print(f"{Fore.RED}❌ Error processing image document: {e}")
                    self.logger.error(f"Image document processing error: {e}")
            else:
                print(f"{Fore.CYAN}📎 Document: {document.mime_type}")
        
        # Update session statistics for images
        if self.current_session:
            self.db.update_session_stats(
                self.current_session, 
                messages_processed=1
            )
            
        return extracted_text, media_info
    
    async def send_fraud_alert(self, message, chat_title, fraud_result, extracted_text=None):
        """Send fraud alert using AlertManager"""
        try:
            # Check if alert manager is initialized
            if not self.alert_manager:
                print(f"{Fore.YELLOW}⚠️  Alert system not initialized yet")
                return
                
            # Create alert context with correct parameter names
            context = AlertContext(
                message_id=str(message.id),
                group_name=chat_title,
                sender_username=getattr(message.sender, 'username', 'Unknown') if message.sender else 'Unknown',
                sender_first_name=getattr(message.sender, 'first_name', 'Unknown') if message.sender else 'Unknown',
                message_text=message.text or "",
                ocr_text=extracted_text,
                timestamp=message.date
            )
            
            # Use analyze_and_alert method which handles everything internally
            alert = await self.alert_manager.analyze_and_alert(context)
            if alert:
                print(f"{Fore.GREEN}📨 Alert notification sent!")
            else:
                print(f"{Fore.YELLOW}⚠️  Alert not sent (rate limited or low risk)")
            
        except Exception as e:
            print(f"{Fore.RED}❌ Failed to send alert: {e}")
            self.logger.error(f"Alert sending error: {e}")
    
    def print_statistics(self):
        """Print current monitoring statistics"""
        print(f"\n{Fore.MAGENTA}📊 MONITORING STATISTICS")
        print(f"{Fore.WHITE}Messages processed: {self.message_count}")
        print(f"{Fore.WHITE}Images detected: {self.image_count}")
        print(f"{Fore.RED}Fraud alerts: {self.fraud_alerts}")
        print(f"{Fore.BLUE}Active groups: {len(self.target_groups)}")
        if self.current_session:
            print(f"{Fore.CYAN}Session ID: {self.current_session}")
        print(f"{Fore.BLUE}{'='*50}")
    
    async def stop(self):
        """Stop the client gracefully"""
        print(f"\n{Fore.YELLOW}🛑 Stopping Telegram Fraud Monitor...")
        
        # Final session update
        if self.current_session:
            self.db.end_monitoring_session(self.current_session)
            print(f"{Fore.GREEN}💾 Session data saved to database")
        
        # Close database connection
        if hasattr(self, 'db'):
            self.db.close()
            print(f"{Fore.GREEN}🔒 Database connection closed")
        
        # Disconnect Telegram client
        if self.client.is_connected():
            await self.client.disconnect()
            print(f"{Fore.GREEN}📱 Telegram client disconnected")
        
        self.print_statistics()
        print(f"{Fore.GREEN}✅ Monitoring stopped successfully!")

async def main():
    """Main function to run the fraud monitor"""
    monitor = TelegramFraudMonitor()
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}🛑 Received stop signal (Ctrl+C)")
    except EOFError:
        print(f"\n{Fore.RED}❌ EOF Error: Cannot read input in this environment")
        print(f"{Fore.YELLOW}💡 This typically happens when:")
        print(f"{Fore.WHITE}   • Running in Docker without a valid session file")
        print(f"{Fore.WHITE}   • No interactive terminal available for authentication")
        print(f"{Fore.CYAN}🔧 Solution: Run locally first to create session file, then copy to Docker")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Unexpected error: {e}")
        import traceback
        print(f"{Fore.RED}📋 Full error details:")
        traceback.print_exc()
    finally:
        try:
            await monitor.stop()
        except Exception as stop_error:
            print(f"{Fore.RED}⚠️  Error during cleanup: {stop_error}")

if __name__ == "__main__":
    asyncio.run(main())