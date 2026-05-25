# macOS launcher

Spotlight-aranabilir `fonliman.app` üretir. Çift tıklayınca:

1. Docker Desktop kapalıysa açar, daemon hazır olana kadar bekler (≤90 s)
2. `docker compose up -d` ile container'ı kaldırır
3. `/api/health` cevap verene kadar bekler
4. `http://localhost:8765` adresini default browser'da açar

## Kurulum

```bash
bash launcher/build.sh
```

Bu komut:
- `fonliman.applescript` şablonuna repo'nun yolunu gömer
- `osacompile` ile `.app` bundle'ı üretir
- Info.plist'i (CFBundleName, bundle id, sürüm) doldurur
- Varsa `fonliman.icns` ikonunu yerleştirir
- Sonucu `/Applications/fonliman.app` olarak kurar
- LaunchServices'i refreshler

Tek seferlik — repoyu taşırsan tekrar çalıştır.

## İkonu yeniden üretmek (opsiyonel)

`fonliman.icns` repo'ya commit edilmiş. Logoyu değiştirirsen
`frontend/public/favicon.svg`'i güncelle ve repo kökünden şu komutu çalıştır:

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

## Bir sorun varsa

| Belirti | Yapılacak |
|---|---|
| "Docker Desktop bulunamadı" | Önce Docker Desktop'ı App Store / docker.com'dan kurup bir kez aç |
| Cmd+Space'te `fonliman` çıkmıyor | `lsregister -f /Applications/fonliman.app` (build.sh zaten yapıyor) |
| Browser açılıyor ama "bağlantı reddedildi" | `docker logs fonliman` ile container loglarını bak |
| Logoyu değiştirdim ama Finder eski ikonu gösteriyor | `touch /Applications/fonliman.app` + Finder restart |
