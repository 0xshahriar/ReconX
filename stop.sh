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
