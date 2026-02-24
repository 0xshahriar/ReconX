#!/bin/bash
# ReconX - Phase 1: Fixed Installation Script for Termux
# Author: Md. Shahriar Alam Shaon

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}[+] Updating Termux packages...${NC}"
pkg update -y && pkg upgrade -y

echo -e "${GREEN}[+] Installing core dependencies...${NC}"
pkg install -y python python-pip git wget curl sqlite

# ---------------------------------------------------------
# Golang Setup (Required for other tools)
# ---------------------------------------------------------
echo -e "${GREEN}[+] Installing Golang...${NC}"
pkg install -y golang

# Setup GOPATH
mkdir -p ~/go/bin
echo 'export GOPATH=$HOME/go' >> ~/.bashrc
echo 'export PATH=$PATH:$GOPATH/bin' >> ~/.bashrc
export GOPATH=$HOME/go
export PATH=$PATH:$GOPATH/bin

# ---------------------------------------------------------
# Install ProjectDiscovery Tools (Pre-compiled Binaries)
# This avoids the "sonic/GoMapIterator" compilation error
# ---------------------------------------------------------
echo -e "${GREEN}[+] Downloading Pre-compiled Tools (ARM64/Android)...${NC}"

# Detect Architecture
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ]; then
    PD_ARCH="linux_arm64"
elif [ "$ARCH" = "x86_64" ]; then
    PD_ARCH="linux_amd64"
else
    echo -e "${RED}[-] Architecture $ARCH not supported for binaries. Falling back to 'go install'.${NC}"
    PD_ARCH="source"
fi

install_pd_tool() {
    TOOL_NAME=$1
    VERSION=$2
    
    if [ "$PD_ARCH" != "source" ]; then
        echo -e "${YELLOW}[*] Downloading $TOOL_NAME $VERSION ($PD_ARCH)...${NC}"
        wget -q "https://github.com/projectdiscovery/$TOOL_NAME/releases/download/v$VERSION/${TOOL_NAME}_${VERSION}_${PD_ARCH}.zip" -O /tmp/$TOOL_NAME.zip
        unzip -o /tmp/$TOOL_NAME.zip -d ~/go/bin/
        rm /tmp/$TOOL_NAME.zip
        chmod +x ~/go/bin/$TOOL_NAME
    else
        echo -e "${YELLOW}[*] Installing $TOOL_NAME via Go (Source)...${NC}"
        CGO_ENABLED=0 go install -v github.com/projectdiscovery/$TOOL_NAME/v2/cmd/$TOOL_NAME@latest
    fi
}

# Install Nuclei, Subfinder, Httpx, Naabu
# Using specific stable versions to ensure compatibility
install_pd_tool "subfinder" "2.6.5"
install_pd_tool "httpx" "1.3.7"
install_pd_tool "nuclei" "3.1.7"
install_pd_tool "naabu" "2.2.1"

# ---------------------------------------------------------
# Install Other Go Tools (Source - usually safe)
# ---------------------------------------------------------
echo -e "${GREEN}[+] Installing Additional Go Tools...${NC}"
CGO_ENABLED=0 go install -v github.com/tomnomnom/gf@latest
CGO_ENABLED=0 go install -v github.com/tomnomnom/waybackurls@latest
CGO_ENABLED=0 go install -v github.com/lc/gau/v2/cmd/gau@latest
CGO_ENABLED=0 go install -v github.com/projectdiscovery/katana/cmd/katana@latest

# ---------------------------------------------------------
# Python Dependencies
# ---------------------------------------------------------
echo -e "${GREEN}[+] Installing Python Dependencies...${NC}"
pip install -r requirements.txt

# ---------------------------------------------------------
# Directory Structure
# ---------------------------------------------------------
echo -e "${GREEN}[+] Creating Project Directories...${NC}"
mkdir -p data/workspace data/wordlists data/cache data/reports logs

echo -e "${YELLOW}[!] IMPORTANT: Restart Termux or run 'source ~/.bashrc'.${NC}"
echo -e "${GREEN}[+] ReconX Phase 1 Installation Complete.${NC}"