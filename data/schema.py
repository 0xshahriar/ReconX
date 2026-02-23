"""
ReconX Database Schema
SQLite schema definitions and migrations
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Current schema version
SCHEMA_VERSION = 1

# SQL to create tables
CREATE_TABLES_SQL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Targets table
CREATE TABLE IF NOT EXISTS targets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    primary_domain TEXT NOT NULL,
    scope TEXT DEFAULT '[]',
    exclusions TEXT DEFAULT '[]',
    asn_list TEXT DEFAULT '[]',
    ip_ranges TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_targets_domain ON targets(primary_domain);
CREATE INDEX IF NOT EXISTS idx_targets_status ON targets(status);

-- Scans table
CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    name TEXT,
    profile TEXT DEFAULT 'normal',
    status TEXT DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    progress TEXT DEFAULT '{}',
    current_task TEXT,
    config TEXT DEFAULT '{}',
    error_message TEXT,
    checkpoint_data TEXT,
    is_resumed BOOLEAN DEFAULT 0,
    llm_model_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scans_target ON scans(target_id);
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);
CREATE INDEX IF NOT EXISTS idx_scans_created ON scans(created_at);

-- Subdomains table
CREATE TABLE IF NOT EXISTS subdomains (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    subdomain TEXT NOT NULL,
    ip_addresses TEXT DEFAULT '[]',
    status_code INTEGER,
    title TEXT,
    tech_stack TEXT DEFAULT '[]',
    is_live BOOLEAN DEFAULT 0,
    screenshot_path TEXT,
    headers TEXT,
    tls_info TEXT,
    source TEXT DEFAULT '[]',
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_subdomains_scan ON subdomains(scan_id);
CREATE INDEX IF NOT EXISTS idx_subdomains_name ON subdomains(subdomain);
CREATE INDEX IF NOT EXISTS idx_subdomains_live ON subdomains(is_live);

-- Endpoints table
CREATE TABLE IF NOT EXISTS endpoints (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    url TEXT NOT NULL,
    method TEXT DEFAULT 'GET',
    status_code INTEGER,
    content_type TEXT,
    content_length INTEGER,
    parameters TEXT DEFAULT '[]',
    gf_patterns TEXT DEFAULT '[]',
    response_hash TEXT,
    discovered_via TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_endpoints_scan ON endpoints(scan_id);
CREATE INDEX IF NOT EXISTS idx_endpoints_url ON endpoints(url);

-- Vulnerabilities table
CREATE TABLE IF NOT EXISTS vulnerabilities (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    cvss_score REAL,
    description TEXT,
    affected_url TEXT,
    parameter TEXT,
    evidence TEXT,
    poc_commands TEXT DEFAULT '[]',
    remediation TEXT,
    tool_source TEXT,
    template_id TEXT,
    false_positive BOOLEAN DEFAULT 0,
    llm_analysis TEXT,
    llm_model TEXT,
    reported BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vulns_scan ON vulnerabilities(scan_id);
CREATE INDEX IF NOT EXISTS idx_vulns_severity ON vulnerabilities(severity);
CREATE INDEX IF NOT EXISTS idx_vulns_fp ON vulnerabilities(false_positive);

-- Ports table
CREATE TABLE IF NOT EXISTS ports (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    protocol TEXT DEFAULT 'tcp',
    service TEXT,
    version TEXT,
    banner TEXT,
    state TEXT DEFAULT 'open',
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ports_scan ON ports(scan_id);
CREATE INDEX IF NOT EXISTS idx_ports_ip ON ports(ip);

-- System state table
CREATE TABLE IF NOT EXISTS system_state (
    id TEXT PRIMARY KEY,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    network_status TEXT DEFAULT 'online',
    tunnel_url TEXT,
    tunnel_service TEXT,
    battery_level INTEGER,
    is_charging BOOLEAN DEFAULT 0,
    temperature REAL,
    llm_status TEXT DEFAULT 'unloaded',
    free_memory_mb INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Continuous monitors table
CREATE TABLE IF NOT EXISTS continuous_monitors (
    target_id TEXT PRIMARY KEY,
    interval_hours INTEGER DEFAULT 24,
    enabled_modules TEXT,
    alert_on_changes BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run TIMESTAMP,
    FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE
);

-- Notifications log
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT,
    severity TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivered BOOLEAN DEFAULT 0
);

-- Scan logs
CREATE TABLE IF NOT EXISTS scan_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    level TEXT,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_logs_scan ON scan_logs(scan_id);
"""

MIGRATIONS: List[Tuple[int, str, str]] = [
    # (version, description, sql)
    (1, "Initial schema", CREATE_TABLES_SQL),
]

def init_database(db_path: str = "data/recon.db") -> bool:
    """Initialize database with schema"""
    try:
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.executescript(CREATE_TABLES_SQL)
        
        # Check/set schema version
        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cursor.fetchone()
        
        if not row:
            cursor.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,)
            )
            logger.info(f"Initialized database with schema version {SCHEMA_VERSION}")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

def run_migrations(db_path: str = "data/recon.db") -> bool:
    """Run pending migrations"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get current version
        try:
            cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            current_version = row[0] if row else 0
        except sqlite3.OperationalError:
            # Table doesn't exist, needs full init
            conn.close()
            return init_database(db_path)
        
        # Apply pending migrations
        for version, description, sql in MIGRATIONS:
            if version > current_version:
                logger.info(f"Applying migration {version}: {description}")
                cursor.executescript(sql)
                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (version,)
                )
                conn.commit()
                logger.info(f"Migration {version} applied")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def get_db_version(db_path: str = "data/recon.db") -> int:
    """Get current database schema version"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception:
        return 0

def vacuum_database(db_path: str = "data/recon.db"):
    """Optimize database file"""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
        logger.info("Database vacuumed")
    except Exception as e:
        logger.error(f"Vacuum failed: {e}")

def backup_database(db_path: str = "data/recon.db", backup_dir: str = "data/backups"):
    """Create database backup"""
    from datetime import datetime
    import shutil
    
    try:
        Path(backup_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(backup_dir) / f"recon_backup_{timestamp}.db"
        
        # Close any open connections first
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA wal_checkpoint=FULL")
        conn.close()
        
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to {backup_path}")
        return str(backup_path)
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return None
