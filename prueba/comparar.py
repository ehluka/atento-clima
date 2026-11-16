"""Compara Atento Clima (publicado) contra las páginas por ciudad de Piedra Libre, mismo momento."""
# v1.16
import re, time
from playwright.sync_api import sync_playwright
BASE = 'https://ehluka.github.io/atento-clima/'
PL = 'https://piedralibre.com.ar/granizo/'
C = [('san-luis/ciudad-de-san-luis', -33.30, -66.34), ('san-luis/villa-mercedes', -33.68, -65.46),
     ('san-luis/merlo', -32.34, -65.01), ('mendoza/ciudad-de-mendoza', -32.89, -68.83),
     ('mendoza/san-rafael', -34.62, -68.33), ('mendoza/general-alvear', -34.98, -67.70),
     ('cordoba/rio-cuarto', -33.13, -64.35), ('cordoba/ciudad-de-cordoba', -31.42, -64.18)]
def clean(t): return re.sub(r'\n\s*\n+', '\n', t).strip()
with sync_playwright() as p:
    b = p.chromium.launch()
    for slug, lat, lon in C:
        print('=' * 70, '\n#', slug, lat, lon, time.strftime('%H:%M:%S'))
        ctx = b.new_context(locale='es-AR', timezone_id='America/Argentina/Buenos_Aires', viewport=dict(width=390, height=844))
        pg = ctx.new_page()
        try:
            pg.goto(PL + slug, timeout=40000); pg.wait_for_timeout(3000)
            print('--- PIEDRA LIBRE ---'); print(clean(pg.inner_text('main') if pg.locator('main').count() else pg.inner_text('body'))[:2500])
        except Exception as e: print('PL error', e)
        ctx.close()
        ctx = b.new_context(geolocation=dict(latitude=lat, longitude=lon), permissions=['geolocation'], locale='es-AR', timezone_id='America/Argentina/Buenos_Aires', viewport=dict(width=390, height=844))
        pg = ctx.new_page()
        try:
            pg.goto(BASE); pg.wait_for_selector('.hero', timeout=40000); pg.wait_for_timeout(3000)
            print('--- ATENTO CLIMA ---'); print(clean(pg.inner_text('main') if pg.locator('main').count() else pg.inner_text('body'))[:2500])
        except Exception as e: print('AC error', e)
        ctx.close()
    b.close()
