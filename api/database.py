"""
ReconX Database Manager
Async SQLite operations using aiosqlite
"""

import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from api.models import (
    Base, Target, Scan, Subdomain, Endpoint, 
    Vulnerability, Port, SystemState, ScanStatus, Severity
)

class DatabaseManager:
    def __init__(self, db_path: str = "data/recon.db"):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Initialize database connection and create tables"""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        
        # Create tables
        await self._create_tables()
        return self
    
    async def disconnect(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def _create_tables(self):
        """Create all tables if they don't exist"""
        # Target table
        await self._connection.execute("""
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
            )
        """)
        
        # Scan table
        await self._connection.execute("""
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
                FOREIGN KEY (target_id) REFERENCES targets(id)
            )
        """)
        
        # Subdomain table
        await self._connection.execute("""
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
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            )
        """)
        
        # Endpoint table
        await self._connection.execute("""
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
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            )
        """)
        
        # Vulnerability table
        await self._connection.execute("""
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
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            )
        """)
        
        # Port table
        await self._connection.execute("""
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
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            )
        """)
        
        # System state table
        await self._connection.execute("""
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
            )
        """)
        
        await self._connection.commit()
    
    # Target operations
    async def create_target(self, target_data: Dict[str, Any]) -> str:
        """Create a new target"""
        target_id = target_data.get('id')
        await self._connection.execute("""
            INSERT INTO targets (id, name, primary_domain, scope, exclusions, asn_list, ip_ranges, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            target_id,
            target_data['name'],
            target_data['primary_domain'],
            json.dumps(target_data.get('scope', [])),
            json.dumps(target_data.get('exclusions', [])),
            json.dumps(target_data.get('asn_list', [])),
            json.dumps(target_data.get('ip_ranges', [])),
            target_data.get('status', 'pending')
        ))
        await self._connection.commit()
        return target_id
    
    async def get_target(self, target_id: str) -> Optional[Dict]:
        """Get target by ID"""
        async with self._connection.execute(
            "SELECT * FROM targets WHERE id = ?", (target_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    async def get_all_targets(self) -> List[Dict]:
        """Get all targets"""
        async with self._connection.execute(
            "SELECT * FROM targets ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # Scan operations
    async def create_scan(self, scan_data: Dict[str, Any]) -> str:
        """Create a new scan"""
        scan_id = scan_data.get('id')
        await self._connection.execute("""
            INSERT INTO scans (id, target_id, name, profile, status, config, is_resumed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            scan_id,
            scan_data['target_id'],
            scan_data.get('name', f"Scan {datetime.now().isoformat()}"),
            scan_data.get('profile', 'normal'),
            scan_data.get('status', 'pending'),
            json.dumps(scan_data.get('config', {})),
            scan_data.get('is_resumed', False)
        ))
        await self._connection.commit()
        return scan_id
    
    async def get_scan(self, scan_id: str) -> Optional[Dict]:
        """Get scan by ID"""
        async with self._connection.execute(
            "SELECT * FROM scans WHERE id = ?", (scan_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    async def update_scan_status(self, scan_id: str, status: str, 
                                  current_task: Optional[str] = None,
                                  progress: Optional[Dict] = None):
        """Update scan status and optional fields"""
        updates = ["status = ?"]
        params = [status]
        
        if current_task:
            updates.append("current_task = ?")
            params.append(current_task)
        
        if progress:
            updates.append("progress = ?")
            params.append(json.dumps(progress))
        
        if status == 'running' and not await self._is_scan_started(scan_id):
            updates.append("started_at = CURRENT_TIMESTAMP")
        elif status in ['completed', 'failed']:
            updates.append("completed_at = CURRENT_TIMESTAMP")
        
        params.append(scan_id)
        
        query = f"UPDATE scans SET {', '.join(updates)} WHERE id = ?"
        await self._connection.execute(query, params)
        await self._connection.commit()
    
    async def _is_scan_started(self, scan_id: str) -> bool:
        """Check if scan has started_at timestamp"""
        async with self._connection.execute(
            "SELECT started_at FROM scans WHERE id = ?", (scan_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row and row['started_at'] is not None
    
    async def save_checkpoint(self, scan_id: str, checkpoint_data: Dict):
        """Save scan checkpoint for resume capability"""
        await self._connection.execute("""
            UPDATE scans SET checkpoint_data = ? WHERE id = ?
        """, (json.dumps(checkpoint_data), scan_id))
        await self._connection.commit()
    
    async def get_active_scans(self) -> List[Dict]:
        """Get all running or paused scans"""
        async with self._connection.execute("""
            SELECT * FROM scans WHERE status IN ('running', 'paused')
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # Subdomain operations
    async def add_subdomain(self, scan_id: str, subdomain_data: Dict):
        """Add a subdomain result"""
        await self._connection.execute("""
            INSERT INTO subdomains 
            (id, scan_id, subdomain, ip_addresses, status_code, title, tech_stack, 
             is_live, screenshot_path, headers, tls_info, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            subdomain_data.get('id'),
            scan_id,
            subdomain_data['subdomain'],
            json.dumps(subdomain_data.get('ip_addresses', [])),
            subdomain_data.get('status_code'),
            subdomain_data.get('title'),
            json.dumps(subdomain_data.get('tech_stack', [])),
            subdomain_data.get('is_live', False),
            subdomain_data.get('screenshot_path'),
            json.dumps(subdomain_data.get('headers')) if subdomain_data.get('headers') else None,
            json.dumps(subdomain_data.get('tls_info')) if subdomain_data.get('tls_info') else None,
            json.dumps(subdomain_data.get('source', []))
        ))
        await self._connection.commit()
    
    async def get_subdomains(self, scan_id: str) -> List[Dict]:
        """Get all subdomains for a scan"""
        async with self._connection.execute("""
            SELECT * FROM subdomains WHERE scan_id = ? ORDER BY subdomain
        """, (scan_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # Vulnerability operations
    async def add_vulnerability(self, scan_id: str, vuln_data: Dict):
        """Add a vulnerability finding"""
        await self._connection.execute("""
            INSERT INTO vulnerabilities
            (id, scan_id, title, severity, cvss_score, description, affected_url,
             parameter, evidence, poc_commands, remediation, tool_source, template_id,
             false_positive, llm_analysis, llm_model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vuln_data.get('id'),
            scan_id,
            vuln_data['title'],
            vuln_data['severity'],
            vuln_data.get('cvss_score'),
            vuln_data.get('description'),
            vuln_data.get('affected_url'),
            vuln_data.get('parameter'),
            vuln_data.get('evidence'),
            json.dumps(vuln_data.get('poc_commands', [])),
            vuln_data.get('remediation'),
            vuln_data.get('tool_source'),
            vuln_data.get('template_id'),
            vuln_data.get('false_positive', False),
            vuln_data.get('llm_analysis'),
            vuln_data.get('llm_model')
        ))
        await self._connection.commit()
    
    async def get_vulnerabilities(self, scan_id: str, 
                                   severity: Optional[str] = None) -> List[Dict]:
        """Get vulnerabilities for a scan, optionally filtered by severity"""
        query = "SELECT * FROM vulnerabilities WHERE scan_id = ?"
        params = [scan_id]
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY CASE severity " \
                 "WHEN 'critical' THEN 1 " \
                 "WHEN 'high' THEN 2 " \
                 "WHEN 'medium' THEN 3 " \
                 "WHEN 'low' THEN 4 " \
                 "ELSE 5 END, created_at DESC"
        
        async with self._connection.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # System state operations
    async def update_system_state(self, state_data: Dict):
        """Update system state"""
        # Check if record exists
        async with self._connection.execute(
            "SELECT id FROM system_state LIMIT 1"
        ) as cursor:
            existing = await cursor.fetchone()
        
        if existing:
            await self._connection.execute("""
                UPDATE system_state SET
                last_seen = CURRENT_TIMESTAMP,
                network_status = ?,
                tunnel_url = ?,
                tunnel_service = ?,
                battery_level = ?,
                is_charging = ?,
                temperature = ?,
                llm_status = ?,
                free_memory_mb = ?,
                updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                state_data.get('network_status', 'online'),
                state_data.get('tunnel_url'),
                state_data.get('tunnel_service'),
                state_data.get('battery_level'),
                state_data.get('is_charging', False),
                state_data.get('temperature'),
                state_data.get('llm_status', 'unloaded'),
                state_data.get('free_memory_mb'),
                existing['id']
            ))
        else:
            await self._connection.execute("""
                INSERT INTO system_state 
                (id, network_status, tunnel_url, tunnel_service, battery_level,
                 is_charging, temperature, llm_status, free_memory_mb)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state_data.get('id'),
                state_data.get('network_status', 'online'),
                state_data.get('tunnel_url'),
                state_data.get('tunnel_service'),
                state_data.get('battery_level'),
                state_data.get('is_charging', False),
                state_data.get('temperature'),
                state_data.get('llm_status', 'unloaded'),
                state_data.get('free_memory_mb')
            ))
        
        await self._connection.commit()
    
    async def get_system_state(self) -> Optional[Dict]:
        """Get current system state"""
        async with self._connection.execute(
            "SELECT * FROM system_state ORDER BY updated_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

# Global database instance
db = DatabaseManager()

async def get_db() -> DatabaseManager:
    """Dependency to get database instance"""
    return db
