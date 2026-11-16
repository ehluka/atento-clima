"""Verifica qué versión está publicada (sin caché)."""
import time, urllib.request
B = 'https://ehluka.github.io/atento-clima/'
g = lambda f: urllib.request.urlopen(urllib.request.Request(B + f + '?x=%d' % time.time(), headers={'Cache-Control': 'no-cache'}), timeout=30)
r = g('sw.js'); s = r.read().decode(); print('sw:', [l for l in s.splitlines() if 'const V' in l], '| age', r.headers.get('Age'), r.headers.get('Last-Modified'))
r = g('index.html'); h = r.read().decode(); print('index:', 'v1.14' in h, [l.strip() for l in h.splitlines() if 'Atento Clima v' in l])
a = g('app.js').read().decode(); print('app.js: zoneTag', 'zoneTag' in a, '| fillZones', 'fillZones' in a, '| smnNear', 'smnNear' in a, '| 1.14', "'1.14'" in a)
