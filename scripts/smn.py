"""Descarga las alertas oficiales del SMN (feeds CAP) y las guarda en data/alerts.json
para que la app las lea sin problemas de CORS. Corre en GitHub Actions.
kind = "alerta" (alertas a 72 h) o "acp" (avisos a muy corto plazo, por radar)."""
import hashlib, json, os, re, sys, time, urllib.error, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = [
    ("acp", "https://ssl.smn.gob.ar/feeds/CAP/avisocortoplazo/rss_acpCAP.xml"),
    ("alerta", "https://ssl.smn.gob.ar/CAP/AR.php"),
]
OUT = sys.argv[1] if len(sys.argv) > 1 else "data/alerts.json"
UA = {"User-Agent": "AtentoClima/1.0 (+https://github.com/ehluka/atento-clima)"}
CACHE = os.environ.get("CAP_CACHE", ".capcache")

def get(url, tries=4):
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=12) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or n == tries - 1:
                raise
            time.sleep(5 * 2 ** n)

def cacheable(url):
    """Avisos con nombre único (fecha y hora en el nombre): se bajan una sola vez."""
    return "xml_generados" in url or re.search(r"\d{12,}", url) is not None

def cache_name(url):
    return hashlib.sha1(url.encode()).hexdigest() + ".xml"

def get_cached(url):
    if not cacheable(url):
        return get(url)
    p = os.path.join(CACHE, cache_name(url))
    if os.path.exists(p):
        with open(p, "rb") as f:
            return f.read()
    time.sleep(0.8)
    data = get(url)
    os.makedirs(CACHE, exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)
    return data

def strip(el):  # quita namespaces
    for e in el.iter():
        if isinstance(e.tag, str) and "}" in e.tag:
            e.tag = e.tag.split("}", 1)[1]
    return el

def txt(el, path):
    x = el.find(path)
    return (x.text or "").strip() if x is not None and x.text else ""

def level(info):
    blob = " ".join([txt(info, "event"), txt(info, "headline"), txt(info, "description")]
                    + [(p.findtext("value") or "") for p in info.findall("parameter")]).lower()
    for word, n in (("rojo", 3), ("naranja", 2), ("amarillo", 1)):
        if word in blob:
            return n
    return {"Extreme": 3, "Severe": 2}.get(txt(info, "severity"), 1)

def parse_alert(root, url=""):
    out = []
    if txt(root, "msgType") == "Cancel" or txt(root, "status") not in ("", "Actual"):
        return out
    infos = root.findall("info")
    es = [i for i in infos if txt(i, "language").lower().startswith("es")] or infos[:1]
    for info in es:
        for area in info.findall("area") or [None]:
            polys = []
            if area is not None:
                for p in area.findall("polygon"):
                    pts = []
                    for pair in (p.text or "").split():
                        try:
                            la, lo = pair.split(",")[:2]; pts.append([round(float(la), 4), round(float(lo), 4)])
                        except ValueError:
                            pass
                    if len(pts) >= 3:
                        polys.append(pts)
            out.append({
                "event": txt(info, "event") or txt(info, "headline"),
                "headline": txt(info, "headline"),
                "description": txt(info, "description")[:1500],
                "instruction": txt(info, "instruction")[:800],
                "severity": txt(info, "severity"),
                "level": level(info),
                "area": txt(area, "areaDesc") if area is not None else "",
                "polygons": polys,
                "sent": txt(root, "sent"),
                "onset": txt(info, "onset") or txt(info, "effective"),
                "expires": txt(info, "expires"),
                "url": txt(info, "web") or url,
            })
    return out

def fetch_feed(kind, feed, used, done):
    root = strip(ET.fromstring(get(feed)))
    alerts = []
    if root.tag == "alert":
        alerts = parse_alert(root, feed)
    else:  # índice Atom / RSS con links a cada CAP
        links = [l.get("href") for l in root.iter("link") if l.get("href")]
        links += [l.text.strip() for l in root.iter("link") if l.text and l.text.strip().startswith("http")]
        links = [l for l in dict.fromkeys(links) if re.search(r"cap|\.xml|\.php", l, re.I) and l != feed]
        print(f"[{kind}] {len(links)} avisos en el índice; ej: {links[:2]}")
        for l in links[:300]:
            used.add(cache_name(l))
            if l in done:  # el feed general repite los avisos a muy corto plazo
                continue
            done.add(l)
            try:
                got = parse_alert(strip(ET.fromstring(get_cached(l))), l)
            except Exception as e:
                print(f"[{kind}] skip", l, e, file=sys.stderr); continue
            for a in got:
                a["kind"] = "acp" if "avisocortoplazo" in l else "alerta"
            alerts += got
    seen, uniq = set(), []
    for a in alerts:
        a.setdefault("kind", kind)
        k = (a["event"], a["area"], a["onset"], a["expires"], json.dumps(a["polygons"])[:200])
        if k not in seen:
            seen.add(k); uniq.append(a)
    if uniq:
        s = uniq[0]
        print(f"[{kind}] sent={s['sent']} onset={s['onset']} expires={s['expires']} url={s['url'][-40:]} desc={s['description'][:300]!r}")
        print(f"[{kind}] {len(uniq)} vigentes; ej: {s['event']!r} | {s['area'][:80]!r} | polígonos={len(s['polygons'])} | vence={s['expires']}")
    else:
        print(f"[{kind}] 0 vigentes")
    return uniq

if __name__ == "__main__":
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data = {"updated": now, "alerts": []}
    used, done = set(), set()
    for kind, feed in FEEDS:
        try:
            data["alerts"] += fetch_feed(kind, feed, used, done)
        except Exception as e:
            print(f"[{kind}] ERROR {e}", file=sys.stderr)
            data["error" if kind == "alerta" else "acp_error"] = str(e)[:300]
    if os.path.isdir(CACHE) and "error" not in data and "acp_error" not in data:
        for fn in os.listdir(CACHE):
            if fn not in used:
                os.remove(os.path.join(CACHE, fn))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(data['alerts'])} alertas en total")
