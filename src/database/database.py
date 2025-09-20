import asyncio
import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, and_
from colorama import Fore, Style

from .models import Base, TelegramGroup, User, Message, MediaFile, FraudDetection, FraudKeyword, MonitoringSession

class DatabaseManager:
    """Manages all database operations for the fraud monitor"""
    
    def __init__(self, database_url: str = "sqlite+aiosqlite:///fraud_monitor.db"):
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        self.logger = logging.getLogger(__name__)
        
    async def initialize_database(self):
        """Initialize database tables and default data"""
        try:
            # Create all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self.logger.info(f"{Fore.GREEN}✅ Database initialized successfully!")
            
            # Insert default fraud keywords
            await self.insert_default_keywords()
            
            return True
        except Exception as e:
            self.logger.error(f"{Fore.RED}❌ Error initializing database: {e}")
            return False
    
    async def insert_default_keywords(self):
        """Insert default fraud detection keywords"""
        default_keywords = [
            # Scam keywords
            ("scam", "scam", 0.9),
            ("fraud", "scam", 0.9),
            ("fake", "scam", 0.7),
            ("phishing", "scam", 0.9),
            
            # Investment scams
            ("investment", "investment", 0.6),
            ("guaranteed profit", "investment", 0.9),
            ("risk-free", "investment", 0.8),
            ("double your money", "investment", 0.9),
            ("get rich quick", "investment", 0.9),
            
            # Crypto scams
            ("crypto", "crypto", 0.5),
            ("bitcoin", "crypto", 0.4),
            ("ethereum", "crypto", 0.4),
            ("free crypto", "crypto", 0.8),
            ("crypto giveaway", "crypto", 0.9),
            
            # Urgency tactics
            ("urgent", "urgency", 0.7),
            ("limited time", "urgency", 0.8),
            ("act now", "urgency", 0.7),
            ("expires soon", "urgency", 0.7),
            
            # Financial keywords
            ("free money", "financial", 0.9),
            ("easy money", "financial", 0.8),
            ("no experience needed", "financial", 0.6),
            ("work from home", "financial", 0.4),
        ]
        
        async with self.async_session() as session:
            try:
                # Check if keywords already exist
                result = await session.execute(select(FraudKeyword))
                existing_keywords = result.scalars().all()
                
                if not existing_keywords:
                    for keyword, category, weight in default_keywords:
                        fraud_keyword = FraudKeyword(
                            keyword=keyword,
                            category=category,
                            weight=weight
                        )
                        session.add(fraud_keyword)
                    
                    await session.commit()
                    self.logger.info(f"{Fore.CYAN}📝 Inserted {len(default_keywords)} default fraud keywords")
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"{Fore.RED}❌ Error inserting default keywords: {e}")
    
    async def get_or_create_group(self, group_id: str, group_name: str, group_username: str = None) -> TelegramGroup:
        """Get existing group or create new one"""
        async with self.async_session() as session:
            try:
                # Try to find existing group
                result = await session.execute(
                    select(TelegramGroup).where(TelegramGroup.group_id == group_id)
                )
                group = result.scalar_one_or_none()
                
                if not group:
                    # Create new group
                    group = TelegramGroup(
                        group_id=group_id,
                        group_name=group_name,
                        group_username=group_username
                    )
                    session.add(group)
                    await session.commit()
                    await session.refresh(group)
                    self.logger.info(f"{Fore.CYAN}📁 Created new group: {group_name}")
                
                return group
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"{Fore.RED}❌ Error with group: {e}")
                raise
    
    async def get_or_create_user(self, user_id: str, username: str = None, 
                                first_name: str = None, last_name: str = None, 
                                phone_number: str = None, is_bot: bool = False) -> User:
        """Get existing user or create new one"""
        async with self.async_session() as session:
            try:
                # Try to find existing user
                result = await session.execute(
                    select(User).where(User.user_id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    # Create new user
                    user = User(
                        user_id=user_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        phone_number=phone_number,
                        is_bot=is_bot
                    )
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                    self.logger.debug(f"{Fore.CYAN}👤 Created new user: {first_name}")
                
                return user
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"{Fore.RED}❌ Error with user: {e}")
                raise
    
    async def save_message(self, message_data: Dict[str, Any]) -> Message:
        """Save a message to the database"""
        async with self.async_session() as session:
            try:
                # Get or create group and user
                group = await self.get_or_create_group(
                    message_data['group_id'],
                    message_data['group_name'],
                    message_data.get('group_username')
                )
                
                user = await self.get_or_create_user(
                    message_data['sender_id'],
                    message_data.get('sender_username'),
                    message_data.get('sender_first_name'),
                    message_data.get('sender_last_name'),
                    is_bot=message_data.get('is_bot', False)
                )
                
                # Create message
                message = Message(
                    message_id=message_data['message_id'],
                    group_id=group.id,
                    sender_id=user.id,
                    text_content=message_data.get('text_content'),
                    message_type=message_data.get('message_type', 'text'),
                    sent_at=message_data['sent_at'],
                    has_media=message_data.get('has_media', False),
                    media_type=message_data.get('media_type')
                )
                
                session.add(message)
                await session.commit()
                await session.refresh(message)
                
                self.logger.debug(f"{Fore.GREEN}💾 Saved message to database")
                return message
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"{Fore.RED}❌ Error saving message: {e}")
                raise
    
    async def save_fraud_detection(self, message_id: int, detection_data: Dict[str, Any]) -> FraudDetection:
        """Save fraud detection results"""
        async with self.async_session() as session:
            try:
                fraud_detection = FraudDetection(
                    message_id=message_id,
                    is_suspicious=detection_data['is_suspicious'],
                    fraud_score=detection_data['fraud_score'],
                    detected_keywords=json.dumps(detection_data.get('detected_keywords', [])),
                    detection_method=detection_data['detection_method'],
                    alert_sent=detection_data.get('alert_sent', False)
                )
                
                session.add(fraud_detection)
                await session.commit()
                await session.refresh(fraud_detection)
                
                return fraud_detection
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"{Fore.RED}❌ Error saving fraud detection: {e}")
                raise
    
    async def get_fraud_keywords(self) -> List[FraudKeyword]:
        """Get all active fraud keywords"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(FraudKeyword).where(FraudKeyword.is_active == True)
                )
                return result.scalars().all()
                
            except Exception as e:
                self.logger.error(f"{Fore.RED}❌ Error getting fraud keywords: {e}")
                return []
    
    async def create_monitoring_session(self, session_name: str, target_groups: List[str]) -> MonitoringSession:
        """Create a new monitoring session"""
        async with self.async_session() as session:
            try:
                monitoring_session = MonitoringSession(
                    session_name=session_name,
                    target_groups=json.dumps(target_groups)
                )
                
                session.add(monitoring_session)
                await session.commit()
                await session.refresh(monitoring_session)
                
                self.logger.info(f"{Fore.CYAN}🎯 Created monitoring session: {session_name}")
                return monitoring_session
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"{Fore.RED}❌ Error creating monitoring session: {e}")
                raise
    
    async def update_session_stats(self, session_id: int, messages_count: int = 0, 
                                 images_count: int = 0, fraud_alerts: int = 0,
                                 end_time: datetime = None, is_active: bool = None):
        """Update monitoring session statistics"""
        async with self.async_session() as session:
            try:
                update_values = {
                    'messages_processed': MonitoringSession.messages_processed + messages_count,
                    'images_processed': MonitoringSession.images_processed + images_count,
                    'fraud_alerts': MonitoringSession.fraud_alerts + fraud_alerts
                }
                
                # Add optional parameters if provided
                if end_time is not None:
                    update_values['end_time'] = end_time
                if is_active is not None:
                    update_values['is_active'] = is_active
                
                await session.execute(
                    update(MonitoringSession)
                    .where(MonitoringSession.id == session_id)
                    .values(**update_values)
                )
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"{Fore.RED}❌ Error updating session stats: {e}")
    
    async def get_recent_messages(self, limit: int = 50) -> List[Message]:
        """Get recent messages with related data"""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(Message)
                    .options(selectinload(Message.group), selectinload(Message.sender))
                    .order_by(Message.processed_at.desc())
                    .limit(limit)
                )
                return result.scalars().all()
                
            except Exception as e:
                self.logger.error(f"{Fore.RED}❌ Error getting recent messages: {e}")
                return []
    
    async def close(self):
        """Close database connections"""
        try:
            if hasattr(self, 'engine') and self.engine:
                await self.engine.dispose()
                self.logger.info(f"{Fore.YELLOW}🔌 Database connections closed")
        except Exception as e:
            self.logger.error(f"{Fore.RED}❌ Error closing database: {e}")