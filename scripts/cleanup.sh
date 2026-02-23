#!/data/data/com.termux/files/usr/bin/bash
# ReconX Cleanup Script
# Clear cache, old logs, and temporary files

set -e

RECONX_DIR="$HOME/ReconX"
DAYS_TO_KEEP=7

echo "🧹 ReconX Cleanup"
echo "================="

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            CLEAN_ALL=true
            shift
            ;;
        --logs)
            CLEAN_LOGS=true
            shift
            ;;
        --cache)
            CLEAN_CACHE=true
            shift
            ;;
        --reports)
            CLEAN_REPORTS=true
            shift
            ;;
        --state)
            CLEAN_STATE=true
            shift
            ;;
        --days)
            DAYS_TO_KEEP="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# If no specific option, clean all
if [ -z "$CLEAN_LOGS" ] && [ -z "$CLEAN_CACHE" ] && [ -z "$CLEAN_REPORTS" ] && [ -z "$CLEAN_STATE" ]; then
    CLEAN_ALL=true
fi

TOTAL_FREED=0

# Function to calculate size
calc_size() {
    if [ -d "$1" ]; then
        du -sb "$1" 2>/dev/null | cut -f1 || echo 0
    else
        echo 0
    fi
}

# Function to format bytes
format_size() {
    local bytes=$1
    if [ $bytes -gt 1073741824 ]; then
        echo "$(echo "scale=2; $bytes/1073741824" | bc) GB"
    elif [ $bytes -gt 1048576 ]; then
        echo "$(echo "scale=2; $bytes/1048576" | bc) MB"
    elif [ $bytes -gt 1024 ]; then
        echo "$(echo "scale=2; $bytes/1024" | bc) KB"
    else
        echo "${bytes} B"
    fi
}

# Clean logs
if [ "$CLEAN_ALL" = true ] || [ "$CLEAN_LOGS" = true ]; then
    echo ""
    echo "📝 Cleaning logs (keeping last $DAYS_TO_KEEP days)..."
    
    if [ -d "$RECONX_DIR/logs" ]; then
        BEFORE=$(calc_size "$RECONX_DIR/logs")
        
        # Remove old log files
        find "$RECONX_DIR/logs" -name "*.log" -type f -mtime +$DAYS_TO_KEEP -delete 2>/dev/null || true
        
        # Remove old compressed logs
        find "$RECONX_DIR/logs" -name "*.gz" -type f -mtime +$DAYS_TO_KEEP -delete 2>/dev/null || true
        
        # Remove old scan logs
        find "$RECONX_DIR/logs/scans" -name "*.log" -type f -mtime +$DAYS_TO_KEEP -delete 2>/dev/null || true
        
        AFTER=$(calc_size "$RECONX_DIR/logs")
        FREED=$((BEFORE - AFTER))
        TOTAL_FREED=$((TOTAL_FREED + FREED))
        
        echo "  ✓ Freed $(format_size $FREED)"
    fi
fi

# Clean cache
if [ "$CLEAN_ALL" = true ] || [ "$CLEAN_CACHE" = true ]; then
    echo ""
    echo "💾 Cleaning cache..."
    
    if [ -d "$RECONX_DIR/data/cache" ]; then
        BEFORE=$(calc_size "$RECONX_DIR/data/cache")
        
        # Remove temp files
        rm -rf "$RECONX_DIR/data/cache/temp/"* 2>/dev/null || true
        
        # Remove old downloads
        find "$RECONX_DIR/data/cache/downloads" -type f -mtime +$DAYS_TO_KEEP -delete 2>/dev/null || true
        
        # Remove old httpx cache
        find "$RECONX_DIR/data/cache/httpx" -type d -mtime +$DAYS_TO_KEEP -exec rm -rf {} + 2>/dev/null || true
        
        # Remove old nuclei cache
        find "$RECONX_DIR/data/cache/nuclei" -type d -mtime +$DAYS_TO_KEEP -exec rm -rf {} + 2>/dev/null || true
        
        AFTER=$(calc_size "$RECONX_DIR/data/cache")
        FREED=$((BEFORE - AFTER))
        TOTAL_FREED=$((TOTAL_FREED + FREED))
        
        echo "  ✓ Freed $(format_size $FREED)"
    fi
fi

# Clean old reports
if [ "$CLEAN_ALL" = true ] || [ "$CLEAN_REPORTS" = true ]; then
    echo ""
    echo "📊 Cleaning old reports..."
    
    if [ -d "$RECONX_DIR/reports" ]; then
        BEFORE=$(calc_size "$RECONX_DIR/reports")
        
        # Remove reports older than specified days
        find "$RECONX_DIR/reports" -type d -name "[a-f0-9-]*" -mtime +30 -exec rm -rf {} + 2>/dev/null || true
        
        AFTER=$(calc_size "$RECONX_DIR/reports")
        FREED=$((BEFORE - AFTER))
        TOTAL_FREED=$((TOTAL_FREED + FREED))
        
        echo "  ✓ Freed $(format_size $FREED)"
    fi
fi

# Clean old state files
if [ "$CLEAN_ALL" = true ] || [ "$CLEAN_STATE" = true ]; then
    echo ""
    echo "💾 Cleaning old state files..."
    
    if [ -d "$RECONX_DIR/data/state" ]; then
        BEFORE=$(calc_size "$RECONX_DIR/data/state")
        
        # Remove state files older than specified days
        find "$RECONX_DIR/data/state" -name "*.json*" -type f -mtime +$DAYS_TO_KEEP -delete 2>/dev/null || true
        
        AFTER=$(calc_size "$RECONX_DIR/data/state")
        FREED=$((BEFORE - AFTER))
        TOTAL_FREED=$((TOTAL_FREED + FREED))
        
        echo "  ✓ Freed $(format_size $FREED)"
    fi
fi

# Vacuum database
echo ""
echo "🗜️  Optimizing database..."
if [ -f "$RECONX_DIR/data/recon.db" ]; then
    BEFORE=$(stat -c%s "$RECONX_DIR/data/recon.db" 2>/dev/null || stat -f%z "$RECONX_DIR/data/recon.db" 2>/dev/null || echo 0)
    
    sqlite3 "$RECONX_DIR/data/recon.db" "VACUUM;" 2>/dev/null || echo "  ⚠ Could not vacuum database"
    
    AFTER=$(stat -c%s "$RECONX_DIR/data/recon.db" 2>/dev/null || stat -f%z "$RECONX_DIR/data/recon.db" 2>/dev/null || echo 0)
    FREED=$((BEFORE - AFTER))
    
    if [ $FREED -gt 0 ]; then
        TOTAL_FREED=$((TOTAL_FREED + FREED))
        echo "  ✓ Database optimized, freed $(format_size $FREED)"
    else
        echo "  ✓ Database already optimized"
    fi
fi

echo ""
echo "==================="
echo "🎉 Cleanup complete!"
echo "💾 Total space freed: $(format_size $TOTAL_FREED)"
echo ""
echo "Current disk usage:"
df -h . | tail -1
