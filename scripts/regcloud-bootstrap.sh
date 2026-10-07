#!/bin/bash
# Первичная настройка VM Рег.облако под сводку отчётов (Docker + nginx).
# Запуск на сервере: bash regcloud-bootstrap.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/reports}"
REPO_URL="${REPO_URL:-https://github.com/a50petr-cmd/Tanya_work.git}"
DOMAIN="${DOMAIN:-}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get upgrade -y
apt-get install -y docker.io docker-compose-plugin git nginx certbot python3-certbot-nginx ufw curl

systemctl enable --now docker

if ! ufw status | grep -q "Status: active"; then
  ufw allow OpenSSH
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw allow from 2a02:6b8:c00::/40 to any port 443 proto tcp comment "Yandex Forms"
  ufw --force enable
fi

mkdir -p "$APP_DIR"
if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
mkdir -p data

if [[ ! -f .env ]]; then
  cp .env.example .env
  sed -i 's|^DATABASE_PATH=.*|DATABASE_PATH=/data/reports.db|' .env
  echo ""
  echo ">>> Отредактируйте $APP_DIR/.env (токен бота, секрет формы, EMPLOYEES), затем:"
  echo "    cd $APP_DIR && docker compose up -d --build"
  echo ""
fi

docker compose up -d --build || true

if [[ -n "$DOMAIN" ]]; then
  cat > "/etc/nginx/sites-available/reports" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
  ln -sf /etc/nginx/sites-available/reports /etc/nginx/sites-enabled/reports
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl reload nginx
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m admin@"$DOMAIN" || true
fi

echo "Health (local): $(curl -sS http://127.0.0.1:8080/health || echo fail)"
echo "IPv6 on host: $(ip -6 addr show scope global 2>/dev/null | awk '/inet6/{print $2}' | head -1 || echo 'не найден — закажите IPv6 в панели')"
