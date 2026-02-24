# core/database.py
import aiosqlite
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "reconx.db"

async def init_db():
    """Initialize the database with required tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Targets Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host TEXT NOT NULL UNIQUE,
                scope TEXT,
                ip_range TEXT,
                asn TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)

        # Scans Table (Tracks the state for Resume feature)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER,
                scan_type TEXT,
                status TEXT, -- pending, running, paused, completed, failed
                progress INTEGER DEFAULT 0,
                current_module TEXT,
                start_time TEXT,
                end_time TEXT,
                FOREIGN KEY(target_id) REFERENCES targets(id)
            )
        """)

        # Subdomains Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subdomains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER,
                subdomain TEXT,
                is_alive INTEGER DEFAULT 0,
                status_code INTEGER,
                content_length INTEGER,
                tech_stack TEXT,
                ports TEXT,
                waf TEXT,
                FOREIGN KEY(target_id) REFERENCES targets(id)
            )
        """)

        # Vulnerabilities Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vulnerabilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER,
                scan_id INTEGER,
                severity TEXT,
                name TEXT,
                url TEXT,
                template_id TEXT,
                matcher_name TEXT,
                raw_output TEXT,
                cvss_score REAL,
                false_positive INTEGER DEFAULT 0,
                FOREIGN KEY(target_id) REFERENCES targets(id),
                FOREIGN KEY(scan_id) REFERENCES scans(id)
            )
        """)

        # OSINT & Secrets Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS osint_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER,
                source TEXT, -- js_file, github, wayback
                type TEXT, -- secret, endpoint, param
                data TEXT,
                url TEXT,
                FOREIGN KEY(target_id) REFERENCES targets(id)
            )
        """)

        # Tool Health Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tool_health (
                tool_name TEXT PRIMARY KEY,
                installed INTEGER DEFAULT 0,
                version TEXT,
                last_checked TEXT
            )
        """)

        await db.commit()

# --- Helper Functions ---

async def add_target(host, scope=""):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO targets (host, scope, created_at, status) VALUES (?, ?, ?, ?)",
            (host, scope, datetime.now().isoformat(), 'added')
        )
        await db.commit()
        return cursor.lastrowid

async def get_target(host):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM targets WHERE host = ?", (host,)) as cursor:
            return await cursor.fetchone()

async def create_scan(target_id, scan_type):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO scans (target_id, scan_type, status, start_time, progress) VALUES (?, ?, ?, ?, ?)",
            (target_id, scan_type, 'pending', datetime.now().isoformat(), 0)
        )
        await db.commit()
        return cursor.lastrowid

async def update_scan_progress(scan_id, progress, current_module, status='running'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE scans SET progress = ?, current_module = ?, status = ? WHERE id = ?",
            (progress, current_module, status, scan_id)
        )
        await db.commit()

# --- Initialize DB on import (for running standalone checks) ---
if __name__ == "__main__":
    import asyncio
    print("[*] Initializing Database...")
    asyncio.run(init_db())
    print("[+] Database initialized at " + str(DB_PATH))