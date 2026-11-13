"""Prueba de factibilidad: bajar rayos (GLM) del GOES-19 desde AWS y filtrar Argentina."""
import io, json, re, sys, time, urllib.request
from datetime import datetime, timedelta, timezone
import numpy as np
import h5py

B = "https://noaa-goes19.s3.amazonaws.com"
ARG = dict(lat=(-56, -21), lon=(-74, -53))

def get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()

def listing(prefix):
    xml = get(f"{B}/?list-type=2&prefix={prefix}").decode()
    keys = re.findall(r"<Key>([^<]+)</Key>", xml)
    sizes = [int(x) for x in re.findall(r"<Size>(\d+)</Size>", xml)]
    return list(zip(keys, sizes))

def recent(product, minutes):
    now = datetime.now(timezone.utc)
    out = []
    for h in (1, 0):
        t = now - timedelta(hours=h)
        out += listing(f"{product}/{t:%Y}/{t:%j}/{t:%H}/")
    def start(k):
        m = re.search(r"_s(\d{4})(\d{3})(\d{2})(\d{2})(\d{2})", k)
        return datetime.strptime("".join(m.groups()), "%Y%j%H%M%S").replace(tzinfo=timezone.utc)
    out = [(k, s, start(k)) for k, s in out]
    lim = now - timedelta(minutes=minutes)
    return [x for x in out if x[2] >= lim], now

t0 = time.time()
files, now = recent("GLM-L2-LCFA", 10)
print(f"GLM: {len(files)} archivos en los últimos 10 min; tamaño medio {np.mean([s for _,s,_ in files])/1024:.0f} KB" if files else "GLM: sin archivos")
if files:
    print(f"   último archivo: {files[-1][2]:%H:%M:%S} UTC (demora vs ahora: {(now-files[-1][2]).total_seconds()/60:.1f} min)")
tot, arg_pts = 0, []
for k, s, st in files:
    with h5py.File(io.BytesIO(get(f"{B}/{k}")), "r") as f:
        la, lo = f["flash_lat"][:], f["flash_lon"][:]
        tot += len(la)
        m = (la >= ARG["lat"][0]) & (la <= ARG["lat"][1]) & (lo >= ARG["lon"][0]) & (lo <= ARG["lon"][1])
        arg_pts += [(round(float(a), 3), round(float(b), 3), st.strftime("%H:%M:%S")) for a, b in zip(la[m], lo[m])]
print(f"GLM: {tot} rayos en total en el disco; {len(arg_pts)} sobre Argentina; tiempo {time.time()-t0:.1f} s")
print("   muestra Argentina:", arg_pts[:5])
js = json.dumps(arg_pts)
print(f"   JSON para la app: {len(js)/1024:.1f} KB")

for prod in ("ABI-L2-ACHAF", "ABI-L2-ACHTF", "ABI-L2-RRQPEF"):
    try:
        fl, _ = recent(prod, 60)
        if fl:
            k, s, st = fl[-1]
            print(f"{prod}: último {st:%H:%M} UTC, {s/1e6:.1f} MB, {len(fl)} archivos en la última hora")
        else:
            print(f"{prod}: sin archivos en la última hora")
    except Exception as e:
        print(prod, "ERROR", e)

# prueba de lectura de la lluvia estimada (RRQPEF) sobre Argentina
try:
    fl, _ = recent("ABI-L2-RRQPEF", 60)
    k, s, st = fl[-1]
    t1 = time.time()
    with h5py.File(io.BytesIO(get(f"{B}/{k}", 60)), "r") as f:
        rr = f["RRQPE"]
        print("RRQPEF variables:", list(f.keys())[:12], "forma:", rr.shape, "attrs:", {a: rr.attrs[a] for a in ("scale_factor","add_offset") if a in rr.attrs})
    print(f"RRQPEF: bajado y abierto en {time.time()-t1:.1f} s")
except Exception as e:
    print("RRQPEF lectura ERROR", e)

# ¿qué productos hay en el bucket?
xml = get(f"{B}/?list-type=2&delimiter=/").decode()
print("PRODUCTOS:", [p for p in re.findall(r"<Prefix>([^<]+)</Prefix>", xml) if "RRQPE" in p or "GLM" in p or "ACH" in p or "DSI" in p])
for prod in ("ABI-L2-RRQPEF",):
    now = datetime.now(timezone.utc)
    for d in range(0, 4):
        t = now - timedelta(days=d)
        ks = listing(f"{prod}/{t:%Y}/{t:%j}/")
        print(f"{prod} día -{d}: {len(ks)} archivos", ks[-1] if ks else "")
        if ks: break
