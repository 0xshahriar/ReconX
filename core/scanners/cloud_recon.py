"""
Cloud Reconnaissance Scanner
S3, GCP, Azure bucket enumeration
"""

import logging
from typing import Dict, List, Any, Optional

import aiohttp

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class CloudRecon:
    """Cloud service enumeration"""
    
    def __init__(self, subprocess_mgr: SubprocessManager, db: DatabaseManager):
        self.subprocess_mgr = subprocess_mgr
        self.db = db
        self.tool_manager = ToolManager()
    
    async def scan(
        self,
        target_id: str,
        scan_id: str,
        config: Dict[str, Any],
        previous_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Scan for cloud resources"""
        
        target = await self.db.get_target(target_id)
        if not target:
            raise ValueError(f"Target {target_id} not found")
        
        domain = target["primary_domain"]
        name = domain.replace(".", "-")
        
        findings = []
        
        # S3 Buckets
        if config.get("scan_s3", True):
            s3_results = await self._scan_s3(name, domain, scan_id)
            findings.extend(s3_results)
        
        # GCP Buckets
        if config.get("scan_gcp", True):
            gcp_results = await self._scan_gcp(name, domain, scan_id)
            findings.extend(gcp_results)
        
        # Azure Blobs
        if config.get("scan_azure", True):
            azure_results = await self._scan_azure(name, domain, scan_id)
            findings.extend(azure_results)
        
        logger.info(f"Cloud recon found {len(findings)} resources")
        
        return {
            "scanned": 3,  # S3, GCP, Azure
            "findings": len(findings),
            "resources": findings
        }
    
    async def _scan_s3(self, name: str, domain: str, scan_id: str) -> List[Dict]:
        """Scan for S3 buckets"""
        await self.tool_manager.ensure_tool("s3scanner")
        
        # Generate bucket names
        bucket_names = [
            name,
            f"{name}-assets",
            f"{name}-data",
            f"{name}-uploads",
            f"{name}-backup",
            f"{name}-dev",
            f"{name}-staging",
            f"{name}-prod",
            domain.replace(".", ""),
            f"com-{name}"
        ]
        
        findings = []
        
        for bucket in bucket_names:
            try:
                # Check with s3scanner
                cmd = f"s3scanner scan -b {bucket}"
                stdout = await self.subprocess_mgr.run_simple(cmd, timeout=30)
                
                if "exists" in stdout.lower() or "found" in stdout.lower():
                    # Check permissions
                    perms = await self._check_s3_perms(bucket)
                    
                    finding = {
                        "service": "s3",
                        "resource": f"s3://{bucket}",
                        "permissions": perms,
                        "severity": "high" if "public" in perms else "medium"
                    }
                    
                    findings.append(finding)
                    
                    # Save vulnerability
                    await self.db.add_vulnerability(scan_id, {
                        "title": f"Exposed S3 Bucket: {bucket}",
                        "severity": finding["severity"],
                        "description": f"S3 bucket found with permissions: {perms}",
                        "affected_url": f"s3://{bucket}",
                        "tool_source": "cloud_recon"
                    })
            
            except Exception as e:
                logger.debug(f"S3 check failed for {bucket}: {e}")
        
        return findings
    
    async def _check_s3_perms(self, bucket: str) -> str:
        """Check S3 bucket permissions"""
        import boto3
        from botocore.exceptions import ClientError
        
        try:
            s3 = boto3.client('s3')
            
            # Try to list bucket
            s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
            return "listable"
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                return "private"
            elif error_code == 'NoSuchBucket':
                return "not_found"
        
        return "unknown"
    
    async def _scan_gcp(self, name: str, domain: str, scan_id: str) -> List[Dict]:
        """Scan for GCP buckets"""
        bucket_names = [
            f"{name}.appspot.com",
            f"{name}_bucket",
            f"{name}-storage"
        ]
        
        findings = []
        
        async with aiohttp.ClientSession() as session:
            for bucket in bucket_names:
                url = f"https://storage.googleapis.com/{bucket}"
                
                try:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            findings.append({
                                "service": "gcp",
                                "resource": f"gs://{bucket}",
                                "status": "public",
                                "severity": "high"
                            })
                            
                            await self.db.add_vulnerability(scan_id, {
                                "title": f"Exposed GCS Bucket: {bucket}",
                                "severity": "high",
                                "description": "Publicly accessible Google Cloud Storage bucket",
                                "affected_url": url,
                                "tool_source": "cloud_recon"
                            })
                        
                        elif resp.status == 403:
                            findings.append({
                                "service": "gcp",
                                "resource": f"gs://{bucket}",
                                "status": "exists_private",
                                "severity": "low"
                            })
                
                except Exception as e:
                    logger.debug(f"GCP check failed for {bucket}: {e}")
        
        return findings
    
    async def _scan_azure(self, name: str, domain: str, scan_id: str) -> List[Dict]:
        """Scan for Azure blobs"""
        container_names = [
            name,
            f"{name}-blob",
            f"{name}-storage",
            "public",
            "assets"
        ]
        
        findings = []
        
        # Common Azure storage account patterns
        account_patterns = [
            f"{name}blob",
            f"{name}storage",
            name.replace("-", ""),
            name.replace(".", "")
        ]
        
        async with aiohttp.ClientSession() as session:
            for account in account_patterns[:3]:
                for container in container_names[:3]:
                    url = f"https://{account}.blob.core.windows.net/{container}"
                    
                    try:
                        async with session.get(url, timeout=10) as resp:
                            if resp.status == 200:
                                findings.append({
                                    "service": "azure",
                                    "resource": url,
                                    "status": "public",
                                    "severity": "high"
                                })
                                
                                await self.db.add_vulnerability(scan_id, {
                                    "title": f"Exposed Azure Blob: {account}/{container}",
                                    "severity": "high",
                                    "description": "Publicly accessible Azure blob container",
                                    "affected_url": url,
                                    "tool_source": "cloud_recon"
                                })
                            
                            elif "ContainerNotFound" not in await resp.text():
                                # Container exists but might be private
                                pass
                    
                    except Exception as e:
                        logger.debug(f"Azure check failed: {e}")
        
        return findings
