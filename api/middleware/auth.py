"""
ReconX Authentication
JWT-based auth for tunnel access
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

class AuthManager:
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or self._generate_secret()
        self.algorithm = "HS256"
        self.token_expire_hours = 24
    
    def _generate_secret(self) -> str:
        """Generate random secret key"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(
            plain_password.encode(),
            hashed_password.encode()
        )
    
    def create_token(self, user_id: str, extra_claims: Optional[Dict] = None) -> str:
        """Create JWT token"""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(hours=self.token_expire_hours),
            "type": "access"
        }
        
        if extra_claims:
            payload.update(extra_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    async def __call__(self, credentials: HTTPAuthorizationCredentials = Security(security)):
        """FastAPI dependency for protected routes"""
        if not credentials:
            raise HTTPException(status_code=403, detail="Authorization required")
        
        return self.verify_token(credentials.credentials)

# Simple password protection for tunnel access
class TunnelAuth:
    def __init__(self):
        self.password_hash: Optional[str] = None
        self._load_password()
    
    def _load_password(self):
        """Load password from config"""
        try:
            import json
            with open('config/settings.json', 'r') as f:
                config = json.load(f)
                password = config.get('tunnel', {}).get('password')
                if password:
                    self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        except Exception:
            pass
    
    def set_password(self, password: str):
        """Set new password"""
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    def verify(self, password: str) -> bool:
        """Verify tunnel password"""
        if not self.password_hash:
            return True  # No password set, allow access
        
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())
