"""Prueba la versión nueva (prueba/site) con datos reales: alertas y rayos del sitio publicado y nombres reales."""
import os, subprocess, time, urllib.request
from playwright.sync_api import sync_playwright
os.makedirs('prueba/site/data', exist_ok=True)
for f in ('alerts.json', 'rayos.json'):
    open('prueba/site/data/' + f, 'wb').write(urllib.request.urlopen('https://ehluka.github.io/atento-clima/data/%s?t=%d' % (f, time.time())).read())
srv = subprocess.Popen(['python3', '-m', 'http.server', '8765', '-d', 'prueba/site'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, lat, lon in [('mendoza', -32.89, -68.83), ('san_luis', -33.30, -66.34), ('lujan', -33.04, -68.88), ('alvear', -34.98, -67.70)]:
        ctx = b.new_context(geolocation=dict(latitude=lat, longitude=lon), permissions=['geolocation'], locale='es-AR', timezone_id='America/Argentina/Buenos_Aires', viewport=dict(width=390, height=844), device_scale_factor=2, service_workers='block')
        pg = ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://localhost:8765/'); pg.wait_for_selector('.hero', timeout=40000); pg.wait_for_timeout(4000)
        al = pg.locator('section.card.alert')
        print(f'[{name}] titular: {pg.inner_text(".hero-head")!r}\n  alertas: {al.inner_text().replace(chr(10), " | ")[:700]}\n  errores: {errs}')
        al.screenshot(path=f'prueba/zona_{name}.png'); ctx.close()
    b.close()
srv.terminate()
