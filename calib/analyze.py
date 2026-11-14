"""Calcula qué tan bien los rayos (GLM) separan granizo de tormentas sin granizo y propone umbrales."""
import csv, glob, gzip, json, os, sys
from collections import defaultdict
import numpy as np

WORK, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
targets = {t["id"]: t for t in json.load(open(f"{WORK}/targets.json"))}
meta = json.load(open(f"{WORK}/meta.json"))
series = defaultdict(dict)
for fn in glob.glob(f"{WORK}/out_*.csv.gz"):
    with gzip.open(fn, "rt") as f:
        for r in csv.DictReader(f):
            series[r["tid"]][int(r["minute"])] = np.array([float(r["n10"]), float(r["n20"]), float(r["n30"]), float(r["n50"])])
assigned = {}
for fn in glob.glob(f"{WORK}/shard_*.json"):
    k = int(fn.split("_")[-1].split(".")[0])
    for e in json.load(open(fn)): assigned[e["hour"]] = k
ok_shards = {}; missing = set()
for fn in glob.glob(f"{WORK}/stats_*.json"):
    s = json.load(open(fn)); ok_shards[s["shard"]] = s; missing |= set(s["missing"])
missing |= {h for h, k in assigned.items() if k not in ok_shards}

def arr(tid, a, b):
    s = series.get(tid, {}); x = np.zeros((b - a + 1, 4))
    for m, c in s.items():
        if a <= m <= b: x[m - a] = c
    return x

