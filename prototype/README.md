# prototype/ — TEFAS API keşif scriptleri

Bu dizin v0.1.0 geliştirme sırasında TEFAS endpoint'lerinin nasıl çalıştığını
çıkarmak için yazılan scriptleri içerir. Üretim akışında kullanılmazlar — ama
TEFAS API'sini öğrenmek isteyen geliştiriciler için kalıcı referanstır.

| Script | Ne yapar |
|---|---|
| `fetch_funds.py` | `tefas-crawler` PyPI paketi ile temel veri çekme |
| `explore_columns.py` | tefas-crawler v0.6.0'da hangi kolonların hâlâ var olduğunu probe eder |
| `probe_tefas_site.py` | Legacy `BindHistory*` endpoint'lerinin retired olduğunu doğrular |
| `probe_listing.py` | `fonGetiriBazliBilgiGetir`'i (pre-computed getiriler) inceler |
| `probe_rich_endpoints.py` | `fonGnlBlgSiraliGetir` ve `dagilimSiraliGetirT`'yi ilk denemeler |
| `probe_rich_v2.py` | Aynı endpoint'ler ama pytefas'ın payload şekliyle (basTarih/bitTarih, YYYYMMDD) |
| `screenshot.py` | Çalışan UI'dan light/dark + dashboard/detail ekran görüntüsü alır |

## Çalıştırmak

```bash
cd prototype
uv venv && uv pip install --python .venv/bin/python tefas-crawler pandas playwright requests
.venv/bin/python probe_rich_v2.py
```

## Çıktıların nereye gittiği

`screens/` dizini playwright ekran görüntülerini barındırır (gitignored — README'ye
giden son screenshot'lar `../docs/`'a kopyalanır).
