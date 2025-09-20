"""
Fraud Detection Configuration Module

This module provides centralized configuration for the fraud detection system,
following Clean Code principles for easy maintenance and modification.
"""

from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

class FraudDetectionConfig:
    """Configuration settings for fraud detection system"""
    
    # Scoring thresholds
    SUSPICIOUS_THRESHOLD: float = float(os.getenv('FRAUD_SCORE_THRESHOLD', '0.7'))
    HIGH_RISK_THRESHOLD: float = float(os.getenv('HIGH_RISK_THRESHOLD', '0.9'))
    
    # Detection settings
    MIN_KEYWORD_LENGTH: int = 3
    MAX_KEYWORDS_PER_MESSAGE: int = 10
    CASE_SENSITIVE: bool = False
    
    # Scoring weights
    EXACT_MATCH_WEIGHT: float = 1.0
    PARTIAL_MATCH_WEIGHT: float = 0.7
    CONTEXT_BONUS: float = 0.2
    
    # Risk level mappings
    RISK_LEVELS: Dict[str, tuple] = {
        'LOW': (0.0, 0.3),
        'MEDIUM': (0.3, 0.7),
        'HIGH': (0.7, 0.9),
        'CRITICAL': (0.9, 1.0)
    }
    
    # Confidence level mappings
    CONFIDENCE_LEVELS: Dict[str, tuple] = {
        'LOW': (0.0, 0.4),
        'MEDIUM': (0.4, 0.7),
        'HIGH': (0.7, 1.0)
    }
    
    # Database settings
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'fraud_monitor.db')
    BACKUP_ENABLED: bool = os.getenv('BACKUP_ENABLED', 'true').lower() == 'true'
    
    # Logging settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'fraud_detection.log')
    
    # Performance settings
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '100'))
    CACHE_SIZE: int = int(os.getenv('CACHE_SIZE', '1000'))
    
    @classmethod
    def get_risk_level(cls, score: float) -> str:
        """Get risk level based on fraud score"""
        for level, (min_score, max_score) in cls.RISK_LEVELS.items():
            if min_score <= score < max_score:
                return level
        return 'CRITICAL'  # For scores >= 1.0
    
    @classmethod
    def get_confidence_level(cls, keyword_count: int, score: float) -> str:
        """Get confidence level based on detection metrics"""
        # Simple confidence calculation based on keyword count and score
        confidence_score = min((keyword_count * 0.2) + (score * 0.8), 1.0)
        
        for level, (min_conf, max_conf) in cls.CONFIDENCE_LEVELS.items():
            if min_conf <= confidence_score < max_conf:
                return level
        return 'HIGH'  # For confidence >= 1.0
    
    @classmethod
    def is_suspicious(cls, score: float) -> bool:
        """Check if a score indicates suspicious activity"""
        return score >= cls.SUSPICIOUS_THRESHOLD
    
    @classmethod
    def is_high_risk(cls, score: float) -> bool:
        """Check if a score indicates high risk activity"""
        return score >= cls.HIGH_RISK_THRESHOLD

# Global configuration instance
fraud_config = FraudDetectionConfig()