# Gmail to Discord Webhook - OAuth 2.0 Setup Guide

This application monitors Gmail for new emails and sends notifications to Discord via webhooks. It uses OAuth 2.0 authentication and is designed for headless server deployment.

## Prerequisites

- Docker and Docker Compose installed
- Google Cloud Platform account
- Discord server with webhook permissions
- Gmail account (personal or Google Workspace)
- Local machine with browser (for initial OAuth setup)

## Setup Guide

### 1. Google Cloud Console Setup

**Create a Google Cloud Project**
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project or select existing one

**Enable Gmail API**
- Navigate to "APIs & Services" > "Library"
- Search for "Gmail API"
- Click "Enable"

**Create OAuth 2.0 Credentials**
- Go to "APIs & Services" > "Credentials"
- Click "+ CREATE CREDENTIALS" > "OAuth client ID"
- Choose "Desktop application"
- Click "Create"
- Download the JSON file and rename it to `client_secret.json`

### 2. Discord Webhook Setup

**Create Discord Webhook**
- Go to your Discord server
- Right-click on the channel where you want notifications
- Select "Edit Channel" > "Integrations" > "Webhooks"
- Click "New Webhook"
- Copy the webhook URL

### 3. OAuth Token Generation

The OAuth token must be generated on a local machine with a browser before deploying to your server.

**On your local machine:**

1. Copy [`client_secret.json`](client_secret.json) to your local machine
2. Install Python dependencies:
   ```bash
   pip install google-auth google-auth-oauthlib google-api-python-client
   ```
3. Run the token generator:
   ```bash
   python generate_token.py
   ```
4. Follow the authentication flow in your browser
5. Copy the generated `token.json` to your server at `data/token.json`

### 4. Server Configuration

**Clone the project:**
```bash
git clone https://github.com/Rockerkemm/GmailToDiscord.git
cd GmailToDiscord
```

**Configure environment variables:**
```bash
cp .env.example .env
```

Edit the [.env](.env) file:
```env
# Discord webhook URL
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here

# OAuth 2.0 configuration
TOKEN_FILE=token.json

# Discord bot profile pictures (optional)
DISCORD_AVATAR_URL=https://example.com/your-bot-avatar.png
DISCORD_ERROR_AVATAR_URL=https://example.com/your-error-bot-avatar.png
```

### 5. Docker Deployment

**Build and start the container:**
```bash
docker-compose up -d
```

**Check status:**
```bash
docker-compose ps
```

**View logs:**
```bash
docker-compose logs -f gmail-webhook
```

**Expected output:**
```
Starting Gmail to Discord webhook with OAuth 2.0...
Loaded existing OAuth credentials
OAuth 2.0 authentication successful
First time running! Will process the most recent email.
Starting continuous monitoring (checking every 10 seconds)
```

## Project Structure

```
GmailToDiscord/
├── gmail_webhook.py         # Main application
├── generate_token.py        # OAuth token generator (run locally)
├── Dockerfile               # Docker configuration
├── docker-compose.yml       # Docker Compose configuration
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables(rename .env.example)
├── .env.example             # Environment template
├── client_secret.json       # OAuth 2.0 credentials (download from Google)
├── data/                    # Persistent data directory
│   ├── token.json           # OAuth token (generated locally, copied here)
│   ├── last_processed.json  # Application state
│   └── error_queue.json     # Error queue for retry logic
└── .github/
    └── workflows/
        └── build-container.yaml  # CI/CD workflow
```

## Configuration

### Environment Variables

The [.env](.env) file contains:
```env
# Discord webhook URL
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url_here

# OAuth 2.0 configuration
TOKEN_FILE=token.json

# Discord bot profile pictures (optional)
DISCORD_AVATAR_URL=https://example.com/your-bot-avatar.png
DISCORD_ERROR_AVATAR_URL=https://example.com/your-error-bot-avatar.png
```

### Discord Bot Customization

You can customize the Discord bot appearance by setting profile picture URLs:

- `DISCORD_AVATAR_URL` - Profile picture for email notifications (incoming/outgoing emails)
- `DISCORD_ERROR_AVATAR_URL` - Profile picture for error notifications

These URLs should point to publicly accessible image files (PNG, JPG, GIF). If not specified, Discord will use the default webhook avatar.

### Gmail API Scopes

The application uses minimal required permissions:
- `https://www.googleapis.com/auth/gmail.readonly` - Read-only access to Gmail

### Message Filtering

The application automatically filters out:
- Draft messages (`DRAFT` label)
- Scheduled messages (`SCHEDULED` label)

## Troubleshooting

### OAuth Token Issues

**Problem:** "OAuth token required - please generate token.json on a local machine"

**Solution:**
```bash
# Ensure token.json exists in the data directory
ls -la data/token.json

# If missing, follow the OAuth Token Generation steps above
```

**Problem:** "Failed to load existing credentials"

**Solution:**
```bash
# Verify token.json is valid JSON
cat data/token.json | python -m json.tool
```

**Problem:** "Failed to refresh credentials"

**Solution:**
```bash
# Regenerate the token on your local machine
# Run generate_token.py again and copy the new token.json to the server
python generate_token.py
```

### Authentication Flow Issues

**Problem:** "OAuth credentials file not found"

**Solution:**
```bash
# Ensure client_secret.json exists
ls -la client_secret.json

# If missing, download from Google Cloud Console
```

### Docker Issues

**Problem:** Container fails to start

**Solution:**
```bash
# Check logs for specific error messages
docker-compose logs gmail-webhook

# Ensure all required files are present
ls -la client_secret.json data/token.json .env
```

### Discord Avatar Issues

**Problem:** Bot avatars not displaying correctly

**Solution:**
```bash
# Ensure avatar URLs are publicly accessible
curl -I https://your-avatar-url.png

# Check if URLs are valid in your .env file
grep DISCORD_.*AVATAR_URL .env
```

## Development

### Running Locally

You can run the application locally for testing:

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure you have the required files
ls -la client_secret.json data/token.json .env

# Run the application
python gmail_webhook.py
```

### Token Generation Scripts

The project includes [`generate_token.py`](generate_token.py) for generating OAuth tokens. Run this script on a local machine with browser access before deploying to your server.