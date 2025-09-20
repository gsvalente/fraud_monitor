"""
Alerts Package - Phase 4.2

Comprehensive alert system that combines fraud detection and brand detection
to send intelligent alerts via Telegram.
"""

from .alert_manager import (
    AlertManager,
    Alert,
    AlertContext,
    AlertType,
    AlertSeverity,
    send_test_alert,
    create_alert_context_from_message
)

__all__ = [
    'AlertManager',
    'Alert', 
    'AlertContext',
    'AlertType',
    'AlertSeverity',
    'send_test_alert',
    'create_alert_context_from_message'
]