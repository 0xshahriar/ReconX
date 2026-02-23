"""
ReconX Report Generator
Generates HTML and PDF reports
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from api.database import DatabaseManager

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.template_dir = Path("web/templates")
    
    async def generate_html_report(self, scan_id: str, output_path: str):
        """Generate HTML report for scan"""
        scan = await self.db.get_scan(scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")
        
        subdomains = await self.db.get_subdomains(scan_id)
        vulnerabilities = await self.db.get_vulnerabilities(scan_id)
        
        html_content = self._build_html(scan, subdomains, vulnerabilities)
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {output_path}")
        return output_path
    
    def _build_html(self, scan: Dict, subdomains: List[Dict], 
                    vulnerabilities: List[Dict]) -> str:
        """Build HTML report content"""
        vuln_by_severity = self._group_by_severity(vulnerabilities)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ReconX Report - {scan.get('name', 'Untitled')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #1a1a1a; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-box {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #4CAF50; }}
        .stat-label {{ color: #666; font-size: 0.9em; }}
        .severity-critical {{ color: #d32f2f; }}
        .severity-high {{ color: #f57c00; }}
        .severity-medium {{ color: #fbc02d; }}
        .severity-low {{ color: #388e3c; }}
        .severity-info {{ color: #1976d2; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        tr:hover {{ background: #f9f9f9; }}
        .vuln-card {{ border-left: 4px solid #ddd; padding: 15px; margin: 10px 0; background: #fafafa; }}
        .vuln-critical {{ border-left-color: #d32f2f; }}
        .vuln-high {{ border-left-color: #f57c00; }}
        .vuln-medium {{ border-left-color: #fbc02d; }}
        .vuln-low {{ border-left-color: #388e3c; }}
        .vuln-info {{ border-left-color: #1976d2; }}
        .timestamp {{ color: #999; font-size: 0.9em; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 6px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 ReconX Security Assessment Report</h1>
        <p class="timestamp">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        
        <h2>Executive Summary</h2>
        <div class="summary">
            <div class="stat-box">
                <div class="stat-number severity-critical">{len(vuln_by_severity.get('critical', []))}</div>
                <div class="stat-label">Critical</div>
            </div>
            <div class="stat-box">
                <div class="stat-number severity-high">{len(vuln_by_severity.get('high', []))}</div>
                <div class="stat-label">High</div>
            </div>
            <div class="stat-box">
                <div class="stat-number severity-medium">{len(vuln_by_severity.get('medium', []))}</div>
                <div class="stat-label">Medium</div>
            </div>
            <div class="stat-box">
                <div class="stat-number severity-low">{len(vuln_by_severity.get('low', []))}</div>
                <div class="stat-label">Low</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{len(subdomains)}</div>
                <div class="stat-label">Subdomains</div>
            </div>
        </div>
        
        <h2>Scan Information</h2>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Scan ID</td><td><code>{scan.get('id')}</code></td></tr>
            <tr><td>Target ID</td><td><code>{scan.get('target_id')}</code></td></tr>
            <tr><td>Profile</td><td>{scan.get('profile', 'normal')}</td></tr>
            <tr><td>Started</td><td>{scan.get('started_at') or 'N/A'}</td></tr>
            <tr><td>Completed</td><td>{scan.get('completed_at') or 'N/A'}</td></tr>
            <tr><td>Status</td><td>{scan.get('status')}</td></tr>
        </table>
        
        <h2>Vulnerability Details</h2>
"""
        
        # Add vulnerability cards
        for severity in ['critical', 'high', 'medium', 'low', 'info']:
            for vuln in vuln_by_severity.get(severity, []):
                html += self._vuln_to_html(vuln)
        
        # Add subdomains table
        html += f"""
        <h2>Discovered Subdomains ({len(subdomains)})</h2>
        <table>
            <tr>
                <th>Subdomain</th>
                <th>IP</th>
                <th>Status</th>
                <th>Technology</th>
            </tr>
"""
        
        for sub in subdomains[:100]:  # Limit to first 100
            ips = json.loads(sub.get('ip_addresses', '[]')) if isinstance(sub.get('ip_addresses'), str) else sub.get('ip_addresses', [])
            tech = json.loads(sub.get('tech_stack', '[]')) if isinstance(sub.get('tech_stack'), str) else sub.get('tech_stack', [])
            
            html += f"""
            <tr>
                <td><code>{sub.get('subdomain')}</code></td>
                <td>{', '.join(ips[:3])}</td>
                <td>{sub.get('status_code') or 'N/A'}</td>
                <td>{', '.join(tech[:3])}</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
</body>
</html>
"""
        return html
    
    def _vuln_to_html(self, vuln: Dict) -> str:
        """Convert vulnerability to HTML card"""
        severity = vuln.get('severity', 'info')
        title = vuln.get('title', 'Untitled')
        description = vuln.get('description', 'No description available')
        affected = vuln.get('affected_url', 'N/A')
        
        return f"""
        <div class="vuln-card vuln-{severity}">
            <h3 class="severity-{severity}">[{severity.upper()}] {title}</h3>
            <p><strong>Affected URL:</strong> <code>{affected}</code></p>
            <p>{description}</p>
            {f'<pre>{vuln.get("evidence")}</pre>' if vuln.get('evidence') else ''}
        </div>
"""
    
    def _group_by_severity(self, vulnerabilities: List[Dict]) -> Dict[str, List[Dict]]:
        """Group vulnerabilities by severity"""
        groups = {'critical': [], 'high': [], 'medium': [], 'low': [], 'info': []}
        for vuln in vulnerabilities:
            sev = vuln.get('severity', 'info')
            if sev in groups:
                groups[sev].append(vuln)
        return groups
    
    async def generate_json_report(self, scan_id: str, output_path: str):
        """Generate JSON report"""
        scan = await self.db.get_scan(scan_id)
        subdomains = await self.db.get_subdomains(scan_id)
        vulnerabilities = await self.db.get_vulnerabilities(scan_id)
        
        report = {
            "scan_info": scan,
            "subdomains": subdomains,
            "vulnerabilities": vulnerabilities,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return output_path
