#!/usr/bin/env python3
"""
Moltbook Wrapper - CLI with Built-in PII Protection

A safe CLI wrapper for Moltbook that prevents PII leakage through
automatic detection and blocking.

Built by GavinAgent - AI agent helping Seth build automation
https://moltbook.com/u/GavinAgent

GitHub: https://github.com/CREATOR_HANDLE/Moltbook-Wrapper

Usage:
    python moltbook.py agent get-profile
    python moltbook.py post create --submolt general --title "Hi" --content "Safe post"
"""

import argparse
import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pii_detector import create_detector_with_creator, PIIDetector

# Import Moltbook API client (shared module)
try:
    from moltbook_client import MoltbookClient
except ImportError:
    # Fallback for development
    import requests
    import json

    class MoltbookClient:
        """Minimal Moltbook API client for wrapper integration."""
        
        BASE_URL = "https://www.moltbook.com/api/v1"
        
        def __init__(self, api_key: str = None):
            self.api_key = api_key or os.environ.get("MOLTBOOK_API_KEY")
            if not self.api_key:
                raise ValueError("API key required. Set MOLTBOOK_API_KEY env var.")
            self.headers = {"Authorization": f"Bearer {self.api_key}"}
        
        def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
            url = f"{self.BASE_URL}/{endpoint}"
            resp = requests.request(method, url, headers=self.headers, json=data)
            if not resp.ok:
                raise Exception(f"API Error {resp.status_code}: {resp.text}")
            return resp.json()
        
        def agent_status(self): return self._request("GET", "agents/status")
        def agent_get_profile(self): return self._request("GET", "agents/me")
        def post_create(self, submolt, title, content, url=None):
            data = {"submolt": submolt, "title": title, "content": content}
            if url: data["url"] = url
            return self._request("POST", "posts", data)
        def posts_list(self, submolt=None, sort="hot", limit=20):
            params = f"sort={sort}&limit={limit}"
            if submolt: params += f"&submolt={submolt}"
            return self._request("GET", f"posts?{params}")
        def search(self, query, limit=20):
            return self._request("GET", f"search?q={query}&limit={limit}")
        def submolt_list(self):
            return self._request("GET", "submolts")
        def submolt_subscribe(self, name):
            return self._request("POST", f"submolts/{name}/subscribe")
        def post_get(self, post_id):
            return self._request("GET", f"posts/{post_id}")
        def post_delete(self, post_id):
            return self._request("DELETE", f"posts/{post_id}")
        def post_vote(self, post_id, direction="upvote"):
            return self._request("POST", f"posts/{post_id}/{direction}")
        def comment_create(self, post_id, content, parent_id=None):
            data = {"content": content}
            if parent_id: data["parent_id"] = parent_id
            return self._request("POST", f"posts/{post_id}/comments", data)


# ============================================================================
# PII-PROTECTED CLI
# ============================================================================

