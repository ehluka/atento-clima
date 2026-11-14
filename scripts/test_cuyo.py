"""Prueba: fuentes de granizo en Cuyo (partes de Contingencias Mendoza + METAR de aeropuertos cuyanos)."""
import csv, io, json, re, time, urllib.request, urllib.parse, html
from collections import Counter
from datetime import datetime, timedelta
UA = {"User-Agent": "AtentoClima-research/1.0 (+https://github.com/ehluka/atento-clima)"}
def get(u, t=120, hdr=False):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t) as r:
        body = r.read().decode("utf-8", "replace")
        return (body, dict(r.headers)) if hdr else body

print("=== Prensa Gobierno de Mendoza (WordPress) ===")
base = "https://www.mendoza.gov.ar/prensa/wp-json/wp/v2/posts"
posts = []
try:
    for page in range(1, 40):
        q = urllib.parse.urlencode({"search": "granizo", "per_page": 100, "page": page, "after": "2018-08-01T00:00:00",
                                    "_fields": "date,title,link,content"})
        body, h = get(f"{base}?{q}", 120, True)
        data = json.loads(body)
        if page == 1: print("total según el sitio:", h.get("X-WP-Total"), "posts")
        if not data: break
        posts += data
        if len(data) < 100: break
except Exception as e:
    print("WP ERROR", e)
def clean(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
mit = [p for p in posts if re.search(r"mitigaci|antigranizo|granizo", clean(p["title"]["rendered"]), re.I)]
print("posts leídos:", len(posts), "| con granizo/mitigación en el título:", len(mit))
def season(d):
    y, m = int(d[:4]), int(d[5:7]); return f"{y}-{y+1}" if m >= 7 else f"{y-1}-{y}"
print("por temporada:", sorted(Counter(season(p["date"]) for p in mit).items()))
hits = [p for p in mit if re.search(r"granizo en|granizó|caída de granizo|lluvias? (fuertes|intensas)? ?y granizo|se detectó granizo|detectó caída de granizo", clean(p["content"]["rendered"]), re.I)]
print("partes que nombran lugares con granizo detectado:", len(hits))
for p in hits[:4]:
    t = clean(p["content"]["rendered"])
    print("\n---", p["date"], "|", clean(p["title"]["rendered"]))
    print(t[:1200])
json.dump([{"date": p["date"], "title": clean(p["title"]["rendered"]), "text": clean(p["content"]["rendered"]), "link": p["link"]} for p in mit], open("dcc_posts.json", "w"), ensure_ascii=False)

print("\n=== METAR aeropuertos de Cuyo (IEM) ===")
GR = re.compile(r"(?<![A-Z])[+-]?(?:TS|SH)?(?:RA)?GR(?![A-Z])")
cuyo = ["SAME", "SAMR", "SAMM", "SANU", "SAOU", "SAOR", "SANL", "SAMI", "SANI", "SAOD"]
q = urllib.parse.urlencode([("station", s) for s in cuyo] + [("data", "metar"), ("year1", 2018), ("month1", 8), ("day1", 1),
    ("year2", 2026), ("month2", 11), ("day2", 13), ("tz", "Etc/UTC"), ("format", "onlycomma"), ("latlon", "yes"),
    ("missing", "empty"), ("report_type", 3), ("report_type", 4)])
rows = list(csv.DictReader(io.StringIO(get("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?" + q, 600))))
print("METAR leídos:", len(rows), "| estaciones con datos:", sorted(Counter(r["station"] for r in rows).items()))
ev = []
for r in sorted(rows, key=lambda r: (r["station"], r["valid"])):
    body = r["metar"].split(" RMK")[0]
    if GR.search(body) and "VCGR" not in body:
        t = datetime.strptime(r["valid"], "%Y-%m-%d %H:%M")
        if ev and ev[-1][0] == r["station"] and t - ev[-1][2] <= timedelta(hours=3): ev[-1][2] = t
        else: ev.append([r["station"], t, t, body[:85]])
print("granizadas en aeropuertos de Cuyo:", len(ev), Counter(e[0] for e in ev))
for e in ev: print("  ", e[0], e[1].strftime("%Y-%m-%d %H:%M UTC"), "|", e[3])