def covered(t):
    hs = range(t["start"] // 60, t["end"] // 60 + 1)
    return sum(h in missing for h in hs) / len(hs) <= 0.2

def roll(x, n):
    if len(x) < n: return x.sum()
    c = np.cumsum(np.r_[0, x]); return (c[n:] - c[:-n]).max()

def jumps(x, thr):
    n = len(x) // 2; fr = x[:2 * n].reshape(n, 2).mean(1); out = []
    for i in range(6, n):
        dfr = np.diff(fr[i - 6:i]) / 2.0
        d = (fr[i] - fr[i - 1]) / 2.0
        if fr[i] >= thr and d > 0 and d > 2 * dfr.std():
            if not out or i - out[-1] >= 3: out.append(i)
    return [2 * i for i in out]

def auc(p, n):
    p = np.asarray(p); n = np.asarray(n)
    if len(p) == 0 or len(n) == 0: return float("nan")
    allv = np.r_[p, n]; ranks = allv.argsort().argsort() + 1.0
    # empates: rango promedio
    from collections import Counter
    vals = {}
    for v, rk in zip(allv, ranks): vals.setdefault(v, []).append(rk)
    avg = {v: np.mean(r) for v, r in vals.items()}
    rp = sum(avg[v] for v in p)
    return (rp - len(p) * (len(p) + 1) / 2) / (len(p) * len(n))

RAD = {10: 0, 20: 1, 30: 2}
rows = []
for tid, t in targets.items():
    if not covered(t): continue
    if t["kind"].startswith("metar"):
        t0 = t["t0"]; x = arr(tid, t0 - 75, t0 + 15)
        r = {"id": tid, "kind": t["kind"], "reg": t["reg"], "st": t["st"]}
        for R, j in RAD.items():
            s = x[:, j]
            r[f"tot30_{R}"] = s[45:76].sum(); r[f"max10_{R}"] = roll(s, 10); r[f"max2_{R}"] = roll(s, 2) / 2
            for thr in (1, 2, 4, 8):
                js = [m - 75 for m in jumps(s, thr) if -60 <= m - 75 <= 5]
                r[f"lj{thr}_{R}"] = js[0] if js else None
        rows.append(r)
    else:
        x = arr(tid, t["start"], t["end"])
        r = {"id": tid, "kind": t["kind"], "reg": "cuyo", "lugar": t["lugar"], "depto": t["depto"]}
        for R, j in RAD.items():
            s = x[:, j]; r[f"tot_{R}"] = s.sum(); r[f"max10_{R}"] = roll(s, 10)
        rows.append(r)

L = []
def P(s=""): L.append(s); print(s)
P("# Calibración granizo vs. rayos (GLM)\n")
P(f"Modo: {meta['modo']}. Tandas completas: {len(ok_shards)}/{len(set(assigned.values()))}. Horas sin datos satelitales: {len(missing)}.\n")
st = meta["stats"]
P(f"Casos METAR en el período (todo el país, sin Patagonia austral): granizo {st['granizo']} | tormentas sin granizo {st['tormentas_sin_granizo']}\n")
summary = {}
for reg in ("cuyo", "todos"):
    sel = [r for r in rows if r["kind"].startswith("metar") and (reg == "todos" or r["reg"] == reg)]
    pos = [r for r in sel if r["kind"] == "metar_granizo"]; neg = [r for r in sel if r["kind"] == "metar_sin_granizo"]
    if not pos or not neg: continue
    Npos = sum(st["granizo"].values()) if reg == "todos" else st["granizo"].get("cuyo", 0)
    Nneg = sum(st["tormentas_sin_granizo"].values()) if reg == "todos" else st["tormentas_sin_granizo"].get("cuyo", 0)
    P(f"## Aeropuertos – {reg}: {len(pos)} granizadas vs {len(neg)} tormentas sin granizo (muestra)\n")
    for R in (10, 20, 30):
        a1 = auc([r[f"max10_{R}"] for r in pos], [r[f"max10_{R}"] for r in neg]); a2 = auc([r[f"tot30_{R}"] for r in pos], [r[f"tot30_{R}"] for r in neg])
        z = np.mean([r[f"tot30_{R}"] == 0 and r[f"max10_{R}"] == 0 for r in pos])
        P(f"- Radio {R} km: AUC rayos máx. en 10 min = {a1:.2f}; AUC rayos 30 min previos = {a2:.2f}; granizadas sin ningún rayo cerca: {z:.0%}")
    R = 20
    P(f"\nUmbrales (radio {R} km, máximo de rayos en 10 min) – detecta / falsa alarma / probabilidad real de granizo si avisa:")
    tab = []
    for thr in (1, 3, 5, 10, 20, 40, 80, 160, 320):
        pod = np.mean([r[f"max10_{R}"] >= thr for r in pos]); pofd = np.mean([r[f"max10_{R}"] >= thr for r in neg])
        prec = pod * Npos / max(pod * Npos + pofd * Nneg, 1e-9)
        tab.append({"umbral": thr, "pod": pod, "pofd": pofd, "prec": prec})
        P(f"  ≥{thr:>3}: detecta {pod:.0%} | falsa alarma {pofd:.0%} | prob. granizo {prec:.0%}")
    P(f"\nSalto brusco de rayos (radio {R} km, 60 min antes del granizo):")
    for thr in (1, 2, 4, 8):
        pj = [r[f"lj{thr}_{R}"] for r in pos]; nj = [r[f"lj{thr}_{R}"] for r in neg]
        pod = np.mean([v is not None for v in pj]); pofd = np.mean([v is not None for v in nj])
        lead = [-v for v in pj if v is not None]
        prec = pod * Npos / max(pod * Npos + pofd * Nneg, 1e-9)
        P(f"  activación ≥{thr} rayos/min: detecta {pod:.0%} | falsa alarma {pofd:.0%} | prob. granizo {prec:.0%} | anticipación mediana {np.median(lead) if lead else float('nan'):.0f} min")
    summary[reg] = tab
    P("")
dh = [r for r in rows if r["kind"] == "dcc_granizo"]; dr = [r for r in rows if r["kind"] == "dcc_lluvia"]
if dh and dr:
    P(f"## Contingencias Mendoza: {len(dh)} lugares con granizo (radar) vs {len(dr)} con lluvia sin granizo\n")
    for R in (10, 20, 30):
        P(f"- Radio {R} km: AUC máx. 10 min = {auc([r[f'max10_{R}'] for r in dh], [r[f'max10_{R}'] for r in dr]):.2f}; AUC total = {auc([r[f'tot_{R}'] for r in dh], [r[f'tot_{R}'] for r in dr]):.2f}")
    R = 20
    P(f"\nUmbrales (radio {R} km, máximo en 10 min):")
    for thr in (1, 3, 5, 10, 20, 40, 80, 160, 320):
        P(f"  ≥{thr:>3}: granizo {np.mean([r[f'max10_{R}'] >= thr for r in dh]):.0%} | lluvia sin granizo {np.mean([r[f'max10_{R}'] >= thr for r in dr]):.0%}")
    q = lambda v: np.percentile(v, [25, 50, 75]).round(0).tolist()
    P(f"\nCuartiles máx. 10 min (20 km): granizo {q([r['max10_20'] for r in dh])} | lluvia {q([r['max10_20'] for r in dr])}")
import shutil
if os.path.exists(f"{WORK}/dcc_raw.json"): shutil.copy(f"{WORK}/dcc_raw.json", f"{OUT}/dcc_raw.json")
open(f"{OUT}/resumen.md", "w").write("\n".join(L) + "\n")
with open(f"{OUT}/casos.csv", "w", newline="") as f:
    keys = sorted({k for r in rows for k in r}); w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(rows)
json.dump({"umbrales": summary, "shards": ok_shards}, open(f"{OUT}/metricas.json", "w"), default=float, indent=1)
