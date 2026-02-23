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
