import re, urllib.request, json
UA = {"User-Agent": "AtentoClima-research/1.0"}
def get(u, t=60):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t) as r: return r.read().decode("utf-8", "replace")
js = get("https://samhi.cima.fcen.uba.ar/static/js/main.97b904e7.js", 120)
print("tamaño js:", len(js))
urls = sorted(set(re.findall(r'["\'`](https?://[^"\'`\s]{6,120})["\'`]', js)))
print("URLs absolutas:", [u for u in urls if "w3.org" not in u and "reactjs" not in u][:60])
paths = sorted(set(re.findall(r'["\'`](/[a-zA-Z][a-zA-Z0-9_\-/]{2,60})["\'`]', js)))
print("rutas:", paths[:200])
for kw in ["download", "Download", "descarg", "Descarg", "csv", "CSV", "licen", "Licen", "CC BY", "términos", "Términos", "terms", "baseURL", "apiUrl", "API_URL", "axios.create", "register", "login", "publicReport", "report/list", "hail", "granizo"]:
    idx = [m.start() for m in re.finditer(re.escape(kw), js)][:3]
    for i in idx:
        print(f"[{kw}]", js[max(0, i-120):i+160].replace("\n", " "))
