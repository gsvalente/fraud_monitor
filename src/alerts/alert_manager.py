"""
Alert Management System for Fraud Detection

This module provides a comprehensive alert system that combines brand detection
and fraud keyword detection to send intelligent alerts via Telegram.
Uses existing Telegram client infrastructure with minimal dependencies.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import winsound
import threading

from telethon import TelegramClient
from colorama import Fore, Style

# Desktop notifications
try:
    from plyer import notification
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    print("⚠️  Desktop notifications not available. Install 'plyer' for notifications: pip install plyer")

# Import existing components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fraud_detection.detector import FraudDetector, DetectionResult
from media.brand_detector import BrandDetector, BrandMatch


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts"""
    FRAUD_ONLY = "fraud_only"
    BRAND_ONLY = "brand_only"
    COMBINED = "combined"  # Both fraud and brand detected


@dataclass
class AlertContext:
    """Context information for alerts"""
    message_id: str
    group_name: str
    sender_username: str
    sender_first_name: str
    message_text: str
    ocr_text: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Alert:
    """Comprehensive alert information"""
    alert_type: AlertType
    severity: AlertSeverity
    context: AlertContext
    fraud_result: Optional[DetectionResult] = None
    brand_matches: Optional[List[BrandMatch]] = None
    risk_score: float = 0.0
    alert_message: str = ""
    
    def __post_init__(self):
        """Calculate risk score and generate alert message"""
        self.risk_score = self._calculate_risk_score()
        self.alert_message = self._generate_alert_message()
    
    def _calculate_risk_score(self) -> float:
        """Calculate combined risk score from fraud and brand detection"""
        fraud_score = self.fraud_result.fraud_score if self.fraud_result else 0.0
        brand_score = 0.0
        
        if self.brand_matches:
            # Use highest brand confidence as brand score
            brand_score = max(match.confidence for match in self.brand_matches)
        
        # Combined scoring with weights
        if self.alert_type == AlertType.COMBINED:
            # Higher weight for combined detection (more suspicious)
            return min((fraud_score * 0.6) + (brand_score * 0.4) + 0.2, 1.0)
        elif self.alert_type == AlertType.FRAUD_ONLY:
            return fraud_score
        elif self.alert_type == AlertType.BRAND_ONLY:
            return brand_score * 0.8  # Slightly lower for brand-only
        
        return 0.0
    
    def _generate_alert_message(self) -> str:
        """Generate formatted alert message"""
        severity_emoji = {
            AlertSeverity.LOW: "🟡",
            AlertSeverity.MEDIUM: "🟠", 
            AlertSeverity.HIGH: "🔴",
            AlertSeverity.CRITICAL: "🚨"
        }
        
        emoji = severity_emoji.get(self.severity, "⚠️")
        
        # Header
        message = f"{emoji} **FRAUD ALERT** - {self.severity.value.upper()}\n\n"
        
        # Context
        message += f"📍 **Group:** {self.context.group_name}\n"
        message += f"👤 **Sender:** {self.context.sender_first_name}"
        if self.context.sender_username:
            message += f" (@{self.context.sender_username})"
        message += f"\n🕐 **Time:** {self.context.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"📊 **Risk Score:** {self.risk_score:.2f}\n\n"
        
        # Detection details
        if self.alert_type == AlertType.COMBINED:
            message += "🎯 **COMBINED THREAT DETECTED**\n"
        
        if self.fraud_result and self.fraud_result.is_suspicious:
            message += f"🚩 **Fraud Keywords:** {', '.join(self.fraud_result.detected_keywords)}\n"
            message += f"📈 **Fraud Score:** {self.fraud_result.fraud_score:.2f}\n"
        
        if self.brand_matches:
            brands = [f"{match.brand} ({match.confidence:.2f})" for match in self.brand_matches]
            message += f"🏢 **Brands Detected:** {', '.join(brands)}\n"
        
        # Message content
        message += f"\n💬 **Message:**\n```\n{self.context.message_text[:500]}"
        if len(self.context.message_text) > 500:
            message += "..."
        message += "\n```"
        
        # OCR content if available
        if self.context.ocr_text:
            message += f"\n🔍 **OCR Text:**\n```\n{self.context.ocr_text[:300]}"
            if len(self.context.ocr_text) > 300:
                message += "..."
            message += "\n```"
        
        return message


