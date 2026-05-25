# Changelog

Dikkat çekici tüm değişiklikler burada.

Format [Keep a Changelog](https://keepachangelog.com/) standardını,
sürüm numaralandırma [Semantic Versioning](https://semver.org/)'ı izler.

## [0.1.0] — 2026-05-25

İlk public sürüm. Takip ettiğin TEFAS fonlarını tek dashboard'da
görselleştirir.

### Eklenenler

**Veri katmanı**
- TEFAS'ın 2026'da yenilenen public JSON API'sine konuşan, dışa bağımlılıksız HTTP client (`backend/fonliman/tefas.py`)
  - `/api/funds/fonGetiriBazliBilgiGetir` — 1009 fonun pre-computed getirileri snapshot
  - `/api/funds/fonFiyatBilgiGetir` — tek fon NAV history + kategori sıralaması
  - `/api/funds/fonGnlBlgSiraliGetir` — günlük NAV + yatırımcı sayısı + AUM + pay sayısı
  - `/api/funds/dagilimSiraliGetirT` — 58 varlık sınıfı portföy dağılımı
- TEFAS rate-limit'ine uyum: exponential backoff + istekler arası bekleme
- Mid-publish anomaly koruması — NAV=0 satırları reddediliyor, hepsi-sıfır getiri blokları None'a çevriliyor, son iyi değerler COALESCE ile korunuyor
- Allocation kodları için ~50 girişlik Türkçe etiket eşleştirmesi

**Senkron motoru**
- Üç tetikleyici: (1) açılışta catch-up, (2) günlük APScheduler (varsayılan 22:30 IST), (3) manuel `/api/refresh`
- BIST tatil + hafta sonu farkındalığı
- Idempotent UPSERT'ler, in-process lock
- Yeni fon eklenince tek-fon backfill thread'i

**Backend**
- FastAPI + Pydantic + SQLite (WAL modu)
- Gruplar CRUD, fonlar CRUD + TEFAS validation, birleşik `/api/dashboard` ve `/api/funds/{code}/detail` view'ları
- Listing endpoint için 10 dakikalık TTL cache (önizleme/ekleme hızlı olsun diye)

**Frontend (React 19 + TypeScript + Tailwind + Recharts + SWR)**
- Apple tarzı arayüz: tabular figures, sistem fontu, light/dark otomatik
- **Panel**: gruplar ve fonların satır halinde listesi, her satırda büyük sparkline, fiyat, günlük/aylık/yıllık getiri chip'leri, kategori sıralaması
- **Detay sayfası**: 5 pencere toggle'lı interaktif NAV grafiği (1A/3A/6A/1Y/Hepsi), getiri tile'ları, portföy dağılımı bar grafiği, akıllı StatBox'lar (sabit veriye grafik çizmiyor)
- Inline grup oluşturma + düzenleme modalları
- TEFAS validate ile canlı önizlemeli fon-ekleme modalı
- SWR'da koşullu polling — backfill sürerken panel otomatik yenileniyor, F5 gerekmiyor
- Akıllı para formatı: ₺0,398112 (küçük NAV), ₺1.735,03 (büyük NAV), ₺1,16 mr (toplam AUM)

**Deployment**
- Multi-stage Dockerfile (Node frontend build → Python runtime), son imaj ~140 MB
- `docker compose up -d` tek komut
- Volume-mount SQLite, port env değişkeniyle (varsayılan 8765)
- Healthcheck dahil
- `restart: unless-stopped` — boot'tan otomatik ayağa kalkar

**Araçlar**
- `setup.sh` — tek komutla kurulum: Docker imajını build eder, container'ı kaldırır, macOS'taysa Spotlight launcher'ını yükler, hazır olunca tarayıcıyı açar
- macOS Spotlight launcher: `launcher/build.sh` ile `/Applications/fonliman.app` üretiyor, `Cmd+Space → "fonliman"` ile tek tıkta açılıyor
- SVG favicon'dan 10 boyutta .icns icon (retina dahil)

**Dokümantasyon**
- Türkçe ağırlıklı README (ekran görüntüleri, mimari, FAQ, yol haritası)
- İki dilli CONTRIBUTING.md (dev kurulumu, kod konvansiyonları, PR akışı)
- Prototype klasöründe TEFAS API keşif scriptleri (eğitim amaçlı referans)

### Bilinen kısıtlamalar

- **Hisse fonları için top N pozisyon** yok — TEFAS public API'sinde sadece varlık sınıfı bazında dağılım var (hisse %X), spesifik şirket adları yok. KAP entegrasyonu Faz 3'te
- **Yönetim ücreti** TEFAS'ın yeni public API'sinden çekilemiyor; aynı şekilde KAP gerektirecek
- **Mobile breakpoint** yok — panel masaüstü için optimize
- **Otomatik test suite** yok — manuel end-to-end Playwright doğrulamaları var
- **i18n** yok — sadece Türkçe

[0.1.0]: https://github.com/tanyelai/fonliman/releases/tag/v0.1.0
