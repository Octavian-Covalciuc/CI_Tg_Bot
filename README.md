# Telegram CI/CD Notification Bot 🤖

A Python-based Telegram bot that monitors your CI/CD pipeline and server health. It receives webhook notifications from GitLab when merges occur and periodically checks if your servers are up and running.

## Features

✅ **GitLab Webhook Integration**
- Receives notifications on merge requests
- Monitors specific branches (development, pre-prod, main)
- Shows merge details, author, and target environment

✅ **Server Health Monitoring**
- Periodic HTTP health checks
- Alerts on status changes (UP ↔ DOWN)
- Configurable check intervals and timeouts

✅ **Telegram Notifications**
- Real-time merge notifications
- Health status alerts
- Formatted messages with emojis

✅ **HTTP API**
- Webhook endpoint for GitLab
- Manual health check trigger
- Test endpoints

## Prerequisites

1. **Telegram Bot Token**
   - Create a bot via [@BotFather](https://t.me/botfather)
   - Use `/newbot` command and follow instructions
   - Save the bot token

2. **Telegram Chat ID**
   - Add your bot to a group or get your personal chat ID
   - Use [@userinfobot](https://t.me/userinfobot) to get your chat ID
   - Or use [@RawDataBot](https://t.me/rawdatabot) in a group

3. **GitLab Repository Access**
   - Admin access to configure webhooks
   - Project settings → Webhooks

## Quick Start

### 1. Clone and Setup

```bash
cd telegram-bot

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
notepad .env
```

### 2. Configure Environment Variables

Edit `.env` file:

```env
# Get this from @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Get this from @userinfobot
TELEGRAM_CHAT_ID=123456789

# Secret token for webhook security
WEBHOOK_SECRET=your-secure-random-string-here

# Webhook configuration
WEBHOOK_PORT=5000
WEBHOOK_HOST=0.0.0.0

# Health check every 5 minutes
HEALTH_CHECK_INTERVAL=300

# Path to the YAML manifest with Front Door + VM endpoints
MONITOR_CONFIG_PATH=CI_Tg_Bot/monitor_urls.yaml
# (Optional fallback) provide comma-separated URLs when YAML can't be mounted
# MONITOR_URLS=http://taxi-disp-rest-dev.germanywestcentral.cloudapp.azure.com,http://taxi-disp-rest-preprod.germanywestcentral.cloudapp.azure.com,http://taxi-disp-rest-prod.germanywestcentral.cloudapp.azure.com

# Branches to monitor
MONITORED_BRANCHES=development,pre-prod,main
```

### 3. Run with Docker (Recommended)

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### 4. Run Locally (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python app.py
```

## GitLab Webhook Configuration

### 1. Expose Your Webhook (for local development)

If running locally, expose your webhook using ngrok or similar:

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 5000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### 2. Configure GitLab Webhook

1. Go to your GitLab project
2. Navigate to **Settings → Webhooks**
3. Add webhook:
   - **URL**: `https://your-server.com/webhook/gitlab` or `https://abc123.ngrok.io/webhook/gitlab`
   - **Secret Token**: Same as `WEBHOOK_SECRET` in your `.env`
   - **Trigger**: 
     - ✅ Push events
     - ✅ Merge request events
   - **SSL verification**: Enable (recommended)
4. Click **Add webhook**
5. Test with **Test → Merge request events**

## API Endpoints

### Health Check (Bot Status)
```bash
GET http://localhost:5000/health
```

### GitLab Webhook
```bash
POST http://localhost:5000/webhook/gitlab
Headers:
  X-Gitlab-Token: your-webhook-secret
  X-Gitlab-Event: Merge Request Hook
```

### Manual Health Check
```bash
GET http://localhost:5000/check-health
```

### Test Webhook
```bash
POST http://localhost:5000/webhook/test
Content-Type: application/json

{
  "message": "Testing webhook!"
}
```

## Usage Examples

### Test Bot Connection
```bash
# Using curl
curl http://localhost:5000/webhook/test \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from CI/CD!"}'
```

### Manual Health Check
```bash
curl http://localhost:5000/check-health
```

## Notification Examples

### Merge Notification
```
🔀 Merge Request Completed
⏰ 2025-11-21 15:30:45 UTC
────────────────────────────────────────

📋 Feature: Add user authentication
🔗 MR !42

📦 Project: taxidispatcher
🌿 feature/auth → development
👤 Merged by: John Doe (@johndoe)
📌 Commit: abc12345

💬 Implements JWT-based authentication...

🧪 Development deployment may be triggered
```

### Health Alert
```
🚨 Service Status Alert
⏰ 2025-11-21 15:35:20 UTC
────────────────────────────

❌ Production is now DOWN
   Previous: UP → Current: DOWN
   Error: Connection Error
   URL: http://taxi-disp-rest-prod...
```

## Integration with Your CI/CD

The bot automatically monitors merges to your configured branches. When a merge happens in GitLab:

1. GitLab sends webhook to bot
2. Bot parses merge details
3. Bot sends formatted notification to Telegram
4. Based on target branch, shows deployment context

### Example GitLab CI Integration

Add to your `.gitlab-ci.yml` (optional - webhooks work automatically):

```yaml
notify_deployment:
  stage: deploy
  script:
    - |
      curl -X POST http://your-bot-server:5000/webhook/test \
        -H "Content-Type: application/json" \
        -d "{\"message\":\"Deployment to $CI_ENVIRONMENT_NAME completed\"}"
  only:
    - development
    - pre-prod
    - main
```

## Monitoring Configuration

### Use the curated endpoint manifest

`monitor_urls.yaml` is now the source of truth. Each entry specifies the environment, whether it hits Azure Front Door or the VM directly, and which controller endpoint is queried (`GET /taxi/ping`). Mount a copy beside the bot or point `MONITOR_CONFIG_PATH` to its location and the bot will load it automatically on startup.

Commit YAML changes whenever endpoints move so both surfaces stay covered.

### Add More URLs to Monitor

Append more entries to `monitor_urls.yaml` (or to the file referenced by `MONITOR_CONFIG_PATH`). Each block supports `env`, `surface`, `method`, `url`, and the expected status code.

Need a quick one-off without shipping a YAML file? Set the legacy `MONITOR_URLS` variable with a comma-separated list and it will act as a fallback.

### Change Check Interval

```env
# Check every 2 minutes (120 seconds)
HEALTH_CHECK_INTERVAL=120
```

### Monitor Different Branches

```env
MONITORED_BRANCHES=main,staging,develop,hotfix
```

## Troubleshooting

### Bot Not Sending Messages

1. **Check bot token**:
   ```bash
   # Test bot manually
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
   ```

2. **Verify chat ID**:
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Look for `"chat":{"id":...}`

3. **Check logs**:
   ```bash
   docker-compose logs -f telegram-bot
   ```

### Webhook Not Triggering

1. **Verify webhook URL is accessible**:
   ```bash
   curl http://your-server:5000/health
   ```

2. **Check GitLab webhook logs**:
   - GitLab → Settings → Webhooks → Recent Deliveries

3. **Verify secret token matches**

### Health Checks Not Working

1. **Check URLs are accessible**:
   ```bash
   curl http://your-monitored-server.com
   ```

2. **Increase timeout** in `.env`:
   ```env
   HEALTH_CHECK_TIMEOUT=30
   ```

## Deployment Options

### Option 1: Docker on VPS
```bash
# On your server
git clone <your-repo>
cd telegram-bot
cp .env.example .env
# Edit .env
docker-compose up -d
```

### Option 2: Azure Container Instances
```bash
# Build and push
docker build -t yourusername/telegram-bot .
docker push yourusername/telegram-bot

# Deploy to Azure
az container create \
  --resource-group your-rg \
  --name telegram-bot \
  --image yourusername/telegram-bot \
  --ports 5000 \
  --environment-variables \
    TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN \
    TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID \
    WEBHOOK_SECRET=$WEBHOOK_SECRET
```

### Option 3: Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: telegram-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: telegram-bot
  template:
    metadata:
      labels:
        app: telegram-bot
    spec:
      containers:
      - name: telegram-bot
        image: yourusername/telegram-bot
        ports:
        - containerPort: 5000
        envFrom:
        - secretRef:
            name: telegram-bot-secrets
```

## Security Best Practices

1. **Use HTTPS** for webhook endpoint (required in production)
2. **Set strong WEBHOOK_SECRET** (use random string generator)
3. **Don't commit `.env` file** (use secrets management)
4. **Restrict webhook IP** in firewall (GitLab IP ranges)
5. **Use environment-specific secrets** for different deployments

## Architecture

```
┌─────────────┐
│   GitLab    │
│  Repository │
└──────┬──────┘
       │ Webhook on merge
       ▼
┌─────────────────────────────┐
│   Telegram Bot (Flask)      │
│  ┌───────────────────────┐  │
│  │ GitLab Webhook        │  │
│  │ Handler               │  │
│  └───────────┬───────────┘  │
│              │               │
│  ┌───────────▼───────────┐  │
│  │ Health Check          │  │
│  │ Scheduler (APScheduler│  │
│  └───────────┬───────────┘  │
│              │               │
│  ┌───────────▼───────────┐  │
│  │ Telegram Notifier     │  │
│  └───────────────────────┘  │
└──────────────┬──────────────┘
               │
               ▼
       ┌───────────────┐
       │   Telegram    │
       │  Chat/Group   │
       └───────────────┘
```

## File Structure

```
telegram-bot/
├── app.py                  # Main application
├── config.py               # Configuration management
├── health_checker.py       # Server health monitoring
├── gitlab_handler.py       # GitLab webhook parsing
├── telegram_notifier.py    # Telegram message sending
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker image
├── docker-compose.yml     # Docker Compose config
├── .env.example           # Environment template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Contributing

Feel free to customize the bot for your needs:
- Add more event types (pipeline success/failure)
- Integrate with other CI/CD platforms (GitHub Actions, Jenkins)
- Add interactive commands (keyboard buttons)
- Store metrics in database
- Add custom health check logic

## License

MIT

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review application logs
3. Test endpoints manually with curl
4. Verify GitLab webhook delivery logs

---

**Happy monitoring! 🚀**
