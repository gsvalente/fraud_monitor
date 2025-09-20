# Simplified Database Structure Guide

## Overview

The Telegram Fraud Monitor has been upgraded with a simplified 4-table database structure that reduces complexity while maintaining all essential functionality. This guide explains the new structure and how to use the message saving toggle feature.

## Database Changes

### From 7 Tables to 4 Tables

**Old Structure (7 tables):**
- `telegram_groups` - Removed (group info now stored directly in messages)
- `users` - Removed (user info now stored directly in messages)  
- `messages` - **Kept** (enhanced with additional fields)
- `media_files` - Removed (media info now stored directly in messages)
- `fraud_detections` - **Kept** (unchanged)
- `fraud_keywords` - **Kept** (unchanged)
- `monitoring_sessions` - **Kept** (enhanced with message saving toggle)

**New Structure (4 tables):**
1. **`messages`** - Stores all message data including sender and group info
2. **`fraud_detections`** - Stores fraud analysis results
3. **`fraud_keywords`** - Stores fraud detection keywords
4. **`monitoring_sessions`** - Stores monitoring session data with saving preferences

## New Features

### 1. Message Saving Toggle

You can now control whether non-suspicious messages are saved to reduce database size:

**Environment Variables:**
```env
# Save all messages (suspicious + non-suspicious)
SAVE_NON_SUSPICIOUS_MESSAGES=true

# Save only suspicious messages
SAVE_NON_SUSPICIOUS_MESSAGES=false

# Save media files for all messages
SAVE_ALL_MEDIA=true

# Save media files only for suspicious messages (default)
SAVE_ALL_MEDIA=false

# Message retention period in days
MESSAGE_RETENTION_DAYS=30
```

**Session-Level Control:**
Each monitoring session can override the global setting:
```python
# Start session with custom message saving preference
session_id = db.start_monitoring_session(
    session_name="Custom Session",
    target_groups=["group1", "group2"],
    save_non_suspicious=False  # Only save suspicious messages for this session
)
```

### 2. Enhanced Message Model

The new `Message` table includes all necessary information:

```python
class Message(Base):
    # Basic message info
    message_id = Column(String(50), nullable=False)
    group_id = Column(String(50), nullable=False)
    group_name = Column(String(255), nullable=False)
    
    # Sender info (previously in separate users table)
    sender_id = Column(String(50), nullable=False)
    sender_username = Column(String(255), nullable=True)
    sender_first_name = Column(String(255), nullable=True)
    
    # Content
    text_content = Column(Text, nullable=True)
    message_type = Column(String(50), default='text')
    
    # Media info (previously in separate media_files table)
    has_media = Column(Boolean, default=False)
    media_type = Column(String(50), nullable=True)
    file_id = Column(String(255), nullable=True)
    local_path = Column(String(500), nullable=True)
    
    # OCR processing
    ocr_text = Column(Text, nullable=True)
    ocr_processed = Column(Boolean, default=False)
    
    # Fraud detection
    is_suspicious = Column(Boolean, default=False)
    fraud_score = Column(Float, default=0.0)
    
    # Timestamps
    sent_at = Column(DateTime, nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)
```

## Migration

### Automatic Migration

Use the provided migration script to convert your existing database:

```bash
# Run the simple migration script
python simple_migration.py
```

This will:
1. Create a new simplified database (`fraud_monitor_simplified.db`)
2. Copy all keywords from the old database
3. Copy all messages with their associated data
4. Copy monitoring sessions
5. Create a default monitoring session if none exist

### Manual Configuration

After migration, update your `.env` file:

```env
# Use the new simplified database
DATABASE_PATH=fraud_monitor_simplified.db

# Configure message saving behavior
SAVE_NON_SUSPICIOUS_MESSAGES=true
SAVE_ALL_MEDIA=false
MESSAGE_RETENTION_DAYS=30
```

## Usage Examples

### 1. Basic Usage

The system works exactly the same as before, but with better performance:

```bash
# Start monitoring (uses simplified database automatically)
python main.py

# Manage keywords (works with simplified database)
python manage_keywords.py list
python manage_keywords.py add "new scam" scam 0.8
```

### 2. Message Saving Control

```python
from src.database.simplified_database import SimplifiedDatabaseManager

db = SimplifiedDatabaseManager()

# Start session that saves all messages
session_id = db.start_monitoring_session(
    session_name="Full Monitoring",
    target_groups=["group1"],
    save_non_suspicious=True
)

# Start session that saves only suspicious messages
session_id = db.start_monitoring_session(
    session_name="Suspicious Only",
    target_groups=["group2"],
    save_non_suspicious=False
)
```

### 3. Configuration Check

```python
from src.database.simplified_models import MessageSavingConfig

# Check current configuration
print(f"Save non-suspicious: {MessageSavingConfig.should_save_message(False)}")
print(f"Save media files: {MessageSavingConfig.should_save_media(False)}")
print(f"Retention days: {MessageSavingConfig.get_retention_days()}")
```

## Benefits

### 1. Reduced Complexity
- 43% fewer tables (7 → 4)
- Simpler relationships
- Easier to understand and maintain

### 2. Better Performance
- Fewer JOINs required for queries
- Reduced database overhead
- Faster message processing

### 3. Flexible Storage
- Toggle message saving on/off
- Session-level control
- Automatic cleanup of old messages

### 4. Maintained Functionality
- All fraud detection features preserved
- Keyword management unchanged
- Session monitoring enhanced

## Troubleshooting

### Common Issues

1. **"No such column" errors**: Make sure you're using the new simplified database file
2. **Missing keywords**: Run the migration script to copy data from old database
3. **Configuration not working**: Check your `.env` file has the new variables

