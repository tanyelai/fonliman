# Katkı rehberi

`fonliman`'a katkıda bulunmak istediğin için teşekkürler. Bug bildirimi de,
özellik önerisi de, kod katkısı da memnuniyetle karşılanır. Bu dosya nereye
ne yazacağını ve nasıl PR açacağını anlatır.

_Contributions welcome. This guide covers issue filing, dev setup, code
conventions and the PR flow. Comments and commits can be in Turkish or
English — both are fine._

## Bug buldun mu?

[GitHub Issues](https://github.com/tanyelai/fonliman/issues)'a aç:

- **Ne yaptın** — adım adım nasıl tekrarlanır ("AOY fonunu ekledim, sonra…")
- **Ne bekliyordun**, **ne oldu**
- Mümkünse bir ekran görüntüsü
- Console log'u (`docker logs fonliman` veya tarayıcı DevTools)
- Platform bilgisi (macOS sürümü, Docker sürümü, tarayıcı)

## Yeni bir özellik öneriyor musun?

Yine [Issues](https://github.com/tanyelai/fonliman/issues)'a aç ama önce
[README'deki yol haritasını](README.md#yol-haritası) bir gözden geçir —
zaten planlanmış olabilir. Yoksa şunlara değin:

- Hangi problemi çözüyor?
- Hangi senaryoda ortaya çıkıyor?
- Başka çözüm yolu düşündün mü?

UX değişikliği, yazım düzeltmesi gibi küçük şeyler için doğrudan PR de
açabilirsin — issue açmak şart değil.

## Geliştirme ortamı

### Gerekenler

- **Python 3.11+** (3.13 önerilir)
- **Node 20+**
- **uv** (Python venv için kolaylık, opsiyonel)
- **Docker** (üretim build'ini test etmek için — geliştirme için zorunlu değil)

### Backend

```bash
git clone https://github.com/tanyelai/fonliman.git
cd fonliman

cd backend
uv venv && source .venv/bin/activate
uv pip install fastapi 'uvicorn[standard]' apscheduler requests pydantic holidays

PYTHONPATH=. uvicorn fonliman.main:app --reload --port 8765
```

İlk açılışta `./data/fonliman.db` oluşur.

### Frontend

```bash
cd frontend
npm install
npm run dev   # Vite dev server :5173'te
```

Vite, `/api/*` isteklerini `localhost:8765`'teki backend'e proxy'liyor.
`http://localhost:5173`'i aç, hot-reload ile geliştir.

### Tam build (üretim gibi)

```bash
cd frontend && npm run build       # → ../backend/fonliman/static
cd ../backend && PYTHONPATH=. python -m fonliman
# Ya da:
docker compose up -d --build
```

## Proje yapısı

```
fonliman/
├── backend/fonliman/
│   ├── tefas.py     # TEFAS HTTP client + allocation field mapping
│   ├── db.py        # SQLite şeması + DAO
│   ├── sync.py      # Üç tetikleyicili sync engine + APScheduler
│   ├── main.py      # FastAPI uygulaması + rotalar
│   ├── config.py    # env var yapılandırması
│   └── __main__.py  # uvicorn entry point
├── frontend/src/
│   ├── pages/       # Dashboard.tsx, FundDetail.tsx
│   ├── components/  # Header, GroupCard, FundRow, Sparkline, StatBox, modallar
│   ├── lib/         # api.ts, types.ts, format.ts
│   └── App.tsx, main.tsx, index.css
├── launcher/        # macOS .app launcher (Spotlight entegrasyonu)
├── docs/            # README ekran görüntüleri
├── prototype/       # TEFAS API keşif scriptleri (eğitim amaçlı referans)
├── setup.sh         # Tek komutla kurulum
└── Dockerfile, docker-compose.yml
```

## Kod konvansiyonları

### Python

- **Type hint zorunlu** — `from __future__ import annotations` her dosyada
- **PEP 8** + 100 sütun
- **Docstring**: NEDEN + NASIL + obvious olmayan tuzaklar. NE-YAPTIĞI zaten kodun kendisinde
- **Hata toleransı**: TEFAS'tan gelen veri pislik içerebilir — kullanılabilir değilse satırı sessizce skip et, sync'i kıllanma

### TypeScript / React

- **Functional component + hooks**, class component yok
- **SWR** server state için (Redux/Zustand kullanmıyoruz)
- **Tailwind utility class'ları**. Custom CSS sadece `.card`, `.btn`, `.pill` gibi semantik bileşenler için (`index.css`)
- **Türkçe arayüz metni** — Tailwind'in `uppercase` class'ı Türkçe'de `i → I` problemini yaratır; bunun yerine Title Case kullan
- **Tabular figures** sayı kolonlarında (`tabular` className)
- **Cömert boşluk** — Apple-tarzı = bol whitespace, nazik border, az renk

### Commit mesajları

[Conventional Commits](https://www.conventionalcommits.org/) tavsiye edilir
ama zorunlu değil:

```
feat: detay sayfasına benchmark karşılaştırma grafiği eklendi
fix: price-only sync investor_count'ü silmesin
docs: TEFAS rate-limit davranışını README'de netleştir
refactor: sparkline'ı paylaşımlı bileşene çıkar
```

İngilizce de OK:

```
feat: add benchmark comparison chart on detail page
fix: nav_history upsert preserves investor_count on price-only refresh
```

## PR akışı

1. **Fork + branch**: `git checkout -b feature/benchmark-karsilastirma`
2. **Küçük tut**: 200-400 satır altı PR'lar hızlı incelenir. Birden çok konuyu tek PR'da paketleme
3. **Test et**:
   - Backend: en azından `python -c "from fonliman.tefas import TefasClient; TefasClient().list_funds()"` ile import sağlam mı bak
   - Frontend: `npm run build` hatasız mı
   - Tam build: `docker compose up -d --build` ile container sağlıklı mı (`docker ps` → `healthy`)
4. **UI değişikliği yapıyorsan ekran görüntüsü ekle**
5. **PR aç** — açıklamada ne değişti, neden, ekran görüntüsü (UI ise)

Henüz otomatik test suite yok. `pytest` ve `vitest` eklemek isteyene açığım.

## Yardım istenen alanlar (good first issues)

- **Test suite** — backend için pytest, frontend için vitest + react-testing-library
- **CI** — GitHub Actions: Docker build + smoke test
- **Linting** — Python için `ruff`, TS için `eslint` + `prettier`
- **Mobile breakpoint** — paneli küçük ekranlara uydur
- **i18n** — şu an Türkçe-sabit; en azından bir EN locale eklemek
- **Code splitting** — frontend bundle 666 KB; Recharts'ı async import et
- **Allocation kod mapping** — `backend/fonliman/tefas.py`'deki `ALLOCATION_LABELS` "best-effort"; bazı kodlar henüz eşleşmemiş, daha doğru Türkçe etiket bulabilirsin

İlgini çeken bir başlık varsa issue aç, "Ben bunu üstleniyorum" diye yaz, başla.

## Sorun mu var?

[GitHub Discussions](https://github.com/tanyelai/fonliman/discussions) (henüz açıksa) ya da yeni bir issue.

Teşekkürler! 🙏
