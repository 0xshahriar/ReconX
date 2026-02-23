#!/data/data/com.termux/files/usr/bin/bash
# ReconX Tunnel Start Script
# Start Cloudflare, Ngrok, or LocalTunnel

set -e

RECONX_DIR="$HOME/ReconX"
CONFIG_FILE="$RECONX_DIR/config/tunnel.yaml"
LOG_FILE="$RECONX_DIR/logs/tunnel.log"
PID_FILE="$RECONX_DIR/.tunnel_pid"

# Ensure log directory
mkdir -p "$(dirname "$LOG_FILE")"

# Read config
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Tunnel not configured. Run: ./scripts/tunnel_setup.sh"
    exit 1
fi

# Detect primary service
SERVICE=$(grep "primary:" "$CONFIG_FILE" | head -1 | awk '{print $2}' | tr -d ' ')

echo "🚇 Starting $SERVICE tunnel..."
echo "Logs: $LOG_FILE"

# Function to extract URL from logs
extract_url() {
    local file=$1
    local pattern=$2
    local timeout=${3:-30}
    
    for i in $(seq 1 $timeout); do
        if [ -f "$file" ]; then
            url=$(grep -oE "$pattern" "$file" | head -1)
            if [ -n "$url" ]; then
                echo "$url"
                return 0
            fi
        fi
        sleep 1
    done
    return 1
}

# Start tunnel based on service
case "$SERVICE" in
    cloudflare)
        # Kill existing
        pkill -f "cloudflared.*localhost:8000" 2>/dev/null || true
        sleep 1
        
        # Start cloudflared
        nohup cloudflared tunnel --url http://localhost:8000 > "$LOG_FILE" 2>&1 &
        TUNNEL_PID=$!
        echo $TUNNEL_PID > "$PID_FILE"
        
        echo "⏳ Waiting for tunnel..."
        URL=$(extract_url "$LOG_FILE" "https://[a-zA-Z0-9-]+\.trycloudflare\.com" 60)
        
        if [ -n "$URL" ]; then
            echo ""
            echo "✅ Tunnel active!"
            echo "🌐 URL: $URL"
            echo ""
            echo "Share this URL to access your dashboard remotely."
            echo "Password protection: $(grep "require_auth:" "$CONFIG_FILE" | awk '{print $2}')"
            
            # Send notification
            if command -v termux-notification >/dev/null 2>&1; then
                termux-notification \
                    --title "🌐 ReconX Tunnel Active" \
                    --content "$URL" \
                    --priority high
            fi
        else
            echo "❌ Failed to get tunnel URL. Check logs:"
            tail -20 "$LOG_FILE"
            exit 1
        fi
        ;;
        
    ngrok)
        # Kill existing
        pkill -f "ngrok.*http.*8000" 2>/dev/null || true
        sleep 1
        
        # Start ngrok
        nohup ngrok http 8000 --log=stdout > "$LOG_FILE" 2>&1 &
        TUNNEL_PID=$!
        echo $TUNNEL_PID > "$PID_FILE"
        
        echo "⏳ Waiting for tunnel..."
        sleep 3
        
        # Get URL from ngrok API
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | \
                    grep -o '"public_url":"[^"]*"' | \
                    head -1 | \
                    cut -d'"' -f4)
        
        if [ -n "$NGROK_URL" ]; then
            echo ""
            echo "✅ Tunnel active!"
            echo "🌐 URL: $NGROK_URL"
            echo ""
            echo "⚠️  This URL will change when you restart!"
        else
            echo "❌ Failed to get tunnel URL"
            tail -20 "$LOG_FILE"
            exit 1
        fi
        ;;
        
    localtunnel)
        # Kill existing
        pkill -f "lt.*port.*8000" 2>/dev/null || true
        sleep 1
        
        # Start localtunnel
        nohup npx localtunnel --port 8000 > "$LOG_FILE" 2>&1 &
        TUNNEL_PID=$!
        echo $TUNNEL_PID > "$PID_FILE"
        
        echo "⏳ Waiting for tunnel..."
        URL=$(extract_url "$LOG_FILE" "https://[a-zA-Z0-9-]+\.loca\.lt" 60)
        
        if [ -n "$URL" ]; then
            echo ""
            echo "✅ Tunnel active!"
            echo "🌐 URL: $URL"
        else
            echo "❌ Failed to get tunnel URL"
            tail -20 "$LOG_FILE"
            exit 1
        fi
        ;;
        
    *)
        echo "❌ Unknown tunnel service: $SERVICE"
        exit 1
        ;;
esac

echo ""
echo "PID: $TUNNEL_PID (saved to $PID_FILE)"
echo "To stop: kill $TUNNEL_PID or ./stop.sh"
