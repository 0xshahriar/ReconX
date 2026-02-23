"""
ReconX Database Models
SQLAlchemy ORM models for SQLite database
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    Text, ForeignKey, JSON, Enum, create_engine
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class ScanStatus(PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class ScanProfile(PyEnum):
    STEALTHY = "stealthy"
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"

class Severity(PyEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class NetworkStatus(PyEnum):
    ONLINE = "online"
    OFFLINE = "offline"

class Target(Base):
    __tablename__ = "targets"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    primary_domain = Column(String(255), nullable=False, index=True)
    scope = Column(JSON, default=list)  # List of in-scope domains/IPs
    exclusions = Column(JSON, default=list)  # Out-of-scope items
    asn_list = Column(JSON, default=list)
    ip_ranges = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING)
    
    # Relationships
    scans = relationship("Scan", back_populates="target", cascade="all, delete-orphan")

class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    target_id = Column(String, ForeignKey("targets.id"), nullable=False)
    name = Column(String(255))
    profile = Column(Enum(ScanProfile), default=ScanProfile.NORMAL)
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    progress = Column(JSON, default=dict)  # Module -> percentage
    current_task = Column(String(500), nullable=True)
    config = Column(JSON, default=dict)  # Full scan configuration
    error_message = Column(Text, nullable=True)
    checkpoint_data = Column(JSON, nullable=True)  # Last saved state
    is_resumed = Column(Boolean, default=False)
    llm_model_used = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    target = relationship("Target", back_populates="scans")
    subdomains = relationship("Subdomain", back_populates="scan", cascade="all, delete-orphan")
    endpoints = relationship("Endpoint", back_populates="scan", cascade="all, delete-orphan")
    vulnerabilities = relationship("Vulnerability", back_populates="scan", cascade="all, delete-orphan")
    ports = relationship("Port", back_populates="scan", cascade="all, delete-orphan")

class Subdomain(Base):
    __tablename__ = "subdomains"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    subdomain = Column(String(500), nullable=False, index=True)
    ip_addresses = Column(JSON, default=list)
    status_code = Column(Integer, nullable=True)
    title = Column(String(500), nullable=True)
    tech_stack = Column(JSON, default=list)
    is_live = Column(Boolean, default=False)
    screenshot_path = Column(String(500), nullable=True)
    headers = Column(JSON, nullable=True)
    tls_info = Column(JSON, nullable=True)
    source = Column(JSON, default=list)  # Which tools found it
    first_seen = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scan = relationship("Scan", back_populates="subdomains")

class Endpoint(Base):
    __tablename__ = "endpoints"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    url = Column(String(2000), nullable=False, index=True)
    method = Column(String(10), default="GET")
    status_code = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=True)
    content_length = Column(Integer, nullable=True)
    parameters = Column(JSON, default=list)
    gf_patterns = Column(JSON, default=list)
    response_hash = Column(String(64), nullable=True)
    discovered_via = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scan = relationship("Scan", back_populates="endpoints")

class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    title = Column(String(500), nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    cvss_score = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    affected_url = Column(String(2000), nullable=True)
    parameter = Column(String(255), nullable=True)
    evidence = Column(Text, nullable=True)  # Request/response
    poc_commands = Column(JSON, default=list)
    remediation = Column(Text, nullable=True)
    tool_source = Column(String(50), nullable=True)  # nuclei, gf, manual
    template_id = Column(String(255), nullable=True)  # Nuclei template ID
    false_positive = Column(Boolean, default=False)
    llm_analysis = Column(Text, nullable=True)
    llm_model = Column(String(50), nullable=True)
    reported = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scan = relationship("Scan", back_populates="vulnerabilities")

class Port(Base):
    __tablename__ = "ports"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    ip = Column(String(45), nullable=False, index=True)  # IPv6 compatible
    port = Column(Integer, nullable=False)
    protocol = Column(String(10), default="tcp")
    service = Column(String(100), nullable=True)
    version = Column(String(200), nullable=True)
    banner = Column(Text, nullable=True)
    state = Column(String(20), default="open")  # open/filtered/closed
    
    # Relationships
    scan = relationship("Scan", back_populates="ports")

class SystemState(Base):
    __tablename__ = "system_state"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    last_seen = Column(DateTime, default=datetime.utcnow)
    network_status = Column(Enum(NetworkStatus), default=NetworkStatus.ONLINE)
    tunnel_url = Column(String(500), nullable=True)
    tunnel_service = Column(String(50), nullable=True)  # cloudflare/ngrok/localtunnel
    battery_level = Column(Integer, nullable=True)
    is_charging = Column(Boolean, default=False)
    temperature = Column(Float, nullable=True)
    llm_status = Column(String(50), default="unloaded")  # unloaded/llama3.1:8b/gemma3:4b/gemma3:1b
    free_memory_mb = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database initialization
def init_db(database_url: str = "sqlite:///data/recon.db"):
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine
