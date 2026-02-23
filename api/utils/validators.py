"""
ReconX Input Validators
Sanitization and validation utilities
"""

import re
from urllib.parse import urlparse
from typing import Optional, List

class InputValidator:
    """Validate and sanitize user inputs"""
    
    # Regex patterns
    DOMAIN_PATTERN = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    )
    IP_PATTERN = re.compile(
        r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )
    URL_PATTERN = re.compile(
        r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    )
    
    DANGEROUS_CHARS = re.compile(r'[;&|`$()]')
    PATH_TRAVERSAL = re.compile(r'\.\./|\.\.\\')
    
    @classmethod
    def validate_domain(cls, domain: str) -> bool:
        """Validate domain name"""
        if not domain or len(domain) > 253:
            return False
        return bool(cls.DOMAIN_PATTERN.match(domain))
    
    @classmethod
    def validate_ip(cls, ip: str) -> bool:
        """Validate IPv4 address"""
        return bool(cls.IP_PATTERN.match(ip))
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except Exception:
            return False
    
    @classmethod
    def sanitize_command_arg(cls, arg: str) -> str:
        """Sanitize command line argument"""
        # Remove dangerous characters
        sanitized = cls.DANGEROUS_CHARS.sub('', arg)
        # Prevent path traversal
        sanitized = cls.PATH_TRAVERSAL.sub('', sanitized)
        return sanitized.strip()
    
    @classmethod
    def sanitize_path(cls, path: str) -> Optional[str]:
        """Sanitize file path"""
        # Normalize path
        path = path.replace('\\', '/')
        
        # Check for path traversal
        if '..' in path or path.startswith('/'):
            return None
        
        # Only allow alphanumeric, dash, underscore, dot, slash
        if not re.match(r'^[\w\-\./]+$', path):
            return None
        
        return path
    
    @classmethod
    def validate_scope(cls, scope_items: List[str]) -> List[str]:
        """Validate scope items (domains/IPs)"""
        valid = []
        for item in scope_items:
            item = item.strip().lower()
            if cls.validate_domain(item) or cls.validate_ip(item):
                valid.append(item)
        return valid
    
    @classmethod
    def sanitize_json_key(cls, key: str) -> str:
        """Sanitize JSON key"""
        # Only allow alphanumeric and underscore
        return re.sub(r'[^\w]', '', key)[:64]
