# Telegram Fraud Monitor 🔍

A comprehensive Python tool for monitoring Telegram groups and detecting potential fraud activities in real-time. This system uses advanced detection methods including keyword analysis, brand recognition, OCR text extraction, and intelligent alerting.

## 🌟 Key Features

### 🚨 Fraud Detection
- **Smart Keyword Detection**: Identifies suspicious phrases and scam indicators
- **Brand Recognition**: Detects impersonation of popular brands (PayPal, Amazon, Microsoft, etc.)
- **Advanced Scoring**: Multi-factor risk assessment with confidence levels
- **Context Analysis**: Recognizes urgency tactics, financial requests, and contact patterns

### 📱 Real-time Monitoring
- **Live Group Monitoring**: Monitor multiple Telegram groups simultaneously
- **Instant Alerts**: Get immediate notifications via Telegram bot
- **Message History**: Complete message tracking with timestamps and metadata
- **User Tracking**: Monitor user behavior and patterns

### 🖼️ Image Analysis
- **OCR Text Extraction**: Extract and analyze text from images using Tesseract
- **Multi-language Support**: Support for 100+ languages
- **Image Preprocessing**: Automatic enhancement for better text recognition
- **Suspicious Content Detection**: Identify fraudulent content in images

### 💾 Data Management
- **SQLite Database**: Persistent storage for all messages and detections
- **Docker Volumes**: Persistent data storage in containerized environments
- **Session Tracking**: Monitor multiple sessions with detailed statistics
- **Rate Limiting**: Intelligent alert throttling to prevent spam
- **Comprehensive Reporting**: Detailed fraud analysis with score breakdowns
- **Database Export**: Easy database access and backup capabilities

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher OR Docker
- Telegram API credentials (get them from https://my.telegram.org/apps)
- Access to the Telegram groups you want to monitor
- Tesseract OCR engine (for image text extraction) - *Not needed for Docker*

### Installation

**For Docker Deployment (Recommended)**:
```bash
git clone <repository-url>
cd automationstep
# Configure your .env file (see Configuration section)
docker build -t fraud-monitor .
docker run --rm --name telegram-fraud-monitor -v fraud_data:/app/data -v fraud_downloads:/app/downloads -v fraud_logs:/app/logs fraud-monitor:latest
```

**For Local Development** (Optional):
```bash
git clone <repository-url>
cd automationstep
pip install -r requirements.txt
# Install Tesseract OCR manually
# Configure your .env file
python main.py
```

## 🐳 Docker Deployment

For containerized deployment, you can use Docker:

1. **Build the Docker Image**:
   ```bash
   docker build -t fraud-monitor .
   ```

2. **Run the Container**:
   ```bash
   docker run --rm --name telegram-fraud-monitor -v fraud_data:/app/data -v fraud_downloads:/app/downloads -v fraud_logs:/app/logs fraud-monitor:latest
   ```

   This command will:
   - Create a container named `telegram-fraud-monitor`
   - Mount persistent volumes for data, downloads, and logs
   - Automatically remove the container when stopped (`--rm`)

3. **Using Docker Compose** (Alternative):
   ```bash
   docker-compose up -d
   ```

### Accessing Docker Database

When running in Docker, the database is stored in a persistent volume. To access your data:

1. **Copy Database from Container**:
   ```bash
   docker run --rm -v fraud_data:/data -v ${PWD}:/host alpine cp /data/fraud_monitor.db /host/fraud_monitor_current.db
   ```

2. **View Database Contents**:
   - Use SQLite Browser: https://sqlitebrowser.org/
   - Or any SQLite tool to open `fraud_monitor_current.db`

3. **Check Database Status**:
   ```bash
   # Check message count
   docker run --rm -v fraud_data:/data alpine sh -c "apk add sqlite > /dev/null 2>&1 && sqlite3 /data/fraud_monitor.db 'SELECT COUNT(*) FROM messages;'"
   
   # Check fraud detections
   docker run --rm -v fraud_data:/data alpine sh -c "apk add sqlite > /dev/null 2>&1 && sqlite3 /data/fraud_monitor.db 'SELECT COUNT(*) FROM fraud_detections;'"
   ```

4. **Volume Management**:
   ```bash
   # List Docker volumes
   docker volume ls
   
   # Inspect volume location
   docker volume inspect fraud_data
   ```

**Important**: Always use the named volumes (`fraud_data`, `fraud_downloads`, `fraud_logs`) to ensure data persistence between container restarts.

## ⚙️ Configuration

Edit your `.env` file with the following settings:

### Required Settings
```env
# Telegram API Credentials
API_ID=your_api_id
API_HASH=your_api_hash
PHONE_NUMBER=+1234567890

# Groups to Monitor
TARGET_GROUPS=group1,group2,group3
```

### Alert System
```env
# Telegram Bot for Alerts
TELEGRAM_BOT_TOKEN=your_bot_token
ALERT_CHAT_ID=your_chat_id

# Alert Settings
FRAUD_SCORE_THRESHOLD=0.6
ALERT_RATE_LIMIT=5
ALERT_COOLDOWN=300
```

### OCR Settings
```env
# OCR Configuration
TESSERACT_PATH=tesseract
OCR_LANGUAGE=eng
OCR_CONFIDENCE_THRESHOLD=60.0
OCR_PREPROCESSING_ENABLED=true
```

### Database Settings
```env
# Database Configuration
DATABASE_URL=sqlite:///fraud_monitor.db
SESSION_NAME=fraud_monitor
LOG_LEVEL=INFO
```

## 🎯 Usage Examples

### Basic Monitoring
```bash
# Start monitoring with default settings
python main.py
```

### Testing the System
```bash
# Test fraud detection
python test_advanced_fraud_scoring.py

# Test brand detection
python test_brand_detection.py

# Test alert system
python test_alert_system.py
```

### Managing Keywords
```bash
# Add or manage fraud keywords
python manage_keywords.py
```

## 📊 Sample Output

When the system detects potential fraud, you'll see output like this:

```
🚀 Starting Telegram Fraud Monitor
📱 Connected to Telegram successfully
💾 Database initialized
✅ Monitoring 3 groups...

📨 New Message Detected
🏷️  Group: Crypto Trading Group
👤 Sender: John Doe (@johndoe)
🕐 Time: 2024-01-15 14:30:25
💬 Message: "Get rich quick with this PayPal investment opportunity!"

🚨 FRAUD ALERT - HIGH RISK
📊 Risk Score: 0.85/1.00
🎯 Detected: Investment scam, Brand impersonation (PayPal)
🚩 Keywords: "get rich quick", "investment", "opportunity"
📤 Alert sent to Telegram bot

💾 Data saved to database
```

## 🏗️ Project Structure

```
automationstep/
├── src/                      # Main source code
│   ├── alerts/              # Alert system
│   ├── database/            # Database models and operations
│   ├── fraud_detection/     # Fraud detection logic
│   ├── media/               # OCR and image processing
│   └── telegram_client/     # Telegram integration
├── config/                  # Configuration files
├── downloads/               # Downloaded media files
├── alembic/                 # Database migrations
├── tests/                   # Test files
├── main.py                  # Main application
├── requirements.txt         # Python dependencies
└── .env                     # Your configuration
```

## 🔧 Troubleshooting

### Common Issues

**Connection Problems**:
- Verify your API_ID and API_HASH are correct
- Make sure your phone number includes the country code
- You may need to enter a verification code on first run

**Group Access**:
- Ensure you're a member of all target groups
- Check that group names in TARGET_GROUPS are correct

**OCR Not Working**:
- Verify Tesseract is installed and in your PATH
- Check TESSERACT_PATH in your .env file
- Ensure you have the correct language packs installed

**Database Issues**:
- Run `alembic upgrade head` to update the database
- Check file permissions for the database file
- Verify DATABASE_URL is correct

**Docker Issues**:
- **Container not saving data**: Ensure you're using named volumes (`-v fraud_data:/app/data`)
- **Database not accessible**: Copy database using: `docker run --rm -v fraud_data:/data -v ${PWD}:/host alpine cp /data/fraud_monitor.db /host/`
- **Container exits immediately**: Check logs with `docker logs <container_name>`
- **Volume conflicts**: Use `docker volume ls` to check existing volumes
- **Anonymous volumes**: Always use the exact command with named volumes for data persistence

**Docker Commands for Debugging**:
```bash
# Check running containers
docker ps

# View container logs
docker logs telegram-fraud-monitor

# Check volumes
docker volume ls
docker volume inspect fraud_data

# Access container shell
docker exec -it telegram-fraud-monitor sh

# Remove problematic volumes
docker volume rm fraud_data fraud_downloads fraud_logs
```

### Getting Help

If you encounter issues:
1. Check the console output for error messages
2. Verify your .env configuration
3. Test individual components using the test files
4. Check that all dependencies are installed correctly

## 📈 Performance Tips

- **Monitor Responsibly**: Don't monitor too many groups simultaneously
- **Adjust Thresholds**: Fine-tune FRAUD_SCORE_THRESHOLD based on your needs
- **Rate Limiting**: Use appropriate ALERT_RATE_LIMIT to avoid spam
- **Database Maintenance**: Regularly clean old data if storage is a concern

## 🛡️ Security & Privacy

- Keep your API credentials secure and never share them
- Use environment variables for sensitive configuration
- Be aware of Telegram's terms of service when monitoring groups
- Respect user privacy and local laws regarding data collection

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This tool is for educational and security research purposes. Always ensure you have proper authorization before monitoring any Telegram groups and comply with all applicable laws and regulations.