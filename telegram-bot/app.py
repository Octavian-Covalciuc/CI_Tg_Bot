import logging
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import Config
from health_checker import HealthChecker
from telegram_notifier import TelegramNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize components
Config.validate()
health_checker = HealthChecker()
notifier = TelegramNotifier()
scheduler = BackgroundScheduler()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for the bot itself"""
    return jsonify({
        'status': 'healthy',
        'bot': 'telegram-ci-notifier',
        'version': '1.0.0'
    }), 200


@app.route('/webhook/test', methods=['POST'])
def test_webhook():
    """Test endpoint to verify webhook is working"""
    try:
        data = request.json or {}
        message = data.get('message', 'Test webhook received!')
        
        notifier.send_message(f"🧪 **Test Webhook**\n\n{message}")
        
        return jsonify({
            'status': 'success',
            'message': 'Test notification sent'
        }), 200
    except Exception as e:
        logger.error(f"Error in test webhook: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/notify/deployment', methods=['POST'])
def deployment_notification():
    """
    Endpoint for CI/CD pipeline deployment notifications
    Expected JSON payload:
    {
        "project": "Project Name",
        "branch": "main",
        "environment": "Production",
        "status": "success",
        "user": "John Doe",
        "pipeline_url": "https://gitlab.com/...",
        "commit_sha": "abc123",
        "commit_message": "Fix bug"
    }
    """
    try:
        data = request.json or {}
        
        # Extract data with defaults
        project = data.get('project', 'Unknown Project')
        branch = data.get('branch', 'unknown')
        environment = data.get('environment', 'Unknown')
        status = data.get('status', 'unknown').lower()
        user = data.get('user', 'Unknown')
        pipeline_url = data.get('pipeline_url', '')
        commit_sha = data.get('commit_sha', '')
        commit_message = data.get('commit_message', '')
        
        # Choose emoji based on status
        if status == 'success':
            status_emoji = '✅'
            status_text = 'SUCCESSFUL'
        elif status == 'failed':
            status_emoji = '❌'
            status_text = 'FAILED'
        elif status == 'running':
            status_emoji = '🔄'
            status_text = 'IN PROGRESS'
        else:
            status_emoji = '⚠️'
            status_text = status.upper()
        
        # Format message
        message = f"{status_emoji} **Deployment {status_text}**\n\n"
        message += f"📦 Project: **{project}**\n"
        message += f"🎯 Environment: **{environment}**\n"
        message += f"🌿 Branch: `{branch}`\n"
        message += f"👤 By: {user}\n"
        
        if commit_sha:
            short_sha = commit_sha[:8]
            message += f"📌 Commit: `{short_sha}`\n"
        
        if commit_message:
            msg = commit_message.split('\n')[0][:100]
            message += f"💬 {msg}\n"
        
        if pipeline_url:
            message += f"\n🔗 [View Pipeline]({pipeline_url})"
        
        # Send notification
        notifier.send_message(message)
        
        logger.info(f"Deployment notification sent for {project} - {environment}")
        return jsonify({
            'status': 'success',
            'message': 'Deployment notification sent'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in deployment notification: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/notify/message', methods=['POST'])
def custom_message():
    """
    Generic endpoint to send any custom message
    Expected JSON payload:
    {
        "message": "Your custom message here",
        "parse_mode": "Markdown"  # optional, default is Markdown
    }
    """
    try:
        data = request.json or {}
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'message field is required'}), 400
        
        parse_mode = data.get('parse_mode', 'Markdown')
        
        # Send notification
        notifier.send_message(message, parse_mode=parse_mode)
        
        logger.info(f"Custom message sent")
        return jsonify({
            'status': 'success',
            'message': 'Message sent'
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending custom message: {str(e)}")
        return jsonify({'error': str(e)}), 500


def scheduled_health_check():
    """Scheduled job to check server health"""
    try:
        logger.info("Running scheduled health check...")
        results = health_checker.check_all()
        
        # Check for status changes
        changes = health_checker.get_status_changes(results)
        
        # Send alert if there are status changes
        if changes:
            alert_message = health_checker.format_status_change_alert(changes)
            if alert_message:
                notifier.send_alert(alert_message)
        
        # Always send health report (even if all services are UP)
        report = health_checker.format_health_report(results, include_all=True)
        notifier.send_health_report(report)
        
        # Log results
        up_count = sum(1 for r in results if r['status'] == 'UP')
        logger.info(f"Health check complete: {up_count}/{len(results)} services UP")
        
    except Exception as e:
        logger.error(f"Error in scheduled health check: {str(e)}", exc_info=True)


@app.route('/check-health', methods=['GET'])
def manual_health_check():
    """Manual health check endpoint"""
    try:
        results = health_checker.check_all()
        report = health_checker.format_health_report(results, include_all=True)
        
        notifier.send_health_report(report)
        
        return jsonify({
            'status': 'success',
            'results': results
        }), 200
    except Exception as e:
        logger.error(f"Error in manual health check: {str(e)}")
        return jsonify({'error': str(e)}), 500


def start_scheduler():
    """Initialize and start the background scheduler"""
    if not Config.MONITOR_URLS:
        logger.warning("No MONITOR_URLS configured - health checks disabled")
        return
    
    # Add health check job
    scheduler.add_job(
        func=scheduled_health_check,
        trigger=IntervalTrigger(seconds=Config.HEALTH_CHECK_INTERVAL),
        id='health_check_job',
        name='Periodic health check',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Scheduler started - health checks every {Config.HEALTH_CHECK_INTERVAL} seconds")


def test_bot_connection():
    """Test the Telegram bot connection on startup"""
    logger.info("Testing Telegram bot connection...")
    result = notifier.test_connection()
    if result:
        logger.info("✅ Telegram bot connection successful")
    else:
        logger.error("❌ Telegram bot connection failed")
        raise Exception("Failed to connect to Telegram bot")


if __name__ == '__main__':
    try:
        # Test bot connection
        test_bot_connection()
        
        # Start scheduler
        start_scheduler()
        
        # Send startup notification
        startup_msg = (
            "🤖 **CI/CD Notification Bot Started**\n\n"
            f"✅ Deployment endpoint: `/notify/deployment`\n"
            f"✅ Custom message endpoint: `/notify/message`\n"
            f"✅ Test endpoint: `/webhook/test`\n"
            f"✅ Health checks: Every {Config.HEALTH_CHECK_INTERVAL}s\n"
            f"✅ Monitoring {len(Config.MONITOR_URLS)} URL(s)"
        )
        notifier.send_message(startup_msg)
        
        # Run Flask app
        logger.info(f"Starting webhook server on {Config.WEBHOOK_HOST}:{Config.WEBHOOK_PORT}")
        app.run(
            host=Config.WEBHOOK_HOST,
            port=Config.WEBHOOK_PORT,
            debug=False
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        scheduler.shutdown()
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
        raise
