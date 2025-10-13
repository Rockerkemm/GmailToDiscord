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

1. Download [`generate_token.py`](generate_token.py) and place your [`client_secret.json`](client_secret.json) in the same directory
2. Install Python dependencies:
   ```bash
   pip install google-auth google-auth-oauthlib google-api-python-client
   ```
3. Run the token generator:
   ```bash
   python generate_token.py
   ```
4. Follow the authentication flow in your browser
5. Copy the generated `token.json` to your server

### 4. Server Configuration

**Download docker-compose.yml**
```bash
# Create project directory
mkdir GmailToDiscord
cd GmailToDiscord

# Download the docker-compose.yml file directly
wget https://raw.githubusercontent.com/Rockerkemm/GmailToDiscord/main/docker-compose.yml
```

**Configure the Docker Compose file:**
Edit the [`docker-compose.yml`](docker-compose.yml) file and update DISCORD_WEBHOOK_URL:

```yaml
services:
  gmail-webhook:
    image: ghcr.io/rockerkemm/gmailtodiscord:latest
    container_name: gmail-to-discord
    restart: unless-stopped
    volumes:
      # Mount data folder and token.json
      - ./data:/app/data
      - ./token.json:/app/token.json
    environment:
      # Discord webhook URL - REPLACE WITH YOUR WEBHOOK URL
      DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE"
      
      # OAuth 2.0 configuration
      TOKEN_FILE: "token.json"

    stdin_open: true
    tty: true
```

**Copy token.json to the project directory:**
```bash
scp token.json username@to_host:/pathToDirectory/
```

### 5. Docker Deployment

The [`docker-compose.yml`](docker-compose.yml) file is configured to automatically pull the latest Docker image from GitHub Container Registry.

**Start the container:**
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

### Gmail API Scopes

The application uses minimal required permissions:
- `https://www.googleapis.com/auth/gmail.readonly` - Read-only access to Gmail

### Message Filtering

The application automatically filters out:
- Draft messages (`DRAFT` label)
- Scheduled messages (`SCHEDULED` label)

## Docker Image

The application is distributed as a Docker image hosted on GitHub Container Registry:
- **Latest stable**: `ghcr.io/rockerkemm/gmailtodiscord:latest`

### Token Generation Scripts

The project includes [`generate_token.py`](generate_token.py) for generating OAuth tokens. Run this script on a local machine with browser access before deploying to your server.