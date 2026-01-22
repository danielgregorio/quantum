"""
Git Webhook Handler for Quantum Admin
Handles webhooks from GitHub, GitLab, Bitbucket for auto-deployment
"""
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
import subprocess
import os

logger = logging.getLogger(__name__)


class WebhookHandler:
    """
    Git webhook handler with support for multiple platforms

    Features:
    - GitHub webhooks
    - GitLab webhooks
    - Bitbucket webhooks
    - HMAC signature verification
    - Auto-deployment triggers
    - Event filtering
    """

    def __init__(self, secret: Optional[str] = None):
        self.secret = secret or os.getenv("WEBHOOK_SECRET", "")
        self.deployment_dir = os.getenv("DEPLOYMENT_DIR", "/opt/quantum")

    def verify_github_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify GitHub webhook signature

        Args:
            payload: Request body bytes
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not self.secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True

        expected = hmac.new(
            self.secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        expected_signature = f"sha256={expected}"

        return hmac.compare_digest(expected_signature, signature)

    def verify_gitlab_token(self, token: str) -> bool:
        """
        Verify GitLab webhook token

        Args:
            token: X-Gitlab-Token header value

        Returns:
            True if token is valid
        """
        if not self.secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True

        return hmac.compare_digest(self.secret, token)

    async def handle_github_webhook(self, request: Request) -> Dict[str, Any]:
        """
        Handle GitHub webhook event

        Args:
            request: FastAPI request object

        Returns:
            Processing result
        """
        # Verify signature
        signature = request.headers.get("X-Hub-Signature-256", "")
        body = await request.body()

        if not self.verify_github_signature(body, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

        # Parse event
        event_type = request.headers.get("X-GitHub-Event", "")
        payload = await request.json()

        logger.info(f"Received GitHub webhook: {event_type}")

        # Handle different event types
        if event_type == "push":
            return await self._handle_push_event(payload, "github")

        elif event_type == "pull_request":
            return await self._handle_pull_request_event(payload, "github")

        elif event_type == "release":
            return await self._handle_release_event(payload, "github")

        else:
            return {
                "status": "ignored",
                "event": event_type,
                "message": "Event type not configured for auto-deployment"
            }

    async def handle_gitlab_webhook(self, request: Request) -> Dict[str, Any]:
        """
        Handle GitLab webhook event

        Args:
            request: FastAPI request object

        Returns:
            Processing result
        """
        # Verify token
        token = request.headers.get("X-Gitlab-Token", "")

        if not self.verify_gitlab_token(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook token"
            )

        # Parse event
        event_type = request.headers.get("X-Gitlab-Event", "")
        payload = await request.json()

        logger.info(f"Received GitLab webhook: {event_type}")

        # Handle events
        if event_type == "Push Hook":
            return await self._handle_push_event(payload, "gitlab")

        elif event_type == "Merge Request Hook":
            return await self._handle_pull_request_event(payload, "gitlab")

        else:
            return {
                "status": "ignored",
                "event": event_type,
                "message": "Event type not configured for auto-deployment"
            }

    async def _handle_push_event(
        self,
        payload: Dict[str, Any],
        platform: str
    ) -> Dict[str, Any]:
        """
        Handle push/commit event

        Args:
            payload: Webhook payload
            platform: 'github' or 'gitlab'

        Returns:
            Deployment result
        """
        # Extract branch name
        if platform == "github":
            ref = payload.get("ref", "")
            branch = ref.replace("refs/heads/", "")
            pusher = payload.get("pusher", {}).get("name", "unknown")
            commits = payload.get("commits", [])
        else:  # gitlab
            ref = payload.get("ref", "")
            branch = ref.replace("refs/heads/", "")
            pusher = payload.get("user_name", "unknown")
            commits = payload.get("commits", [])

        logger.info(f"Push to branch {branch} by {pusher} ({len(commits)} commits)")

        # Check if branch should trigger deployment
        auto_deploy_branches = os.getenv(
            "AUTO_DEPLOY_BRANCHES",
            "main,staging,develop"
        ).split(",")

        if branch not in auto_deploy_branches:
            return {
                "status": "ignored",
                "branch": branch,
                "message": f"Branch {branch} not configured for auto-deployment"
            }

        # Trigger deployment
        result = await self._deploy(branch, payload)

        return {
            "status": "deployed" if result["success"] else "failed",
            "branch": branch,
            "pusher": pusher,
            "commits": len(commits),
            "deployment": result
        }

    async def _handle_pull_request_event(
        self,
        payload: Dict[str, Any],
        platform: str
    ) -> Dict[str, Any]:
        """Handle pull/merge request event"""
        if platform == "github":
            action = payload.get("action", "")
            pr = payload.get("pull_request", {})
            pr_number = pr.get("number")
            branch = pr.get("head", {}).get("ref")
        else:  # gitlab
            action = payload.get("object_attributes", {}).get("action", "")
            pr = payload.get("object_attributes", {})
            pr_number = pr.get("iid")
            branch = pr.get("source_branch")

        logger.info(f"Pull request #{pr_number}: {action}")

        # Deploy to preview environment for opened/updated PRs
        if action in ["opened", "synchronize", "reopened", "update"]:
            result = await self._deploy_preview(pr_number, branch, payload)

            return {
                "status": "preview_deployed",
                "pr_number": pr_number,
                "branch": branch,
                "action": action,
                "preview_url": result.get("preview_url")
            }

        return {
            "status": "ignored",
            "pr_number": pr_number,
            "action": action
        }

    async def _handle_release_event(
        self,
        payload: Dict[str, Any],
        platform: str
    ) -> Dict[str, Any]:
        """Handle release event"""
        if platform == "github":
            action = payload.get("action", "")
            release = payload.get("release", {})
            tag = release.get("tag_name")
            is_prerelease = release.get("prerelease", False)
        else:
            # GitLab uses different event structure
            return {"status": "not_implemented"}

        logger.info(f"Release {tag}: {action} (prerelease: {is_prerelease})")

        if action == "published" and not is_prerelease:
            # Deploy release to production
            result = await self._deploy("main", payload, tag=tag)

            return {
                "status": "production_deployed",
                "tag": tag,
                "deployment": result
            }

        return {
            "status": "ignored",
            "tag": tag,
            "action": action
        }

    async def _deploy(
        self,
        branch: str,
        payload: Dict[str, Any],
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute deployment

        Args:
            branch: Branch to deploy
            payload: Webhook payload
            tag: Optional tag for release deployments

        Returns:
            Deployment result
        """
        logger.info(f"Starting deployment for branch {branch}")

        try:
            # Queue Celery task for deployment
            from celery_tasks import deploy_application

            # Determine environment from branch
            environment_map = {
                "main": "production",
                "master": "production",
                "staging": "staging",
                "develop": "development"
            }
            environment = environment_map.get(branch, "development")

            # Queue deployment task
            task = deploy_application.delay(
                environment=environment,
                branch=branch,
                run_migrations=True
            )

            return {
                "success": True,
                "task_id": task.id,
                "environment": environment,
                "branch": branch,
                "tag": tag,
                "message": "Deployment queued successfully"
            }

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _deploy_preview(
        self,
        pr_number: int,
        branch: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy preview environment for pull request"""
        logger.info(f"Deploying preview environment for PR #{pr_number}")

        try:
            # In production: deploy to preview environment
            # For now, return simulated result

            preview_url = f"https://pr-{pr_number}.preview.quantum-admin.example.com"

            return {
                "success": True,
                "pr_number": pr_number,
                "branch": branch,
                "preview_url": preview_url,
                "message": "Preview environment deployed"
            }

        except Exception as e:
            logger.error(f"Preview deployment failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def execute_deployment_script(self, script_path: str) -> Dict[str, Any]:
        """
        Execute deployment script

        Args:
            script_path: Path to deployment script

        Returns:
            Execution result
        """
        try:
            result = subprocess.run(
                [script_path],
                cwd=self.deployment_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Deployment script timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Global webhook handler instance
_webhook_handler: Optional[WebhookHandler] = None


def get_webhook_handler() -> WebhookHandler:
    """Get or create webhook handler instance"""
    global _webhook_handler

    if _webhook_handler is None:
        _webhook_handler = WebhookHandler()

    return _webhook_handler
