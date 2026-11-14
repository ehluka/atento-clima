"""Arma la lista de casos para calibrar granizo vs. rayos (GLM):
- METAR de aeropuertos argentinos (IEM): granizo (GR) y tormentas sin granizo, con hora exacta.
- Partes de Contingencias Climáticas de Mendoza (prensa): distritos con granizo detectado por radar y con lluvia sin granizo.
Reparte las horas de datos satelitales en tandas para procesarlas en paralelo."""
import csv, html, io, json, math, os, random, re, sys, time, unicodedata, urllib.parse, urllib.request, zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

UA = {"User-Agent": "AtentoClima-research/1.0 (+https://github.com/ehluka/atento-clima)"}
OUT = sys.argv[1] if len(sys.argv) > 1 else "work"
MODO = open(os.path.join(os.path.dirname(__file__), "MODO")).read().strip()
PILOTO = MODO == "piloto"
NSHARDS = 2 if PILOTO else 15
UTC = timezone.utc
LOC = timezone(timedelta(hours=-3))
os.makedirs(OUT, exist_ok=True)
random.seed(42)

def get(url, timeout=600, tries=4, binary=False):
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                b = r.read()
                return b if binary else b.decode("utf-8", "replace")
        except Exception as e:
            if n == tries - 1: raise
            time.sleep(5 * (n + 1))

