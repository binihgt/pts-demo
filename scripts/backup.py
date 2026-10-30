#!/usr/bin/env python3
"""
Automated SQLite Online Backup & Retention Script for PTS Demo.
Uses SQLite's native backup API (sqlite3.Connection.backup) for zero-downtime,
safe snapshots during live transactions, and maintains a rolling 14-backup retention window.

Usage:
    python scripts/backup.py
    python scripts/backup.py --retention-count 14
    python scripts/backup.py --help

Cron Example (Daily at 02:00 AM):
    0 2 * * * /path/to/project/.venv/bin/python /path/to/project/scripts/backup.py >> /var/log/pts_backup.log 2>&1
"""
import os
import sys
import sqlite3
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("pts_backup")


def get_default_db_path() -> Path:
    """Resolve SQLite database path from DATABASE_URL, instance folder, or BASE_DIR."""
    # Check Flask-SQLAlchemy instance folder first
    instance_db = BASE_DIR / "instance" / "pts_demo.db"
    if instance_db.exists():
        return instance_db

    root_db = BASE_DIR / "pts_demo.db"
    if root_db.exists():
        return root_db

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("sqlite:///"):
        raw_path = db_url.replace("sqlite:///", "")
        path = Path(raw_path)
        if not path.is_absolute():
            # Check instance then base
            if (BASE_DIR / "instance" / path).exists():
                return BASE_DIR / "instance" / path
            return BASE_DIR / path
        return path

    return instance_db


def run_sqlite_backup(source_path: Path, dest_path: Path) -> None:
    """
    Safely backup an active SQLite database using SQLite's native online backup API.
    Guarantees consistent, uncorrupted snapshots during live write operations.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source database file does not exist: {source_path}")

    # Ensure parent directory of destination exists
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initiating online SQLite backup from {source_path} to {dest_path}")
    source_conn = sqlite3.connect(str(source_path))
    dest_conn = sqlite3.connect(str(dest_path))

    try:
        # Perform online backup: copies pages while respecting active locks
        source_conn.backup(dest_conn, pages=100)
        logger.info(f"Backup completed successfully: {dest_path.name} ({dest_path.stat().st_size:,} bytes)")
    finally:
        dest_conn.close()
        source_conn.close()


def rotate_backups(backup_dir: Path, retention_count: int = 14) -> list[Path]:
    """
    Enforce retention policy: keeps the newest `retention_count` backups
    and deletes older ones. Returns list of deleted file paths.
    """
    if not backup_dir.exists():
        return []

    # Find all backup files matching standard naming pattern
    backup_files = sorted(
        backup_dir.glob("pts_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True  # Newest first
    )

    deleted_files = []
    if len(backup_files) > retention_count:
        excess_files = backup_files[retention_count:]
        logger.info(f"Found {len(backup_files)} backups. Retaining newest {retention_count}; purging {len(excess_files)} older backups.")

        for old_file in excess_files:
            try:
                old_file.unlink()
                deleted_files.append(old_file)
                logger.info(f"Deleted expired backup: {old_file.name}")
            except OSError as e:
                logger.error(f"Failed to delete {old_file.name}: {e}")
    else:
        logger.info(f"Retention check OK: {len(backup_files)} backups present (limit is {retention_count}). No deletions needed.")

    return deleted_files


def perform_backup(
    db_path: Path | None = None,
    backup_dir: Path | None = None,
    retention_count: int = 14
) -> Path:
    """Convenience function to execute both backup and retention rotation."""
    if db_path is None:
        db_path = get_default_db_path()
    if backup_dir is None:
        backup_dir = BASE_DIR / "backups"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"pts_backup_{timestamp}.db"
    dest_backup_path = backup_dir / backup_filename

    # 1. Run online backup
    run_sqlite_backup(db_path, dest_backup_path)

    # 2. Run rotation
    rotate_backups(backup_dir, retention_count=retention_count)

    return dest_backup_path


def main():
    parser = argparse.ArgumentParser(description="PTS Demo - Automated SQLite Backup & Rotation")
    parser.add_argument("--db-path", help="Path to source SQLite database file", default=None)
    parser.add_argument("--backup-dir", help="Directory where backups are stored", default=None)
    parser.add_argument("--retention-count", type=int, default=14, help="Number of backups to keep (default: 14)")
    args = parser.parse_args()

    source_db = Path(args.db_path) if args.db_path else get_default_db_path()
    backup_dir = Path(args.backup_dir) if args.backup_dir else BASE_DIR / "backups"

    try:
        dest_file = perform_backup(
            db_path=source_db,
            backup_dir=backup_dir,
            retention_count=args.retention_count
        )
        print(f"\n[+] Success! Backup saved: {dest_file}")
    except Exception as e:
        logger.error(f"Backup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
