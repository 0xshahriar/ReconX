#!/data/data/com.termux/files/usr/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

RECONX_DIR="$HOME/reconx"
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
# DO NOT upgrade pip on Termux - it breaks the system package
pip install -r "$RECONX_DIR/requirements.txt"

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

echo -e "\n${GREEN}=== Installation Complete ===${NC}"
echo -e "Start: ${BLUE}./start.sh${NC} or ${BLUE}./start.sh --with-tunnel${NC}"
echo -e "Stop:  ${BLUE}./stop.sh${NC}"
echo -e "\n${GREEN}Happy Hunting!${NC}"
