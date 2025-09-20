"""
Simplified Database Manager - Clean Code Architecture
Manages the simplified 4-table structure with configurable message saving
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import create_engine, and_, or_, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .simplified_models import Base, Message, FraudDetection, FraudKeyword, MonitoringSession, MessageSavingConfig

logger = logging.getLogger(__name__)

class SimplifiedDatabaseManager:
    """Simplified database manager with clean architecture principles"""
    
    def __init__(self, database_path: str = None):
        """Initialize database manager"""
        self.database_path = database_path or os.getenv('DATABASE_PATH', 'fraud_monitor.db')
        self.engine = create_engine(f'sqlite:///{self.database_path}', echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._create_tables()
    
    def _create_tables(self):
        """Create all tables if they don't exist"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()
    
    def close(self):
        """Close database connections"""
        try:
            self.engine.dispose()
            logger.info("Database connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    # Message Management
    def save_message(self, message_data: Dict, fraud_result: Dict = None, session_config: bool = None) -> Optional[int]:
        """
        Save a message if it meets the saving criteria
        
        Args:
            message_data: Dictionary containing message information
            fraud_result: Optional fraud detection results
            session_config: Session-specific saving configuration
            
        Returns:
            Message ID if saved, None if not saved
        """
        is_suspicious = fraud_result.get('is_suspicious', False) if fraud_result else False
        
        # Check if we should save this message
        if not MessageSavingConfig.should_save_message(is_suspicious, session_config):
            logger.debug(f"Skipping non-suspicious message {message_data.get('message_id')}")
            return None
        
        with self.get_session() as session:
            try:
                # Create message record
                message = Message(
                    message_id=str(message_data['message_id']),
                    group_id=str(message_data['group_id']),
                    group_name=message_data.get('group_name', 'Unknown'),
                    sender_id=str(message_data['sender_id']),
                    sender_username=message_data.get('sender_username'),
                    sender_first_name=message_data.get('sender_first_name'),
                    text_content=message_data.get('text_content'),
                    message_type=message_data.get('message_type', 'text'),
                    has_media=message_data.get('has_media', False),
                    media_type=message_data.get('media_type'),
                    file_id=message_data.get('file_id'),
                    local_path=message_data.get('local_path'),
                    ocr_text=message_data.get('ocr_text'),
                    ocr_processed=message_data.get('ocr_processed', False),
                    is_suspicious=is_suspicious,
                    fraud_score=fraud_result.get('fraud_score', 0.0) if fraud_result else 0.0,
                    sent_at=message_data.get('sent_at', datetime.utcnow())
                )
                
                session.add(message)
                session.flush()  # Get the ID
                
                # Save fraud detection details if suspicious
                if is_suspicious and fraud_result:
                    fraud_detection = FraudDetection(
                        message_id=message.id,
                        fraud_score=fraud_result['fraud_score'],
                        detected_keywords=fraud_result.get('detected_keywords', []),
                        detection_method=fraud_result.get('detection_method', 'keyword_analysis'),
                        risk_level=fraud_result.get('risk_level'),
                        confidence_level=fraud_result.get('confidence_level')
                    )
                    session.add(fraud_detection)
                
                session.commit()
                logger.info(f"Saved message {message.message_id} (suspicious: {is_suspicious})")
                return message.id
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error saving message: {e}")
                return None
    
    def get_suspicious_messages(self, limit: int = 100) -> List[Dict]:
        """Get recent suspicious messages"""
        with self.get_session() as session:
            try:
                messages = session.query(Message).filter(
                    Message.is_suspicious == True
                ).order_by(desc(Message.processed_at)).limit(limit).all()
                
                return [self._message_to_dict(msg) for msg in messages]
            except SQLAlchemyError as e:
                logger.error(f"Error fetching suspicious messages: {e}")
                return []
    
    def get_message_with_fraud_details(self, message_id: int) -> Optional[Dict]:
        """Get message with detailed fraud detection information"""
        with self.get_session() as session:
            try:
                message = session.query(Message).filter(Message.id == message_id).first()
                if not message:
                    return None
                
                result = self._message_to_dict(message)
                
                # Add fraud detection details if available
                fraud_detections = session.query(FraudDetection).filter(
                    FraudDetection.message_id == message_id
                ).all()
                
                result['fraud_detections'] = [self._fraud_detection_to_dict(fd) for fd in fraud_detections]
                return result
                
            except SQLAlchemyError as e:
                logger.error(f"Error fetching message details: {e}")
                return None
    
    # Keyword Management
    def add_keyword(self, keyword: str, category: str, fraud_score: float, description: str = None) -> bool:
        """Add a new fraud keyword"""
        with self.get_session() as session:
            try:
                fraud_keyword = FraudKeyword(
                    keyword=keyword.lower().strip(),
                    category=category,
                    fraud_score=fraud_score,
                    description=description
                )
                session.add(fraud_keyword)
                session.commit()
                logger.info(f"Added keyword: {keyword}")
                return True
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error adding keyword: {e}")
                return False
    
    def get_keywords(self, category: str = None, active_only: bool = True) -> List[Dict]:
        """Get fraud keywords, optionally filtered by category"""
        with self.get_session() as session:
            try:
                query = session.query(FraudKeyword)
                
                if active_only:
                    query = query.filter(FraudKeyword.is_active == True)
                
                if category:
                    query = query.filter(FraudKeyword.category == category)
                
                keywords = query.all()
                return [self._keyword_to_dict(kw) for kw in keywords]
            except SQLAlchemyError as e:
                logger.error(f"Error fetching keywords: {e}")
                return []
    
    def remove_keyword(self, keyword: str) -> bool:
        """Remove a fraud keyword"""
        with self.get_session() as session:
            try:
                keyword_obj = session.query(FraudKeyword).filter(
                    FraudKeyword.keyword == keyword.lower().strip()
                ).first()
                
                if keyword_obj:
                    session.delete(keyword_obj)
                    session.commit()
                    logger.info(f"Removed keyword: {keyword}")
                    return True
                return False
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error removing keyword: {e}")
                return False
    
    # Session Management
    def start_monitoring_session(self, session_name: str, target_groups: List[str], 
                                save_non_suspicious: bool = True) -> int:
        """Start a new monitoring session"""
        with self.get_session() as session:
            try:
                monitoring_session = MonitoringSession(
                    session_name=session_name,
                    target_groups=target_groups,
                    save_non_suspicious=save_non_suspicious
                )
                session.add(monitoring_session)
                session.commit()
                logger.info(f"Started monitoring session: {session_name}")
                return monitoring_session.id
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error starting session: {e}")
                raise
    
    def update_session_stats(self, session_id: int, messages_processed: int = 0, 
                           suspicious_messages: int = 0, fraud_alerts: int = 0):
        """Update session statistics"""
        with self.get_session() as session:
            try:
                monitoring_session = session.query(MonitoringSession).filter(
                    MonitoringSession.id == session_id
                ).first()
                
                if monitoring_session:
                    monitoring_session.messages_processed += messages_processed
                    monitoring_session.suspicious_messages += suspicious_messages
                    monitoring_session.fraud_alerts += fraud_alerts
                    session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error updating session stats: {e}")
    
    def end_monitoring_session(self, session_id: int):
        """End a monitoring session"""
        with self.get_session() as session:
            try:
                monitoring_session = session.query(MonitoringSession).filter(
                    MonitoringSession.id == session_id
                ).first()
                
                if monitoring_session:
                    monitoring_session.ended_at = datetime.utcnow()
                    monitoring_session.is_active = False
                    session.commit()
                    logger.info(f"Ended monitoring session: {monitoring_session.session_name}")
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error ending session: {e}")
    
    # Cleanup and Maintenance
    def cleanup_old_messages(self, retention_days: int = None) -> int:
        """Clean up old messages based on retention policy"""
        retention_days = retention_days or MessageSavingConfig.get_retention_days()
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        with self.get_session() as session:
            try:
                # Delete old non-suspicious messages
                deleted_count = session.query(Message).filter(
                    and_(
                        Message.processed_at < cutoff_date,
                        Message.is_suspicious == False
                    )
                ).delete()
                
                session.commit()
                logger.info(f"Cleaned up {deleted_count} old messages")
                return deleted_count
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error cleaning up messages: {e}")
                return 0
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        with self.get_session() as session:
            try:
                stats = {
                    'total_messages': session.query(Message).count(),
                    'suspicious_messages': session.query(Message).filter(Message.is_suspicious == True).count(),
                    'fraud_detections': session.query(FraudDetection).count(),
                    'active_keywords': session.query(FraudKeyword).filter(FraudKeyword.is_active == True).count(),
                    'active_sessions': session.query(MonitoringSession).filter(MonitoringSession.is_active == True).count()
                }
                return stats
            except SQLAlchemyError as e:
                logger.error(f"Error getting database stats: {e}")
                return {}
    
    # Helper methods
    def _message_to_dict(self, message: Message) -> Dict:
        """Convert Message object to dictionary"""
        return {
            'id': message.id,
            'message_id': message.message_id,
            'group_id': message.group_id,
            'group_name': message.group_name,
            'sender_id': message.sender_id,
            'sender_username': message.sender_username,
            'sender_first_name': message.sender_first_name,
            'text_content': message.text_content,
            'message_type': message.message_type,
            'has_media': message.has_media,
            'media_type': message.media_type,
            'file_id': message.file_id,
            'local_path': message.local_path,
            'ocr_text': message.ocr_text,
            'ocr_processed': message.ocr_processed,
            'is_suspicious': message.is_suspicious,
            'fraud_score': message.fraud_score,
            'sent_at': message.sent_at,
            'processed_at': message.processed_at
        }
    
    def _fraud_detection_to_dict(self, fraud_detection: FraudDetection) -> Dict:
        """Convert FraudDetection object to dictionary"""
        return {
            'id': fraud_detection.id,
            'message_id': fraud_detection.message_id,
            'fraud_score': fraud_detection.fraud_score,
            'detected_keywords': fraud_detection.detected_keywords,
            'detection_method': fraud_detection.detection_method,
            'risk_level': fraud_detection.risk_level,
            'confidence_level': fraud_detection.confidence_level,
            'alert_sent': fraud_detection.alert_sent,
            'alert_sent_at': fraud_detection.alert_sent_at,
            'created_at': fraud_detection.created_at
        }
    
    def _keyword_to_dict(self, keyword: FraudKeyword) -> Dict:
        """Convert FraudKeyword object to dictionary"""
        return {
            'id': keyword.id,
            'keyword': keyword.keyword,
            'category': keyword.category,
            'fraud_score': keyword.fraud_score,
            'description': keyword.description,
            'is_active': keyword.is_active,
            'created_at': keyword.created_at,
            'updated_at': keyword.updated_at
        }