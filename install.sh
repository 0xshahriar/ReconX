#!/data/data/com.termux/files/usr/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

RECONX_DIR="$HOME/ReconX"
GO_BIN="$HOME/go/bin"

echo -e "${BLUE}=== ReconX Installation ===${NC}"
echo -e "${YELLOW}Optimizing for Termux on Android (ARM64)...${NC}\n"

if [[ $(uname -m) != "aarch64" ]]; then
    echo -e "${YELLOW}Warning: Not running on ARM64.${NC}"
fi

echo -e "${BLUE}[1/7] Updating packages...${NC}"
pkg update -y
pkg upgrade -y

echo -e "${BLUE}[2/7] Installing dependencies...${NC}"
pkg install -y \
    python \
    python-pip \
    git \
    curl \
    wget \
    unzip \
    tar \
    clang \
    make \
    openssl \
    libxml2 \
    libxslt \
    libjpeg-turbo \
    libpng \
    freetype \
    rust \
    golang \
    nmap \
    dnsutils \
    whois \
    jq \
    termux-api

echo -e "${BLUE}[3/7] Setting up directories...${NC}"
termux-setup-storage
mkdir -p $RECONX_DIR/{api,core,web,data,logs,reports,scripts,wordlists,config}
mkdir -p $RECONX_DIR/core/{scanners,monitors}
mkdir -p $RECONX_DIR/web/{css,js,assets}
mkdir -p $RECONX_DIR/web/js/{components,utils}
mkdir -p $RECONX_DIR/wordlists/{subdomains,fuzzing,directories}
mkdir -p $RECONX_DIR/data/state

cd $RECONX_DIR

echo -e "${BLUE}[4/7] Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${BLUE}[5/7] Installing Go tools...${NC}"
export GOPATH=$HOME/go
export PATH=$PATH:$GO_BIN

go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/tomnomnom/assetfinder@latest
go install -v github.com/tomnomnom/gf@latest
go install -v github.com/tomnomnom/waybackurls@latest
go install -v github.com/lc/gau/v2/cmd/gau@latest
go install -v github.com/ffuf/ffuf/v2@latest
go install -v github.com/trufflesecurity/trufflehog@latest
go install -v github.com/zricethezav/gitleaks/v8@latest

echo -e "${BLUE}Installing Amass...${NC}"
wget -q https://github.com/OWASP/Amass/releases/latest/download/amass_linux_arm64.zip -O /tmp/amass.zip
unzip -qo /tmp/amass.zip -d /tmp/
cp /tmp/amass_linux_arm64/amass $PREFIX/bin/ 2>/dev/null || cp /tmp/amass_linux_arm64/amass $GO_BIN/
chmod +x $PREFIX/bin/amass 2>/dev/null || chmod +x $GO_BIN/amass

echo -e "${BLUE}Installing Findomain...${NC}"
wget -q https://github.com/Findomain/Findomain/releases/latest/download/findomain-linux-aarch64 -O $PREFIX/bin/findomain
chmod +x $PREFIX/bin/findomain

echo -e "${BLUE}[6/7] Setting up Ollama...${NC}"
curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null || {
    wget -q https://github.com/ollama/ollama/releases/latest/download/ollama-linux-arm64 -O $PREFIX/bin/ollama
    chmod +x $PREFIX/bin/ollama
}

(ollama pull llama3.1:8b 2>/dev/null || true) &
(ollama pull gemma3:4b 2>/dev/null || true) &

echo -e "${BLUE}[7/7] Downloading wordlists...${NC}"
cd $RECONX_DIR/wordlists

wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt -O subdomains/subdomains-medium.txt || true
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-20000.txt -O subdomains/subdomains-large.txt || true
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/XSS/XSS-Jhaddix.txt -O fuzzing/xss.txt || true
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/SQLi/Generic-SQLi.txt -O fuzzing/sqli.txt || true
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LFI/LFI-Jhaddix.txt -O fuzzing/lfi.txt || true
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/raft-medium-directories.txt -O directories.txt || true
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/raft-medium-files.txt -O files.txt || true

cd $RECONX_DIR

cat > config/settings.py << 'EOF'
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
WORDLISTS_DIR = os.path.join(BASE_DIR, "wordlists")

DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/recon.db"
API_HOST = "0.0.0.0"
API_PORT = 8000

