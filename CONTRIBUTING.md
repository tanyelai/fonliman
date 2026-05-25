# Katkıda bulunma rehberi

`fonliman`'a katkı için teşekkürler! Hem bug raporları, hem özellik önerileri, hem
de kod katkıları bekleniyor. Bu dosya nereye ne yazacağını ve nasıl PR
açacağını anlatır.

_Contributions welcome. This guide covers issue filing, dev setup, code
conventions and the PR flow. Comments and commits can be in Turkish or
English — both are accepted._

## Bir bug buldun mu?

[GitHub Issues](https://github.com/tanyelai/tefas/issues)'a aç:

- **Ne yaptın** (reprodüksiyon adımları — "AOY fonunu ekledim, …")
- **Ne bekliyordun** vs **ne oldu**
- Mümkünse ekran görüntüsü
- Console log'u (`docker logs fonliman` veya browser DevTools)
- Çalıştığın platform (macOS sürümü, Docker sürümü, browser)

## Bir özellik mi öneriyorsun?

Yine [Issues](https://github.com/tanyelai/tefas/issues)'a aç ama önce yol haritasını
([README'deki "Yol haritası"](README.md#yol-haritası)) bir tara — zaten planlanmış olabilir. Plan'da yoksa:

- Hangi problemi çözüyor?
- Hangi kullanıcı senaryosunda ortaya çıkıyor?
- Alternatif çözüm düşündün mü?

Küçük (UX iyileştirmesi, copy düzeltmesi) için doğrudan PR de olur — issue
açmadan.

## Geliştirme ortamı

### Gereksinimler

- **Python 3.11+** (3.13 önerilir)
- **Node 20+**
- **uv** (Python venv yönetimi için tavsiye, opsiyonel)
- **Docker** (üretim build'i test etmek için, geliştirme için zorunlu değil)

### Backend kurulumu

```bash
git clone https://github.com/tanyelai/tefas.git
cd tefas

# Python venv ve bağımlılıklar
cd backend
uv venv && source .venv/bin/activate
uv pip install fastapi 'uvicorn[standard]' apscheduler requests pydantic holidays

# Backend'i ayağa kaldır (frontend dev server için 5173'e ayarlı, yine 8765'te çalışır)
PYTHONPATH=. uvicorn fonliman.main:app --reload --port 8765
```

Veritabanı `./data/fonliman.db`'de oluşur (ilk açılışta).

### Frontend kurulumu

```bash
cd frontend
npm install
npm run dev  # Vite dev server :5173'te
```

Vite, `/api/*` çağrılarını `localhost:8765`'teki backend'e proxy'ler. `http://localhost:5173`'i aç, hot-reload ile geliştir.

### Tam build (production gibi)

```bash
cd frontend && npm run build       # → ../backend/fonliman/static
cd ../backend && PYTHONPATH=. python -m fonliman
# Veya:
docker compose up -d --build
```

## Proje yapısı

```
fonliman/
├── backend/fonliman/
│   ├── tefas.py     # TEFAS HTTP client + allocation field mapping
│   ├── db.py        # SQLite schema + DAO
│   ├── sync.py      # 3-trigger sync engine + APScheduler
│   ├── main.py      # FastAPI app + routes
│   ├── config.py    # env var configuration
│   └── __main__.py  # uvicorn entry point
├── frontend/src/
│   ├── pages/       # Dashboard.tsx, FundDetail.tsx
│   ├── components/  # Header, GroupCard, FundRow, Sparkline, StatBox, modals
│   ├── lib/         # api.ts, types.ts, format.ts
│   └── App.tsx, main.tsx, index.css
├── launcher/        # macOS .app launcher (Spotlight integration)
├── docs/            # README ekran görüntüleri
├── prototype/       # TEFAS API keşif scriptleri (eğitici referans)
└── Dockerfile, docker-compose.yml
```

## Kod konvansiyonları

### Python

- **Type hints zorunlu** — `from __future__ import annotations` her dosyada.
- **PEP 8** + 100 sütun.
- **Docstring**: "WHY" + "HOW" + non-obvious caveats. "WHAT" zaten kodun kendisi.
- **Hata yönetimi**: TEFAS'tan gelen veri kirli olabilir — düzgün rakam değilse satırı sessizce skip et, sync'i kıllanma.

### TypeScript / React

- **Functional components + hooks**, class component yok.
- **SWR** sunucu state'i için (Redux/Zustand kullanmıyoruz).
- **Tailwind utility classes**. Custom CSS sadece `.card`, `.btn`, `.pill` gibi semantic component'ler için (`index.css`).
- **Türkçe arayüz metni** — `i → İ` problemini önlemek için `text-transform: uppercase` yerine Title Case kullan.
- **Tabular figures** sayı kolonlarında (`tabular` className).
- **Akıllı boşluk** — Apple-like UX = bol whitespace, subtle border, az renk.

### Commit mesajları

[Conventional Commits](https://www.conventionalcommits.org/) önerilir ama zorunlu değil:

```
feat: add benchmark comparison chart on detail page
fix: nav_history upsert preserves investor_count on price-only refresh
docs: clarify TEFAS rate-limit behavior in README
refactor: extract sparkline rendering into a shared component
```

Türkçe de OK:

```
feat: detay sayfasında benchmark karşılaştırma grafiği eklendi
fix: price-only sync'te investor_count silinmesin
```

## Pull request akışı

1. **Fork + branch**: `git checkout -b feature/benchmark-karsilastirma`
2. **Küçük tut**: 200-400 satır altı PR'lar daha hızlı review olur. Birden çok konuyu tek PR'da paketleme.
3. **Test et**:
   - Backend: en az `python -c "from fonliman.tefas import TefasClient; TefasClient().list_funds()"` ile import sağlam
   - Frontend: `npm run build` hatasız
   - Tam build: `docker compose up -d --build` ile container sağlıklı (`docker ps` → `healthy`)
4. **Screenshot ekle** UI değişikliklerine
5. **PR aç** — açıklamaya: ne değişti, neden, ekran görüntüsü (UI ise)

Henüz formal test suite yok. `pytest` / `vitest` eklemek isteyen olursa kabul.

## Bir alana yardım istenenler (good first issues)

- **Test suite** — backend için pytest, frontend için vitest + react-testing-library
- **CI** — GitHub Actions: Docker build + smoke test
- **Linting** — `ruff` Python için, `eslint` + `prettier` TS için
- **Mobile breakpoint** — dashboard'ı küçük ekranlara optimize et
- **i18n** — şu an Türkçe-sabit; en azından bir EN locale eklemek
- **Code splitting** — frontend bundle 666 KB; Recharts'ı async import et
- **Allocation code mapping** — `backend/fonliman/tefas.py`'deki `ALLOCATION_LABELS` "best-effort" — bazı kodlar henüz mapping'siz, daha doğru Türkçe etiketler bul

İlgini çeken bir başlık varsa issue aç, "I want to take this" diye yaz, başla.

## Soruların mı var?

[GitHub Discussions](https://github.com/tanyelai/tefas/discussions) (varsa) veya yeni bir issue.

Teşekkürler! 🙏