def norm(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()

def km(a, b, c, d):
    return 111.2 * math.hypot(a - c, (b - d) * math.cos(math.radians((a + c) / 2)))

# ---------------- 1) METAR ----------------
CUYO = {"SAME", "SAMR", "SAMM", "SANU", "SAOU", "SAOR", "SANL"}
WX = re.compile(r"^[+-]?(VC|RE)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(DZ|RA|SN|SG|IC|PL|GR|GS|UP)*$")
IEM = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?"
seasons = [(datetime(y, 9, 1), datetime(y + 1, 6, 1)) for y in range(2018, 2026)] + [(datetime(2026, 9, 1), datetime(2026, 11, 14))]
reports = defaultdict(dict)  # station -> {time: (hail, ts, heavy)}
coords = {}
for a, b in seasons:
    q = urllib.parse.urlencode([("network", "AR__ASOS"), ("data", "metar"), ("year1", a.year), ("month1", a.month), ("day1", a.day),
        ("year2", b.year), ("month2", b.month), ("day2", b.day), ("tz", "Etc/UTC"), ("format", "onlycomma"), ("latlon", "yes"),
        ("missing", "empty"), ("report_type", 3), ("report_type", 4)])
    n = 0
    for r in csv.DictReader(io.StringIO(get(IEM + q))):
        n += 1
        st = r["station"]
        try:
            coords[st] = (float(r["lat"]), float(r["lon"]))
        except ValueError:
            continue
        toks = [t for t in r["metar"].split(" RMK")[0].split()[2:] if len(t) >= 2 and WX.match(t)]
        cur = [t for t in toks if not t.lstrip("+-").startswith(("VC", "RE"))]
        hail = any("GR" in t for t in cur)
        ts = any("TS" in t for t in cur)
        heavy = any(t.startswith("+") and "TS" in t for t in cur)
        if hail or ts:
            t = datetime.strptime(r["valid"], "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
            reports[st][t] = (hail, ts, heavy)
    print(f"METAR {a:%Y-%m}..{b:%Y-%m}: {n} filas", flush=True)

def group(times, gap=timedelta(hours=3)):
    ev = []
    for t in sorted(times):
        if ev and t - ev[-1][-1] <= gap: ev[-1].append(t)
        else: ev.append([t])
    return ev

pos, neg = [], []
for st, rep in reports.items():
    lat, lon = coords[st]
    if lat < -42: continue  # Patagonia austral: granizo chico de frente frío, no de tormenta
    reg = "cuyo" if st in CUYO else "resto"
    hail_t = [t for t, v in rep.items() if v[0]]
    hail_ev = group(hail_t)
    for e in hail_ev:
        tsnear = any(v[1] for t, v in rep.items() if abs((t - e[0]).total_seconds()) <= 7200)
        pos.append({"st": st, "reg": reg, "lat": lat, "lon": lon, "t0": e[0], "ts": tsnear})
    ts_t = [t for t, v in rep.items() if v[1] and not v[0]]
    for e in group(ts_t):
        if any(abs((h - e[0]).total_seconds()) < 6 * 3600 or abs((h - e[-1]).total_seconds()) < 6 * 3600 for h in hail_t):
            continue
        heavy = [t for t in e if rep[t][2]]
        neg.append({"st": st, "reg": reg, "lat": lat, "lon": lon, "t0": (heavy or e)[0]})
stats = {"granizo": Counter(p["reg"] for p in pos), "tormentas_sin_granizo": Counter(n["reg"] for n in neg)}
print("Casos METAR:", json.dumps(stats))
negc = [n for n in neg if n["reg"] == "cuyo"]; nego = [n for n in neg if n["reg"] == "resto"]
random.shuffle(negc); random.shuffle(nego)
if PILOTO:
    pos = [p for p in pos if p["reg"] == "cuyo"][:4] + [p for p in pos if p["reg"] == "resto"][:4]
    negs = negc[:4] + nego[:4]
else:
    negs = negc[:400] + nego[:300]

targets = []
def add(tid, kind, reg, lat, lon, a, b, step, meta):
    targets.append({"id": tid, "kind": kind, "reg": reg, "lat": round(lat, 4), "lon": round(lon, 4),
                    "start": int(a.timestamp() // 60), "end": int(b.timestamp() // 60), "step": step, **meta})
for i, p in enumerate(pos):
    add(f"MP{i}", "metar_granizo", p["reg"], p["lat"], p["lon"], p["t0"] - timedelta(minutes=75), p["t0"] + timedelta(minutes=15), 1,
        {"st": p["st"], "t0": int(p["t0"].timestamp() // 60), "ts": p["ts"]})
for i, n in enumerate(negs):
    add(f"MN{i}", "metar_sin_granizo", n["reg"], n["lat"], n["lon"], n["t0"] - timedelta(minutes=75), n["t0"] + timedelta(minutes=15), 1,
        {"st": n["st"], "t0": int(n["t0"].timestamp() // 60)})

# ---------------- 2) Partes de Contingencias Mendoza ----------------
z = zipfile.ZipFile(io.BytesIO(get("https://download.geonames.org/export/dump/AR.zip", binary=True)))
rows = [l.split("\t") for l in z.read("AR.txt").decode("utf-8").splitlines()]
adm1 = next(r[10] for r in rows if r[1] == "Mendoza" and r[7] == "PPLA")
STOP = {"este", "norte", "sur", "oeste", "centro", "campo", "ciudad", "industrial", "costa", "colonia", "villa", "capital", "oasis",
        "zona", "mendoza", "san juan", "san luis", "cordoba", "chile", "argentina", "la central", "el campo", "puente", "la isla"}
DEPTOS = {"godoy cruz", "guaymallen", "las heras", "lavalle", "lujan de cuyo", "lujan", "maipu", "san martin", "junin", "rivadavia",
          "santa rosa", "la paz", "tunuyan", "tupungato", "san carlos", "san rafael", "general alvear", "malargue"}
gaz = {}
for r in rows:
    if r[10] != adm1 or r[6] not in ("P", "A"): continue
    pop = int(r[14] or 0) + (10**7 if r[6] == "P" else 0)
    for nm in {norm(r[1]), norm(r[2])}:
        if len(nm) < 4 or nm in STOP: continue
        if nm not in gaz or pop > gaz[nm][2]:
            gaz[nm] = (float(r[4]), float(r[5]), pop)
gaz.setdefault("lujan", gaz.get("lujan de cuyo"))
print("Nomenclador Mendoza:", len(gaz), "nombres")

def names_in(text):
    w = norm(text).split(); out = []; i = 0
    while i < len(w):
        for L in range(5, 0, -1):
            nm = " ".join(w[i:i + L])
            if nm in gaz and gaz[nm]:
                out.append(nm); i += L; break
        else:
            i += 1
    return out

HAIL = re.compile(r"\bgraniz")
RAIN = re.compile(r"\blluvi|precipitaci|\bllovi")
DOW = re.compile(r"\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\s+(\d{1,2})\b")
HRS = re.compile(r"\b(?:entre las|desde las?|a partir de las)\s+(\d{1,2})(?:[.:](\d{2}))?\s*(?:h\w*)?\s+(?:y las|hasta las?|hasta pasadas? las)\s+(\d{1,2})(?:[.:](\d{2}))?")

def parse_post(p):
    raw = p["content"]["rendered"]
    t = re.sub(r"(?i)<\s*(br|/p|/li|/h\d|/div|/tr|/ul)\s*/?>", "\n", raw)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    lines = [re.sub(r"\s+", " ", l).strip() for l in t.split("\n")]
    lines = [l for l in lines if l]
    hail, rain = [], []
    state = None
    for line in lines:
        for s in re.split(r"(?<=[a-záéíóúñ\)\d])\.\s+(?=[A-ZÁÉÍÓÚÑ])", line):
            n = norm(s).replace("sin granizo", " singrz ")
            header = s.rstrip().endswith(":")
            hk = [m.start() for m in HAIL.finditer(n)]
            if hk:
                cut = hk[-1]
                hail += names_in(n[cut:])
                if RAIN.search(n[:cut]): rain += names_in(n[:cut])
                state = "hail" if header or n.rstrip().endswith("en") else state
            elif "singrz" in n:
                rain += names_in(n); state = None
            elif RAIN.search(n):
                rain += names_in(n); state = "rain" if header else None
            elif state and len(s) < 220 and not re.search(r"\boasis\b|\bzona\b|denuncia|pronostico", n):
                (hail if state == "hail" else rain).extend(names_in(n))
            else:
                state = None
    return hail, rain, norm(t)

def window(p, text):
    d = datetime.fromisoformat(p["date"]).replace(tzinfo=LOC)
    ev = None
    m = DOW.search(text)
    if m:
        day = int(m.group(2))
        for back in range(0, 5):
            c = d - timedelta(days=back)
            if c.day == day: ev = c.date(); break
    if ev is None:
        ev = (d - timedelta(days=1)).date() if ("anoche" in text or "ayer" in text or d.hour < 15) else d.date()
    base = datetime(ev.year, ev.month, ev.day, tzinfo=LOC)
    h = HRS.search(text)
    if h:
        h1, m1, h2, m2 = int(h.group(1)), int(h.group(2) or 0), int(h.group(3)), int(h.group(4) or 0)
        if 0 <= h1 < 24 and 0 <= h2 < 24:
            a = base + timedelta(hours=h1, minutes=m1)
            b = base + timedelta(hours=h2, minutes=m2)
            if b <= a: b += timedelta(days=1)
            if (b - a) <= timedelta(hours=20):
                return a - timedelta(hours=1), b + timedelta(hours=1), True
    return base + timedelta(hours=12), base + timedelta(hours=31), False

posts = []
WP = "https://www.mendoza.gov.ar/prensa/wp-json/wp/v2/posts?"
for page in range(1, 40):
    q = urllib.parse.urlencode({"search": "granizo", "per_page": 100, "page": page, "after": "2018-08-01T00:00:00", "_fields": "date,title,link,content"})
    try:
        data = json.loads(get(WP + q, 180))
    except Exception as e:
        print("fin de páginas:", e); break
    if not data: break
    posts += data
    if len(data) < 100: break
ops = [p for p in posts if re.search(r"radar", p["content"]["rendered"], re.I)]
print("Partes de prensa:", len(posts), "| con datos de radar:", len(ops))
if PILOTO: ops = ops[:3]
dcc_meta = []
nh = nr = nexact = 0
for i, p in enumerate(ops):
    hail, rain, text = parse_post(p)
    if not hail: continue
    a, b, exact = window(p, text)
    nexact += exact
    hp = []
    for nm in dict.fromkeys(hail):
        lat, lon, _ = gaz[nm]; hp.append((lat, lon))
        add(f"DH{i}_{len(hp)}", "dcc_granizo", "cuyo", lat, lon, a, b, 3, {"lugar": nm, "depto": nm in DEPTOS, "post": i})
        nh += 1
    k = 0
    for nm in dict.fromkeys(rain):
        if nm in hail: continue
        lat, lon, _ = gaz[nm]
        if any(km(lat, lon, x, y) < 15 for x, y in hp): continue
        k += 1; nr += 1
        add(f"DR{i}_{k}", "dcc_lluvia", "cuyo", lat, lon, a, b, 3, {"lugar": nm, "depto": nm in DEPTOS, "post": i})
    dcc_meta.append({"post": i, "fecha": p["date"], "link": p["link"], "ventana_exacta": exact, "granizo": list(dict.fromkeys(hail)), "lluvia": list(dict.fromkeys(rain))})
print(f"Contingencias: {len(dcc_meta)} partes con lugares | {nh} puntos con granizo, {nr} con lluvia sin granizo | ventanas con hora explícita: {nexact}")
for m in dcc_meta[:4]: print("  ", m["fecha"], "| granizo:", m["granizo"][:8], "| lluvia:", m["lluvia"][:6])

# ---------------- 3) Tandas por hora ----------------
hours = {}
for t in targets:
    for h in range(t["start"] // 60, t["end"] // 60 + 1):
        e = hours.setdefault(h, {"step": 3, "t": []})
        e["t"].append(t["id"]); e["step"] = min(e["step"], t["step"])
load = [0] * NSHARDS; shards = [[] for _ in range(NSHARDS)]
for h, e in sorted(hours.items(), key=lambda kv: -180 // kv[1]["step"]):
    k = load.index(min(load)); shards[k].append({"hour": h, **e}); load[k] += 180 // e["step"]
for k in range(NSHARDS):
    json.dump(shards[k], open(f"{OUT}/shard_{k}.json", "w"))
json.dump(targets, open(f"{OUT}/targets.json", "w"))
json.dump({"stats": {k: dict(v) for k, v in stats.items()}, "dcc": dcc_meta, "modo": MODO}, open(f"{OUT}/meta.json", "w"), ensure_ascii=False)
print(f"Objetivos: {len(targets)} | horas de satélite: {len(hours)} | archivos estimados: {sum(load)} | por tanda: {max(load)}")
with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
    f.write(f"shards={json.dumps(list(range(NSHARDS)))}\n")

# ---------------- 4) ¿SAMHI permite registrarse? ----------------
try:
    idx = get("https://samhi.cima.fcen.uba.ar/", 60)
    js = get("https://samhi.cima.fcen.uba.ar" + re.search(r'src="(/static/js/main[^"]+)"', idx).group(1), 180)
    pats = [r"mutation\s+\w*(Regist|SignUp|Signup|CreateAccount|CreateUser|Request)\w*", r"[Rr]egistr(arse|ate|o de usuario)", r"[Ss]ign ?[Uu]p", r"[Cc]rear (una )?cuenta", r"[Ss]olicit\w+ (de )?(acceso|cuenta|usuario)"]
    found = []
    for pat in pats:
        for m in list(re.finditer(pat, js))[:3]:
            found.append(js[max(0, m.start() - 60): m.end() + 60].replace("\n", " "))
    print("SAMHI registro:", found if found else "no hay registro público (solo inicio de sesión)")
except Exception as e:
    print("SAMHI: no se pudo revisar", e)
