#!/data/data/com.termux/files/usr/bin/bash
# ReconX Tool Installer
# Automated installation of all security tools

set -e

RECONX_DIR="$HOME/ReconX"
LOG_FILE="$RECONX_DIR/logs/tools_install.log"
GO_BIN="$HOME/go/bin"
PREFIX="/data/data/com.termux/files/usr"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
mkdir -p "$(dirname "$LOG_FILE")"
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Progress tracking
TOTAL_STEPS=8
CURRENT_STEP=0

progress() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    log ""
    log "${BLUE}[$CURRENT_STEP/$TOTAL_STEPS]${NC} $1"
}

# Error handling
error_exit() {
    log "${RED}✗ Error: $1${NC}"
    log "Check log: $LOG_FILE"
    exit 1
}

# Success message
success() {
    log "${GREEN}✓${NC} $1"
}

# Warning message
warn() {
    log "${YELLOW}⚠${NC} $1"
}

echo ""
echo "🔧 ReconX Tool Installer"
echo "========================"
echo ""
echo "This will install all required security tools."
echo "Estimated time: 15-30 minutes depending on network."
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Installation cancelled."
    exit 0
fi

# Step 1: Update packages
progress "Updating Termux packages..."
pkg update -y >> "$LOG_FILE" 2>&1 || error_exit "Failed to update packages"
pkg upgrade -y >> "$LOG_FILE" 2>&1 || warn "Some packages failed to upgrade"
success "Packages updated"

# Step 2: Install dependencies
progress "Installing base dependencies..."

DEPS="git curl wget python python-pip golang nodejs-lts make clang pkg-config openssl-tool libffi rust"

for dep in $DEPS; do
    echo "  Installing $dep..."
    pkg install -y "$dep" >> "$LOG_FILE" 2>&1 || warn "Failed to install $dep"
done

success "Dependencies installed"

# Step 3: Setup Go environment
progress "Setting up Go environment..."

export GOPATH="$HOME/go"
export PATH="$PATH:$GOPATH/bin"

mkdir -p "$GOPATH/bin"

# Add to .bashrc if not present
if ! grep -q "GOPATH" "$HOME/.bashrc"; then
    echo 'export GOPATH="$HOME/go"' >> "$HOME/.bashrc"
    echo 'export PATH="$PATH:$GOPATH/bin"' >> "$HOME/.bashrc"
    success "Go environment added to .bashrc"
fi

success "Go ready: $(go version)"

# Step 4: Install Go tools
progress "Installing Go-based security tools..."

GO_TOOLS=(
    "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
    "github.com/projectdiscovery/httpx/cmd/httpx@latest"
    "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"
    "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
    "github.com/projectdiscovery/dnsx/cmd/dnsx@latest"
    "github.com/projectdiscovery/asnmap/cmd/asnmap@latest"
    "github.com/projectdiscovery/tlsx/cmd/tlsx@latest"
    "github.com/owasp-amass/amass/v4/...@master"
    "github.com/tomnomnom/assetfinder@latest"
    "github.com/tomnomnom/waybackurls@latest"
    "github.com/tomnomnom/gf@latest"
    "github.com/tomnomnom/anew@latest"
    "github.com/tomnomnom/unfurl@latest"
    "github.com/tomnomnom/qsreplace@latest"
    "github.com/lc/gau/v2/cmd/gau@latest"
    "github.com/ffuf/ffuf@latest"
    "github.com/jaeles-project/gospider@latest"
    "github.com/trufflesecurity/trufflehog@latest"
    "github.com/gitleaks/gitleaks@latest"
)

for tool in "${GO_TOOLS[@]}"; do
    tool_name=$(echo "$tool" | cut -d'/' -f5 | cut -d'@' -f1)
    echo "  Installing $tool_name..."
    
    if go install -v "$tool" >> "$LOG_FILE" 2>&1; then
        success "$tool_name installed"
    else
        warn "Failed to install $tool_name"
    fi
done

# Step 5: Install Python tools
progress "Installing Python-based tools..."

PIP_TOOLS="requests aiohttp beautifulsoup4 lxml urllib3 selenium sqlmap git-dumper"

for tool in $PIP_TOOLS; do
    echo "  Installing $tool..."
    pip install "$tool" --quiet >> "$LOG_FILE" 2>&1 || warn "Failed to install $tool"
done

success "Python tools installed"

# Step 6: Install additional tools
progress "Installing additional tools..."

# Findomain
if ! command -v findomain &> /dev/null; then
    echo "  Installing findomain..."
    curl -LO https://github.com/Findomain/Findomain/releases/latest/download/findomain-linux.zip >> "$LOG_FILE" 2>&1
    unzip -o findomain-linux.zip -d "$PREFIX/bin/" >> "$LOG_FILE" 2>&1
    chmod +x "$PREFIX/bin/findomain"
    rm -f findomain-linux.zip
    success "findomain installed"
