"""
Simplified Database Models - Clean Code Architecture
Only 4 tables instead of 7, with configurable message saving
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import os

Base = declarative_base()

class Message(Base):
    """Simplified model storing all message information in one table"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    
    # Telegram identifiers
    message_id = Column(String(50), nullable=False)
    group_id = Column(String(50), nullable=False)
    group_name = Column(String(255), nullable=False)
    
    # Sender information (denormalized for simplicity)
    sender_id = Column(String(50), nullable=False)
    sender_username = Column(String(255), nullable=True)
    sender_first_name = Column(String(255), nullable=True)
    
    # Message content
    text_content = Column(Text, nullable=True)
    message_type = Column(String(50), default='text')
    
    # Media information (simplified)
    has_media = Column(Boolean, default=False)
    media_type = Column(String(50), nullable=True)
    file_id = Column(String(255), nullable=True)  # Telegram file ID
    local_path = Column(String(500), nullable=True)  # Local file path
    
    # OCR results (for Phase 3)
    ocr_text = Column(Text, nullable=True)
    ocr_processed = Column(Boolean, default=False)
    
    # Fraud detection summary (for quick queries)
    is_suspicious = Column(Boolean, default=False)
    fraud_score = Column(Float, default=0.0)
    
    # Timestamps
    sent_at = Column(DateTime, nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    fraud_detections = relationship("FraudDetection", back_populates="message", cascade="all, delete-orphan")

class FraudDetection(Base):
    """Detailed fraud detection results - only created for suspicious messages"""
    __tablename__ = 'fraud_detections'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    
    # Detection results
    fraud_score = Column(Float, nullable=False)
    detected_keywords = Column(JSON, nullable=True)  # Store as JSON array
    detection_method = Column(String(100), nullable=False)
    risk_level = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH, CRITICAL
    confidence_level = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH
    
    # Alert management
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="fraud_detections")

class FraudKeyword(Base):
    """Fraud keywords for detection"""
    __tablename__ = 'fraud_keywords'
    
    id = Column(Integer, primary_key=True)
    keyword = Column(String(255), nullable=False, unique=True)
    category = Column(String(100), nullable=False)
    fraud_score = Column(Float, default=0.7)  # Renamed from weight for clarity
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MonitoringSession(Base):
    """Session tracking for monitoring activities"""
    __tablename__ = 'monitoring_sessions'
    
    id = Column(Integer, primary_key=True)
    session_name = Column(String(255), nullable=False)
    
    # Session timing
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Statistics
    messages_processed = Column(Integer, default=0)
    suspicious_messages = Column(Integer, default=0)
    fraud_alerts = Column(Integer, default=0)
    
    # Configuration
    target_groups = Column(JSON, nullable=True)  # Store as JSON array
    save_non_suspicious = Column(Boolean, default=True)  # NEW: Toggle feature
    
    is_active = Column(Boolean, default=True)

# Configuration class for message saving behavior
class MessageSavingConfig:
    """Configuration for controlling message saving behavior"""
    
    @staticmethod
    def should_save_message(is_suspicious: bool, session_config: bool = None) -> bool:
        """
        Determine if a message should be saved based on suspicion level and configuration
        
        Args:
            is_suspicious: Whether the message is flagged as suspicious
            session_config: Session-specific configuration (if None, uses env var)
            
        Returns:
            bool: True if message should be saved
        """
        # Always save suspicious messages
        if is_suspicious:
            return True
        
        # Check session-specific config first, then environment variable
        if session_config is not None:
            return session_config
        
        # Default from environment variable
        return os.getenv('SAVE_NON_SUSPICIOUS_MESSAGES', 'true').lower() == 'true'
    
    @staticmethod
    def get_retention_days() -> int:
        """Get message retention period in days"""
        return int(os.getenv('MESSAGE_RETENTION_DAYS', '30'))
    
    @staticmethod
    def should_save_media(is_suspicious: bool) -> bool:
        """Determine if media files should be downloaded and saved"""
        # Only save media for suspicious messages to save space
        return is_suspicious or os.getenv('SAVE_ALL_MEDIA', 'false').lower() == 'true'