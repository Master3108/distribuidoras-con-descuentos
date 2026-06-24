#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------------
# ai-pipeline VPS setup
# VPS: 72.60.245.87 (Hostinger)
# Cron: 8:30, 13:30, 19:30 America/Santiago
# -------------------------------------------------------

APP_DIR="/opt/distribuidoras-con-descuentos/ai-pipeline"
LOG_FILE="/var/log/ai-pipeline.log"
PYTHON_BIN="python3"

echo "Installing system dependencies..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv ffmpeg

echo "Creating app directory..."
mkdir -p "$APP_DIR"

echo "Setting up Python virtualenv..."
"$PYTHON_BIN" -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --no-cache-dir -r "$APP_DIR/requirements.txt"

echo "Creating log file..."
touch "$LOG_FILE"

echo ""
echo "-------------------------------------------------------"
echo "MANUAL STEP: Create .env from .env.example"
echo "  cp $APP_DIR/.env.example $APP_DIR/.env"
echo "  nano $APP_DIR/.env"
echo "-------------------------------------------------------"
echo ""
echo "CRON SETUP (run: crontab -e):"
echo "  TZ=America/Santiago"
echo "  30 8,13,19 * * * cd $APP_DIR && .venv/bin/python -m src.main >> $LOG_FILE 2>&1"
echo ""
echo "Setup complete."
