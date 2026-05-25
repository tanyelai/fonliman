# fonliman

> **Kendi takip ettiğin TEFAS fonlarını tek ekranda.** Sade, hızlı, self-hosted.
> _Self-hosted dashboard for tracking your Turkish (TEFAS) investment funds._

`fonliman`, izlediğin yatırım fonlarının günlük getirilerini, kategori sıralamasını,
yatırımcı sayısını, fon büyüklüğünü ve portföy dağılımını **tek bir
dashboard'da** birleştirir. TEFAS sitesinde her fonu tek tek açmaktan kurtarır.

Tamamen lokalde çalışır — verin senin makinende kalır, hesap istemez.

![fonliman dashboard](docs/dashboard-light.png)

---

## Neden?

TEFAS'ın resmi web sitesinde fonlarını takip etmek için her birini tek tek
açıp aynı verileri tekrar tekrar görmek gerekiyor. Yatırımcı olarak senin
sorduğun sorular daha basit:

- "Bugün portföyüm ne durumda?"
- "Hangi fonum kategorisinde nerede duruyor?"
- "Geçen aydan beri fon büyüklüğü/yatırımcı sayısı nasıl evrildi?"
- "Bu fon ne tutuyor — hisse mi, repo mu, altın mı?"

`fonliman` bu soruları **bir ekranda** cevaplar.

## Özellikler

- **Gruplu dashboard** — Kendi taksonomini kur (ABD Hisse / BIST / Para Piyasası / Altın…). Her grupta fonların satır halinde fiyatı, sparkline'ı, günlük/aylık/yıllık getirisi, KIID risk skoru, kategori sıralaması.
- **Görsel-ağırlıklı detay sayfası** — Büyük interaktif NAV grafiği (1A / 3A / 6A / 1Y / Hepsi). Hover'da günlük NAV. Portföy dağılımı (50+ varlık sınıfı, Türkçe etiketlerle). Yatırımcı sayısı + AUM trend grafikleri.
- **Akıllı stat-box'lar** — Düz veride anlamsız grafik çizmez; sadece büyük rakam + caption gösterir. "Kategori sıralaması 3 / 190 — kategorinin üst %1,6'lık diliminde" gibi.
- **TEFAS otomatik sync** — Günde bir 22:30 İstanbul saatinde fiyatlar güncellenir. Uygulama açıldığında varsa eksik günleri otomatik backfill eder. Manuel "şimdi güncelle" butonu da var.
- **BIST tatil aware** — Türk milli + dini bayramları + hafta sonları biliyor, gereksiz TEFAS isteği atmaz.
- **Apple-like UX** — Tabular figures, sistem fontu, light/dark sistem tercihine göre, akıllı para formatı (₺0,398112 küçük fon · ₺1.735,03 büyük fon · ₺1,16 mr toplam).
- **Mac launcher** — `Cmd+Space → "fonliman" → Enter` ile bir tıkta açılır (opsiyonel).

## Hızlı başlangıç

### Docker (her platform)

```bash
git clone https://github.com/tanyelai/tefas.git fonliman
cd fonliman
docker compose up -d
open http://localhost:8765
```

Sağ üstteki **+ Fon ekle** ile TEFAS kodlarını (örn. `AOY`, `BDS`, `TP2`) eklemeye başla. Yeni fonun verisi arkada otomatik backfill olur, ~10 saniye içinde dashboard'da görünür.

`8765` portu sende kullanılıyorsa `.env` dosyasıyla değiştir:

```bash
echo "PORT=9876" > .env
docker compose up -d
```

`./data/fonliman.db` SQLite dosyası volume-mount'la container dışında durur — container'ı silsen bile verin kaybolmaz.

### macOS: Spotlight'tan tek tıkla aç

```bash
bash launcher/build.sh
```

`/Applications/fonliman.app` kurar. `Cmd+Space → "fonliman" → Enter` dediğinde Docker Desktop'ı gerekirse açar, container'ı kaldırır, browser'da `localhost:8765`'i açar. Detaylar: [`launcher/README.md`](launcher/README.md).

## Ekran görüntüleri

| Light | Dark |
|---|---|
| ![dashboard light](docs/dashboard-light.png) | ![dashboard dark](docs/dashboard-dark.png) |
| ![detail light](docs/detail-light.png) | ![detail dark](docs/detail-dark.png) |

## Nasıl çalışıyor?

```
       ┌──────────────────────────┐
       │  Docker container        │
       │  ┌────────────────────┐  │
       │  │  FastAPI (Python)  │  │
       │  │  /api/groups       │  │
       │  │  /api/funds        │  │
       │  │  /api/dashboard    │  │
       │  │  /api/refresh      │  │
       │  │  /     (React SPA) │  │
       │  ├────────────────────┤  │
       │  │  APScheduler       │  │
       │  │  daily 22:30 IST   │  │
       │  ├────────────────────┤  │
       │  │  TEFAS client      │──┼──→ tefas.gov.tr
       │  ├────────────────────┤  │
       │  │  SQLite (volume)   │  │
       │  └────────────────────┘  │
       └──────────────────────────┘
              ↓ :8765
         http://localhost
```

