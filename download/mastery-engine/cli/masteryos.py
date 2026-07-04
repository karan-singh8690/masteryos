#!/usr/bin/env python3
"""MasteryOS CLI — command-line tool for managing MasteryOS.

Usage:
    masteryos login          — Authenticate with your API key
    masteryos deploy         — Deploy content changes
    masteryos users          — List/manage users
    masteryos content        — Manage content packs
    masteryos analytics      — View analytics
    masteryos workers        — Check worker status
    masteryos backups        — Manage backups
    masteryos health         — Check platform health
    masteryos version        — Show CLI + API version
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

__version__ = "1.0.0"

CONFIG_DIR = Path.home() / ".masteryos"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict[str, str]:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config: dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    CONFIG_FILE.chmod(0o600)


def get_client():
    config = load_config()
    api_key = config.get("api_key") or os.environ.get("MASTERYOS_API_KEY")
    if not api_key:
        print("Error: Not authenticated. Run 'masteryos login' first.")
        sys.exit(1)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sdks" / "python"))
    from masteryos import MasteryOS
    return MasteryOS(api_key=api_key, base_url=config.get("base_url", "https://api.masteryos.com"))


def cmd_login(args):
    print("MasteryOS CLI — Login")
    print("=====================")
    api_key = input("Enter your API key: ").strip()
    if not api_key:
        print("Error: API key is required.")
        sys.exit(1)
    base_url = input("API base URL [https://api.masteryos.com]: ").strip() or "https://api.masteryos.com"
    save_config({"api_key": api_key, "base_url": base_url})
    print(f"\n✓ Saved credentials to {CONFIG_FILE}")
    print(f"  API key: {api_key[:8]}...{api_key[-4:]}")
    print(f"  Base URL: {base_url}")


def cmd_health(args):
    client = get_client()
    try:
        result = client.beta_ops.get_operations()
        platform = result.get("platform_health", {})
        status = platform.get("status", "unknown")
        print("✅ All systems operational" if status == "healthy" else f"⚠️  Platform status: {status}")
        print(f"  Outbox pending: {platform.get('outbox_pending', 'N/A')}")
        print(f"  Active workers: {platform.get('active_workers', 'N/A')}")
        print(f"  Dead letters:   {platform.get('dead_letters_unresolved', 'N/A')}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        sys.exit(1)


def cmd_version(args):
    print(f"MasteryOS CLI v{__version__}")


def cmd_analytics(args):
    client = get_client()
    try:
        d = client.beta_ops.get_dashboard()
        print("=== Beta Operations Dashboard ===")
        for k in ["total_invited", "active_beta_users", "daily_active_users", "weekly_active_users",
                     "invite_conversion_rate", "study_sessions_completed", "feedback_received",
                     "bugs_reported", "nps_score", "user_satisfaction", "learning_progress_avg"]:
            print(f"  {k}: {d.get(k, 'N/A')}")
    except Exception as e:
        print(f"❌ Failed to fetch analytics: {e}")
        sys.exit(1)


def cmd_workers(args):
    client = get_client()
    try:
        ops = client.beta_ops.get_operations()
        workers = ops.get("worker_health", {})
        print("=== Worker Status ===")
        print(f"  Total: {workers.get('total_workers', 0)}  Running: {workers.get('running', 0)}  Stale: {workers.get('stale', 0)}")
        for w in workers.get("workers", []):
            print(f"  {'✅' if w.get('status') == 'running' else '⚠️'} {w.get('worker_id', '?')} — {w.get('status', '?')} (processed: {w.get('jobs_processed', 0)})")
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)


def cmd_users(args): print("User management — use /admin/users portal.")
def cmd_content(args): print("Content management — use /content/dashboard portal.")
def cmd_backups(args): print("Backup management — run ./scripts/backup.sh on the server.")
def cmd_deploy(args): print("Deployment — use 'make prod-build && make prod-up' on the server.")


def main():
    parser = argparse.ArgumentParser(prog="masteryos", description="MasteryOS CLI")
    parser.add_argument("--version", action="version", version=f"masteryos {__version__}")
    sub = parser.add_subparsers(dest="command")
    for cmd in ["login", "health", "version", "users", "content", "analytics", "workers", "backups", "deploy"]:
        sub.add_parser(cmd, help=f"{cmd} command")
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    {"login": cmd_login, "health": cmd_health, "version": cmd_version, "users": cmd_users,
     "content": cmd_content, "analytics": cmd_analytics, "workers": cmd_workers,
     "backups": cmd_backups, "deploy": cmd_deploy}.get(args.command, lambda a: parser.print_help())(args)


if __name__ == "__main__":
    main()