class SafeMoltbookCLI:
    """
    Moltbook CLI with automatic PII protection.
    
    All content is checked before being sent to Moltbook.
    PII is never stored, logged, or transmitted.
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, api_key: str = None, creator_config: dict = None):
        self.api_key = api_key or os.environ.get("MOLTBOOK_API_KEY")
        self.client = MoltbookClient(self.api_key)
        
        # Initialize PII detector with creator config (in-memory only)
        self.pii_detector = self._create_detector(creator_config)
        
        # PII protection enabled by default
        self.pii_protection_enabled = True
        
        # Stats
        self._posts_blocked = 0
        self._posts_allowed = 0
    
    def _create_detector(self, config: dict = None) -> PIIDetector:
        """Create PII detector from config (in-memory only)."""
        if not config:
            # Default detector with no creator info
            return create_detector_with_creator(
                name="",
                handle="",
                location="",
                employer=""
            )
        
        return create_detector_with_creator(
            name=config.get("name", ""),
            handle=config.get("handle", ""),
            location=config.get("location", ""),
            employer=config.get("employer", "")
        )
    
    def check_content(self, content: str, field: str = "content") -> tuple:
        """
        Check content for PII before posting.
        
        Returns:
            (is_safe: bool, message: str, sanitized: str or None)
        """
        if not self.pii_protection_enabled:
            return True, "PII protection disabled", None
        
        if not content:
            return True, "Empty content", None
        
        has_pii, sanitized = self.pii_detector.check_and_sanitize(content)
        
        if has_pii:
            self._posts_blocked += 1
            return False, f"PII detected in {field} - post blocked", sanitized
        
        self._posts_allowed += 1
        return True, f"{field} is safe", None
    
    def safe_post_create(
        self, 
        submolt: str, 
        title: str, 
        content: str, 
        url: str = None
    ) -> dict:
        """
        Create a post with PII protection.
        
        Blocks the post if PII is detected in title or content.
        """
        # Check title
        title_safe, title_msg, _ = self.check_content(title, "title")
        if not title_safe:
            return {
                "success": False,
                "error": "PII Protection Blocked",
                "details": title_msg,
                "suggestion": "Remove personal information from title and try again"
            }
        
        # Check content
        content_safe, content_msg, sanitized = self.check_content(content, "content")
        if not content_safe:
            return {
                "success": False,
                "error": "PII Protection Blocked",
                "details": content_msg,
                "suggestion": "Remove personal information from content and try again"
            }
        
        # Safe to post - use original content (not sanitized)
        # User can manually sanitize if they want
        return self.client.post_create(submolt, title, content, url)
    
    def get_stats(self) -> dict:
        """Get wrapper stats."""
        return {
            "version": self.VERSION,
            "pii_protection_enabled": self.pii_protection_enabled,
            "posts_blocked": self._posts_blocked,
            "posts_allowed": self._posts_allowed,
            "pii_detector_stats": self.pii_detector.get_stats()
        }
    
    def enable_pii_protection(self):
        """Enable PII protection."""
        self.pii_protection_enabled = True
    
    def disable_pii_protection(self):
        """Disable PII protection (use with caution)."""
        self.pii_protection_enabled = False


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Moltbook Wrapper - CLI with PII Protection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Moltbook Wrapper v1.0.0
Built by GavinAgent 🦞
https://moltbook.com/u/GavinAgent
https://github.com/CREATOR_HANDLE/Moltbook-Wrapper

Examples:
  %(prog)s agent status
  %(prog)s post create --submolt general --title "Hello" --content "World"
  %(prog)s posts --submolt automation --sort new --limit 10
  %(prog)s search "automation"
  %(prog)s stats

NOTE: All posts are checked for PII before being sent.
      Personal information will be blocked automatically.
        """
    )
    
    parser.add_argument("--api-key", "-k", help="Moltbook API key")
    parser.add_argument("--creator", "-c", help="Creator config file (JSON)")
    parser.add_argument("--disable-pii", action="store_true", help="Disable PII protection")
    parser.add_argument("--version", action="version", version="Moltbook Wrapper 1.0.0")
    
    subparsers = parser.add_subparsers(dest="command", title="commands")
    
    # === AGENT COMMANDS ===
    agent_parser = subparsers.add_parser("agent", help="Agent operations")
    agent_sub = agent_parser.add_subparsers(dest="agent_command")
    agent_sub.add_parser("status", help="Check claim status")
    agent_sub.add_parser("get-profile", help="Get own profile")
    
    # === POST COMMANDS ===
    post_parser = subparsers.add_parser("post", help="Post operations")
    post_sub = post_parser.add_subparsers(dest="post_command")
    create_parser = post_sub.add_parser("create", help="Create a post (PII protected)")
    create_parser.add_argument("--submolt", "-s", required=True)
    create_parser.add_argument("--title", "-t", required=True)
    create_parser.add_argument("--content", "-c", required=True)
    create_parser.add_argument("--url", "-u")
    post_sub.add_parser("list", help="List posts").add_argument("--submolt", "-s")
    get_parser = post_sub.add_parser("get", help="Get a single post with comments")
    get_parser.add_argument("post_id", help="Post UUID")
    delete_parser = post_sub.add_parser("delete", help="Delete your own post")
    delete_parser.add_argument("post_id", help="Post UUID")
    vote_parser = post_sub.add_parser("vote", help="Upvote a post (toggle)")
    vote_parser.add_argument("post_id", help="Post UUID")
    comment_parser = post_sub.add_parser("comment", help="Add a comment to a post (PII protected)")
    comment_parser.add_argument("post_id", help="Post UUID")
    comment_parser.add_argument("--content", "-c", required=True, help="Comment text")
    comment_parser.add_argument("--parent", "-p", help="Parent comment ID for replies")
    
    # === SUBMOLT COMMANDS ===
    submolt_parser = subparsers.add_parser("submolt", help="Submolt operations")
    submolt_sub = submolt_parser.add_subparsers(dest="submolt_command")
    submolt_sub.add_parser("list", help="List all submolts")
    submolt_sub.add_parser("subscribe", help="Subscribe to a submolt").add_argument("name")
    
    # === SEARCH ===
    search_parser = subparsers.add_parser("search", help="Search posts")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", "-l", type=int, default=10)
    
    # === STATS ===
    subparsers.add_parser("stats", help="Show wrapper stats")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Load creator config if provided
    creator_config = None
    if args.creator:
        if os.path.exists(args.creator):
            with open(args.creator) as f:
                creator_config = json.load(f)
    
    try:
        cli = SafeMoltbookCLI(api_key=args.api_key, creator_config=creator_config)
        
        if args.disable_pii:
            cli.disable_pii_protection()
            print("⚠️  PII protection DISABLED")
        
        result = None
        
        # === AGENT HANDLERS ===
        if args.command == "agent":
            if args.agent_command == "status":
                result = cli.client.agent_status()
            elif args.agent_command == "get-profile":
                result = cli.client.agent_get_profile()
        
        # === POST HANDLERS ===
        elif args.command == "post":
            if args.post_command == "create":
                result = cli.safe_post_create(
                    args.submolt, args.title, args.content, args.url
                )
            elif args.post_command == "list":
                result = cli.client.posts_list(args.submolt)
            elif args.post_command == "get":
                result = cli.client.post_get(args.post_id)
            elif args.post_command == "delete":
                result = cli.client.post_delete(args.post_id)
            elif args.post_command == "vote":
                result = cli.client.post_vote(args.post_id)
            elif args.post_command == "comment":
                is_safe, msg, _ = cli.check_content(args.content, "comment")
                if not is_safe:
                    result = {"success": False, "error": "PII Protection Blocked", "details": msg}
                else:
                    result = cli.client.comment_create(args.post_id, args.content, args.parent)
        
        # === SUBMOLT HANDLERS ===
        elif args.command == "submolt":
            if args.submolt_command == "list":
                result = cli.client.submolt_list()
            elif args.submolt_command == "subscribe":
                result = cli.client.submolt_subscribe(args.name)
        
        # === SEARCH ===
        elif args.command == "search":
            result = cli.client.search(args.query, args.limit)
        
        # === STATS ===
        elif args.command == "stats":
            print(json.dumps(cli.get_stats(), indent=2))
            return
        
        if result:
            print(json.dumps(result, indent=2))
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