### Üç sync tetiği

1. **Startup catch-up** — uygulama açıldığında elindeki en yeni veriden bugüne kadar eksik günleri otomatik çeker. Mac uykuda kalmış olsa bile sen açtığında dolu olur.
2. **Daily scheduled** — günde bir 22:30 IST'de. Tatil günleri atlanır.
3. **Manuel refresh** — header'daki ↻ butonu.

İdempotent — aynı günü 100 kez çeksen veri çift olmaz.

### TEFAS endpoint'leri

TEFAS'ın 2026'da yenilenen public JSON API'sini kullanır (auth/key gerekmez):

| Endpoint | Ne verir |
|---|---|
| `/api/funds/fonGetiriBazliBilgiGetir` | 1009 fonun pre-computed getirileri (1A/3A/6A/YBD/1Y/3Y/5Y), risk skoru, kategori |
| `/api/funds/fonFiyatBilgiGetir` | Per-fon NAV history + kategori sıralaması (5 yıla kadar) |
| `/api/funds/fonGnlBlgSiraliGetir` | Per-fon günlük NAV + yatırımcı sayısı + AUM + pay sayısı |
| `/api/funds/dagilimSiraliGetirT` | Portföy dağılımı (58 varlık sınıfı) |

Rate-limit var — uygulama exponential backoff + per-call sleep yapar.

## Yapılandırma

Tüm ayarlar ortam değişkenleriyle (`.env` veya `docker compose` `environment`):

| Değişken | Default | Açıklama |
|---|---|---|
| `PORT` | `8765` | HTTP portu |
| `FONLIMAN_DATA_DIR` | `/data` | SQLite dosyasının yaşadığı klasör (Docker'da volume-mount) |
| `FONLIMAN_SYNC_HOUR` | `22` | Günlük sync saati (İstanbul) |
| `FONLIMAN_SYNC_MINUTE` | `30` | Günlük sync dakikası |

## Sık sorulan sorular

**Verim sızar mı?**
Hayır. Lokalde çalışır, hiçbir 3. parti servise veri yollamaz. Sadece TEFAS'ın kendi public endpoint'lerini çağırır.

**TEFAS hesabım gerekli mi?**
Hayır. TEFAS public endpoint'lerini auth olmadan kullanır — aynen TEFAS sitesinin kendi yaptığı gibi.

**Fiyatlar ne sıklıkta güncellenir?**
TEFAS fon NAV'larını günde bir, akşam (~21:30 IST) yayımlar. Intraday güncelleme yok. `fonliman` 22:30 IST'de güvenli aralıkta sync eder.

**Mac uykudaysa fiyat kaçırır mıyım?**
Kısa cevap: Hayır. Sen sonradan açtığında startup catch-up otomatik backfill yapar.

**Birden fazla portföy için kullanabilir miyim?**
Tek-kullanıcı için tasarlandı. Birden fazla profil için ileri sürümlerde ayrı container kaldırabilirsin (`PORT=9876` ile farklı port, ayrı `data/` dizini).

**Hisse fonum için hangi şirketleri tuttuğunu görebilir miyim?**
TEFAS'ın public API'sinde varlık sınıfı bazında dağılım var (hisse %X, yabancı hisse %Y) ama spesifik hisse adları yok. Bu Faz 3 yol haritasında — KAP entegrasyonu gerekecek.

**E-posta özet?**
Henüz yok, yol haritasında. Şimdilik app'i açtığında "on-open digest" düşünülüyor.

## Yol haritası

- [ ] Hedef ağırlık drift uyarısı (kullanıcı `target_pct` set ettiğinde portföy dağılımı kaymışsa)
- [ ] Daily/weekly digest sayfası — "dün ne oldu", "geçen hafta ne oldu" özetleri
- [ ] Opsiyonel SMTP e-posta gönderimi
- [ ] Hisse fonları için top N pozisyon (KAP entegrasyonu)
- [ ] Yönetim ücreti şeffaflığı
- [ ] Benchmark karşılaştırma (BIST100, S&P500, TLREF)
- [ ] CSV export
- [ ] Stopaj-aware net getiri

## Katkıda bulunma

Buyrun! Bug bildirmek, özellik önerisi yapmak, kod katkısı sunmak — hepsi açık. Geliştirme ortamını kurmak, kod konvansiyonları ve PR akışı için → [CONTRIBUTING.md](CONTRIBUTING.md).

## Teşekkür

- **TEFAS / Takasbank** — public veri sağladığı için. https://tefas.gov.tr
- **[burakyilmaz321/tefas-crawler](https://github.com/burakyilmaz321/tefas-crawler)** ve **[mirzazad/pytefas](https://github.com/mirzazad/pytefas)** — TEFAS API'sini açan referans implementasyonlar.

## Lisans

[MIT](LICENSE). TEFAS verileri Takasbank'a aittir — bu proje sadece kendi makinende kişisel kullanım için bir okuyucudur.

---

> _Built by [Toygar Tanyel](https://github.com/tanyelai). Issues & contributions welcome._
