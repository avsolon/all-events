#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "=== All Events — Deploy ==="

# 1. Check .env
if [ ! -f .env ]; then
    if [ -f .env.production ]; then
        echo "[!] .env not found. Copying from .env.production..."
        cp .env.production .env
        echo "[!] Edit .env with your settings and re-run."
        exit 1
    else
        echo "[!] .env not found. Create it from .env.production"
        exit 1
    fi
fi

# 2. Pull latest images and rebuild
echo "[+] Building and starting containers..."
docker compose build
docker compose up -d

# 3. Wait for DB
echo "[+] Waiting for database..."
sleep 5

# 4. Run initial scrape
echo "[+] Running initial scrape..."
docker compose run --rm scraper

# 5. Status
echo ""
echo "=== Deploy complete ==="
echo "Web:   http://localhost:8090"
echo "DB:    localhost:5433"
echo ""
echo "Nginx: скопируйте deploy/nginx/all-events.conf в /etc/nginx/sites-available/"
echo "       и выполните: sudo ln -s /etc/nginx/sites-available/all-events.conf /etc/nginx/sites-enabled/"
echo "       затем: sudo nginx -t && sudo systemctl reload nginx"
docker compose ps
