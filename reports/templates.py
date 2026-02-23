"""
ReconX Report Templates
HTML/CSS templates for different report styles
"""

from typing import Dict

class ReportTemplates:
    """Predefined report templates"""
    
    TEMPLATES: Dict[str, Dict[str, str]] = {
        "default": {
            "name": "Default Dark",
            "description": "Modern dark theme with severity colors",
            "css": "default.css"
        },
        "light": {
            "name": "Light Corporate",
            "description": "Professional light theme for executives",
            "css": "light.css"
        },
        "hackerone": {
            "name": "HackerOne Style",
            "description": "HackerOne-compatible format",
            "css": "hackerone.css"
        },
        "bugcrowd": {
            "name": "Bugcrowd Style", 
            "description": "Bugcrowd-compatible format",
            "css": "bugcrowd.css"
        }
    }
    
    @classmethod
    def list_templates(cls) -> Dict[str, Dict[str, str]]:
        """List available templates"""
        return cls.TEMPLATES
    
    @classmethod
    def get_template(cls, name: str) -> Dict[str, str]:
        """Get template by name"""
        return cls.TEMPLATES.get(name, cls.TEMPLATES["default"])
    
    @classmethod
    def get_css(cls, template_name: str) -> str:
        """Get CSS for template"""
        templates = {
            "default": """
                :root {
                    --bg-primary: #0f172a;
                    --bg-secondary: #1e293b;
                    --text-primary: #f8fafc;
                    --text-secondary: #94a3b8;
                    --critical: #dc2626;
                    --high: #ea580c;
                    --medium: #ca8a04;
                    --low: #16a34a;
                    --info: #2563eb;
                }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: var(--bg-primary);
                    color: var(--text-primary);
                    line-height: 1.6;
                }
            """,
            "light": """
                :root {
                    --bg-primary: #ffffff;
                    --bg-secondary: #f1f5f9;
                    --text-primary: #0f172a;
                    --text-secondary: #64748b;
                    --critical: #dc2626;
                    --high: #ea580c;
                    --medium: #ca8a04;
                    --low: #16a34a;
                    --info: #2563eb;
                }
                body {
                    font-family: Georgia, serif;
                    background: var(--bg-primary);
                    color: var(--text-primary);
                    line-height: 1.6;
                }
            """
        }
        
        return templates.get(template_name, templates["default"])
