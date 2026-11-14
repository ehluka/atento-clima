"""Cuenta granizadas en METAR de aeropuertos argentinos (IEM) para las temporadas con satélite GLM (2018-2026)."""
import csv, io, re, time, urllib.request, urllib.parse, json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
UA = {"User-Agent": "AtentoClima-research/1.0 (+https://github.com/ehluka/atento-clima)"}
def get(u, t=600):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t) as r: return r.read().decode("utf-8", "replace")
GR = re.compile(r"(?<![A-Z])[+-]?(?:VC)?(?:TS|SH)?(?:RA)?GR(?![A-Z])")
GS = re.compile(r"(?<![A-Z])[+-]?(?:VC)?(?:TS|SH)?(?:RA)?GS(?![A-Z])")
TS = re.compile(r"(?<![A-Z])[+-]?(?:VC)?TS")
pos, gs_warm, ts_obs = [], [], []
per_season = {}
for y in range(2018, 2026):
    q = urllib.parse.urlencode([("network", "AR__ASOS"), ("data", "metar"), ("data", "tmpf"), ("year1", y), ("month1", 9), ("day1", 1),
        ("year2", y + 1), ("month2", 5), ("day2", 1), ("tz", "Etc/UTC"), ("format", "onlycomma"), ("latlon", "yes"),
        ("missing", "empty"), ("report_type", 3), ("report_type", 4)])
    rows = list(csv.DictReader(io.StringIO(get("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?" + q))))
    n_gr = n_ts = 0
    for r in rows:
        body = r["metar"].split(" RMK")[0]
        if VCfree := True:
            pass
        t = datetime.strptime(r["valid"], "%Y-%m-%d %H:%M")
        rec = (r["station"], t, float(r["lat"]), float(r["lon"]), body)
        if GR.search(body) and "VCGR" not in body:
            pos.append(rec); n_gr += 1
        elif GS.search(body) and r["tmpf"] and float(r["tmpf"]) >= 59 and TS.search(body):
            gs_warm.append(rec)
        elif TS.search(body):
            ts_obs.append(rec); n_ts += 1
    per_season[f"{y}-{y+1}"] = (len(rows), n_gr, n_ts)
    print(f"{y}-{y+1}: {len(rows)} METAR, {n_gr} con granizo (GR), {n_ts} con tormenta sin granizo", flush=True)

def events(recs, gap_h=3):
    recs = sorted(recs, key=lambda x: (x[0], x[1])); ev = []
    for s, t, la, lo, b in recs:
        if ev and ev[-1]["st"] == s and t - ev[-1]["end"] <= timedelta(hours=gap_h):
            ev[-1]["end"] = t
        else:
            ev.append({"st": s, "start": t, "end": t, "lat": la, "lon": lo, "metar": b})
    return ev
E = events(pos); G = events(gs_warm); T = events(ts_obs)
print(f"\nEVENTOS DE GRANIZO (GR) distintos: {len(E)} en {len({e['st'] for e in E})} aeropuertos")
print(f"Eventos de granizo chico en tormenta con calor (GS): {len(G)}")
print(f"Eventos de tormenta SIN granizo (para medir falsas alarmas): {len(T)}")
print("Por aeropuerto:", Counter(e["st"] for e in E).most_common(25))
print("Por mes:", sorted(Counter(e["start"].month for e in E).items()))
print("Por hora local (UTC-3):", sorted(Counter((e["start"].hour - 3) % 24 for e in E).items()))
for e in E[:12]: print("  ", e["st"], e["start"], e["metar"][:80])
json.dump([{**e, "start": e["start"].isoformat(), "end": e["end"].isoformat()} for e in E + G], open("hail_events.json", "w"))
