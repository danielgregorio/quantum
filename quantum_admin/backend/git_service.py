"""
Git Service for Quantum Admin
Handles Git operations using GitPython
"""
import os
import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import git
    from git import Repo, GitCommandError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    logger.warning("GitPython not installed. Git operations will be unavailable.")


@dataclass
class CommitInfo:
    """Information about a Git commit"""
    sha: str
    short_sha: str
    message: str
    author: str
    author_email: str
    date: datetime
    branch: Optional[str] = None

    def to_dict(self):
        return {
            "sha": self.sha,
            "short_sha": self.short_sha,
            "message": self.message,
            "author": self.author,
            "author_email": self.author_email,
            "date": self.date.isoformat() if self.date else None,
            "branch": self.branch
        }


class GitService:
    """Service for Git operations"""

    def __init__(self, repos_base_path: str = None):
        """
        Initialize Git service

        Args:
            repos_base_path: Base directory for cloned repositories
        """
        if not GIT_AVAILABLE:
            raise RuntimeError("GitPython is not installed. Run: pip install gitpython")

        self.repos_base_path = repos_base_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "repos"
        )
        os.makedirs(self.repos_base_path, exist_ok=True)

    def get_repo_path(self, project_name: str) -> str:
        """Get the local path for a project repository"""
        return os.path.join(self.repos_base_path, project_name)

    def clone_repo(self, repo_url: str, project_name: str, branch: str = "main") -> bool:
        """
        Clone a repository

        Args:
            repo_url: Git repository URL (HTTPS or SSH)
            project_name: Name to use for local directory
            branch: Branch to checkout after clone

        Returns:
            True if successful
        """
        dest_path = self.get_repo_path(project_name)

        # If repo already exists, just pull
        if os.path.exists(dest_path):
            logger.info(f"Repository already exists at {dest_path}, pulling latest")
            return self.pull_latest(project_name, branch) is not None

        try:
            logger.info(f"Cloning {repo_url} to {dest_path}")
            Repo.clone_from(repo_url, dest_path, branch=branch)
            logger.info(f"Successfully cloned repository")
            return True
        except GitCommandError as e:
            logger.error(f"Failed to clone repository: {e}")
            return False

    def pull_latest(self, project_name: str, branch: str = None) -> Optional[str]:
        """
        Pull latest changes from remote

        Args:
            project_name: Project name (directory name)
            branch: Branch to pull (optional, uses current if not specified)

        Returns:
            New commit SHA if successful, None if failed
        """
        repo_path = self.get_repo_path(project_name)

        if not os.path.exists(repo_path):
            logger.error(f"Repository not found: {repo_path}")
            return None

        try:
            repo = Repo(repo_path)

            # Checkout branch if specified
            if branch and repo.active_branch.name != branch:
                self.checkout_branch(project_name, branch)

            # Fetch and pull
            origin = repo.remotes.origin
            origin.fetch()
            origin.pull()

            commit_sha = repo.head.commit.hexsha
            logger.info(f"Pulled latest: {commit_sha[:7]}")
            return commit_sha

        except GitCommandError as e:
            logger.error(f"Failed to pull: {e}")
            return None

    def checkout_branch(self, project_name: str, branch: str) -> bool:
        """
        Checkout a specific branch

        Args:
            project_name: Project name
            branch: Branch name to checkout

        Returns:
            True if successful
        """
        repo_path = self.get_repo_path(project_name)

        try:
            repo = Repo(repo_path)

            # Check if branch exists locally
            if branch in repo.heads:
                repo.heads[branch].checkout()
            else:
                # Try to checkout from remote
                origin = repo.remotes.origin
                origin.fetch()
                repo.create_head(branch, origin.refs[branch]).checkout()

            logger.info(f"Checked out branch: {branch}")
            return True

        except GitCommandError as e:
            logger.error(f"Failed to checkout branch {branch}: {e}")
            return False

    def checkout_commit(self, project_name: str, commit_sha: str) -> bool:
        """
        Checkout a specific commit (for rollback)

        Args:
            project_name: Project name
            commit_sha: Full or short commit SHA

        Returns:
            True if successful
        """
        repo_path = self.get_repo_path(project_name)

        try:
            repo = Repo(repo_path)
            repo.git.checkout(commit_sha)
            logger.info(f"Checked out commit: {commit_sha[:7]}")
            return True

        except GitCommandError as e:
            logger.error(f"Failed to checkout commit {commit_sha}: {e}")
            return False

    def get_commit_info(self, project_name: str, commit_sha: str = "HEAD") -> Optional[CommitInfo]:
        """
        Get information about a specific commit

        Args:
            project_name: Project name
            commit_sha: Commit SHA or "HEAD"

        Returns:
            CommitInfo object or None
        """
        repo_path = self.get_repo_path(project_name)

        try:
            repo = Repo(repo_path)
            commit = repo.commit(commit_sha)

            # Get current branch name
            try:
                branch = repo.active_branch.name
            except TypeError:
                branch = None  # Detached HEAD

            return CommitInfo(
                sha=commit.hexsha,
                short_sha=commit.hexsha[:7],
                message=commit.message.strip(),
                author=commit.author.name,
                author_email=commit.author.email,
                date=datetime.fromtimestamp(commit.committed_date),
                branch=branch
            )

        except Exception as e:
            logger.error(f"Failed to get commit info: {e}")
            return None

    def get_recent_commits(self, project_name: str, branch: str = None, limit: int = 20) -> List[CommitInfo]:
        """
        Get recent commits

        Args:
            project_name: Project name
            branch: Branch to get commits from (optional)
            limit: Maximum number of commits to return

        Returns:
            List of CommitInfo objects
        """
        repo_path = self.get_repo_path(project_name)
        commits = []

        try:
            repo = Repo(repo_path)

            # Determine which ref to use
            if branch:
                ref = branch
            else:
                ref = repo.head.commit

            for commit in repo.iter_commits(ref, max_count=limit):
                commits.append(CommitInfo(
                    sha=commit.hexsha,
                    short_sha=commit.hexsha[:7],
                    message=commit.message.strip(),
                    author=commit.author.name,
                    author_email=commit.author.email,
                    date=datetime.fromtimestamp(commit.committed_date),
                    branch=branch
                ))

        except Exception as e:
            logger.error(f"Failed to get recent commits: {e}")

        return commits

    def get_branches(self, project_name: str) -> List[str]:
        """
        Get list of branches

        Args:
            project_name: Project name

        Returns:
            List of branch names
        """
        repo_path = self.get_repo_path(project_name)

        try:
            repo = Repo(repo_path)
            return [head.name for head in repo.heads]
        except Exception as e:
            logger.error(f"Failed to get branches: {e}")
            return []

    def get_remote_url(self, project_name: str) -> Optional[str]:
        """
        Get the remote origin URL

        Args:
            project_name: Project name

        Returns:
            Remote URL or None
        """
        repo_path = self.get_repo_path(project_name)

        try:
            repo = Repo(repo_path)
            return repo.remotes.origin.url
        except Exception as e:
            logger.error(f"Failed to get remote URL: {e}")
            return None

    def is_repo(self, project_name: str) -> bool:
        """
        Check if a directory is a Git repository

        Args:
            project_name: Project name

        Returns:
            True if it's a valid Git repository
        """
        repo_path = self.get_repo_path(project_name)

        try:
            Repo(repo_path)
            return True
        except Exception:
            return False

    def get_current_branch(self, project_name: str) -> Optional[str]:
        """
        Get current branch name

        Args:
            project_name: Project name

        Returns:
            Branch name or None
        """
        repo_path = self.get_repo_path(project_name)

        try:
            repo = Repo(repo_path)
            return repo.active_branch.name
        except Exception:
            return None

    def has_uncommitted_changes(self, project_name: str) -> bool:
        """
        Check if repository has uncommitted changes

        Args:
            project_name: Project name

        Returns:
            True if there are uncommitted changes
        """
        repo_path = self.get_repo_path(project_name)

        try:
            repo = Repo(repo_path)
            return repo.is_dirty()
        except Exception:
            return False


# Singleton instance
_git_service = None


def get_git_service() -> GitService:
    """Get singleton instance of GitService"""
    global _git_service
    if _git_service is None:
        try:
            _git_service = GitService()
        except RuntimeError:
            return None
    return _git_service
