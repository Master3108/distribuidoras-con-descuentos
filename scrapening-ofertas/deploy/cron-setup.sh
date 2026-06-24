#!/bin/bash
# Setup cron job for scrapening-ofertas on VPS
# Runs 3x daily: 8:00, 13:00, 19:00 (America/Santiago)

# Set timezone
timedatectl set-timezone America/Santiago 2>/dev/null || true

# Add cron entry
CRON_JOB="0 8,13,19 * * * cd /opt/scrapening-ofertas && node src/main.js >> /var/log/scrapening-ofertas.log 2>&1"

# Check if already installed
if crontab -l 2>/dev/null | grep -q "scrapening-ofertas"; then
    echo "Cron job already installed"
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cron job installed: $CRON_JOB"
fi
