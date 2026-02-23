#!/data/data/com.termux/files/usr/bin/bash
# ReconX Tunnel Setup Script
# Interactive setup for Cloudflare, Ngrok, or LocalTunnel

set -e

RECONX_DIR="$HOME/ReconX"
CONFIG_FILE="$RECONX_DIR/config/tunnel.yaml"

echo "🚇 ReconX Tunnel Setup"
echo "======================"
echo ""
echo "This script will help you set up remote access to your ReconX dashboard."
echo ""

# Check if already configured
if [ -f "$CONFIG_FILE" ] && grep -q "cloudflare:" "$CONFIG_FILE"; then
    echo "⚠️  Tunnel configuration already exists."
    read -p "Reconfigure? (yes/no): " reconfig
    if [ "$reconfig" != "yes" ]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

echo "Choose your preferred tunnel service:"
echo ""
echo "1) Cloudflare Tunnel (Recommended)"
echo "   ✓ Most stable and reliable"
echo "   ✓ Custom subdomain support"
echo "   ✓ Free unlimited bandwidth"
echo "   ⚠ Requires Cloudflare account"
echo ""
echo "2) Ngrok (Easiest setup)"
echo "   ✓ Instant setup, no account needed for basic use"
echo "   ✗ Random URLs change on restart"
echo "   ⚠ Connection limits on free tier"
echo ""
echo "3) LocalTunnel (No signup)"
echo "   ✓ No account required"
echo "   ✗ Less stable, public URLs"
echo "   ⚠ Requires Node.js"
echo ""

read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "🔵 Setting up Cloudflare Tunnel..."
        
        # Check/install cloudflared
        if ! command -v cloudflared &> /dev/null; then
            echo "📦 Installing cloudflared..."
            
            # Try package manager first
            if pkg install cloudflared -y 2>/dev/null; then
                echo "✓ Installed via pkg"
            else
                # Manual install for Termux
                ARCH=$(uname -m)
                if [ "$ARCH" = "aarch64" ]; then
                    CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
                else
                    CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm"
                fi
                
                curl -L --output "$PREFIX/bin/cloudflared" "$CF_URL"
                chmod +x "$PREFIX/bin/cloudflared"
                echo "✓ Installed manually"
            fi
        else
            echo "✓ cloudflared already installed"
        fi
        
        # Authenticate
        echo ""
        echo "🔐 Authenticating with Cloudflare..."
        echo "A browser window will open (if possible) or you'll get a URL to visit."
        echo ""
        
        cloudflared tunnel login
        
        # Create tunnel
        echo ""
        echo "🚇 Creating tunnel 'reconx'..."
        cloudflared tunnel create reconx 2>/dev/null || echo "Tunnel may already exist, continuing..."
        
        # Update config
        cat > "$CONFIG_FILE" <<EOF
tunnel:
  primary: cloudflare
  auto_start: true
  auto_restart: true
  notify_on_start: true
  notify_on_reconnect: true
  
  cloudflare:
    enabled: true
    tunnel_name: "reconx"
    custom_domain: ""
    
  security:
    require_auth: true
    auth_password: ""
    allowed_ips: []
    auto_shutdown: 7200
    
  retry:
    max_attempts: 5
    delay_seconds: 60
EOF
        
        echo ""
        echo "✅ Cloudflare setup complete!"
        echo ""
        echo "To use a custom domain (optional):"
        echo "1. Add a CNAME record in Cloudflare DNS pointing to your tunnel"
        echo "2. Run: cloudflared tunnel route dns reconx yourdomain.com"
        echo "3. Update config/tunnel.yaml with your domain"
        ;;
        
    2)
        echo ""
        echo "🟢 Setting up Ngrok..."
        
        # Check/install ngrok
        if ! command -v ngrok &> /dev/null; then
            echo "📦 Installing ngrok..."
            
            if pkg install ngrok -y 2>/dev/null; then
                echo "✓ Installed via pkg"
            else
                # Manual install
                curl -L --output ngrok.zip "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.zip"
                unzip -o ngrok.zip -d "$PREFIX/bin/"
                rm ngrok.zip
                echo "✓ Installed manually"
            fi
        else
            echo "✓ ngrok already installed"
        fi
        
        # Configure
        echo ""
        read -p "Enter your ngrok auth token (get from https://dashboard.ngrok.com): " authtoken
        
        if [ -n "$authtoken" ]; then
            ngrok config add-authtoken "$authtoken"
            echo "✓ Auth token configured"
        fi
        
        # Update config
        cat > "$CONFIG_FILE" <<EOF
tunnel:
  primary: ngrok
  auto_start: true
  auto_restart: true
  notify_on_start: true
  notify_on_reconnect: true
  
  ngrok:
    enabled: true
    region: us
    auth_token: "$authtoken"
    
  security:
    require_auth: true
    auth_password: ""
    allowed_ips: []
    auto_shutdown: 7200
EOF
        
        echo ""
        echo "✅ Ngrok setup complete!"
        echo "Note: Free tier uses random URLs that change on restart."
        echo "For stable URLs, upgrade to ngrok Pro or use Cloudflare."
        ;;
        
    3)
        echo ""
        echo "🟡 Setting up LocalTunnel..."
        
        # Check/install Node.js
        if ! command -v node &> /dev/null; then
            echo "📦 Installing Node.js..."
            pkg install nodejs -y
        fi
        
        # Install localtunnel
        echo "📦 Installing LocalTunnel..."
        npm install -g localtunnel
        
        # Update config
        cat > "$CONFIG_FILE" <<EOF
tunnel:
  primary: localtunnel
  auto_start: true
  auto_restart: true
  notify_on_start: true
  notify_on_reconnect: true
  
  localtunnel:
    enabled: true
    host: "https://localtunnel.me"
    
  security:
    require_auth: true
    auth_password: ""
    allowed_ips: []
    auto_shutdown: 7200
EOF
        
        echo ""
        echo "✅ LocalTunnel setup complete!"
        echo "Note: LocalTunnel is less stable and URLs are public."
        ;;
        
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🛡️ Security Configuration"
echo "=========================="
read -p "Set dashboard password (recommended): " password

if [ -n "$password" ]; then
    # Update config with password (base64 encoded for basic obscurity)
    ENCODED=$(echo "$password" | base64)
    sed -i "s/auth_password: \"\"/auth_password: \"$ENCODED\"/" "$CONFIG_FILE"
    echo "✓ Password configured"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start ReconX: ./start.sh --with-tunnel"
echo "2. Or enable auto-tunnel in web settings"
echo "3. Check logs: tail -f logs/tunnel.log"
echo ""
echo "To test tunnel now:"
echo "  ./scripts/start_tunnel.sh"
