#!/data/data/com.termux/files/usr/bin/bash
# ReconX Health Check Script
# System diagnostics and requirements verification

set -e

RECONX_DIR="$HOME/ReconX"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🏥 ReconX Health Check"
echo "======================"
echo ""

# Function to print status
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Termux environment
echo "📱 Environment:"
if [ -n "$TERMUX_VERSION" ]; then
    check_pass "Running in Termux v$TERMUX_VERSION"
else
    check_warn "Not running in Termux"
fi

# Check storage permission
if [ -d "/sdcard" ] && [ -r "/sdcard" ]; then
    check_pass "Storage permission granted"
else
    check_fail "Storage permission not granted"
    echo "   Run: termux-setup-storage"
fi

echo ""
echo "💾 Storage:"

# Check disk space
DISK_USAGE=$(df -h "$HOME" | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 80 ]; then
    check_pass "Disk usage: ${DISK_USAGE}%"
else
    check_warn "Disk usage high: ${DISK_USAGE}%"
fi

# Check available space
AVAILABLE=$(df -h "$HOME" | tail -1 | awk '{print $4}')
echo "   Available: $AVAILABLE"

# Check memory
echo ""
echo "🧠 Memory:"
if [ -f "/proc/meminfo" ]; then
    TOTAL_MEM=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    TOTAL_GB=$((TOTAL_MEM / 1024 / 1024))
    
    if [ $TOTAL_GB -ge 6 ]; then
        check_pass "RAM: ~${TOTAL_GB}GB"
    else
        check_warn "RAM low: ~${TOTAL_GB}GB (Recommended: 6GB+)"
    fi
fi

# Check swap
if [ -f "/proc/swaps" ] && grep -q "file" /proc/swaps 2>/dev/null; then
    SWAP_SIZE=$(grep "file" /proc/swaps | awk '{print $3}' | head -1)
    if [ -n "$SWAP_SIZE" ]; then
        SWAP_GB=$((SWAP_SIZE / 1024 / 1024))
        check_pass "Swap: ${SWAP_GB}GB"
    fi
else
    check_warn "No swap configured (Recommended for 8GB devices)"
fi

echo ""
echo "📦 Dependencies:"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VER=$(python3 --version 2>&1 | cut -d' ' -f2)
    check_pass "Python $PYTHON_VER"
else
    check_fail "Python3 not found"
fi

# Check Go
if command -v go &> /dev/null; then
    GO_VER=$(go version | cut -d' ' -f3)
    check_pass "Go $GO_VER"
else
    check_fail "Go not found (Required for tools)"
    echo "   Install: pkg install golang"
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VER=$(node --version)
    check_pass "Node.js $NODE_VER"
else
    check_warn "Node.js not found (Optional for LocalTunnel)"
fi

# Check git
if command -v git &> /dev/null; then
    check_pass "Git available"
else
    check_fail "Git not found"
fi

echo ""
echo "🔧 ReconX Tools:"

# Check installed tools
TOOLS=("subfinder" "httpx" "naabu" "nuclei" "ffuf" "dnsx")
for tool in "${TOOLS[@]}"; do
    if command -v $tool &> /dev/null; then
        VER=$($tool -version 2>&1 | head -1 || echo "unknown")
        check_pass "$tool installed"
    else
        check_fail "$tool not found"
    fi
done

echo ""
echo "📁 ReconX Installation:"

# Check directory structure
if [ -d "$RECONX_DIR" ]; then
    check_pass "ReconX directory exists"
else
    check_fail "ReconX directory not found"
    exit 1
fi

# Check subdirectories
for dir in api core web config data logs reports scripts tools wordlists; do
    if [ -d "$RECONX_DIR/$dir" ]; then
        check_pass "$dir/ directory"
    else
        check_fail "$dir/ directory missing"
    fi
done

# Check database
echo ""
echo "💾 Database:"
if [ -f "$RECONX_DIR/data/recon.db" ]; then
    DB_SIZE=$(stat -c%s "$RECONX_DIR/data/recon.db" 2>/dev/null || stat -f%z "$RECONX_DIR/data/recon.db" 2>/dev/null || echo 0)
    DB_SIZE_MB=$((DB_SIZE / 1024 / 1024))
    check_pass "Database exists (${DB_SIZE_MB}MB)"
    
    # Check integrity
    if sqlite3 "$RECONX_DIR/data/recon.db" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
        check_pass "Database integrity OK"
    else
        check_fail "Database integrity check failed"
    fi
else
    check_warn "Database not initialized"
fi

# Check Ollama
echo ""
echo "🤖 LLM (Ollama):"
if command -v ollama &> /dev/null; then
    check_pass "Ollama installed"
    
    # Check if models available
    MODELS=$(ollama list 2>/dev/null | tail -n +2 | wc -l)
    if [ "$MODELS" -gt 0 ]; then
        check_pass "$MODELS models available"
        ollama list 2>/dev/null | tail -n +2 | while read line; do
            echo "   - $line"
        done
    else
        check_warn "No models downloaded"
        echo "   Run: ollama pull llama3.1:8b"
    fi
else
    check_warn "Ollama not installed (Optional for AI features)"
fi

# Check network
echo ""
echo "🌐 Network:"
if ping -c 1 -W 5 1.1.1.1 &> /dev/null; then
    check_pass "Internet connectivity OK"
else
    check_fail "No internet connectivity"
fi

# Check battery (Termux)
if command -v termux-battery-status &> /dev/null; then
    BATTERY=$(termux-battery-status 2>/dev/null | grep percentage | cut -d':' -f2 | tr -d ' ,')
    if [ -n "$BATTERY" ]; then
        if [ "$BATTERY" -gt 20 ]; then
            check_pass "Battery: ${BATTERY}%"
        else
            check_warn "Battery low: ${BATTERY}%"
        fi
    fi
fi

echo ""
echo "======================"
echo "✅ Health check complete!"

# Summary
echo ""
echo "Quick fixes:"
echo "  Install missing tools: ~/ReconX/tools/install_tools.sh"
echo "  Update all tools: ~/ReconX/tools/update_tools.sh"
echo "  Clean up space: ~/ReconX/scripts/cleanup.sh"
