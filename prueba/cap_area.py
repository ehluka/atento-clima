"""Diagnóstico: ¿dónde viene el nombre de la zona en los avisos CAP del SMN?"""
import re, urllib.request, xml.etree.ElementTree as ET
UA = {"User-Agent": "AtentoClima/1.0 (+https://github.com/ehluka/atento-clima)"}
g = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20).read()
idx = g("https://ssl.smn.gob.ar/CAP/AR.php").decode('utf8', 'replace')
links = re.findall(r'<link>([^<]+)</link>', idx)
print(len(links), 'links', links[:3])
for l in [x for x in links if 'xml' in x][:3]:
    x = g(l).decode('utf8', 'replace')
    for m in re.finditer(r'<area>(.*?)</area>', x, re.S):
        a = re.sub(r'<polygon>.*?</polygon>', '<polygon>…</polygon>', m.group(1), flags=re.S)
        print('---', l[-50:]); print(a[:800])
    print('INFO-PARAMS:', re.findall(r'<parameter>.*?</parameter>', x, re.S)[:6])
