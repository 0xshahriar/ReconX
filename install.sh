#!/bin/bash
# ReconX - Phase 1: Installation Script for Termux
# Author: Md. Shahriar Alam Shaon

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}[+] Updating Termux packages...${NC}"
pkg update -y && pkg upgrade -y

echo -e "${GREEN}[+] Installing core dependencies...${NC}"
pkg install -y python python-pip git golang nodejs sqlite wget curl

# Setup Golang environment for Termux
echo -e "${GREEN}[+] Configuring Golang environment...${NC}"
mkdir -p ~/go/bin
echo 'export GOPATH=$HOME/go' >> ~/.bashrc
echo 'export PATH=$PATH:$GOPATH/bin' >> ~/.bashrc
export GOPATH=$HOME/go
export PATH=$PATH:$GOPATH/bin

echo -e "${GREEN}[+] Installing Bug Bounty Tools (Golang)...${NC}"
# Installing Subfinder (Subdomain enumeration)
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# Installing Httpx (Live host detection)
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest

# Installing Nuclei (Vulnerability scanner)
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# Installing Naabu (Port scanning - lightweight mode)
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest

# Installing Gau (GetAllUrls)
go install -v github.com/lc/gau/v2/cmd/gau@latest

# Installing Gf (Grep Fuzz)
go install -v github.com/tomnomnom/gf@latest

# Installing Waybackurls
go install -v github.com/tomnomnom/waybackurls@latest

# Installing Ghauri (SQLi detection - alternative to sqlmap, lighter)
go install -v github.com/r0oth3x49/ghauri@latest

echo -e "${GREEN}[+] Installing Python Dependencies...${NC}"
pip install -r requirements.txt

echo -e "${GREEN}[+] Creating Project Directories...${NC}"
mkdir -p data/workspace data/wordlists data/cache data/reports logs

echo -e "${YELLOW}[!] IMPORTANT: Please restart Termux or run 'source ~/.bashrc' to update PATH.${NC}"
echo -e "${GREEN}[+] ReconX Phase 1 Installation Complete.${NC}"