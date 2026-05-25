#!/usr/bin/env bash
# fonliman tek komut kurulum
#
# Yaptıkları:
#   1. Docker'ın açık olduğunu doğrular
#   2. Image'i build eder (ilk seferde ~2-3 dk; sonraki çağrılarda cache'lenir)
#   3. Container'ı kaldırır
#   4. API hazır olana kadar bekler
#   5. macOS'taysa Spotlight launcher'ı (/Applications/fonliman.app) kurar
#   6. Tarayıcıda http://localhost:8765 açar
#
# Kullanım:
#   bash setup.sh
#
# İkinci kez çalıştırırsan: container'ı yeniden inşa etmez, hızlı çalışır.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

# 1. Docker hazır mı?
if ! command -v docker >/dev/null 2>&1; then
  echo "✗ Docker komutu bulunamadı."
  echo "  Önce Docker Desktop'ı kur: https://www.docker.com/products/docker-desktop"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker çalışmıyor. Açılıyor..."
  if [ "$(uname)" = "Darwin" ]; then
    open -ga Docker
    # Daemon'un cevap vermesini bekle (≤90 sn)
    for _ in $(seq 1 90); do
      sleep 1
      if docker info >/dev/null 2>&1; then break; fi
    done
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "✗ Docker daemon hazır olmadı. Docker Desktop'ı manuel aç ve tekrar dene."
    exit 1
  fi
fi

# 2-3. Image build + container start (idempotent)
echo "→ Container hazırlanıyor (ilk seferde 2-3 dakika sürebilir)..."
docker compose up -d --build

# 4. API hazır olana kadar bekle
echo "→ Backend cevap vermesi bekleniyor..."
PORT="${PORT:-8765}"
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:${PORT}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if ! curl -fsS "http://localhost:${PORT}/api/health" >/dev/null 2>&1; then
  echo "✗ Backend 30 saniyede cevap vermedi. 'docker logs fonliman' ile bak."
  exit 1
fi

# 5. macOS launcher
if [ "$(uname)" = "Darwin" ] && [ -f launcher/build.sh ]; then
  echo "→ macOS Spotlight launcher kuruluyor..."
  bash launcher/build.sh
fi

# 6. Browser'da aç
echo
echo "✓ fonliman hazır: http://localhost:${PORT}"
if [ "$(uname)" = "Darwin" ]; then
  echo "  Bundan sonra Cmd+Space → 'fonliman' → Enter ile açabilirsin."
  open "http://localhost:${PORT}"
fi
