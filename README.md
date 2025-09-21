# Gmail to Discord Monitor

This project monitors a Gmail account and sends notifications to a Discord channel using webhooks. It is designed for automation, monitoring, and alerting based on incoming and outgoing emails.

## Features
- Monitors Gmail inbox for new messages
- Sends notifications to Discord via webhooks
- Tracks processed messages and statistics
- Configurable via `config.json`
- Includes logging and error reporting

## Requirements
- Python 3.8+
- Google API credentials (OAuth2)
- Discord webhook URL(s)

## Setup
1. **Clone the repository**
2. **Install dependencies:**
   pip install -r requirements.txt
   # or manually:
   pip install google-api-python-client requests ratelimit filelock tenacity python-dotenv google-auth-oauthlib

3. **Google API Setup:**
   - Create a project in Google Cloud Console
   - Enable Gmail API
   - Download `credentials.json` and place it in the project directory (do NOT upload this to GitHub)

4. **Run authentication:**
   python auth.py
   This will generate a `token.pickle` or `token.json` file (do NOT upload this to GitHub)

5. **Configure environment variables:**
   - Create a `.env` file with your Discord webhook URLs:
     WEBHOOK_URL=your_discord_webhook_url
     MONITOR_WEBHOOK_URL=your_monitoring_webhook_url

6. **Edit `config.json` as needed**

7. **Run the monitor:**
   python gmail_webhook.py
   # or
   python gmail_webhookV2.py


## Files
- `auth.py` - Handles Google OAuth2 authentication
- `gmail_webhook.py` - Main monitoring scripts
- `config.json` - Configuration for monitoring
- `gmail-monitor.service` - Example systemd service file (Linux)

## Do NOT Upload
- `credentials.json`, `token.json`, `token.pickle` (contain secrets)
- `gmail_monitor.log`, `gmail_monitor.lock`, `tempCodeRunnerFile.py` (runtime or temp files)


## Credits
- Google API Python Client
- Discord Webhooks
- Contributors: [Daniel Smyth]
