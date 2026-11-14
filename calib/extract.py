"""Baja los rayos del GLM (GOES-16 hasta abr-2025, GOES-19 después) para las horas de una tanda
y cuenta, por minuto, los rayos a 10/20/30/50 km de cada punto."""
import gzip, io, json, re, sys, threading, time, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import h5py, numpy as np

WORK, K = sys.argv[1], int(sys.argv[2])
UA = {"User-Agent": "AtentoClima-research/1.0"}
B = {16: "https://noaa-goes16.s3.amazonaws.com", 19: "https://noaa-goes19.s3.amazonaws.com"}
SWITCH = datetime(2025, 4, 7, tzinfo=timezone.utc)
T = {t["id"]: t for t in json.load(open(f"{WORK}/targets.json"))}
hours = json.load(open(f"{WORK}/shard_{K}.json"))
R = np.array([10, 20, 30, 50])

def get(url, timeout=60, tries=5):
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception:
            if n == tries - 1: raise
            time.sleep(2 * (n + 1))

def list_hour(h):
    dt = datetime.fromtimestamp(h * 3600, timezone.utc)
    order = [16, 19] if dt < SWITCH else [19, 16]
    for sat in order:
        x = get(f"{B[sat]}/?list-type=2&prefix=GLM-L2-LCFA/{dt:%Y}/{dt:%j}/{dt:%H}/").decode()
        keys = sorted(re.findall(r"<Key>([^<]+)</Key>", x))
        if keys: return sat, keys
    return None, []

def ktime(k):
    m = re.search(r"_s(\d{13})", k)
    return int(datetime.strptime(m.group(1), "%Y%j%H%M%S").replace(tzinfo=timezone.utc).timestamp() // 60)

acc = defaultdict(lambda: np.zeros(4))
lock = threading.Lock()
done = [0]; t0 = time.time()

def job(sat, key, tids, w):
    minute = ktime(key)
    act = [T[i] for i in tids if T[i]["start"] <= minute <= T[i]["end"]]
    if not act: return
    data = get(f"{B[sat]}/{key}")
    with h5py.File(io.BytesIO(data), "r") as f:
        la = f["flash_lat"][:].astype(np.float64); lo = f["flash_lon"][:].astype(np.float64)
    res = []
    for t in act:
        m = (np.abs(la - t["lat"]) < 0.5) & (np.abs(lo - t["lon"]) < 0.65)
        if not m.any(): continue
        d = 111.2 * np.hypot(la[m] - t["lat"], (lo[m] - t["lon"]) * np.cos(np.radians(t["lat"])))
        c = (d[:, None] <= R[None, :]).sum(0)
        if c[-1]: res.append((t["id"], c * w))
    with lock:
        for tid, c in res: acc[(tid, minute)] += c
        done[0] += 1
        if done[0] % 2000 == 0:
            print(f"  {done[0]} archivos, {done[0] / (time.time() - t0):.1f}/s", flush=True)

missing = []; nfiles = 0
with ThreadPoolExecutor(32) as ex:
    futs = []
    for e in hours:
        try:
            sat, keys = list_hour(e["hour"])
        except Exception as err:
            print("listado falló", e["hour"], err); missing.append(e["hour"]); continue
        if not keys: missing.append(e["hour"]); continue
        sel = keys if e["step"] == 1 else keys[::3]
        w = 1 if e["step"] == 1 else 3
        nfiles += len(sel)
        futs += [ex.submit(job, sat, k, e["t"], w) for k in sel]
    errs = 0
    for f in futs:
        try: f.result()
        except Exception as err:
            errs += 1
            if errs <= 5: print("error archivo:", err)
dt = time.time() - t0
with gzip.open(f"{WORK}/out_{K}.csv.gz", "wt") as f:
    f.write("tid,minute,n10,n20,n30,n50\n")
    for (tid, m), c in acc.items():
        f.write(f"{tid},{m},{c[0]:g},{c[1]:g},{c[2]:g},{c[3]:g}\n")
json.dump({"shard": K, "hours": len(hours), "missing": missing, "files": nfiles, "errors": errs, "seconds": round(dt)},
          open(f"{WORK}/stats_{K}.json", "w"))
print(f"Tanda {K}: {len(hours)} horas, {nfiles} archivos, {errs} errores, {len(missing)} horas sin datos, {dt:.0f} s ({nfiles / max(dt, 1):.1f} archivos/s)")
