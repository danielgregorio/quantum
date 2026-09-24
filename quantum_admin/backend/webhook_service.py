"""
Webhook Service for Quantum Admin
Handles GitHub/GitLab webhook events for CI/CD
"""
import hmac
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

try:
    from .models import WebhookEvent, Project
    from .database import SessionLocal
except ImportError:
    from models import WebhookEvent, Project
    from database import SessionLocal


class WebhookService:
    """Service for processing CI/CD webhooks"""

    def __init__(self, db: Session = None):
        """
        Initialize webhook service

        Args:
            db: SQLAlchemy session (optional)
        """
        self._db = db
        self._own_session = db is None

        # Secrets from environment
        self.github_secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
        self.gitlab_token = os.environ.get("GITLAB_WEBHOOK_TOKEN", "")

    @property
    def db(self) -> Session:
        """Get database session"""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def close(self):
        """Close database session if we own it"""
        if self._own_session and self._db:
            self._db.close()
            self._db = None

    # =========================================================================
    # Signature Verification
    # =========================================================================

    def verify_github_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify GitHub webhook HMAC-SHA256 signature

        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not self.github_secret:
            # This returned True: with no secret configured — the state of
            # every default install — an unsigned POST to /webhooks/github
            # was accepted (a push event then started a deployment, when the
            # admin still deployed). Anyone who could reach the port could
            # write events.
            #
            # Refusing is the only safe answer. An unconfigured webhook that
            # does nothing is a missing feature; one that trusts everybody is
            # a way in.
            logger.error(
                "GITHUB_WEBHOOK_SECRET is not set — refusing the webhook. "
                "Set it to the secret configured in GitHub."
            )
            return False

        if not signature or not signature.startswith("sha256="):
            return False

        expected_signature = signature[7:]  # Remove 'sha256=' prefix

        computed = hmac.new(
            self.github_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed, expected_signature)

    def verify_gitlab_token(self, token: str) -> bool:
        """
        Verify GitLab webhook token

        Args:
            token: X-Gitlab-Token header value

        Returns:
            True if token matches
        """
        if not self.gitlab_token:
            # Same fail-open as the GitHub path, same answer: refuse.
            logger.error(
                "GITLAB_WEBHOOK_TOKEN is not set — refusing the webhook. "
                "Set it to the token configured in GitLab."
            )
            return False

        return hmac.compare_digest(token, self.gitlab_token)

    # =========================================================================
    # Payload Parsing
    # =========================================================================

    def parse_github_push(self, payload: Dict) -> Dict[str, Any]:
        """
        Parse GitHub push event payload

        Args:
            payload: Decoded JSON payload

        Returns:
            Normalized event data
        """
        ref = payload.get("ref", "")
        branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

        head_commit = payload.get("head_commit", {})
        repo = payload.get("repository", {})

        return {
            "provider": "github",
            "event_type": "push",
            "branch": branch,
            "commit": head_commit.get("id"),
            "author": head_commit.get("author", {}).get("username") or head_commit.get("author", {}).get("name"),
            "message": head_commit.get("message"),
            "repo_url": repo.get("clone_url") or repo.get("ssh_url"),
            "repo_name": repo.get("full_name"),
            "commits_count": len(payload.get("commits", [])),
            "pusher": payload.get("pusher", {}).get("name"),
            "before": payload.get("before"),
            "after": payload.get("after")
        }

    def parse_gitlab_push(self, payload: Dict) -> Dict[str, Any]:
        """
        Parse GitLab push event payload

        Args:
            payload: Decoded JSON payload

        Returns:
            Normalized event data
        """
        ref = payload.get("ref", "")
        branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

        commits = payload.get("commits", [])
        last_commit = commits[-1] if commits else {}
        project = payload.get("project", {})

        return {
            "provider": "gitlab",
            "event_type": "push",
            "branch": branch,
            "commit": payload.get("after") or payload.get("checkout_sha"),
            "author": last_commit.get("author", {}).get("name"),
            "message": last_commit.get("message"),
            "repo_url": project.get("git_http_url") or project.get("git_ssh_url"),
            "repo_name": project.get("path_with_namespace"),
            "commits_count": payload.get("total_commits_count", len(commits)),
            "pusher": payload.get("user_username") or payload.get("user_name"),
            "before": payload.get("before"),
            "after": payload.get("after")
        }

    # =========================================================================
    # Project Matching
    # =========================================================================

    def find_project_by_repo(self, repo_url: str) -> Optional[Project]:
        """
        Find a project by its repository URL

        Args:
            repo_url: Git repository URL

        Returns:
            Project or None
        """
        # Normalize URL for comparison
        normalized = self._normalize_repo_url(repo_url)

        # Check projects with git_repo field (if exists)
        # For now, we'll use a simple name match
        # In production, you'd store repo_url in the Project model

        projects = self.db.query(Project).filter(Project.status == 'active').all()

        for project in projects:
            # Try to match by project name in repo URL
            if project.name.lower() in normalized.lower():
                return project

        return None

    def _normalize_repo_url(self, url: str) -> str:
        """Normalize a git URL for comparison"""
        # Remove .git suffix
        if url.endswith(".git"):
            url = url[:-4]

        # Convert SSH to HTTPS format for comparison
        if url.startswith("git@"):
            # git@github.com:user/repo -> github.com/user/repo
            url = url.replace(":", "/").replace("git@", "")

        # Remove protocol
        for prefix in ["https://", "http://", "ssh://"]:
            if url.startswith(prefix):
                url = url[len(prefix):]

        return url.lower()

    # =========================================================================
    # Event Processing
    # =========================================================================

    def create_webhook_event(self, data: Dict[str, Any]) -> WebhookEvent:
        """
        Create a webhook event record

        Args:
            data: Normalized event data

        Returns:
            Created WebhookEvent
        """
        # Find matching project
        project = None
        if data.get("repo_url"):
            project = self.find_project_by_repo(data["repo_url"])

        event = WebhookEvent(
            project_id=project.id if project else None,
            provider=data.get("provider"),
            event_type=data.get("event_type"),
            branch=data.get("branch"),
            commit=data.get("commit"),
            author=data.get("author") or data.get("pusher"),
            message=data.get("message"),
            payload_json=json.dumps(data),
            processed=False,
            received_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        logger.info(f"Created webhook event: {event.id} ({event.provider}/{event.event_type})")
        return event

    async def process_github_push(self, payload: Dict) -> Tuple[WebhookEvent, Optional[int]]:
        """
        Process a GitHub push event

        Args:
            payload: GitHub webhook payload

        Returns:
            Tuple of (WebhookEvent, None)
        """
        data = self.parse_github_push(payload)
        event = self.create_webhook_event(data)

        # The event is recorded; nothing is deployed (the admin's deploy feature
        # was removed). The second value stays for callers: always None.
        return event, None

    async def process_gitlab_push(self, payload: Dict) -> Tuple[WebhookEvent, Optional[int]]:
        """
        Process a GitLab push event

        Args:
            payload: GitLab webhook payload

        Returns:
            Tuple of (WebhookEvent, None)
        """
        data = self.parse_gitlab_push(payload)
        event = self.create_webhook_event(data)

        # The event is recorded; nothing is deployed (the admin's deploy feature
        # was removed). The second value stays for callers: always None.
        return event, None

    # =========================================================================
    # Event Queries
    # =========================================================================

    def list_events(
        self,
        project_id: Optional[int] = None,
        limit: int = 50,
        processed_only: bool = False
    ) -> list:
        """
        List webhook events

        Args:
            project_id: Filter by project (optional)
            limit: Maximum events to return
            processed_only: Only return processed events

        Returns:
            List of WebhookEvent objects
        """
        query = self.db.query(WebhookEvent)

        if project_id:
            query = query.filter(WebhookEvent.project_id == project_id)

        if processed_only:
            query = query.filter(WebhookEvent.processed == True)

        return query.order_by(WebhookEvent.received_at.desc()).limit(limit).all()

    def get_event(self, event_id: int) -> Optional[WebhookEvent]:
        """Get a specific webhook event"""
        return self.db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()


# Singleton instance
_webhook_service = None


def get_webhook_service(db: Session = None) -> WebhookService:
    """Get webhook service instance"""
    if db:
        return WebhookService(db)

    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service
