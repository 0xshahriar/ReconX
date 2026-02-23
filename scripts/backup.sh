#!/data/data/com.termux/files/usr/bin/bash
# ReconX Backup Script
# Backup database and critical files to /sdcard/

set -e

RECONX_DIR="$HOME/ReconX"
BACKUP_DIR="/sdcard/ReconX_Backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="reconx_backup_${TIMESTAMP}.tar.gz"

echo "🔒 ReconX Backup - $TIMESTAMP"
echo "================================"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if ReconX directory exists
if [ ! -d "$RECONX_DIR" ]; then
    echo "❌ ReconX directory not found at $RECONX_DIR"
    exit 1
fi

# Create temp directory for backup contents
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo "📦 Collecting files..."

# Copy database
if [ -f "$RECONX_DIR/data/recon.db" ]; then
    cp "$RECONX_DIR/data/recon.db" "$TEMP_DIR/"
    echo "  ✓ Database copied"
else
    echo "  ⚠ Database not found"
fi

# Copy config
if [ -d "$RECONX_DIR/config" ]; then
    cp -r "$RECONX_DIR/config" "$TEMP_DIR/"
    echo "  ✓ Config copied"
fi

# Copy wordlists (compressed reference)
if [ -d "$RECONX_DIR/wordlists" ]; then
    echo "wordlists_dir=$RECONX_DIR/wordlists" > "$TEMP_DIR/wordlists.info"
    echo "  ✓ Wordlists reference saved"
fi

# Copy important reports (last 30 days)
if [ -d "$RECONX_DIR/reports" ]; then
    mkdir -p "$TEMP_DIR/reports"
    find "$RECONX_DIR/reports" -type d -mtime -30 -exec cp -r {} "$TEMP_DIR/reports/" \; 2>/dev/null || true
    echo "  ✓ Recent reports copied"
fi

# Create manifest
cat > "$TEMP_DIR/manifest.json" <<EOF
{
    "version": "1.0",
    "timestamp": "$TIMESTAMP",
    "source": "$RECONX_DIR",
    "files": ["recon.db", "config", "reports"]
}
EOF

# Create archive
echo "🗜️  Creating archive..."
cd "$TEMP_DIR"
tar -czf "$BACKUP_DIR/$BACKUP_NAME" .

# Verify backup
if [ -f "$BACKUP_DIR/$BACKUP_NAME" ]; then
    SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)
    echo ""
    echo "✅ Backup created successfully!"
    echo "📁 Location: $BACKUP_DIR/$BACKUP_NAME"
    echo "📊 Size: $SIZE"
else
    echo "❌ Backup failed"
    exit 1
fi

# Cleanup old backups (keep last 10)
echo "🧹 Cleaning up old backups..."
cd "$BACKUP_DIR"
ls -t reconx_backup_*.tar.gz | tail -n +11 | xargs -r rm -f

BACKUP_COUNT=$(ls -1 reconx_backup_*.tar.gz 2>/dev/null | wc -l)
echo "💾 Total backups: $BACKUP_COUNT"

echo ""
echo "🎉 Backup complete!"
