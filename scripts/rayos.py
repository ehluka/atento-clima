"""Rayos de los últimos 40 minutos sobre Argentina, detectados por el satélite GOES-19 (sensor GLM, NOAA).
Escribe data/rayos.json: {"updated": ISO, "t0": minuto epoch de los datos, "f": [[lat*100, lon*100, minutos antes de t0, rayos], ...]}
(posiciones en una grilla de 0,02°, unos 2 km). Guarda en .raycache lo ya procesado, así cada corrida baja solo
los archivos nuevos del satélite (sale uno cada 20 segundos). Si algo falla, no corta el resto de la publicación."""
import io, json, os, re, sys, time, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

OUT = sys.argv[1] if len(sys.argv) > 1 else "data/rayos.json"
CACHE = ".raycache/rayos.json"
BUCKET = "https://noaa-goes19.s3.amazonaws.com"
UA = {"User-Agent": "AtentoClima/1.0"}
LAT0, LAT1, LON0, LON1 = -56.5, -20.5, -74.5, -52.5  # Argentina con 0,6° de margen
KEEP = 40  # minutos que se guardan


def get(url, timeout=30, tries=3):
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception:
            if n == tries - 1:
                raise
            time.sleep(2 * (n + 1))


def kmin(key):
    s = re.search(r"_s(\d{13})", key).group(1)
    return int(datetime.strptime(s, "%Y%j%H%M%S").replace(tzinfo=timezone.utc).timestamp() // 60)


def var(f, name):
    v = f[name]
    a = v[:].astype("float64")
    sf, ao = v.attrs.get("scale_factor"), v.attrs.get("add_offset")
    if sf is not None:
        a = a * float(sf.ravel()[0] if hasattr(sf, "ravel") else sf) + (float(ao.ravel()[0] if hasattr(ao, "ravel") else ao) if ao is not None else 0.0)
    return a


def flashes(key):
    import h5py
    data = get(f"{BUCKET}/{key}")
    with h5py.File(io.BytesIO(data), "r") as f:
        la, lo = var(f, "flash_lat"), var(f, "flash_lon")
    m = (la >= LAT0) & (la <= LAT1) & (lo >= LON0) & (lo <= LON1)
    # grilla de 0,02°: el satélite ubica cada rayo con un margen de algunos km
    return key, [(int(round(a * 50)) * 2, int(round(b * 50)) * 2) for a, b in zip(la[m], lo[m])]


def write(t0, store, note=None):
    c = Counter()
    for m, la, lo, n in store:
        if 0 <= t0 - m < KEEP:
            c[(la, lo, t0 - m)] += n
    out = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "t0": t0,
           "f": [[la, lo, ago, n] for (la, lo, ago), n in sorted(c.items(), key=lambda x: x[0][2])]}
    if note:
        out["error"] = note
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    return out


def main():
    t_start = time.time()
    try:
        cache = json.load(open(CACHE))
    except Exception:
        cache = {"t0": None, "done": [], "f": []}
    now = datetime.now(timezone.utc)
    nowm = int(now.timestamp() // 60)
    try:
        keys = []
        for h in (now - timedelta(hours=1), now):
            x = get(f"{BUCKET}/?list-type=2&prefix=GLM-L2-LCFA/{h:%Y}/{h:%j}/{h:%H}/").decode()
            keys += re.findall(r"<Key>([^<]+)</Key>", x)
        keys = sorted(k for k in keys if nowm - kmin(k) < KEEP + 2)
        if not keys:
            raise RuntimeError("el satélite no publicó archivos en los últimos 40 min")
        done = set(cache["done"])
        new = [k for k in keys if k not in done]
        store = [r for r in cache["f"] if nowm - r[0] < KEEP + 2]
        errs = 0
        with ThreadPoolExecutor(16) as ex:
            for fut in [ex.submit(flashes, k) for k in new]:
                try:
                    key, pts = fut.result()
                except Exception as e:
                    errs += 1
                    print("archivo con error:", e)
                    continue
                m = kmin(key)
                for (la, lo), n in Counter(pts).items():
                    store.append([m, la, lo, n])
                done.add(key)
        t0 = max(kmin(k) for k in keys if k in done) if done & set(keys) else cache["t0"]
        if t0 is None:
            raise RuntimeError("no se pudo leer ningún archivo")
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump({"t0": t0, "done": sorted(k for k in done if nowm - kmin(k) < KEEP + 2), "f": store}, open(CACHE, "w"))
        out = write(t0, store)
        print(f"Rayos: {len(new)} archivos nuevos ({errs} con error), {sum(r[3] for r in out['f'])} rayos en {len(out['f'])} puntos, "
              f"datos de hace {nowm - t0} min, {os.path.getsize(OUT) / 1024:.0f} KB, {time.time() - t_start:.1f} s")
    except Exception as e:
        print("Rayos: no se pudo actualizar:", e)
        if cache.get("t0"):  # se publica lo último que había: la app muestra su antigüedad
            write(cache["t0"], cache["f"], str(e))


if __name__ == "__main__":
    main()
