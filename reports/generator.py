"""
ReconX Report Generator
Generate HTML, PDF, JSON, and Markdown reports
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from api.database import DatabaseManager
from api.utils.cvss_calculator import CVSSCalculator

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate security assessment reports"""
    
    def __init__(self, db: DatabaseManager, reports_dir: str = "reports"):
        self.db = db
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.cvss_calc = CVSSCalculator()
    
    async def generate_html_report(self, scan_id: str, 
                                    template: str = "default") -> Path:
        """Generate HTML report"""
        scan = await self.db.get_scan(scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")
        
        target = await self.db.get_target(scan["target_id"])
        
        # Gather data
        data = await self._gather_report_data(scan_id)
        
        # Create report directory
        report_dir = self.reports_dir / scan_id
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate HTML
        html_content = self._render_html(scan, target, data, template)
        
        # Save
        report_path = report_dir / "report.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Save JSON data
        json_path = report_dir / "data.json"
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"HTML report generated: {report_path}")
        return report_path
    
    async def generate_pdf_report(self, scan_id: str) -> Optional[Path]:
        """Generate PDF report from HTML"""
        try:
            import pdfkit
            
            html_path = await self.generate_html_report(scan_id)
            pdf_path = html_path.parent / "report.pdf"
            
            pdfkit.from_file(str(html_path), str(pdf_path))
            
            logger.info(f"PDF report generated: {pdf_path}")
            return pdf_path
            
        except ImportError:
            logger.error("pdfkit not installed, cannot generate PDF")
            return None
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return None
    
    async def generate_json_report(self, scan_id: str) -> Path:
        """Generate raw JSON report"""
        data = await self._gather_report_data(scan_id)
        
        report_dir = self.reports_dir / scan_id
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = report_dir / "report.json"
        with open(report_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return report_path
    
    async def generate_markdown_report(self, scan_id: str) -> Path:
        """Generate Markdown report"""
        scan = await self.db.get_scan(scan_id)
        data = await self._gather_report_data(scan_id)
        
        report_dir = self.reports_dir / scan_id
        report_dir.mkdir(parents=True, exist_ok=True)
        
        md_content = self._render_markdown(scan, data)
        
        report_path = report_dir / "report.md"
        with open(report_path, 'w') as f:
            f.write(md_content)
        
        return report_path
    
    async def _gather_report_data(self, scan_id: str) -> Dict[str, Any]:
        """Gather all data for report"""
        return {
            "scan_info": await self.db.get_scan(scan_id),
            "subdomains": await self.db.get_subdomains(scan_id),
            "endpoints": await self._get_endpoints(scan_id),
            "vulnerabilities": await self.db.get_vulnerabilities(scan_id),
            "ports": await self._get_ports(scan_id),
            "statistics": await self._calculate_statistics(scan_id),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def _get_endpoints(self, scan_id: str) -> List[Dict]:
        """Get endpoints for scan"""
        async with self.db._connection.execute(
            "SELECT * FROM endpoints WHERE scan_id = ? ORDER BY url",
            (scan_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def _get_ports(self, scan_id: str) -> List[Dict]:
        """Get ports for scan"""
        async with self.db._connection.execute(
            "SELECT * FROM ports WHERE scan_id = ? ORDER BY ip, port",
            (scan_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def _calculate_statistics(self, scan_id: str) -> Dict[str, Any]:
        """Calculate scan statistics"""
        vulns = await self.db.get_vulnerabilities(scan_id)
        
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for v in vulns:
            sev = v.get("severity", "info")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        subdomains = await self.db.get_subdomains(scan_id)
        live_count = sum(1 for s in subdomains if s.get("is_live"))
        
        return {
            "total_subdomains": len(subdomains),
            "live_hosts": live_count,
            "total_vulnerabilities": len(vulns),
            "severity_breakdown": severity_counts,
            "false_positives": sum(1 for v in vulns if v.get("false_positive"))
        }
    
    def _render_html(self, scan: Dict, target: Dict, data: Dict, 
                     template: str) -> str:
        """Render HTML report"""
        stats = data["statistics"]
        vulns = data["vulnerabilities"]
        
        # Group vulnerabilities by severity
        vuln_by_severity = {"critical": [], "high": [], "medium": [], "low": [], "info": []}
        for v in vulns:
            if not v.get("false_positive"):
                sev = v.get("severity", "info")
                vuln_by_severity[sev].append(v)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Assessment Report - {target.get("primary_domain", "Unknown")}</title>
    <style>
        :root {{
            --color-critical: #dc2626;
            --color-high: #ea580c;
            --color-medium: #ca8a04;
            --color-low: #16a34a;
            --color-info: #2563eb;
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        header {{
            border-bottom: 2px solid var(--color-high);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }}
        
        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            text-transform: uppercase;
        }}
        
        .severity-critical {{ color: var(--color-critical); }}
        .severity-high {{ color: var(--color-high); }}
        .severity-medium {{ color: var(--color-medium); }}
        .severity-low {{ color: var(--color-low); }}
        .severity-info {{ color: var(--color-info); }}
        
        .section {{
            background: var(--bg-card);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        
        .section h2 {{
            border-bottom: 1px solid var(--bg-dark);
            padding-bottom: 0.75rem;
            margin-bottom: 1rem;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th, td {{
            text-align: left;
            padding: 0.75rem;
            border-bottom: 1px solid var(--bg-dark);
        }}
        
        th {{
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
        }}
        
        .vuln-card {{
            border-left: 4px solid;
            padding: 1rem;
            margin-bottom: 1rem;
            background: rgba(30, 41, 59, 0.5);
        }}
        
        .vuln-critical {{ border-left-color: var(--color-critical); }}
        .vuln-high {{ border-left-color: var(--color-high); }}
        .vuln-medium {{ border-left-color: var(--color-medium); }}
        .vuln-low {{ border-left-color: var(--color-low); }}
        .vuln-info {{ border-left-color: var(--color-info); }}
        
        .vuln-title {{
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        
        .vuln-meta {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
        }}
        
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .badge-critical {{ background: var(--color-critical); color: white; }}
        .badge-high {{ background: var(--color-high); color: white; }}
        .badge-medium {{ background: var(--color-medium); color: black; }}
        .badge-low {{ background: var(--color-low); color: white; }}
        .badge-info {{ background: var(--color-info); color: white; }}
        
        pre {{
            background: var(--bg-dark);
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
        }}
        
        .footer {{
            text-align: center;
            color: var(--text-secondary);
            padding: 2rem;
            border-top: 1px solid var(--bg-card);
            margin-top: 2rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Security Assessment Report</h1>
            <p class="subtitle">
                Target: <strong>{target.get("primary_domain", "Unknown")}</strong> | 
                Scan ID: <code>{scan.get("id", "N/A")}</code> | 
                Generated: {data.get("generated_at", "Unknown")}
            </p>
        </header>
        
        <div class="summary-grid">
            <div class="stat-card">
                <div class="stat-number severity-critical">{stats["severity_breakdown"]["critical"]}</div>
                <div class="stat-label">Critical</div>
            </div>
            <div class="stat-card">
                <div class="stat-number severity-high">{stats["severity_breakdown"]["high"]}</div>
                <div class="stat-label">High</div>
            </div>
            <div class="stat-card">
                <div class="stat-number severity-medium">{stats["severity_breakdown"]["medium"]}</div>
                <div class="stat-label">Medium</div>
            </div>
            <div class="stat-card">
                <div class="stat-number severity-low">{stats["severity_breakdown"]["low"]}</div>
                <div class="stat-label">Low</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats["total_subdomains"]}</div>
                <div class="stat-label">Subdomains</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🎯 Executive Summary</h2>
            <p>This security assessment identified <strong>{stats["total_vulnerabilities"]} vulnerabilities</strong> 
            across <strong>{stats["total_subdomains"]} subdomains</strong>. 
            Of these, <strong class="severity-critical">{stats["severity_breakdown"]["critical"]} are critical</strong> 
            and <strong class="severity-high">{stats["severity_breakdown"]["high"]} are high severity</strong>.</p>
        </div>
        
        <div class="section">
            <h2>🚨 Vulnerability Details</h2>
"""
        
        # Add vulnerability cards by severity
        for severity in ["critical", "high", "medium", "low", "info"]:
            for vuln in vuln_by_severity.get(severity, []):
                html += self._render_vuln_card(vuln)
        
        html += f"""
        </div>
        
        <div class="section">
            <h2>🌐 Discovered Assets</h2>
            <table>
                <tr>
                    <th>Subdomain</th>
                    <th>Status</th>
                    <th>Technology</th>
                    <th>IP</th>
                </tr>
"""
        
        for sub in data["subdomains"][:50]:
            ips = json.loads(sub.get("ip_addresses", "[]")) if isinstance(sub.get("ip_addresses"), str) else sub.get("ip_addresses", [])
            tech = json.loads(sub.get("tech_stack", "[]")) if isinstance(sub.get("tech_stack"), str) else sub.get("tech_stack", [])
            
            html += f"""
                <tr>
                    <td><code>{sub.get("subdomain", "N/A")}</code></td>
                    <td>{sub.get("status_code", "N/A")}</td>
                    <td>{", ".join(tech[:3])}</td>
                    <td>{", ".join(ips[:2])}</td>
                </tr>
"""
        
        html += """
            </table>
        </div>
        
        <div class="footer">
            <p>Generated by ReconX - Mobile Bug Bounty Platform</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def _render_vuln_card(self, vuln: Dict) -> str:
        """Render single vulnerability card"""
        severity = vuln.get("severity", "info")
        title = vuln.get("title", "Unknown")
        url = vuln.get("affected_url", "N/A")
        description = vuln.get("description", "")
        
        return f"""
        <div class="vuln-card vuln-{severity}">
            <div class="vuln-title">
                <span class="badge badge-{severity}">{severity.upper()}</span>
                {title}
            </div>
            <div class="vuln-meta">
                <strong>URL:</strong> <code>{url}</code>
                {f' | <strong>Parameter:</strong> {vuln.get("parameter")}' if vuln.get("parameter") else ''}
            </div>
            <p>{description}</p>
            {f'<pre>{vuln.get("evidence")[:500]}</pre>' if vuln.get("evidence") else ''}
        </div>
"""
    
    def _render_markdown(self, scan: Dict, data: Dict) -> str:
        """Render Markdown report"""
        stats = data["statistics"]
        
        md = f"""# Security Assessment Report

## Target Information
- **Target:** {scan.get("target_id", "Unknown")}
- **Scan ID:** {scan.get("id", "Unknown")}
- **Generated:** {data.get("generated_at", "Unknown")}

## Executive Summary

| Severity | Count |
|----------|-------|
| Critical | {stats["severity_breakdown"]["critical"]} |
| High | {stats["severity_breakdown"]["high"]} |
| Medium | {stats["severity_breakdown"]["medium"]} |
| Low | {stats["severity_breakdown"]["low"]} |
| Info | {stats["severity_breakdown"]["info"]} |

**Total Vulnerabilities:** {stats["total_vulnerabilities"]}
**Total Subdomains:** {stats["total_subdomains"]}
**Live Hosts:** {stats["live_hosts"]}

## Vulnerabilities

"""
        
        for vuln in data["vulnerabilities"]:
            if not vuln.get("false_positive"):
                md += f"""### [{vuln.get("severity", "info").upper()}] {vuln.get("title", "Unknown")}

- **URL:** {vuln.get("affected_url", "N/A")}
- **Severity:** {vuln.get("severity", "info")}
- **Tool:** {vuln.get("tool_source", "Unknown")}

{vuln.get("description", "")}

"""
        
        return md
