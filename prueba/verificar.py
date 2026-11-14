"""Verifica el sitio publicado: versión, datos de rayos y la app real en un navegador (sin simular nada)."""
import json, time, urllib.request, gzip
from collections import Counter
from playwright.sync_api import sync_playwright
BASE = 'https://ehluka.github.io/atento-clima/'
def get(u, gz=False):
    r = urllib.request.urlopen(urllib.request.Request(u, headers={'Accept-Encoding': 'gzip'} if gz else {}), timeout=30)
    return r, r.read()
_, html = get(BASE + 'index.html?x=%d' % time.time()); html = html.decode()
print('index:', 'v1.11' in html and 'Atento Clima v1.11' or 'VERSION?', '| NOAA en pie:', 'NOAA (GOES-19)' in html)
_, sw = get(BASE + 'sw.js?x=%d' % time.time()); print('sw:', 'ac-v12' in sw.decode())
r, raw = get(BASE + 'data/rayos.json?t=%d' % time.time(), gz=True)
enc = r.headers.get('Content-Encoding'); body = gzip.decompress(raw) if enc == 'gzip' else raw
d = json.loads(body)
print(f"rayos.json: {len(raw)//1024} KB transferidos (Content-Encoding={enc}), {len(body)//1024} KB, datos de hace {int(time.time()//60) - d['t0']} min, {len(d['f'])} puntos")
c = Counter()
for la, lo, ago, n in d['f']:
    if ago < 10: c[(round(la / 10) / 10, round(lo / 10) / 10)] += n
spot = c.most_common(1)[0][0] if c else (-31.42, -64.18)
_, al = get(BASE + 'data/alerts.json?t=%d' % time.time()); a = json.loads(al)
print('alerts.json:', len(a['alerts']), 'alertas, faltan', a.get('faltan'), '| actualizado', a['updated'])
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, (lat, lon) in [('tormenta', spot), ('mendoza', (-32.89, -68.83))]:
        ctx = b.new_context(geolocation=dict(latitude=lat, longitude=lon), permissions=['geolocation'], viewport=dict(width=390, height=844), device_scale_factor=2, locale='es-AR', timezone_id='America/Argentina/Buenos_Aires')
        pg = ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        pg.goto(BASE); pg.wait_for_selector('.hero', timeout=40000); pg.wait_for_timeout(2500)
        row = pg.locator('.card.ray-mini')
        print(f"[{name}] {lat},{lon} | titular: {pg.inner_text('.hero-head')!r} | fila: {row.first.inner_text().replace(chr(10), ' | ') if row.count() else 'NO HAY FILA'} | errores: {errs}")
        pg.screenshot(path=f'prueba/live_{name}.png')
        if row.count() and row.first.locator('summary').count():
            row.first.locator('summary').first.click(); pg.wait_for_timeout(500); row.first.screenshot(path=f'prueba/live_{name}_abierta.png')
        ctx.close()
    b.close()
