from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class TelegramGroup(Base):
    """Model for storing Telegram group information"""
    __tablename__ = 'telegram_groups'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(String(50), unique=True, nullable=False)  # Telegram group ID
    group_name = Column(String(255), nullable=False)
    group_username = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="group")

class User(Base):
    """Model for storing Telegram user information"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, nullable=False)  # Telegram user ID
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    is_bot = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="sender")

class Message(Base):
    """Model for storing Telegram messages"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), nullable=False)  # Telegram message ID
    group_id = Column(Integer, ForeignKey('telegram_groups.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Message content
    text_content = Column(Text, nullable=True)
    message_type = Column(String(50), default='text')  # text, photo, document, etc.
    
    # Timestamps
    sent_at = Column(DateTime, nullable=False)  # When message was sent on Telegram
    processed_at = Column(DateTime, default=datetime.utcnow)  # When we processed it
    
    # Media information
    has_media = Column(Boolean, default=False)
    media_type = Column(String(50), nullable=True)  # photo, document, video, etc.
    
    # Relationships
    group = relationship("TelegramGroup", back_populates="messages")
    sender = relationship("User", back_populates="messages")
    media_files = relationship("MediaFile", back_populates="message")
    fraud_detections = relationship("FraudDetection", back_populates="message")

class MediaFile(Base):
    """Model for storing media file information"""
    __tablename__ = 'media_files'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    
    # File information
    file_id = Column(String(255), nullable=False)  # Telegram file ID
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Local storage
    local_path = Column(String(500), nullable=True)  # Path where file is stored locally
    
    # OCR results (for Phase 3)
    ocr_text = Column(Text, nullable=True)
    ocr_processed = Column(Boolean, default=False)
    ocr_processed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="media_files")

class FraudDetection(Base):
    """Model for storing fraud detection results"""
    __tablename__ = 'fraud_detections'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    
    # Detection results
    is_suspicious = Column(Boolean, default=False)
    fraud_score = Column(Float, default=0.0)  # 0.0 to 1.0
    detected_keywords = Column(Text, nullable=True)  # JSON string of detected keywords
    detection_method = Column(String(100), nullable=False)  # keyword, ocr, ml, etc.
    
    # Alert information
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="fraud_detections")

class FraudKeyword(Base):
    """Model for storing fraud keywords and patterns"""
    __tablename__ = 'fraud_keywords'
    
    id = Column(Integer, primary_key=True)
    keyword = Column(String(255), nullable=False, unique=True)
    category = Column(String(100), nullable=False)  # scam, investment, crypto, etc.
    weight = Column(Float, default=1.0)  # Weight for scoring
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MonitoringSession(Base):
    """Model for tracking monitoring sessions"""
    __tablename__ = 'monitoring_sessions'
    
    id = Column(Integer, primary_key=True)
    session_name = Column(String(255), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Statistics
    messages_processed = Column(Integer, default=0)
    images_processed = Column(Integer, default=0)
    fraud_alerts = Column(Integer, default=0)
    
    # Configuration
    target_groups = Column(Text, nullable=True)  # JSON string of monitored groups
    is_active = Column(Boolean, default=True)