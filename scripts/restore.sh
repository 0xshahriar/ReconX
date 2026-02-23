#!/data/data/com.termux/files/usr/bin/bash
# ReconX Restore Script
# Restore from backup archive

set -e

RECONX_DIR="$HOME/ReconX"
BACKUP_DIR="/sdcard/ReconX_Backups"

echo "📦 ReconX Restore"
echo "================="

# List available backups
if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A $BACKUP_DIR/*.tar.gz 2>/dev/null)" ]; then
    echo "❌ No backups found in $BACKUP_DIR"
    exit 1
fi

echo "Available backups:"
ls -lh "$BACKUP_DIR"/*.tar.gz | nl

echo ""
read -p "Enter backup number to restore: " choice

BACKUP_FILE=$(ls -1 "$BACKUP_DIR"/*.tar.gz | sed -n "${choice}p")

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Invalid selection"
    exit 1
fi

echo ""
echo "⚠️  WARNING: This will overwrite current ReconX data!"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Restore cancelled"
    exit 0
fi

# Create safety backup of current data
if [ -f "$RECONX_DIR/data/recon.db" ]; then
    SAFETY_BACKUP="$RECONX_DIR/data/recon.db.pre_restore.$(date +%s)"
    cp "$RECONX_DIR/data/recon.db" "$SAFETY_BACKUP"
    echo "🛡️  Safety backup created: $SAFETY_BACKUP"
fi

# Extract backup
echo "📂 Extracting backup..."
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Verify manifest
if [ ! -f "$TEMP_DIR/manifest.json" ]; then
    echo "❌ Invalid backup (no manifest)"
    exit 1
fi

echo "✓ Backup verified"

# Restore files
echo "🔄 Restoring files..."

# Restore database
if [ -f "$TEMP_DIR/recon.db" ]; then
    mkdir -p "$RECONX_DIR/data"
    cp "$TEMP_DIR/recon.db" "$RECONX_DIR/data/recon.db"
    echo "  ✓ Database restored"
fi

# Restore config
if [ -d "$TEMP_DIR/config" ]; then
    rm -rf "$RECONX_DIR/config"
    cp -r "$TEMP_DIR/config" "$RECONX_DIR/"
    echo "  ✓ Config restored"
fi

# Restore reports
if [ -d "$TEMP_DIR/reports" ]; then
    mkdir -p "$RECONX_DIR/reports"
    cp -r "$TEMP_DIR/reports/"* "$RECONX_DIR/reports/" 2>/dev/null || true
    echo "  ✓ Reports restored"
fi

echo ""
echo "🎉 Restore complete!"
echo "Please restart ReconX to apply changes."
