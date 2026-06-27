#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------------
# Orquestación completa en el VPS (Hostinger)
#   - Extracción (src.main): 3x/día, tras el scraper
#   - Publicación espaciada (src.publicar): cada hora 8–20
# El cerebro Python llama al extractor de precios (Node/Playwright), por eso
# instalamos también Node + las dependencias del proyecto hermano.
# -------------------------------------------------------

REPO_DIR="/opt/distribuidoras-con-descuentos"
APP_DIR="$REPO_DIR/ai-pipeline"
SCRAPER_DIR="$REPO_DIR/scrapening-ofertas"
LOG="/var/log/ai-pipeline.log"
PUBLOG="/var/log/ai-pipeline-publicar.log"

echo "1/5 · Dependencias de sistema (Python, FFmpeg, Node)..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv ffmpeg curl
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

echo "2/5 · Entorno Python..."
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --no-cache-dir -r "$APP_DIR/requirements.txt"

echo "3/5 · Extractor de precios (Node + Playwright)..."
cd "$SCRAPER_DIR"
npm install --omit=dev --no-audit --no-fund
npx playwright install --with-deps chromium

echo "4/5 · Logs..."
touch "$LOG" "$PUBLOG"

echo "5/5 · Listo. Pasos manuales:"
cat <<EOF

  cp $APP_DIR/.env.example $APP_DIR/.env && nano $APP_DIR/.env

  CRON (crontab -e):
    TZ=America/Santiago
    # Extracción: 3x/día (después del scraper de redes)
    30 8,13,19 * * *  cd $APP_DIR && .venv/bin/python -m src.main     >> $LOG 2>&1
    # Publicación espaciada: cada hora de 8 a 20 (1 datazo por corrida, mayor ahorro primero)
    0  8-20  * * *    cd $APP_DIR && .venv/bin/python -m src.publicar >> $PUBLOG 2>&1

Setup completo.
EOF
