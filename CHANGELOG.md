# Changelog

Tüm dikkat çekici değişiklikler bu dosyada listelenir.

Format [Keep a Changelog](https://keepachangelog.com/) standardına dayanır;
sürüm numaralandırma [Semantic Versioning](https://semver.org/)'ı izler.

## [0.1.0] — 2026-05-25

İlk public sürüm. Faz 1 tamamen kapsanır: takip etmek istediğin TEFAS
fonlarını tek dashboard'da görselleştirir.

### Eklenenler

**Veri katmanı**
- TEFAS'ın 2026 sonrası yenilenen public JSON API'sine konuşan bağımlılıksız HTTP client (`backend/fonliman/tefas.py`)
  - `/api/funds/fonGetiriBazliBilgiGetir` — 1009 fonun pre-computed getirileri snapshot
  - `/api/funds/fonFiyatBilgiGetir` — fon başına NAV history + kategori sıralaması
  - `/api/funds/fonGnlBlgSiraliGetir` — günlük NAV + yatırımcı sayısı + AUM + pay sayısı
  - `/api/funds/dagilimSiraliGetirT` — 58 varlık sınıfı bazlı portföy dağılımı
- Otomatik exponential backoff + per-call sleep ile TEFAS throttle uyumu
- TEFAS mid-publish anomaly koruması (NAV=0 satırları reddedilir, all-zero return blokları None'a çevrilir, son iyi değerler COALESCE ile korunur)
- Allocation kodları için ~50 girişlik Türkçe etiket mapping'i

**Sync engine**
- Üç tetikleyici: (1) startup catch-up, (2) günlük APScheduler (varsayılan 22:30 IST), (3) manuel `/api/refresh`
- BIST tatil + hafta sonu aware
- Idempotent UPSERT'ler, in-process lock
- Yeni fon eklendiğinde tek-fon backfill thread'i

**Backend**
- FastAPI + Pydantic + SQLite (WAL modu)
- Gruplar CRUD, fonlar CRUD + TEFAS validation, birleşik `/api/dashboard` ve `/api/funds/{code}/detail` view'ları
- Listing endpoint için 10 dakikalık TTL cache (preview/add hızlı olsun diye)

**Frontend (React 19 + TypeScript + Tailwind + Recharts + SWR)**
- Apple-like UX: tabular figures, sistem fontu (SF Pro fallback), light/dark sistem tercihine göre
- **Dashboard**: gruplar ve fonların satır halinde listesi, her satırda büyük sparkline, fiyat, günlük/aylık/yıllık getiri chip'leri, kategori sıralaması
- **Detay sayfası**: 5 pencere toggle'lı interaktif NAV grafiği (1A/3A/6A/1Y/Hepsi), getiri tile'ları, portföy dağılımı bar grafiği, akıllı StatBox'lar (düz veriye chart çizmez)
- Inline grup oluşturma + düzenleme modalları
- TEFAS validate ile live preview'lu fon-ekleme modalı
- SWR conditional polling — backfill devam ederken dashboard otomatik refresh olur, F5 gerekmez
- Akıllı para formatı: ₺0,398112 (küçük NAV), ₺1.735,03 (büyük NAV), ₺1,16 mr (compact AUM)

**Deployment**
- Multi-stage Dockerfile (Node frontend build → Python runtime), final image ~140 MB
- `docker compose up -d` tek komut deploy
- Volume-mount'lu SQLite, env-configurable port (default 8765)
- Healthcheck dahil
- `restart: unless-stopped` ile boot'tan ayağa kalkma

**Tooling**
- macOS Spotlight launcher: `launcher/build.sh` ile `/Applications/fonliman.app` üretir, Cmd+Space → "fonliman" ile bir tıkta açılır
- SVG favicon → 10 boyutta .icns icon, retina dahil

**Dokümantasyon**
- Türkçe ağırlıklı README (ekran görüntüleri, mimari diyagramı, FAQ, yol haritası)
- Bilingual CONTRIBUTING.md (dev setup, kod konvansiyonları, PR akışı)
- Prototype dizininde TEFAS API keşif scriptleri (eğitici referans)

### Bilinen kısıtlamalar

- **Hisse fonları için top N pozisyon** — TEFAS public API'sinde sadece varlık sınıfı bazlı dağılım var (hisse %X), spesifik şirket adları yok. KAP entegrasyonu Faz 3'te.
- **Yönetim ücreti** — TEFAS'ın yeni public API'sinden çekilemiyor. Aynı şekilde gelecek sürümlerde KAP'tan.
- **Mobile** — Dashboard masaüstü için optimize. Small-screen breakpoint'ler eklenecek.
- **Test suite** — Henüz formal otomasyon testi yok. Manuel end-to-end Playwright doğrulamaları var.
- **i18n** — Sadece Türkçe.

[0.1.0]: https://github.com/tanyelai/fonliman/releases/tag/v0.1.0
