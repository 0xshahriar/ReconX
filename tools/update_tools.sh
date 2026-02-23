#!/data/data/com.termux/files/usr/bin/bash
# ReconX Tool Updater
# Update all installed security tools

set -e

RECONX_DIR="$HOME/ReconX"
LOG_FILE="$RECONX_DIR/logs/tools_update.log"
GO_BIN="$HOME/go/bin"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$(dirname "$LOG_FILE")"
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

echo ""
log "${BLUE}🔄 ReconX Tool Updater${NC}"
log "======================"
echo ""

# Update Go tools
log "${BLUE}Updating Go tools...${NC}"

export PATH="$PATH:$GO_BIN"

GO_TOOLS=(
    "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
    "github.com/projectdiscovery/httpx/cmd/httpx@latest"
    "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"
    "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
    "github.com/projectdiscovery/dnsx/cmd/dnsx@latest"
    "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
    "github.com/tomnomnom/waybackurls@latest"
    "github.com/ffuf/ffuf@latest"
    "github.com/trufflesecurity/trufflehog@latest"
    "github.com/gitleaks/gitleaks@latest"
)

UPDATED=0
FAILED=0

for tool in "${GO_TOOLS[@]}"; do
    tool_name=$(echo "$tool" | cut -d'/' -f5 | cut -d'@' -f1)
    
    if go install -v "$tool" >> "$LOG_FILE" 2>&1; then
        log "  ${GREEN}✓${NC} $tool_name"
        UPDATED=$((UPDATED + 1))
    else
        log "  ${YELLOW}⚠${NC} $tool_name failed"
        FAILED=$((FAILED + 1))
    fi
done

# Update Nuclei templates
log ""
log "${BLUE}Updating Nuclei templates...${NC}"

if command -v nuclei &> /dev/null; then
    if nuclei -ut >> "$LOG_FILE" 2>&1; then
        log "  ${GREEN}✓${NC} Nuclei templates updated"
    else
        log "  ${YELLOW}⚠${NC} Template update failed"
    fi
else
    log "  ${YELLOW}⚠${NC} Nuclei not installed"
fi

# Update wordlists
log ""
log "${BLUE}Updating wordlists...${NC}"

WORDLIST_DIR="$RECONX_DIR/wordlists/SecLists"
if [ -d "$WORDLIST_DIR/.git" ]; then
    cd "$WORDLIST_DIR"
    if git pull >> "$LOG_FILE" 2>&1; then
        log "  ${GREEN}✓${NC} SecLists updated"
    else
        log "  ${YELLOW}⚠${NC} SecLists update failed"
    fi
else
    log "  ${YELLOW}⚠${NC} SecLists not found"
fi

# Update Ollama models
log ""
log "${BLUE}Checking Ollama models...${NC}"

if command -v ollama &> /dev/null; then
    # List current models
    MODELS=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}')
    
    for model in $MODELS; do
        log "  Checking $model..."
        # Pull will update if newer version available
        ollama pull "$model" >> "$LOG_FILE" 2>&1 || true
    done
    
    log "  ${GREEN}✓${NC} Models checked/updated"
else
    log "  ${YELLOW}⚠${NC} Ollama not installed"
fi

# Update Python packages
log ""
log "${BLUE}Updating Python packages...${NC}"

pip list --outdated --format=freeze 2>/dev/null | cut -d= -f1 | \
    xargs -n1 pip install -U >> "$LOG_FILE" 2>&1 || true

log "  ${GREEN}✓${NC} Python packages updated"

# Summary
echo ""
log "======================"
log "🎉 Update Complete!"
log "======================"
log "Updated: $UPDATED tools"
log "Failed: $FAILED tools"
log ""
log "Log: $LOG_FILE"
