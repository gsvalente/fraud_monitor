#!/usr/bin/env python3
"""
Telegram Fraud Monitor - Phase 1
Basic message collection and monitoring
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from telegram_client.client import main

if __name__ == "__main__":
    print("🚀 Starting Telegram Fraud Monitor - Phase 1")
    print("📋 Features: Basic message collection, simple keyword detection")
    print("⚠️  Make sure to configure your .env file first!")
    print("-" * 60)
    
    asyncio.run(main())