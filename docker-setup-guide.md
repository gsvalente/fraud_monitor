# Docker Setup Guide for Telegram Fraud Monitor

## Problem: EOF Error in Docker

The "EOF when reading a line" error occurs because Telethon requires interactive authentication on first run, but Docker containers don't have interactive terminals by default.

## Solution: Pre-create Session File

### Step 1: Run Locally First
1. Run the application locally to create the session file:
   ```bash
   python main.py
   ```
2. Complete the Telegram authentication (phone number, verification code)
3. This creates a `fraud_monitor_session.session` file

### Step 2: Copy Session to Docker
1. Copy the session file to your project directory
2. Ensure it's included in the Docker build context
3. The Dockerfile should copy this file to the container

### Step 3: Update Dockerfile (if needed)
Add this line to your Dockerfile to ensure the session file is copied:
```dockerfile
COPY fraud_monitor_session.session ./
```

### Step 4: Environment Variables
Ensure these environment variables are set in your `.env` file:
- `API_ID`: Your Telegram API ID
- `API_HASH`: Your Telegram API Hash
- `BOT_TOKEN`: Your bot token (if using bot mode)
- `TARGET_GROUPS`: Comma-separated list of group IDs/usernames

## Alternative: Bot Mode
If you prefer not to use a user session, you can modify the code to use bot authentication:
1. Create a bot via @BotFather
2. Use the bot token instead of user authentication
3. Add the bot to your target groups

## Troubleshooting
- If you still get EOF errors, ensure the session file has proper permissions
- Check that the session file isn't corrupted
- Verify your API credentials are correct
- Make sure the Docker container has access to the session file

## Current Error Handling
The application now includes:
- Docker environment detection
- Session file validation
- Detailed EOF error messages with solutions
- Graceful error handling and cleanup