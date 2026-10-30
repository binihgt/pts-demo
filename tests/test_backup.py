import sqlite3
import time
from pathlib import Path
from scripts.backup import run_sqlite_backup, rotate_backups, perform_backup


def test_sqlite_online_backup_integrity(tmp_path):
    """Test that SQLite online backup produces an exact, readable replica."""
    source_db = tmp_path / "source.db"
    dest_db = tmp_path / "backups" / "pts_backup_test.db"

    # Create and populate source SQLite database
    conn = sqlite3.connect(str(source_db))
    cur = conn.cursor()
    cur.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL);")
    cur.execute("INSERT INTO products (name, price) VALUES ('Dell Laptop', 45000.0);")
    cur.execute("INSERT INTO products (name, price) VALUES ('Samsung Monitor', 12500.0);")
    conn.commit()
    conn.close()

    # Perform online backup
    run_sqlite_backup(source_db, dest_db)

    # Verify backup exists and is readable
    assert dest_db.exists()
    assert dest_db.stat().st_size > 0

    backup_conn = sqlite3.connect(str(dest_db))
    backup_cur = backup_conn.cursor()
    backup_cur.execute("SELECT name, price FROM products ORDER BY id ASC;")
    rows = backup_cur.fetchall()
    backup_conn.close()

    assert len(rows) == 2
    assert rows[0] == ("Dell Laptop", 45000.0)
    assert rows[1] == ("Samsung Monitor", 12500.0)


def test_backup_rotation_14_retention(tmp_path):
    """Test that backup rotation strictly keeps the newest 14 backups and purges older ones."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create 20 mock backup files with staggered timestamps
    created_files = []
    base_time = time.time() - 3600  # 1 hour ago

    for i in range(20):
        f = backup_dir / f"pts_backup_20261030_{i:04d}.db"
        f.write_text(f"dummy backup content {i}")
        # Set distinct modification times (i=0 oldest, i=19 newest)
        mod_time = base_time + (i * 60)
        os_time = (mod_time, mod_time)
        import os
        os.utime(str(f), os_time)
        created_files.append(f)

    assert len(list(backup_dir.glob("pts_backup_*.db"))) == 20

    # Run rotation with retention_count = 14
    deleted = rotate_backups(backup_dir, retention_count=14)

    # Exactly 6 oldest files should be deleted
    assert len(deleted) == 6

    # Exactly 14 files should remain
    remaining = sorted(backup_dir.glob("pts_backup_*.db"))
    assert len(remaining) == 14

    # Ensure the 6 oldest (indices 0 to 5) were purged
    for old_file in created_files[:6]:
        assert not old_file.exists()

    # Ensure the 14 newest (indices 6 to 19) are preserved
    for new_file in created_files[6:]:
        assert new_file.exists()