OLLAMA_URL = "http://localhost:11434"
DEFAULT_LLM_MODEL = "llama3.1:8b"
FALLBACK_LLM_MODEL = "gemma3:4b"
EMERGENCY_LLM_MODEL = "gemma3:1b"

LLM_MEMORY_THRESHOLDS = {
    "llama3.1:8b": 6000,
    "gemma3:4b": 3500,
    "gemma3:1b": 1500,
}

LLM_AUTO_SCALE = True
LLM_UNLOAD_IDLE_MINUTES = 5

MAX_CONCURRENT_SCANS = 2
DEFAULT_RATE_LIMIT = 50

RESILIENCE_CHECK_INTERVAL = 10
PAUSE_AFTER_OFFLINE = 30
STATE_SAVE_INTERVAL = 30
RESUME_DELAY = 10
PAUSE_ON_LOW_BATTERY = True
LOW_BATTERY_THRESHOLD = 20
PAUSE_ON_OVERHEAT = True
MAX_TEMPERATURE = 45

TUNNEL_PRIMARY = "cloudflare"
TUNNEL_AUTO_START = True
TUNNEL_REQUIRE_AUTH = True
EOF

cat > start.sh << 'EOFSCRIPT'
#!/data/data/com.termux/files/usr/bin/bash

cd $HOME/ReconX

if pgrep -f "uvicorn api.main:app" > /dev/null; then
    echo "ReconX already running!"
    echo "Local: http://localhost:8000"
    [ -f "$HOME/ReconX/.tunnel_url" ] && echo "Remote: $(cat $HOME/ReconX/.tunnel_url)"
    exit 0
fi

mkdir -p logs data

termux-wake-lock 2>/dev/null || true

if ! pgrep -f "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve > logs/ollama.log 2>&1 &
    sleep 4
fi

echo "Starting ReconX API..."
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 >> logs/api.log 2>&1 &

sleep 3

if [[ "$1" == "--with-tunnel" ]] || [[ "$1" == "-t" ]]; then
    echo "Starting tunnel..."
    touch .tunnel_enabled
    scripts/start_tunnel.sh &
    sleep 8
    [ -f ".tunnel_url" ] && echo "Remote: $(cat .tunnel_url)"
fi

if command -v termux-job-scheduler >/dev/null 2>&1; then
    termux-job-scheduler --cancel-all 2>/dev/null || true
    termux-job-scheduler --job-path scripts/watchdog.sh --period-ms 30000 --persist true 2>/dev/null || true
fi

echo ""
echo "=================================="
echo "ReconX Started!"
echo "=================================="
echo "Local: http://localhost:8000"
[ -f ".tunnel_url" ] && echo "Remote: $(cat .tunnel_url)"
echo "Logs: tail -f logs/api.log"
echo ""

if [[ "$2" != "--daemon" ]]; then
    tail -f logs/api.log
fi
EOFSCRIPT
chmod +x start.sh

cat > stop.sh << 'EOFSCRIPT'
#!/data/data/com.termux/files/usr/bin/bash

echo "Stopping ReconX..."

pkill -f "uvicorn api.main:app" && echo "API stopped" || echo "API not running"
pkill -f "cloudflared" 2>/dev/null && echo "Cloudflare tunnel stopped"
pkill -f "ngrok" 2>/dev/null && echo "Ngrok stopped"
pkill -f "localtunnel" 2>/dev/null && echo "LocalTunnel stopped"

termux-wake-unlock 2>/dev/null || true
termux-job-scheduler --cancel-all 2>/dev/null || true

rm -f .tunnel_url .tunnel_enabled

echo "ReconX stopped."
EOFSCRIPT
chmod +x stop.sh

mkdir -p scripts

cat > scripts/watchdog.sh << 'EOFSCRIPT'
#!/data/data/com.termux/files/usr/bin/bash

STATE_FILE="$HOME/ReconX/.paused_due_to_outage"
API_URL="http://localhost:8000/api"
LOG_FILE="$HOME/ReconX/logs/watchdog.log"

