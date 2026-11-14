"""Prueba: ¿qué fuentes de granizadas se pueden leer? (SAMHI, METAR de aeropuertos vía IEM, archivo GLM)."""
import csv, io, re, sys, time, urllib.request, urllib.parse, json
from collections import Counter, defaultdict

UA = {"User-Agent": "AtentoClima-research/1.0 (+https://github.com/ehluka/atento-clima)"}
def get(url, timeout=120):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()

print("=== SAMHI ===")
for u in ["https://samhi.cima.fcen.uba.ar/", "https://samhi.cima.fcen.uba.ar/publicHomePageText/list?id=PROJECTS"]:
    try:
        html = get(u, 40).decode("utf-8", "replace")
        title = re.search(r"<title>(.*?)</title>", html, re.S)
        links = sorted(set(re.findall(r'href="([^"#]+)"', html)))
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style).*?</\1>", " ", html)))
        print(u, "| título:", title.group(1).strip() if title else None)
        print("  links:", links[:80])
        print("  texto:", text[:1500])
        scripts = re.findall(r'src="([^"]+\.js[^"]*)"', html)
        print("  scripts:", scripts[:20])
    except Exception as e:
        print(u, "ERROR", e)

print("=== IEM METAR Argentina ===")
try:
    st = json.loads(get("https://mesonet.agron.iastate.edu/api/1/network/AR__ASOS.json", 60))
    stations = [(f["properties"]["sid"], f["properties"]["name"], f["geometry"]["coordinates"]) for f in st["features"]] if "features" in st else [(d["id"], d["name"], (d.get("longitude"), d.get("latitude"))) for d in st.get("data", [])]
    print("estaciones AR:", len(stations), stations[:6])
except Exception as e:
    print("red AR__ASOS ERROR", e); stations = []

hail_re = re.compile(r"(?<![A-Z])[+-]?(?:VC)?(?:TS|SH)?(?:RA|DZ)?(GR|GS)(?![A-Z])")
tot = Counter(); samples = []; obs = 0
for year in (2023, 2024):
    t0 = time.time()
    q = urllib.parse.urlencode([("network", "AR__ASOS"), ("data", "metar"), ("year1", year), ("month1", 9), ("day1", 1),
                                 ("year2", year + 1), ("month2", 4), ("day2", 1), ("tz", "Etc/UTC"), ("format", "onlycomma"),
                                 ("latlon", "yes"), ("missing", "empty"), ("report_type", 3), ("report_type", 4)])
    try:
        raw = get("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?" + q, 600).decode("utf-8", "replace")
        rows = list(csv.DictReader(io.StringIO(raw)))
        obs += len(rows)
        for r in rows:
            m = r.get("metar", "")
            body = m.split(" RMK")[0]
            if hail_re.search(body):
                tot[(r["station"], m and hail_re.search(body).group(1))] += 1
                if len(samples) < 15: samples.append((r["station"], r["valid"], body[:90]))
        print(f"temporada {year}-{year+1}: {len(rows)} METAR leídos en {time.time()-t0:.0f} s")
    except Exception as e:
        print("IEM", year, "ERROR", e)
print("METAR con granizo (estación, GR=granizo/GS=granizo chico):", sorted(tot.items(), key=lambda x: -x[1])[:30])
print("total METAR con GR:", sum(v for (s, k), v in tot.items() if k == "GR"), "| con GS:", sum(v for (s, k), v in tot.items() if k == "GS"), "| de", obs)
for s in samples: print("  ", s)

print("=== Archivo GLM GOES-16 (para eventos 2019-2024) ===")
try:
    xml = get("https://noaa-goes16.s3.amazonaws.com/?list-type=2&prefix=GLM-L2-LCFA/2019/342/18/", 60).decode()
    print("GOES-16 GLM 2019-12-08 18 UTC:", len(re.findall(r"<Key>", xml)), "archivos")
except Exception as e:
    print("GOES-16 ERROR", e)
