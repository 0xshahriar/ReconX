# ReconX

Mobile-first bug bounty reconnaissance platform for Termux on Android.

## Hardware Requirements

| Component    | Specification                              |
| ------------ | ------------------------------------------ |
| RAM          | 16GB (8GB physical + 8GB extended/virtual) |
| Storage      | 256GB total, 10GB+ available               |
| CPU          | MediaTek Helio G88, Octa-core Max 2.00GHz  |
| Architecture | ARM64                                      |
| OS           | Android 14                                 |

## Installation

```bash
curl -sSL https://raw.githubusercontent.com/0xshahriar/reconx/main/install.sh | bash
```

Or manual:

```bash
git clone https://github.com/0xshahriar/reconx.git
cd reconx
chmod +x install.sh
./install.sh
```

Quick Start

```bash
# Start locally
./start.sh

# Start with remote tunnel
./start.sh --with-tunnel

# View logs
tail -f logs/api.log

# Stop
./stop.sh
```

Features

- Mobile Optimized: Touch-friendly interface for Android
- Offline LLM: Local analysis with llama3.1:8b/gemma3:4b/gemma3:1b auto-scaling
- Power Resilience: Auto-pause/resume on power/internet loss
- Remote Access: Free tunneling via Cloudflare/Ngrok/LocalTunnel
- 16GB Optimized: Memory-aware operation for Helio G88

File Structure

```
ReconX/
├── api/              # FastAPI backend
├── core/             # Scanner modules
├── web/              # Frontend (vanilla JS)
│   ├── css/
│   ├── js/
│   └── index.html
├── data/             # SQLite database
├── logs/             # Application logs
├── wordlists/        # SecLists integration
├── scripts/          # Helper scripts
├── install.sh        # Installation script
├── start.sh          # Startup script
├── stop.sh           # Shutdown script
└── requirements.txt  # Python dependencies
```

Configuration

Edit `config/settings.py`:

- `LLM_MEMORY_THRESHOLDS`: RAM thresholds for model switching
- `TUNNEL_PRIMARY`: Preferred tunnel service
- `LOW_BATTERY_THRESHOLD`: Battery protection level
- `MAX_CONCURRENT_SCANS`: Parallel scan limit

API Endpoints

Method	Endpoint	Description	
GET	/```markdown
# ReconX

Mobile-first bug bounty reconnaissance platform for Termux on Android.

## Hardware Requirements

| Component    | Specification                              |
| ------------ | ------------------------------------------ |
| RAM          | 16GB (8GB physical + 8GB extended/virtual) |
| Storage      | 256GB total, 10GB+ available               |
| CPU          | MediaTek Helio G88, Octa-core Max 2.00GHz  |
| Architecture | ARM64                                      |
| OS           | Android 14                                 |

## Installation

```bash
curl -sSL https://raw.githubusercontent.com/0xshahriar/reconx/main/install.sh | bash
```

Or manual:

```bash
git clone https://github.com/0xshahriar/reconx.git
cd reconx
chmod +x install.sh
./install.sh
```

Quick Start

```bash
# Start locally
./start.sh

# Start with remote tunnel
./start.sh --with-tunnel

# View logs
tail -f logs/api.log

# Stop
./stop.sh
```

Features

- Mobile Optimized: Touch-friendly interface for Android
- Offline LLM: Local analysis with llama3.1:8b/gemma3:4b/gemma3:1b auto-scaling
- Power Resilience: Auto-pause/resume on power/internet loss
- Remote Access: Free tunneling via Cloudflare/Ngrok/LocalTunnel
- 16GB Optimized: Memory-aware operation for Helio G88

File Structure

```
ReconX/
├── api/              # FastAPI backend
├── core/             # Scanner modules
├── web/              # Frontend (vanilla JS)
│   ├── css/
│   ├── js/
│   └── index.html
├── data/             # SQLite database
├── logs/             # Application logs
├── wordlists/        # SecLists integration
├── scripts/          # Helper scripts
├── install.sh        # Installation script
├── start.sh          # Startup script
├── stop.sh           # Shutdown script
└── requirements.txt  # Python dependencies
```

Configuration

Edit `config/settings.py`:

- `LLM_MEMORY_THRESHOLDS`: RAM thresholds for model switching
- `TUNNEL_PRIMARY`: Preferred tunnel service
- `LOW_BATTERY_THRESHOLD`: Battery protection level
- `MAX_CONCURRENT_SCANS`: Parallel scan limit

API Endpoints

Method	Endpoint	Description	
GET	`/api/targets`	List targets	
POST	`/api/targets`	Create target	
GET	`/api/scans`	List scans	
POST	`/api/scans`	Start scan	
POST	`/api/scans/{id}/pause`	Pause scan	
POST	`/api/scans/{id}/resume`	Resume scan	
GET	`/api/system/status`	System stats	
WS	`/ws/system`	Real-time updates	

LLM Auto-Scaling

Model	RAM Required	Use Case	
`llama3.1:8b`	6GB	Deep analysis (idle)	
`gemma3:4b`	3.5GB	Balanced (scanning)	
`gemma3:1b`	1.5GB	Emergency (low memory)	

Resilience

- State saved every 30 seconds to SQLite
- Automatic pause on internet loss (30s detection)
- Automatic resume on reconnection (10s stability check)
- Battery protection (< 20% pauses scans)
- Thermal protection (> 45C pauses scans)

Security

- Password-protected dashboard when tunneled
- Input validation and path traversal prevention
- Parameterized command execution (no injection)

License

```
MIT License

```