class AlertManager:
    """
    Main alert management system
    
    Combines fraud detection and brand detection to send intelligent alerts
    via Telegram using existing client infrastructure.
    """
    
    def __init__(self, telegram_client=None, alert_chat_id: str = None, enable_desktop_notifications: bool = True, enable_sound_alerts: bool = True, bot_token: str = None, bot_alert_chat_id: str = None):
        """
        Initialize AlertManager.
        
        Args:
            telegram_client: Telegram client instance for sending alerts
            alert_chat_id: Chat ID to send alerts to (defaults to 'me')
            enable_desktop_notifications: Enable desktop notifications when alerts are sent
            enable_sound_alerts: Enable sound alerts when alerts are sent
            bot_token: Telegram bot token for sending alerts via bot
            bot_alert_chat_id: Chat ID for bot alerts (group/channel ID)
        """
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Notification settings
        self.enable_desktop_notifications = enable_desktop_notifications and NOTIFICATIONS_AVAILABLE
        self.enable_sound_alerts = enable_sound_alerts
        
        if enable_desktop_notifications and not NOTIFICATIONS_AVAILABLE:
            self.logger.warning("Desktop notifications requested but 'plyer' not available. Install with: pip install plyer")
        
        # Initialize Telegram client
        if telegram_client is None:
            # Import and create Telegram client
            from telethon import TelegramClient
            from dotenv import load_dotenv
            
            load_dotenv()
            api_id = os.getenv('API_ID')
            api_hash = os.getenv('API_HASH')
            phone_number = os.getenv('PHONE_NUMBER')
            
            if not all([api_id, api_hash, phone_number]):
                raise ValueError("Missing Telegram credentials in .env file")
            
            self.telegram_client = TelegramClient('alert_session', api_id, api_hash)
            self.phone_number = phone_number
            self._client_needs_start = True
        else:
            self.telegram_client = telegram_client
            self._client_needs_start = False
            
        self.alert_chat_id = alert_chat_id or "me"
        
        # Initialize bot client if bot token is provided
        self.bot_token = bot_token
        self.bot_alert_chat_id = bot_alert_chat_id
        self.bot_client = None
        
        if bot_token:
            try:
                import requests
                self.bot_available = True
                self.logger.info(f"Bot token provided. Bot alerts will be sent to chat: {bot_alert_chat_id}")
            except ImportError:
                self.bot_available = False
                self.logger.warning("Bot token provided but 'requests' library not available. Install with: pip install requests")
        else:
            self.bot_available = False
        
        # Initialize detection systems
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from fraud_detection.keyword_manager import KeywordManager
        keyword_manager = KeywordManager()
        self.fraud_detector = FraudDetector(keyword_manager)
        self.brand_detector = BrandDetector()
        
        # Alert configuration
        self.min_alert_score = 0.3  # Minimum score to trigger alert
        self.rate_limit_window = timedelta(minutes=5)  # Rate limiting window
        self.max_alerts_per_window = 10  # Max alerts per window
        
        # Rate limiting tracking
        self.recent_alerts: List[datetime] = []
        
        # Statistics
        self.alerts_sent = 0
        self.alerts_suppressed = 0
        
        self.logger = logging.getLogger(__name__)
    
    async def analyze_and_alert(self, context: AlertContext) -> Optional[Alert]:
        """
        Analyze text for fraud/brand detection and send alert if needed.
        
        Args:
            context: Alert context with message information
            
        Returns:
            Alert object if alert was generated and sent, None otherwise
        """
        try:
            # Always run fraud detection
            fraud_result = self.fraud_detector.detect_fraud(context.message_text)
            
            # Run brand detection on combined text
            combined_text = context.message_text
            if context.ocr_text:
                combined_text += " " + context.ocr_text
                
            brand_matches = self.brand_detector.detect_brands(combined_text)
            
            # Calculate combined risk score
            risk_score = self._calculate_risk_score(fraud_result, brand_matches)
            
            # Determine if we should send an alert
            should_alert = False
            alert_type = AlertType.FRAUD_ONLY  # Default
            severity = AlertSeverity.LOW  # Default
            
            # Send alert if fraud is detected (regardless of brand detection)
            if fraud_result and fraud_result.is_suspicious:
                should_alert = True
                if brand_matches:
                    alert_type = AlertType.COMBINED
                    severity = self._determine_severity(risk_score, has_brands=True)
                else:
                    alert_type = AlertType.FRAUD_ONLY
                    severity = self._determine_severity(fraud_result.fraud_score, has_brands=False)
            
            # Also send alert if high-risk brands are detected (even without fraud keywords)
            elif brand_matches:
                high_risk_brands = [m for m in brand_matches if m.risk_level in ['high', 'critical']]
                if high_risk_brands:
                    should_alert = True
                    alert_type = AlertType.BRAND_ONLY
                    severity = self._determine_severity(risk_score, has_brands=True)
            
            if should_alert:
                # Create alert
                alert = Alert(
                    alert_type=alert_type,
                    severity=severity,
                    context=context,
                    fraud_result=fraud_result,
                    brand_matches=brand_matches,
                    risk_score=risk_score
                )
                
                # Send alert
                if self.telegram_client:
                    # Ensure Telegram client is connected
                    if not self.telegram_client.is_connected():
                        if hasattr(self, '_client_needs_start') and self._client_needs_start:
                            await self.telegram_client.start(phone=self.phone_number)
                            self.logger.info("Telegram client connected for alerts")
                        else:
                            await self.telegram_client.connect()
                            self.logger.info("Telegram client reconnected for alerts")
                    
                    success = await self.send_alert(alert)
                    if success:
                        return alert
                else:
                    self.logger.warning("No Telegram client available for sending alerts")
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error in analyze_and_alert: {e}")
            return None
    
    def _calculate_risk_score(self, fraud_result: Optional[DetectionResult], brand_matches: Optional[List[BrandMatch]]) -> float:
        """Calculate combined risk score from fraud and brand detection"""
        fraud_score = fraud_result.fraud_score if fraud_result else 0.0
        brand_score = 0.0
        
        if brand_matches:
            # Calculate brand risk based on highest risk brand
            risk_weights = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'critical': 1.0}
            brand_score = max([risk_weights.get(match.risk_level, 0.0) for match in brand_matches], default=0.0)
        
        # Combine scores with weighted average
        if fraud_score > 0 and brand_score > 0:
            # Both detected - higher combined risk
            return min(1.0, (fraud_score * 0.7) + (brand_score * 0.5))
        elif fraud_score > 0:
            return fraud_score
        elif brand_score > 0:
            return brand_score
        else:
            return 0.0

    def _determine_severity(self, risk_score: float, has_brands: bool = False) -> AlertSeverity:
        """Determine alert severity based on risk score and brand presence"""
        if has_brands and risk_score > 0.7:
            return AlertSeverity.CRITICAL
        elif risk_score > 0.8:
            return AlertSeverity.HIGH
        elif risk_score > 0.6:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW

    def _should_send_alert(self) -> bool:
        """Check if we should send an alert based on rate limiting"""
        now = datetime.now()
        
        # Clean old alerts outside the window
        cutoff = now - self.rate_limit_window
        self.recent_alerts = [alert_time for alert_time in self.recent_alerts if alert_time > cutoff]
        
        # Check if we're at the limit
        return len(self.recent_alerts) < self.max_alerts_per_window

    def _update_rate_limit(self):
        """Update rate limiting tracking"""
        self.recent_alerts.append(datetime.now())
        self.alerts_sent += 1

    def _send_desktop_notification(self, alert: Alert):
        """Send desktop notification for alert"""
        if not self.enable_desktop_notifications:
            return
            
        try:
            # Create notification title and message
            severity_emoji = {
                AlertSeverity.LOW: "🟡",
                AlertSeverity.MEDIUM: "🟠", 
                AlertSeverity.HIGH: "🔴",
                AlertSeverity.CRITICAL: "🚨"
            }
            
            title = f"{severity_emoji.get(alert.severity, '⚠️')} Fraud Alert - {alert.severity.value.upper()}"
            
            # Create concise message for notification
            message_parts = []
            if alert.fraud_result:
                keywords = ", ".join(alert.fraud_result.matched_keywords)
                message_parts.append(f"Keywords: {keywords}")
            
            if alert.brand_matches:
                brands = ", ".join([match.brand_name for match in alert.brand_matches])
                message_parts.append(f"Brands: {brands}")
            
            message_parts.append(f"Group: {alert.context.group_name}")
            message_parts.append(f"Risk Score: {alert.risk_score:.2f}")
            
            message = "\n".join(message_parts)
            
            # Send notification in a separate thread to avoid blocking
            def send_notification():
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Fraud Monitor",
                    timeout=10,
                    toast=True  # Use Windows toast notifications if available
                )
            
            threading.Thread(target=send_notification, daemon=True).start()
            self.logger.info("Desktop notification sent")
            
        except Exception as e:
            self.logger.error(f"Failed to send desktop notification: {e}")

    def _play_alert_sound(self, alert: Alert):
        """
        Play alert sound based on severity level.
        
        Args:
            alert: Alert object containing severity information
        """
        if not self.enable_sound_alerts:
            return
            
        try:
            # Play different sounds based on severity
            if alert.severity == AlertSeverity.CRITICAL:
                winsound.MessageBeep(winsound.MB_ICONHAND)
                # Additional beeps for critical alerts
                for _ in range(2):
                    winsound.Beep(1000, 200)  # 1000Hz for 200ms
            elif alert.severity == AlertSeverity.HIGH:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                winsound.Beep(800, 300)  # 800Hz for 300ms
            elif alert.severity == AlertSeverity.MEDIUM:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            else:  # LOW
                winsound.MessageBeep(winsound.MB_OK)
                
            self.logger.info(f"Alert sound played for {alert.severity.value} severity")
            
        except Exception as e:
            self.logger.error(f"Failed to play alert sound: {e}")

    async def _send_bot_alert(self, alert: Alert) -> bool:
        """
        Send alert via Telegram bot to a group/channel.
        
        Args:
            alert: Alert object to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.bot_available or not self.bot_token or not self.bot_alert_chat_id:
            return False
            
        try:
            import requests
            
            # Telegram Bot API URL
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            # Prepare message data
            data = {
                'chat_id': self.bot_alert_chat_id,
                'text': alert.alert_message,
                'parse_mode': 'HTML'
            }
            
            # Send message via bot
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                self.logger.info(f"Bot alert sent successfully to chat {self.bot_alert_chat_id}")
                return True
            else:
                self.logger.error(f"Bot alert failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to send bot alert: {e}")
            return False

    async def send_alert(self, alert: Alert) -> bool:
        """
        Send alert via Telegram with optional desktop notifications, sounds, and bot alerts.
        
        Args:
            alert: Alert object to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Check rate limiting
            if not self._should_send_alert():
                self.logger.info("Alert suppressed due to rate limiting")
                self.alerts_suppressed += 1
                return False
            
            # Format message
            message = alert.alert_message
            
            # Try to send via bot first if available
            bot_sent = False
            if self.bot_available:
                bot_sent = await self._send_bot_alert(alert)
                if bot_sent:
                    print(f"🤖 Bot alert sent to group: {alert.alert_type.value}")
            
            # Send to configured chat (group, channel, or saved messages) if bot failed or not available
            if not bot_sent:
                await self.telegram_client.send_message(self.alert_chat_id, message)
                print(f"📱 Telegram alert sent: {alert.alert_type.value}")
            
            # Update rate limiting
            self._update_rate_limit()
            
            # Send desktop notification if enabled
            if self.enable_desktop_notifications:
                self._send_desktop_notification(alert)
                print(f"🖥️  Desktop notification triggered")
            
            # Play alert sound if enabled
            if self.enable_sound_alerts:
                self._play_alert_sound(alert)
                print(f"🔊 Sound alert triggered")
            
            self.logger.info(f"Alert sent successfully: {alert.alert_type.value}")
            self.alerts_sent += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Get alert system statistics"""
        return {
            "alerts_sent": self.alerts_sent,
            "alerts_suppressed": self.alerts_suppressed,
            "recent_alerts_count": len(self.recent_alerts),
            "rate_limit_window_minutes": self.rate_limit_window.total_seconds() / 60,
            "max_alerts_per_window": self.max_alerts_per_window,
            "min_alert_score": self.min_alert_score
        }
    
    def update_configuration(self, **kwargs):
        """Update alert configuration"""
        if "min_alert_score" in kwargs:
            self.min_alert_score = max(0.0, min(1.0, kwargs["min_alert_score"]))
        
        if "max_alerts_per_window" in kwargs:
            self.max_alerts_per_window = max(1, kwargs["max_alerts_per_window"])
        
        if "rate_limit_minutes" in kwargs:
            self.rate_limit_window = timedelta(minutes=max(1, kwargs["rate_limit_minutes"]))
        
        self.logger.info("Alert configuration updated")


# Utility functions for easy integration
async def send_test_alert(telegram_client: TelegramClient, target_chat: str = "me"):
    """Send a test alert to verify the system works"""
    test_context = AlertContext(
        message_id="test_123",
        group_name="Test Group",
        sender_username="testuser",
        sender_first_name="Test User",
        message_text="This is a test message with PayPal and investment opportunity keywords"
    )
    
    alert_manager = AlertManager(telegram_client)
    alert = await alert_manager.analyze_and_alert(test_context)
    
    if alert:
        print(f"{Fore.GREEN}✅ Test alert sent successfully!")
        print(f"Alert type: {alert.alert_type.value}")
        print(f"Severity: {alert.severity.value}")
        print(f"Risk score: {alert.risk_score:.2f}")
    else:
        print(f"{Fore.YELLOW}⚠️ No alert generated (may be below threshold)")


def create_alert_context_from_message(message, group_name: str, ocr_text: str = None) -> AlertContext:
    """Helper function to create AlertContext from Telegram message"""
    return AlertContext(
        message_id=str(message.id),
        group_name=group_name,
        sender_username=message.sender.username if message.sender else "unknown",
        sender_first_name=message.sender.first_name if message.sender else "Unknown",
        message_text=message.text or "",
        ocr_text=ocr_text,
        timestamp=message.date
    )