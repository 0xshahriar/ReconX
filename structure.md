```
ReconX/
├── app.py                      # Main entry point. Starts the FastAPI server & scheduler.
├── requirements.txt            # Python dependencies (fastapi, uvicorn, requests, etc.).
├── install.sh                  # Automation script to install deps (golang, python, tools).
├── README.md                   # Documentation.
│
├── core/                       # The "Brain" of the framework.
│   ├── __init__.py
│   ├── config.py               # Manages API keys, settings, scope, and env variables.
│   ├── database.py             # SQLite handler (targets, results, state, caching).
│   ├── orchestrator.py         # Manages scan queues, resume logic, and tool health.
│   ├── executor.py             # Runs system commands (subprocess wrapper) safely.
│   ├── notification.py         # Discord/Telegram/Slack webhook handlers.
│   ├── llm_integration.py      # Handles Google AI API calls for analysis.
│   └── utils.py                # Helpers (IP rotation, rate limiting, file utils).
│
├── modules/                    # The "Muscle" (Specific automation tasks).
│   ├── __init__.py
│   ├── recon.py                # Subdomains, ASN, Cert Transparency.
│   ├── host_analysis.py        # Live hosts, Ports, Takeover, WAF/CDN detection.
│   ├── content_discovery.py    # Fuzzing, URL Discovery, Wayback intelligence.
│   ├── vulnerability.py        # Nuclei, GF Patterns, Secret Detection.
│   ├── osint.py                # Git recon, Cloud recon, Shodan integration.
│   └── reporting.py            # CVSS scoring, POC generation, Report creation.
│
├── dashboard/                  # The "Face" (Frontend).
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css       # Minimalistic, modern, responsive styling.
│   │   ├── js/
│   │   │   ├── app.js          # Main logic, WebSocket connection.
│   │   │   ├── charts.js       # Chart.js configuration for graphs.
│   │   │   └── ui_controller.js# Handles modals, buttons, and progress bars.
│   │   └── img/
│   │       └── reconx_logo.png # ReconX Logo.
│   └── templates/
│       ├── index.html          # Main dashboard layout.
│       ├── target_view.html    # Detailed view for a specific target.
│       └── settings.html       # Configuration page.
│
├── data/                       # Dynamic Data Storage.
│   ├── workspace/              # Organized output folders per target.
│   │   └── example.com/        # (subdomains.txt, nuclei_results.json, etc.)
│   ├── wordlists/              # Auto-downloaded wordlists (chunked).
│   ├── cache/                  # Local cache layer (API responses, tool checks).
│   └── reports/                # Generated PDF/HTML reports.
│
├── logs/                       # System & Scan Logs.
│   ├── system.log              # General framework logs.
│   └── scan_errors.log         # Error logs for debugging.
│
└── tests/                      # (Optional) Simple tests to verify installation.
    └── test_installation.py
```