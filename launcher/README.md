# macOS launcher

Spotlight'tan aratılabilen `fonliman.app` üretir. Çift tıklayınca:

1. Docker Desktop kapalıysa açar, daemon hazır olana kadar bekler (90 saniyeye kadar)
2. `docker compose up -d` ile container'ı kaldırır
3. `/api/health` cevap verene kadar bekler
4. `http://localhost:8765` adresini varsayılan tarayıcıda açar

## Kurulum

Normal akış: repo kökünden `bash setup.sh` çalıştır — launcher otomatik
kurulur. Sadece launcher'ı yeniden derlemek istersen:

```bash
bash launcher/build.sh
```

Bu komut:

- `fonliman.applescript` şablonuna repo yolunu gömer
- `osacompile` ile `.app` paketini üretir
- Info.plist alanlarını (CFBundleName, bundle id, sürüm) doldurur
- Varsa `fonliman.icns` ikonunu yerine kopyalar
- Sonucu `/Applications/fonliman.app` olarak kurar
- LaunchServices önbelleğini yeniler

Tek seferlik bir iş — repoyu başka bir klasöre taşırsan tekrar çalıştırman gerek.

## İkonu yeniden üretmek (opsiyonel)

`fonliman.icns` zaten repo'da. Logoyu değiştirirsen `frontend/public/favicon.svg`'i
güncelle ve repo kökünden şunu çalıştır:

```bash
prototype/.venv/bin/python -c "
import asyncio, pathlib
from playwright.async_api import async_playwright
SVG = pathlib.Path('frontend/public/favicon.svg').read_text()
SIZES = [('icon_16x16.png',16),('icon_16x16@2x.png',32),('icon_32x32.png',32),
         ('icon_32x32@2x.png',64),('icon_128x128.png',128),('icon_128x128@2x.png',256),
         ('icon_256x256.png',256),('icon_256x256@2x.png',512),('icon_512x512.png',512),
         ('icon_512x512@2x.png',1024)]
async def main():
    out = pathlib.Path('launcher/fonliman.iconset'); out.mkdir(exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, sz in SIZES:
            page = await b.new_page(viewport={'width':sz,'height':sz})
            await page.set_content(f'<html><body style=margin:0>{SVG.replace(\"<svg\",f\"<svg width={sz} height={sz}\")}</body></html>')
            await page.screenshot(path=str(out/name), omit_background=True)
        await b.close()
asyncio.run(main())
"
iconutil -c icns launcher/fonliman.iconset -o launcher/fonliman.icns
bash launcher/build.sh
```

## Sorun çıkarsa

| Belirti | Çözüm |
|---|---|
| "Docker Desktop bulunamadı" | Önce Docker Desktop'ı kur (docker.com) ve bir kez aç |
| Spotlight'ta `fonliman` çıkmıyor | `lsregister -f /Applications/fonliman.app` (build.sh zaten yapıyor) |
| Tarayıcı açılıyor ama "bağlantı reddedildi" diyor | `docker logs fonliman` ile log'lara bak |
| Logo'yu değiştirdim, Finder eskisini gösteriyor | `touch /Applications/fonliman.app` + Finder'ı yeniden başlat |
