#!/data/data/com.termux/files/usr/bin/bash
# ReconX Watchdog Script
# Monitor power/network and auto-resume scans
# Run via: termux-job-scheduler --job-path ~/ReconX/scripts/watchdog.sh --period-ms 30000

RECONX_DIR="$HOME/ReconX"
API_URL="http://localhost:8000/api"
STATE_FILE="$RECONX_DIR/.paused_due_to_outage"
LOG_FILE="$RECONX_DIR/logs/watchdog.log"
CONFIG_FILE="$RECONX_DIR/config/tunnel.yaml"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check if ReconX is running
is_reconx_running() {
    pgrep -f "python.*main.py" > /dev/null 2>&1 || \
    pgrep -f "uvicorn.*main:app" > /dev/null 2>&1
}

# Check internet connectivity
check_internet() {
    # Try multiple DNS servers
    if ping -c 1 -W 3 1.1.1.1 >/dev/null 2>&1 || \
       ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1 || \
       ping -c 1 -W 3 9.9.9.9 >/dev/null 2>&1; then
        return 0  # Online
    else
        return 1  # Offline
    fi
}

# Check battery level
check_battery() {
    if command -v termux-battery-status >/dev/null 2>&1; then
        BATTERY=$(termux-battery-status 2>/dev/null | grep percentage | cut -d':' -f2 | tr -d ' ,')
        echo "$BATTERY"
    else
        echo "100"  # Assume full if can't check
    fi
}

# Check if charging
is_charging() {
    if command -v termux-battery-status >/dev/null 2>&1; then
        STATUS=$(termux-battery-status 2>/dev/null | grep status | cut -d'"' -f4)
        [ "$STATUS" = "CHARGING" ] || [ "$STATUS" = "FULL" ]
    else
        return 1  # Assume not charging
    fi
}

# Main logic
main() {
    # Don't run if ReconX isn't active
    if ! is_reconx_running; then
        exit 0
    fi
    
    BATTERY=$(check_battery)
    ONLINE=false
    
    if check_internet; then
        ONLINE=true
    fi
    
    # Handle state transitions
    if [ "$ONLINE" = true ]; then
        # Internet is available
        
        if [ -f "$STATE_FILE" ]; then
            # We were paused due to outage
            log "🌐 Internet restored"
            
            # Check if we should auto-resume
            if [ "$BATTERY" -gt 15 ] || is_charging; then
                log "🔋 Battery OK ($BATTERY%), resuming scan"
                
                # Resume via API
                curl -s -X POST "$API_URL/system/resume" \
                     -H "Content-Type: application/json" \
                     -d '{"reason": "network_restored"}' > /dev/null 2>&1
                
                # Restart tunnel if configured
                if grep -q "auto_start: true" "$CONFIG_FILE" 2>/dev/null; then
                    log "🚇 Restarting tunnel"
                    "$RECONX_DIR/scripts/start_tunnel.sh" &
                fi
                
                # Remove pause state
                rm -f "$STATE_FILE"
                
                # Send notification
                if command -v termux-notification >/dev/null 2>&1; then
                    termux-notification \
                        --title "🔌 ReconX Resumed" \
                        --content "Scan resumed after connection restored" \
                        --priority high
                fi
            else
                log "⚠️ Battery too low to resume ($BATTERY%)"
            fi
        fi
        
        # Check battery even if not paused
        if [ "$BATTERY" -lt 10 ] && ! is_charging; then
            log "🪫 Critical battery ($BATTERY%), requesting pause"
            
            curl -s -X POST "$API_URL/system/pause" \
                 -H "Content-Type: application/json" \
                 -d '{"reason": "low_battery"}' > /dev/null 2>&1
            
            if command -v termux-notification >/dev/null 2>&1; then
                termux-notification \
                    --title "🪫 Low Battery" \
                    --content "Scan paused to preserve battery ($BATTERY%)" \
                    --priority high
            fi
        fi
        
    else
        # Internet is down
        
        if [ ! -f "$STATE_FILE" ]; then
            log "❌ Internet lost, pausing scan"
            
            # Create pause state
            echo "paused_at=$(date +%s)" > "$STATE_FILE"
            
            # Pause via API
            curl -s -X POST "$API_URL/system/pause" \
                 -H "Content-Type: application/json" \
                 -d '{"reason": "network_outage"}' > /dev/null 2>&1
            
            # Stop tunnel to save resources
            pkill -f "cloudflared" 2>/dev/null || true
            pkill -f "ngrok" 2>/dev/null || true
            
            if command -v termux-notification >/dev/null 2>&1; then
                termux-notification \
                    --title "📴 Connection Lost" \
                    --content "Scan paused, will resume when online" \
                    --priority high
            fi
        fi
    fi
}

# Rotate log if too large
if [ -f "$LOG_FILE" ] && [ $(stat -c%s "$LOG_FILE" 2>/dev/null || stat -f%z "$LOG_FILE" 2>/dev/null || echo 0) -gt 1048576 ]; then
    mv "$LOG_FILE" "$LOG_FILE.old"
    touch "$LOG_FILE"
fi

# Run main check
main
