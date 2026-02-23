"""
ReconX Report Manager
Manage generated reports and storage
"""

import json
import logging
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ReportManager:
    """Manage generated reports"""
    
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Aggregated stats directory
        self.aggregated_dir = self.reports_dir / "aggregated"
        self.aggregated_dir.mkdir(exist_ok=True)
    
    def list_reports(self) -> List[Dict[str, Any]]:
        """List all generated reports"""
        reports = []
        
        for scan_dir in self.reports_dir.iterdir():
            if scan_dir.is_dir() and scan_dir.name != "aggregated":
                report_files = []
                
                for report_file in scan_dir.iterdir():
                    stat = report_file.stat()
                    report_files.append({
                        "name": report_file.name,
                        "type": report_file.suffix,
                        "size_kb": round(stat.st_size / 1024, 2),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                
                reports.append({
                    "scan_id": scan_dir.name,
                    "path": str(scan_dir),
                    "files": report_files,
                    "created": datetime.fromtimestamp(scan_dir.stat().st_ctime).isoformat()
                })
        
        return sorted(reports, key=lambda x: x["created"], reverse=True)
    
    def get_report(self, scan_id: str, format: str = "html") -> Optional[Path]:
        """Get path to specific report"""
        scan_dir = self.reports_dir / scan_id
        
        if not scan_dir.exists():
            return None
        
        format_map = {
            "html": "report.html",
            "pdf": "report.pdf",
            "json": "report.json",
            "md": "report.md",
            "data": "data.json"
        }
        
        filename = format_map.get(format, f"report.{format}")
        report_path = scan_dir / filename
        
        return report_path if report_path.exists() else None
    
    def delete_report(self, scan_id: str) -> bool:
        """Delete report directory for scan"""
        scan_dir = self.reports_dir / scan_id
        
        if scan_dir.exists():
            try:
                shutil.rmtree(scan_dir)
                logger.info(f"Deleted report: {scan_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete report {scan_id}: {e}")
        
        return False
    
    def cleanup_old_reports(self, max_age_days: int = 30):
        """Remove reports older than specified days"""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        removed = 0
        
        for scan_dir in self.reports_dir.iterdir():
            if scan_dir.is_dir() and scan_dir.name != "aggregated":
                if datetime.fromtimestamp(scan_dir.stat().st_mtime) < cutoff:
                    try:
                        shutil.rmtree(scan_dir)
                        removed += 1
                    except Exception as e:
                        logger.error(f"Failed to remove {scan_dir}: {e}")
        
        if removed:
            logger.info(f"Removed {removed} old reports")
        
        return removed
    
    def archive_reports(self, scan_ids: Optional[List[str]] = None) -> Path:
        """Archive reports to tar.gz"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.reports_dir / f"reports_archive_{timestamp}.tar.gz"
        
        with tarfile.open(archive_path, "w:gz") as tar:
            if scan_ids:
                for scan_id in scan_ids:
                    scan_dir = self.reports_dir / scan_id
                    if scan_dir.exists():
                        tar.add(scan_dir, arcname=scan_id)
            else:
                for scan_dir in self.reports_dir.iterdir():
                    if scan_dir.is_dir() and scan_dir.name != "aggregated":
                        tar.add(scan_dir, arcname=scan_dir.name)
        
        logger.info(f"Archived reports to {archive_path}")
        return archive_path
    
    def get_total_size(self) -> Dict[str, float]:
        """Get storage statistics"""
        def dir_size(path: Path) -> float:
            total = 0
            for item in path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
            return round(total / (1024 * 1024), 2)  # MB
        
        return {
            "total_mb": dir_size(self.reports_dir),
            "report_count": sum(1 for d in self.reports_dir.iterdir() if d.is_dir() and d.name != "aggregated")
        }
    
    def update_aggregated_stats(self):
        """Update aggregated statistics file"""
        reports = self.list_reports()
        
        total_vulns = 0
        severity_totals = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        
        for report in reports:
            data_file = Path(report["path"]) / "data.json"
            if data_file.exists():
                try:
                    with open(data_file) as f:
                        data = json.load(f)
                        stats = data.get("statistics", {})
                        total_vulns += stats.get("total_vulnerabilities", 0)
                        
                        for sev in severity_totals:
                            severity_totals[sev] += stats.get("severity_breakdown", {}).get(sev, 0)
                except Exception:
                    pass
        
        aggregated = {
            "updated_at": datetime.now().isoformat(),
            "total_reports": len(reports),
            "total_vulnerabilities": total_vulns,
            "severity_totals": severity_totals,
            "recent_scans": reports[:10]
        }
        
        stats_file = self.aggregated_dir / "stats.json"
        with open(stats_file, 'w') as f:
            json.dump(aggregated, f, indent=2)
        
        return aggregated
