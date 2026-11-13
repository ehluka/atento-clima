"""Descarga las alertas oficiales del SMN (feed CAP) y las guarda en data/alerts.json
para que la app las lea sin problemas de CORS. Corre en GitHub Actions."""
import hashlib, json, os, re, sys, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEED = "https://ssl.smn.gob.ar/CAP/AR.php"
OUT = sys.argv[1] if len(sys.argv) > 1 else "data/alerts.json"
UA = {"User-Agent": "AtentoClima/1.0 (+https://github.com/ehluka/atento-clima)"}

def get(url, tries=4):
    import time, urllib.error
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or n == tries - 1:
                raise
            time.sleep(5 * 2 ** n)

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
                "severity": txt(info, "severity"),
                "level": level(info),
                "area": txt(area, "areaDesc") if area is not None else "",
                "polygons": polys,
                "onset": txt(info, "onset") or txt(info, "effective"),
                "expires": txt(info, "expires"),
                "url": txt(info, "web") or url,
            })
    return out

CACHE = os.environ.get("CAP_CACHE", ".capcache")

def get_cached(url):
    """Los CAP de xml_generados tienen nombre único e inmutable: se bajan una sola vez."""
    if "xml_generados" not in url:
        return get(url)
    p = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".xml")
    if os.path.exists(p):
        with open(p, "rb") as f:
            return f.read()
    time.sleep(0.8)
    data = get(url)
    os.makedirs(CACHE, exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)
    return data

def main():
    root = strip(ET.fromstring(get(FEED)))
    alerts = []
    if root.tag == "alert":
        alerts = parse_alert(root, FEED)
    else:  # índice Atom / RSS con links a cada CAP
        links = [l.get("href") for l in root.iter("link") if l.get("href")]
        links += [l.text.strip() for l in root.iter("link") if l.text and l.text.strip().startswith("http")]
        links = [l for l in dict.fromkeys(links) if re.search(r"cap|\.xml|\.php", l, re.I) and l != FEED]
        from concurrent.futures import ThreadPoolExecutor
        def one(l):
            try:
                return parse_alert(strip(ET.fromstring(get_cached(l))), l)
            except Exception as e:
                print("skip", l, e, file=sys.stderr); return []
        if os.path.isdir(CACHE):
            keep = {hashlib.sha1(l.encode()).hexdigest() + ".xml" for l in links}
            for fn in os.listdir(CACHE):
                if fn not in keep:
                    os.remove(os.path.join(CACHE, fn))
        with ThreadPoolExecutor(1) as ex:
            for r in ex.map(one, links[:300]):
                alerts += r
    seen, uniq = set(), []
    for a in alerts:
        k = (a["event"], a["area"], a["onset"], a["expires"])
        if k not in seen:
            seen.add(k); uniq.append(a)
    return uniq

if __name__ == "__main__":
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        data = {"updated": now, "source": FEED, "alerts": main()}
    except Exception as e:
        data = {"updated": now, "source": FEED, "alerts": [], "error": str(e)[:300]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(data['alerts'])} alertas", data.get("error", ""))
