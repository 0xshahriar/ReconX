#!/data/data/com.termux/files/usr/bin/bash
# Quick tool health check

echo "🔧 Tool Health Check"
echo "===================="

TOOLS="subfinder httpx naabu nuclei ffuf dnsx waybackurls gf"

for tool in $TOOLS; do
    if command -v $tool &> /dev/null; then
        VER=$($tool -version 2>&1 | head -1 || echo "unknown")
        echo "✓ $tool: $VER"
    else
        echo "✗ $tool: NOT FOUND"
    fi
done

echo ""
echo "Go bin: $HOME/go/bin"
echo "PATH: $PATH"
