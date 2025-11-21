import logging
from datetime import datetime
from typing import Dict, Optional
from config import Config

logger = logging.getLogger(__name__)


class GitLabWebhookHandler:
    """Handler for GitLab webhook events"""
    
    @staticmethod
    def is_monitored_branch(branch: str) -> bool:
        """Check if the branch should be monitored"""
        return branch in Config.MONITORED_BRANCHES
    
    @staticmethod
    def parse_merge_request_event(payload: Dict) -> Optional[Dict]:
        """Parse GitLab merge request webhook payload"""
        try:
            object_attributes = payload.get('object_attributes', {})
            user = payload.get('user', {})
            project = payload.get('project', {})
            
            action = object_attributes.get('action')
            state = object_attributes.get('state')
            
            # We're interested in merge events
            if action != 'merge' and state != 'merged':
                return None
            
            target_branch = object_attributes.get('target_branch')
            
            # Check if we should monitor this branch
            if not GitLabWebhookHandler.is_monitored_branch(target_branch):
                logger.info(f"Ignoring merge to unmonitored branch: {target_branch}")
                return None
            
            return {
                'type': 'merge_request',
                'action': 'merged',
                'title': object_attributes.get('title'),
                'description': object_attributes.get('description'),
                'source_branch': object_attributes.get('source_branch'),
                'target_branch': target_branch,
                'author': user.get('name'),
                'author_username': user.get('username'),
                'merge_commit_sha': object_attributes.get('merge_commit_sha'),
                'url': object_attributes.get('url'),
                'project_name': project.get('name'),
                'project_url': project.get('web_url'),
                'merged_at': object_attributes.get('updated_at'),
                'iid': object_attributes.get('iid')  # Merge request ID
            }
            
        except Exception as e:
            logger.error(f"Error parsing merge request event: {str(e)}")
            return None
    
    @staticmethod
    def parse_push_event(payload: Dict) -> Optional[Dict]:
        """Parse GitLab push webhook payload"""
        try:
            ref = payload.get('ref', '')
            branch = ref.replace('refs/heads/', '')
            
            # Check if we should monitor this branch
            if not GitLabWebhookHandler.is_monitored_branch(branch):
                logger.info(f"Ignoring push to unmonitored branch: {branch}")
                return None
            
            user = payload.get('user_name')
            project = payload.get('project', {})
            commits = payload.get('commits', [])
            
            # Only notify if there are commits (not a branch deletion)
            if payload.get('total_commits_count', 0) == 0:
                return None
            
            return {
                'type': 'push',
                'branch': branch,
                'user': user,
                'user_username': payload.get('user_username'),
                'project_name': project.get('name'),
                'project_url': project.get('web_url'),
                'commit_count': len(commits),
                'commits': commits[:5],  # First 5 commits
                'before': payload.get('before'),
                'after': payload.get('after'),
                'compare_url': f"{project.get('web_url')}/compare/{payload.get('before')}...{payload.get('after')}"
            }
            
        except Exception as e:
            logger.error(f"Error parsing push event: {str(e)}")
            return None
    
    @staticmethod
    def format_merge_notification(event: Dict) -> str:
        """Format merge event as Telegram message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        message = "🔀 **Merge Request Completed**\n"
        message += f"⏰ {timestamp}\n"
        message += f"{'─' * 40}\n\n"
        
        message += f"📋 **{event['title']}**\n"
        message += f"🔗 [MR !{event['iid']}]({event['url']})\n\n"
        
        message += f"📦 Project: **{event['project_name']}**\n"
        message += f"🌿 `{event['source_branch']}` → `{event['target_branch']}`\n"
        message += f"👤 Merged by: {event['author']} (@{event['author_username']})\n"
        
        if event.get('merge_commit_sha'):
            short_sha = event['merge_commit_sha'][:8]
            message += f"📌 Commit: `{short_sha}`\n"
        
        if event.get('description'):
            desc = event['description'][:200]
            if len(event['description']) > 200:
                desc += "..."
            message += f"\n💬 {desc}\n"
        
        # Add environment-specific emoji
        branch = event['target_branch']
        if branch == 'main':
            message += "\n🚀 **Production deployment may be triggered**"
        elif 'prod' in branch.lower():
            message += "\n🔶 **Pre-production deployment may be triggered**"
        elif 'dev' in branch.lower():
            message += "\n🧪 **Development deployment may be triggered**"
        
        return message
    
    @staticmethod
    def format_push_notification(event: Dict) -> str:
        """Format push event as Telegram message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        message = "📤 **Direct Push to Protected Branch**\n"
        message += f"⏰ {timestamp}\n"
        message += f"{'─' * 40}\n\n"
        
        message += f"📦 Project: **{event['project_name']}**\n"
        message += f"🌿 Branch: `{event['branch']}`\n"
        message += f"👤 Pushed by: {event['user']} (@{event['user_username']})\n"
        message += f"📊 Commits: {event['commit_count']}\n\n"
        
        # List commits
        if event.get('commits'):
            message += "**Recent commits:**\n"
            for commit in event['commits']:
                short_sha = commit.get('id', '')[:8]
                commit_msg = commit.get('message', '').split('\n')[0][:60]
                author = commit.get('author', {}).get('name', 'Unknown')
                message += f"• `{short_sha}` {commit_msg} - {author}\n"
        
        if event.get('compare_url'):
            message += f"\n🔗 [View changes]({event['compare_url']})\n"
        
        return message
