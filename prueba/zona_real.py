"""Prueba la versión nueva (prueba/site) con datos reales: alertas y rayos del sitio publicado y nombres reales."""
import os, subprocess, time, urllib.request
from playwright.sync_api import sync_playwright
os.makedirs('prueba/site/data', exist_ok=True)
for f in ('alerts.json', 'rayos.json'):
    open('prueba/site/data/' + f, 'wb').write(urllib.request.urlopen('https://ehluka.github.io/atento-clima/data/%s?t=%d' % (f, time.time())).read())
srv = subprocess.Popen(['python3', '-m', 'http.server', '8765', '-d', 'prueba/site'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, lat, lon in [('sl_dias', -33.30, -66.34)]: #[('mendoza', -32.89, -68.83), ('san_luis', -33.30, -66.34), ('lujan', -33.04, -68.88), ('maipu', -32.98, -68.79), ('godoy_cruz', -32.93, -68.85)]:
        ctx = b.new_context(geolocation=dict(latitude=lat, longitude=lon), permissions=['geolocation'], locale='es-AR', timezone_id='America/Argentina/Buenos_Aires', viewport=dict(width=360, height=800), device_scale_factor=2, service_workers='block')
        ctx.add_init_script("localStorage.setItem('ac.places', JSON.stringify([{id:'sl',name:'Villa Mercedes',lat:-33.68,lon:-65.46,prov:'San Luis'}]))")
        pg = ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append('PAGEERR ' + str(e))); pg.on('response', lambda r: r.status >= 400 and errs.append(f'{r.status} {r.url[:90]}')); pg.on('requestfailed', lambda r: errs.append('FAIL ' + r.url[:90])); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        pg.goto('http://localhost:8765/')
        try: pg.wait_for_selector('.hero', timeout=30000)
        except Exception: print('SIN HERO', errs, pg.inner_html('body')[:900]); ctx.close(); continue
        pg.wait_for_timeout(4000)
        pg.screenshot(path=f'prueba/{name}_top.png')
        al = pg.locator('section.card.alert')
        zs = pg.eval_on_selector_all('.zone', 'es => es.map(e => e.dataset.z + "=" + e.textContent)'); print('  zonas:', zs, pg.evaluate('localStorage.getItem("ac.zones")'))
        print(f'[{name}] titular: {pg.inner_text(".hero-head")!r}\n  alertas: {al.inner_text().replace(chr(10), " | ")[:700]}\n  errores: {errs}')
        al.screenshot(path=f'prueba/zona_{name}.png')
        if name == 'sl_dias':
            for k in (1, 2):
                pg.locator('.days summary').nth(k).click(); pg.wait_for_timeout(300)
            pg.locator('section.card:has-text("Próximos días")').screenshot(path='prueba/sl_dias.png')
            print('  dias:', pg.eval_on_selector_all('.d-txt', 'es => es.map(e => e.textContent)'))
        ctx.close()
    b.close()
srv.terminate()

