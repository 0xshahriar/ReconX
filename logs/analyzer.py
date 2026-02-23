"""
ReconX Log Analyzer
Analyze logs for errors, patterns, and statistics
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class LogAnalyzer:
    """Analyze log files"""
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
    
    def analyze_errors(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze error patterns in logs"""
        cutoff = datetime.now().timestamp() - (hours * 3600)
        
        errors = []
        error_pattern = re.compile(r'ERROR.*?:\s*(.+)')
        
        # Check error log
        error_log = self.logs_dir / "errors" / "error.log"
        if error_log.exists():
            with open(error_log, 'r') as f:
                for line in f:
                    # Check timestamp if available
                    if '[' in line:
                        try:
                            timestamp_str = line[1:line.index(']')]
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            if log_time.timestamp() < cutoff:
                                continue
                        except:
                            pass
                    
                    match = error_pattern.search(line)
                    if match:
                        errors.append(match.group(1))
        
        # Count patterns
        error_counts = Counter(errors)
        
        return {
            "total_errors": len(errors),
            "unique_errors": len(error_counts),
            "top_errors": error_counts.most_common(10),
            "time_range_hours": hours
        }
    
    def get_scan_statistics(self, scan_id: str) -> Dict[str, Any]:
        """Get statistics from scan log"""
        log_file = self.logs_dir / "scans" / f"{scan_id}.log"
        
        if not log_file.exists():
            return {"error": "Log file not found"}
        
        stats = {
            "modules_run": set(),
            "tools_executed": [],
            "errors": 0,
            "warnings": 0,
            "findings": 0
        }
        
        module_pattern = re.compile(r'Running module:\s*(\w+)')
        tool_pattern = re.compile(r'Executing:\s*(.+)')
        error_pattern = re.compile(r'ERROR')
        warning_pattern = re.compile(r'WARNING')
        finding_pattern = re.compile(r'Found|Discovered|Detected')
        
        with open(log_file, 'r') as f:
            for line in f:
                # Modules
                match = module_pattern.search(line)
                if match:
                    stats["modules_run"].add(match.group(1))
                
                # Tools
                match = tool_pattern.search(line)
                if match:
                    stats["tools_executed"].append(match.group(1).strip())
                
                # Errors/Warnings
                if error_pattern.search(line):
                    stats["errors"] += 1
                if warning_pattern.search(line):
                    stats["warnings"] += 1
                
                # Findings
                if finding_pattern.search(line):
                    stats["findings"] += 1
        
        stats["modules_run"] = list(stats["modules_run"])
        stats["tools_executed"] = list(set(stats["tools_executed"]))
        
        return stats
    
    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive log report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "error_analysis": self.analyze_errors(hours=168),  # 7 days
            "log_sizes": self._get_log_sizes(),
            "recent_scans": self._get_recent_scans()
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
        
        return report
    
    def _get_log_sizes(self) -> Dict[str, float]:
        """Get sizes of all log files"""
        sizes = {}
        
        for log_file in self.logs_dir.rglob("*.log"):
            rel_path = str(log_file.relative_to(self.logs_dir))
            sizes[rel_path] = round(log_file.stat().st_size / 1024, 2)  # KB
        
        return sizes
    
    def _get_recent_scans(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently active scans from logs"""
        scan_logs = sorted(
            self.logs_dir.glob("scans/*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]
        
        scans = []
        for log_file in scan_logs:
            stat = log_file.stat()
            scans.append({
                "scan_id": log_file.stem,
                "size_kb": round(stat.st_size / 1024, 2),
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "statistics": self.get_scan_statistics(log_file.stem)
            })
        
        return scans