check_internet() {
    ping -c 1 -W 5 1.1.1.1 >/dev/null 2>&1 || ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

BATTERY_LEVEL=$(termux-battery-status 2>/dev/null | jq -r '.percentage // 100' || echo "100")

if check_internet; then
    if [ -f "$STATE_FILE" ]; then
        log "Internet restored - Resuming"
        rm "$STATE_FILE"
        curl -s -X POST "$API_URL/system/resume" -H "Content-Type: application/json" || true
        [ -f "$HOME/ReconX/.tunnel_enabled" ] && $HOME/ReconX/scripts/start_tunnel.sh &
    fi
else
    if [ ! -f "$STATE_FILE" ]; then
        log "Internet lost - Pausing"
        touch "$STATE_FILE"
        curl -s -X POST "$API_URL/system/pause" -H "Content-Type: application/json" -d '{"reason": "network_outage"}' || true
    fi
fi

if [ "$BATTERY_LEVEL" -lt 20 ] && [ ! -f "$HOME/ReconX/.paused_battery" ]; then
    log "Low battery ($BATTERY_LEVEL%) - Pausing"
    touch "$HOME/ReconX/.paused_battery"
    curl -s -X POST "$API_URL/system/pause" -H "Content-Type: application/json" -d '{"reason": "low_battery"}' || true
elif [ "$BATTERY_LEVEL" -gt 25 ] && [ -f "$HOME/ReconX/.paused_battery" ]; then
    log "Battery restored ($BATTERY_LEVEL%) - Resuming"
    rm "$HOME/ReconX/.paused_battery"
    curl -s -X POST "$API_URL/system/resume" -H "Content-Type: application/json" || true
fi
EOFSCRIPT
chmod +x scripts/watchdog.sh

cat > scripts/start_tunnel.sh << 'EOFSCRIPT'
#!/data/data/com.termux/files/usr/bin/bash

API_URL="http://localhost:8000"
TUNNEL_FILE="$HOME/ReconX/.tunnel_url"
LOG_FILE="$HOME/ReconX/logs/tunnel.log"

if command -v cloudflared >/dev/null 2>&1 && [ -f "$HOME/.cloudflared/cert.pem" ]; then
    echo "Starting Cloudflare tunnel..." >> "$LOG_FILE"
    cloudflared tunnel --url http://localhost:8000 > /tmp/cloudflare.log 2>&1 &
    sleep 8
    URL=$(grep -o 'https://.*trycloudflare.com' /tmp/cloudflare.log | head -1)
    
    if [ ! -z "$URL" ]; then
        echo "$URL" > "$TUNNEL_FILE"
        curl -s -X POST "$API_URL/tunnel/status" -H "Content-Type: application/json" -d "{\"active\": true, \"url\": \"$URL\"}" || true
        exit 0
    fi
fi

if command -v ngrok >/dev/null 2>&1; then
    echo "Starting ngrok..." >> "$LOG_FILE"
    ngrok http 8000 --log=stdout > /tmp/ngrok.log 2>&1 &
    sleep 5
    URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | jq -r '.tunnels[0].public_url' 2>/dev/null)
    
    if [ ! -z "$URL" ] && [ "$URL" != "null" ]; then
        echo "$URL" > "$TUNNEL_FILE"
        curl -s -X POST "$API_URL/tunnel/status" -H "Content-Type: application/json" -d "{\"active\": true, \"url\": \"$URL\"}" || true
        exit 0
    fi
fi

if command -v npx >/dev/null 2>&1; then
    echo "Starting LocalTunnel..." >> "$LOG_FILE"
    npx localtunnel --port 8000 > /tmp/lt.log 2>&1 &
    sleep 5
    URL=$(grep -o 'https://[^ ]*' /tmp/lt.log | head -1)
    
    if [ ! -z "$URL" ]; then
        echo "$URL" > "$TUNNEL_FILE"
        curl -s -X POST "$API_URL/tunnel/status" -H "Content-Type: application/json" -d "{\"active\": true, \"url\": \"$URL\"}" || true
        exit 0
    fi
fi

echo "Failed to start tunnel" >> "$LOG_FILE"
EOFSCRIPT
chmod +x scripts/start_tunnel.sh

if [ -d "$HOME/.termux/boot" ]; then
    cat > $HOME/.termux/boot/start-reconx.sh << 'EOFSCRIPT'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
$HOME/ReconX/scripts/watchdog.sh &
EOFSCRIPT
    chmod +x $HOME/.termux/boot/start-reconx.sh
fi

echo -e "\n${GREEN}=== Installation Complete ===${NC}"
echo -e "Start: ${BLUE}./start.sh${NC} or ${BLUE}./start.sh --with-tunnel${NC}"
echo -e "Stop:  ${BLUE}./stop.sh${NC}"
echo -e "\n${GREEN}Happy Hunting!${NC}"