fi

# Massdns
if ! command -v massdns &> /dev/null; then
    echo "  Installing massdns..."
    git clone https://github.com/blechschmidt/massdns.git /tmp/massdns >> "$LOG_FILE" 2>&1
    cd /tmp/massdns
    make >> "$LOG_FILE" 2>&1
    cp bin/massdns "$PREFIX/bin/"
    cd -
    rm -rf /tmp/massdns
    success "massdns installed"
fi

# Nmap
if ! command -v nmap &> /dev/null; then
    echo "  Installing nmap..."
    pkg install nmap -y >> "$LOG_FILE" 2>&1 || warn "nmap installation failed"
fi

# Cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "  Installing cloudflared..."
    pkg install cloudflared -y >> "$LOG_FILE" 2>&1 || {
        # Fallback download
        curl -L --output "$PREFIX/bin/cloudflared" \
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" >> "$LOG_FILE" 2>&1
        chmod +x "$PREFIX/bin/cloudflared"
    }
    success "cloudflared installed"
fi

# Ngrok
if ! command -v ngrok &> /dev/null; then
    echo "  Installing ngrok..."
    pkg install ngrok -y >> "$LOG_FILE" 2>&1 || {
        curl -L --output ngrok.zip \
            "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.zip" >> "$LOG_FILE" 2>&1
        unzip -o ngrok.zip -d "$PREFIX/bin/" >> "$LOG_FILE" 2>&1
        rm ngrok.zip
    }
fi

success "Additional tools installed"

# Step 7: Download wordlists
progress "Downloading wordlists..."

WORDLIST_DIR="$RECONX_DIR/wordlists"
mkdir -p "$WORDLIST_DIR/fuzzing"

# SecLists (shallow clone)
if [ ! -d "$WORDLIST_DIR/SecLists" ]; then
    echo "  Downloading SecLists..."
    git clone --depth 1 https://github.com/danielmiessler/SecLists.git \
        "$WORDLIST_DIR/SecLists" >> "$LOG_FILE" 2>&1 || warn "SecLists clone failed"
fi

# Create symlinks for common wordlists
if [ -d "$WORDLIST_DIR/SecLists" ]; then
    ln -sf "$WORDLIST_DIR/SecLists/Discovery/DNS/subdomains-top1million-110000.txt" \
        "$WORDLIST_DIR/subdomains-medium.txt" 2>/dev/null || true
    
    ln -sf "$WORDLIST_DIR/SecLists/Discovery/Web-Content/common.txt" \
        "$WORDLIST_DIR/directories.txt" 2>/dev/null || true
    
    ln -sf "$WORDLIST_DIR/SecLists/Discovery/Web-Content/raft-large-files.txt" \
        "$WORDLIST_DIR/files.txt" 2>/dev/null || true
    
    success "Wordlists ready"
else
    warn "Wordlists not available"
fi

# Step 8: Setup Ollama (optional)
progress "Setting up Ollama (LLM)..."

if command -v ollama &> /dev/null; then
    success "Ollama already installed"
else
    echo "  Installing Ollama..."
    
    # Check if install script works
    if curl -fsSL https://ollama.com/install.sh | sh >> "$LOG_FILE" 2>&1; then
        success "Ollama installed"
    else
        warn "Ollama auto-install failed. Manual install required."
        echo "    Visit: https://github.com/ollama/ollama"
    fi
fi

# Pull recommended models
if command -v ollama &> /dev/null; then
    echo "  Downloading LLM models (this may take a while)..."
    
    # Small model first (for quick testing)
    ollama pull gemma3:1b >> "$LOG_FILE" 2>&1 || warn "Failed to pull gemma3:1b"
    
    # Main model
    echo "  Downloading llama3.1:8b (this will take 10-20 minutes)..."
    ollama pull llama3.1:8b >> "$LOG_FILE" 2>&1 || warn "Failed to pull llama3.1:8b"
    
    # Fallback model
    ollama pull gemma3:4b >> "$LOG_FILE" 2>&1 || warn "Failed to pull gemma3:4b"
    
    success "LLM models ready"
fi

# Final summary
echo ""
echo "========================"
echo "🎉 Installation Complete!"
echo "========================"
echo ""
echo "Installed tools:"
echo "  $(ls -1 "$GO_BIN" 2>/dev/null | wc -l) Go tools in ~/go/bin"
echo "  $(pip list 2>/dev/null | wc -l) Python packages"
echo ""
echo "Next steps:"
echo "  1. Restart Termux or run: source ~/.bashrc"
echo "  2. Verify: ./tools/health_check.sh"
echo "  3. Start ReconX: ./start.sh"
echo ""
echo "Log saved to: $LOG_FILE"
