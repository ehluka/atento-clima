'use strict';
/* Atento Clima — alertas por ubicación. Sin servidor: Open-Meteo, USGS y SMN (vía data/alerts.json). */

const LS_PLACES = 'ac.places', LS_SEL = 'ac.sel', LS_CACHE = 'ac.cache.', LS_GEO = 'ac.geoname';
const LVL = ['Sin riesgo', 'Bajo', 'Moderado', 'Alto'];
const SMN_LVL = { 1: 'Amarillo', 2: 'Naranja', 3: 'Rojo' };
// Qué hacer según el color (guía del SMN). Las de temperatura extrema hablan de efectos en la salud.
const SMN_DO = { 1: 'Informate', 2: 'Preparate', 3: 'Seguí las instrucciones oficiales' };
const SMN_HEALTH = { 1: 'Efecto leve a moderado en la salud', 2: 'Efecto moderado a alto en la salud', 3: 'Efecto alto a extremo en la salud' };
// Advertencias (niebla, ceniza, polvo, humo): no tienen colores, el SMN las muestra en violeta.
const isAdv = x => /niebla|ceniza|polvo|humo|visibilidad|advertencia/.test(norm(x.event + ' ' + x.headline));

const WMO = {
  0: 'Despejado', 1: 'Mayormente despejado', 2: 'Parcialmente nublado', 3: 'Nublado',
  45: 'Niebla', 48: 'Niebla con escarcha', 51: 'Llovizna débil', 53: 'Llovizna', 55: 'Llovizna intensa',
  56: 'Llovizna helada', 57: 'Llovizna helada intensa', 61: 'Lluvia débil', 63: 'Lluvia', 65: 'Lluvia intensa',
  66: 'Lluvia helada', 67: 'Lluvia helada intensa', 71: 'Nevada débil', 73: 'Nevada', 75: 'Nevada intensa',
  77: 'Granos de nieve', 80: 'Chaparrones débiles', 81: 'Chaparrones', 82: 'Chaparrones fuertes',
  85: 'Chaparrones de nieve', 86: 'Chaparrones de nieve fuertes', 95: 'Tormenta',
  96: 'Tormenta con granizo', 99: 'Tormenta fuerte con granizo'
};
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const ls = {
  get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { } }
};

let places = ls.get(LS_PLACES, []);
let selected = ls.get(LS_SEL, 'gps');
let gpsCoords = null;
let smnCache = null;
const levels = {}; // id -> max level, para el puntito del chip

/* ---------- Lugares ---------- */
let gpsName = ls.get(LS_GEO, {});
function allPlaces() { return [{ id: 'gps', name: '📍 ' + (gpsName.name || 'Mi ubicación'), gps: true, prov: gpsName.prov || '' }, ...places]; }

function renderChips() {
  const nav = $('#places');
  nav.innerHTML = allPlaces().map(p => {
    const l = levels[p.id];
    const dot = l == null ? '' : `<span class="dot" style="background:var(${['--ok', '--low', '--mid', '--high'][l]})"></span>`;
    return `<button class="chip ${p.id === selected ? 'on' : ''}" data-id="${esc(p.id)}">${esc(p.name)}${dot}</button>`;
  }).join('') + `<button class="chip" id="addBtn" aria-label="Agregar lugar">＋ Lugar</button>`;
  nav.querySelectorAll('[data-id]').forEach(b => b.onclick = () => select(b.dataset.id));
  $('#addBtn').onclick = openAdd;
}

function select(id) {
  selected = id; ls.set(LS_SEL, id);
  renderChips(); load();
}

function openAdd() {
  $('#q').value = ''; $('#alias').value = ''; $('#results').innerHTML = '';
  $('#addDlg').showModal(); $('#q').focus();
}
$('#cancelAdd').onclick = () => $('#addDlg').close();

let searchT;
$('#q').addEventListener('input', () => {
  clearTimeout(searchT);
  const q = $('#q').value.trim();
  if (q.length < 2) { $('#results').innerHTML = ''; return; }
  searchT = setTimeout(() => search(q), 350);
});
$('#addForm').addEventListener('submit', e => e.preventDefault());

async function search(q) {
  const ul = $('#results');
  try {
    const r = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(q)}&count=10&language=es&format=json&countryCode=AR`);
    const j = await r.json();
    const res = (j.results || []).filter(p => p.country_code === 'AR');
    if (!res.length) { ul.innerHTML = '<li class="muted">Sin resultados</li>'; return; }
    ul.innerHTML = res.map((p, i) =>
      `<li tabindex="0" data-i="${i}"><b>${esc(p.name)}</b> <span class="muted">${esc([p.admin2, p.admin1].filter(Boolean).join(', '))}</span></li>`).join('');
    ul.querySelectorAll('li[data-i]').forEach(li => {
      const pick = () => addPlace(res[+li.dataset.i]);
      li.onclick = pick; li.onkeydown = e => { if (e.key === 'Enter') pick(); };
    });
  } catch { ul.innerHTML = '<li class="muted">No se pudo buscar. Revisá la conexión.</li>'; }
}

function addPlace(p) {
  const alias = $('#alias').value.trim();
  const id = 'p' + Date.now();
  places.push({ id, name: alias || p.name, lat: p.latitude, lon: p.longitude, prov: p.admin1 || '', full: [p.name, p.admin1].filter(Boolean).join(', ') });
  ls.set(LS_PLACES, places);
  $('#addDlg').close();
  select(id);
}

function removePlace(id) {
  places = places.filter(p => p.id !== id); ls.set(LS_PLACES, places);
  delete levels[id]; select('gps');
}

/* ---------- Ubicación ---------- */
function getGPS() {
  return new Promise((res, rej) => {
    if (!navigator.geolocation) return rej(new Error('Este navegador no permite ubicación.'));
    navigator.geolocation.getCurrentPosition(
      p => res({ lat: p.coords.latitude, lon: p.coords.longitude }),
      e => rej(new Error(e.code === 1 ? 'Permiso de ubicación denegado.' : 'No se pudo obtener la ubicación.')),
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 10 * 60 * 1000 });
  });
}

/* ---------- Nombre del lugar por GPS ---------- */
async function placeName(lat, lon) {
  const key = lat.toFixed(2) + ',' + lon.toFixed(2), c = ls.get(LS_GEO, {});
  if (c.key === key) return c;
  const r = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=es`);
  const j = await r.json();
  const adm = (j.localityInfo?.administrative || []).filter(a => a.adminLevel >= 5).sort((a, b) => b.adminLevel - a.adminLevel);
  const name = j.city || j.locality || adm[0]?.name || '';
  const prov = (j.principalSubdivision || '').replace(/^Provincia de /i, '');
  const out = { key, name, prov };
  if (name) ls.set(LS_GEO, out);
  return out;
}

/* ---------- Datos ---------- */
async function getJSON(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}

function forecastURL(lat, lon) {
  const h = 'temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m,cape,lifted_index,freezing_level_height,is_day';
  const d = 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_gusts_10m_max,uv_index_max';
  const c = 'is_day,temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_gusts_10m';
  return `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=${c}&hourly=${h}&daily=${d}&timezone=auto&forecast_days=7`;
}

function quakesURL(lat, lon) {
  const start = new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10);
  return `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude=${lat}&longitude=${lon}&maxradiuskm=400&minmagnitude=2.5&starttime=${start}&orderby=time&limit=15`;
}

async function getSMN() {
  if (smnCache && Date.now() - smnCache.t < 5 * 60e3) return smnCache.d;
  const d = await getJSON('data/alerts.json?t=' + Date.now());
  smnCache = { t: Date.now(), d };
  return d;
}

/* ---------- Rayos cerca (satélite GOES-19, vía data/rayos.json) ---------- */
// Formato: { t0: minuto (epoch) de los datos, f: [[lat*100, lon*100, minutos antes de t0, rayos], ...] }
let rayCache = null;
async function getRayos() {
  if (rayCache && Date.now() - rayCache.t < 60e3) return rayCache.d;
  const d = await getJSON('data/rayos.json?t=' + Date.now());
  rayCache = { t: Date.now(), d };
  return d;
}
// Solo los rayos a ~60 km del lugar (para guardar en caché sin ocupar de más).
const raySub = (d, lat, lon) => d && { t0: d.t0, f: (d.f || []).filter(([la, lo]) => Math.abs(la / 100 - lat) < .6 && Math.abs(lo / 100 - lon) < .7) };
const DIRS = ['norte', 'noreste', 'este', 'sureste', 'sur', 'suroeste', 'oeste', 'noroeste'];
// Niveles calibrados con granizadas en aeropuertos de Cuyo: rayos a menos de 10 km en los últimos 30 min.
const RAY_LVL = n => n >= 80 ? 3 : n >= 20 ? 2 : n >= 5 ? 1 : 0;
function rayosNear(d, lat, lon) {
  const age = Math.max(0, Math.round(Date.now() / 60e3 - d.t0));
  const cosl = Math.cos(lat * Math.PI / 180), perMin = new Array(40).fill(0), pts = [];
  let n10 = 0, a = 0, b = 0, near = null, near5 = null;
  for (const [la, lo, ago, n] of d.f || []) {
    if (ago >= 40) continue;
    const y = (la / 100 - lat) * 111.2, x = (lo / 100 - lon) * 111.2 * cosl, km = Math.hypot(x, y);
    if (km > 50) continue;
    if (ago < 30) pts.push({ x, y, km, ago, n });
    if (km <= 10 && ago < 30) n10 += n;
    if (km <= 20) { perMin[39 - ago] += n; if (ago < 10) a += n; else if (ago < 20) b += n; }
    const nr = { km, ago: ago + age, dir: DIRS[Math.round(((Math.atan2(x, y) * 180 / Math.PI + 360) % 360) / 45) % 8] };
    if (ago < 15 && (!near || km < near.km)) near = nr;
    if (ago < 5 && (!near5 || km < near5.km)) near5 = nr;
  }
  near = near5 || near;
  const trend = a >= 1.5 * b + 3 ? 'up' : a <= 0.6 * b - 3 ? 'down' : 'flat';
  const j = lightningJump(perMin);
  return { age, pts, n10, perMin, near, trend, jump: j == null ? null : j + age, lvl: RAY_LVL(n10) };
}
// Salto brusco de rayos (algoritmo 2σ de Schultz et al.): tasa en períodos de 2 min; salto si el aumento
// supera 2 desvíos de los 10 min previos y la tasa es de 4 rayos/min o más. Devuelve hace cuántos minutos.
function lightningJump(perMin) {
  const fr = [];
  for (let i = 0; i + 1 < perMin.length; i += 2) fr.push((perMin[i] + perMin[i + 1]) / 2);
  for (let i = fr.length - 1; i >= Math.max(6, fr.length - 8); i--) {
    const prev = [];
    for (let j = i - 5; j < i; j++) prev.push((fr[j] - fr[j - 1]) / 2);
    const m = prev.reduce((s, v) => s + v, 0) / prev.length;
    const sd = Math.sqrt(prev.reduce((s, v) => s + (v - m) ** 2, 0) / prev.length);
    const d = (fr[i] - fr[i - 1]) / 2;
    if (fr[i] >= 4 && d > 0 && d > 2 * sd) return (fr.length - 1 - i) * 2;
  }
  return null;
}
const distTxt = r => r.km < 5 ? 'a menos de 5 km' : `a unos ${Math.round(r.km / 5) * 5} km al ${r.dir}`;
const haceMin = m => m <= 1 ? 'recién' : `hace ${m} min`;
function polar(pts) {
  const S = 136, C = S / 2, K = 60 / 30;
  let s = `<svg class="polar" viewBox="0 0 ${S} ${S}" width="${S}" height="${S}" role="img" aria-label="Rayos alrededor de este lugar">
    <circle cx="${C}" cy="${C}" r="60" class="ring"/><circle cx="${C}" cy="${C}" r="${20 * K}" class="ring"/>
    <circle cx="${C}" cy="${C}" r="${10 * K}" class="ring ring10"/>
    <text x="${C}" y="7" class="pl">N</text>`;
  for (const p of pts.filter(p => p.km <= 30).sort((u, v) => v.ago - u.ago)) {
    const op = (1 - p.ago / 36).toFixed(2), r = Math.min(4, 1.7 + Math.log2(p.n + 1) * 0.7);
    s += `<circle cx="${(C + p.x * K).toFixed(1)}" cy="${(C - p.y * K).toFixed(1)}" r="${r.toFixed(1)}" class="flash" style="opacity:${op}"/>`;
  }
  return s + `<circle cx="${C}" cy="${C}" r="4.5" class="me"/>${[10, 20, 30].map(k => `<text x="${C}" y="${C + k * K + 3}" class="pl halo">${k === 30 ? '30 km' : k}</text>`).join('')}</svg>`;
}
function spark(perMin, age) {
  const v = perMin.slice(10), mx = Math.max(4, ...v), W = 6, H = 40;
  return `<svg class="spark" viewBox="0 0 ${v.length * W} ${H}" preserveAspectRatio="none" aria-hidden="true">${v.map((x, i) => {
    const h = x ? Math.max(2, x / mx * H) : 0;
    return `<rect x="${i * W + 1}" y="${(H - h).toFixed(1)}" width="${W - 2}" height="${h.toFixed(1)}" rx="1.5" class="sb"/>`;
  }).join('')}</svg><div class="row muted small"><span>hace ${30 + age} min</span><span>${age <= 1 ? 'ahora' : `hace ${age} min`}</span></div>`;
}
const BOLT = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M13.5 2 4.5 13.5h6L9.5 22l9-11.5h-6z" fill="currentColor"/></svg>';
const cap = t => t[0].toUpperCase() + t.slice(1);
// Versión simple: una fila chiquita; si hay rayos, al tocarla se abre el detalle.
function rayosCard(r, err) {
  const row = (ic, title, sub, extra = '', tail = '') => `<div class="rm-row"><span class="ray-ic ${ic}">${BOLT}</span><div class="rm-txt"><div class="rm-t">${title}</div><div class="muted small">${sub}</div>${extra}</div>${tail}</div>`;
  const mini = (title, sub) => `<section class="card ray-mini">${row('off', title, sub)}</section>`;
  if (err || !r) return mini('Rayos: sin datos', 'No se pudieron leer los datos del satélite');
  if (r.age > 20) return mini('Rayos: sin datos recientes', `Son de hace ${r.age} min: no se puede confirmar si hay rayos cerca`);
  if (!r.pts.length) return mini('Sin rayos cerca', `Ninguno a menos de 50 km · ${r.age <= 1 ? 'recién' : `hace ${r.age} min`}`);
  const L = r.lvl;
  const title = `Rayos cerca${L ? ` <span class="badge b-${L}">Granizo: ${LVL[L].toLowerCase()}</span>` : ''}`;
  const sub = r.near ? `${cap(distTxt(r.near))}, ${haceMin(r.near.ago)}` : 'Hubo rayos en la última media hora';
  const lj = r.jump != null ? `<div class="rm-lj">Salto brusco de rayos ${haceMin(r.jump)}</div>` : '';
  const near = r.near ? `Más cercano: <b>${distTxt(r.near)}</b>, ${haceMin(r.near.ago)}` : 'Ningún rayo en los últimos 15 min';
  const tr = { up: '<span class="tr up">↑ En aumento</span>', down: '<span class="tr down">↓ Bajando</span>', flat: '<span class="tr">→ Estable</span>' }[r.trend];
  return `<details class="card ray-mini${L ? ' lvlb-' + L : ''}"><summary>${row('on', title, sub, lj, '<span class="chev" aria-hidden="true">›</span>')}</summary>
    <div class="ray-more"><div class="ray-grid">${polar(r.pts)}<div class="ray-info">
      <div class="ray-n"><b>${Math.round(r.n10)}</b> ${Math.round(r.n10) === 1 ? 'rayo' : 'rayos'}</div><div class="muted small">a menos de 10 km en la última media hora</div>
      <div class="ray-near">${near}</div>${tr}</div></div>
    ${r.jump != null ? `<div class="lj"><b>Salto brusco de rayos</b> ${haceMin(r.jump)}: suele anticipar el granizo unos 25 minutos.</div>` : ''}
    <div class="spark-wrap"><span class="muted small">Rayos por minuto a menos de 20 km</span>${spark(r.perMin, r.age)}</div>
    <details><summary class="muted small">Cómo se calcula</summary><p class="small">Contamos los rayos que detecta el satélite GOES-19 (NOAA) a menos de 10 km de este lugar en la última media hora. Los niveles se calibraron con 48 granizadas registradas en aeropuertos de Cuyo y 900 tormentas sin granizo (2018-2026): con 5 rayos o más se detectó el 96% de las granizadas, y con 80 o más el granizo fue unas 6 veces más probable que en una tormenta común. El satélite ubica cada rayo con un margen de algunos kilómetros, y es una estimación: el granizo puede no caer justo en tu punto.</p></details>
    <p class="muted small">Satélite GOES-19 · ${r.age <= 1 ? 'actualizado recién' : `actualizado hace ${r.age} min`}</p></div>
  </details>`;
}

/* ---------- Riesgos estimados ---------- */
// Granizo: inestabilidad (CAPE / índice de levantamiento) + altura de la isoterma 0 °C + código de tormenta con granizo.
function hailLevel(x) {
  if (x.wc === 96 || x.wc === 99) return 3;
  const li = x.li ?? -99, fl = x.fl ?? 0, cape = x.cape ?? 0, pp = x.pp ?? 0;
  if (cape >= 2500 && li <= -5 && fl <= 4300 && pp >= 30) return 3;
  if (cape >= 1500 && li <= -3 && fl <= 4500 && pp >= 30) return 2;
  if ((cape >= 800 && li <= -1 && pp >= 30) || x.wc === 95) return 1;
  return 0;
}
function stormLevel(x) {
  if (x.wc >= 96) return 3;
  if (x.wc === 95) return 2;
  const cape = x.cape ?? 0, pp = x.pp ?? 0;
  if (cape >= 1500 && pp >= 50) return 2;
  if (cape >= 500 && pp >= 30) return 1;
  return 0;
}
const windLevel = g => g >= 90 ? 3 : g >= 70 ? 2 : g >= 50 ? 1 : 0;

function analyze(f) {
  const H = f.hourly, now = Date.now(), off = offsetStr(f.utc_offset_seconds);
  const all = H.time.map((t, i) => ({
    date: t.slice(0, 10), t: new Date(t + ':00' + off), wc: H.weather_code[i], day: H.is_day?.[i] ?? 1,
    temp: H.temperature_2m[i], pp: H.precipitation_probability[i], mm: H.precipitation[i],
    wind: H.wind_speed_10m[i], gust: H.wind_gusts_10m[i],
    cape: H.cape?.[i], li: H.lifted_index?.[i], fl: H.freezing_level_height?.[i]
  })).filter(h => h.t.getTime() > now - 3600e3);
  all.forEach(h => h.hail = hailLevel(h));
  const hours = all.slice(0, 24);
  const dayHail = {};
  all.forEach(h => dayHail[h.date] = Math.max(dayHail[h.date] || 0, h.hail));
  const risk = fn => {
    let best = { lvl: 0, at: null };
    hours.forEach(h => { const l = fn(h); if (l > best.lvl) best = { lvl: l, at: h.t }; });
    return best;
  };
  return { hours, dayHail, hail: risk(h => h.hail), storm: risk(stormLevel), wind: risk(h => windLevel(h.gust ?? 0)) };
}
function offsetStr(s) {
  const sign = s < 0 ? '-' : '+', a = Math.abs(s);
  return sign + String(Math.floor(a / 3600)).padStart(2, '0') + ':' + String(Math.floor(a % 3600 / 60)).padStart(2, '0');
}

/* ---------- SMN: ¿la alerta cubre este punto? ---------- */
function inPoly(lat, lon, poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [yi, xi] = poly[i], [yj, xj] = poly[j];
    if (((yi > lat) !== (yj > lat)) && (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi)) inside = !inside;
  }
  return inside;
}
const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
function smnFor(data, lat, lon, prov) {
  const now = Date.now();
  return (data?.alerts || []).filter(a => {
    if (a.expires && Date.parse(a.expires) < now) return false;
    if (a.polygons?.length) return a.polygons.some(p => inPoly(lat, lon, p));
    return prov && norm(a.area).includes(norm(prov));
  });
}

/* ---------- Sismos ---------- */
function distKm(a, b, c, d) {
  const R = 6371, r = x => x * Math.PI / 180;
  const h = Math.sin(r(c - a) / 2) ** 2 + Math.cos(r(a)) * Math.cos(r(c)) * Math.sin(r(d - b) / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/* ---------- Íconos del clima (SVG propios) ---------- */
const CLOUD = 'M18 44a10 10 0 0 1 1.5-19.9A14 14 0 0 1 46 22a11 11 0 0 1 0 22z';
function wxIcon(code, day = 1, size = 64) {
  const rays = [0, 45, 90, 135, 180, 225, 270, 315].map(a => `<line x1="0" y1="-13" x2="0" y2="-17" transform="rotate(${a})"/>`).join('');
  const sun = (x, y, k = 1) => `<g transform="translate(${x} ${y}) scale(${k})"><g class="wx-spin" stroke="#fbbf24" stroke-width="3" stroke-linecap="round">${rays}</g><circle r="9" fill="#fbbf24"/></g>`;
  const moon = (x, y, k = 1) => `<g transform="translate(${x} ${y}) scale(${k})"><path d="M4-11A11 11 0 1 0 11 6 9.5 9.5 0 0 1 4-11z" fill="#e2e8f0"/></g>`;
  const orb = (x, y, k) => day ? sun(x, y, k) : moon(x, y, k);
  const cloud = (dy = 0, fill = '#cbd5e1', dx = 0, k = 1) => `<path d="${CLOUD}" fill="${fill}" transform="translate(${dx} ${dy}) scale(${k})"/>`;
  const drops = n => Array.from({ length: n }, (_, i) => { const x = 32 + (i - (n - 1) / 2) * 11;
    return `<line class="wx-fall" style="animation-delay:${-i * .3}s" x1="${x}" y1="43" x2="${x - 3}" y2="51" stroke="#60a5fa" stroke-width="3" stroke-linecap="round"/>`; }).join('');
  const flakes = n => Array.from({ length: n }, (_, i) => `<circle class="wx-fall" style="animation-delay:${-i * .4}s" cx="${32 + (i - (n - 1) / 2) * 11}" cy="47" r="2.4" fill="#e0f2fe" stroke="#93c5fd"/>`).join('');
  const bolt = `<path class="wx-flash" d="M33 33l-7 12h6l-3 11 11-15h-6l4-8z" fill="#facc15"/>`;
  const hail = [[19, 49], [45, 50], [38, 58]].map(([x, y], i) => `<circle class="wx-fall" style="animation-delay:${-i * .35}s" cx="${x}" cy="${y}" r="3" fill="#e0f2fe" stroke="#7dd3fc" stroke-width="1.2"/>`).join('');
  const fog = [48, 55].map(y => `<line x1="14" y1="${y}" x2="50" y2="${y}" stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>`).join('');
  let g;
  if (code === 0) g = orb(32, 32, 1.35);
  else if (code <= 2) g = orb(23, 23, .95) + cloud(6, '#e2e8f0', 6, .9);
  else if (code === 3) g = cloud(-2, '#94a3b8', 12, .7) + cloud(6);
  else if (code <= 48) g = cloud(-6) + fog;
  else if (code <= 57) g = cloud(-8) + drops(2);
  else if (code <= 67 || (code >= 80 && code <= 82)) g = cloud(-8, code === 65 || code === 82 ? '#94a3b8' : '#cbd5e1') + drops(3);
  else if (code <= 77 || code === 85 || code === 86) g = cloud(-8) + flakes(3);
  else if (code === 95) g = cloud(-10, '#64748b') + bolt;
  else g = cloud(-10, '#64748b') + bolt + hail;
  return `<svg class="wx" viewBox="0 0 64 64" width="${size}" height="${size}" aria-hidden="true">${g}</svg>`;
}
const RISK_ICON = {
  hail: `<svg viewBox="0 0 64 64" width="34" height="34" aria-hidden="true"><path d="${CLOUD}" fill="#94a3b8" transform="translate(0 -10)"/>${[[20, 46], [32, 52], [44, 46]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="4.5" fill="#e0f2fe" stroke="#38bdf8" stroke-width="1.5"/>`).join('')}</svg>`,
  storm: `<svg viewBox="0 0 64 64" width="34" height="34" aria-hidden="true"><path d="${CLOUD}" fill="#64748b" transform="translate(0 -10)"/><path d="M33 33l-7 12h6l-3 11 11-15h-6l4-8z" fill="#facc15"/></svg>`,
  wind: `<svg viewBox="0 0 64 64" width="34" height="34" aria-hidden="true" fill="none" stroke="#38bdf8" stroke-width="4" stroke-linecap="round"><path d="M8 24h30a7 7 0 1 0-7-7"/><path d="M8 34h42a7 7 0 1 1-7 7"/><path d="M8 44h20"/></svg>`
};
function skyClass(code, day) {
  if (code >= 95) return 'sky-storm';
  if (code >= 51) return 'sky-rain';
  if (code >= 3) return 'sky-cloud';
  return day ? 'sky-day' : 'sky-night';
}

/* ---------- Render ---------- */
const fmtH = d => d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hour12: false });
const fmtDay = d => d.toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric' });
const fmtWhen = d => {
  if (!d) return '';
  const today = new Date().toDateString() === d.toDateString();
  return (today ? 'hoy' : fmtDay(d)) + ' ' + fmtH(d) + ' h';
};
const fmtAgo = ms => { const m = Math.max(0, Math.round((Date.now() - ms) / 60e3)); return m < 60 ? `hace ${m} min` : m < 1440 ? `hace ${Math.round(m / 60)} h` : `hace ${Math.round(m / 1440)} d`; };
const COLOR = ['var(--ok)', 'var(--low)', 'var(--mid)', 'var(--high)'];

function riskTile(name, key, r) {
  const pips = [1, 2, 3].map(i => `<i style="background:${i <= r.lvl ? COLOR[r.lvl] : 'var(--pip)'}"></i>`).join('');
  return `<div class="tile ${key === 'hail' && r.lvl ? 'hot-' + r.lvl : ''}">${RISK_ICON[key]}<div class="muted">${name}</div>
    <b class="t-${r.lvl}">${LVL[r.lvl]}</b><div class="pips">${pips}</div>
    <div class="muted small">${!r.lvl ? '&nbsp;' : r.smn ? 'SMN · ' + (r.smn === 'ahora' ? 'ahora' : fmtH(r.at) + ' h') : fmtWhen(r.at)}</div></div>`;
}

function hourChart(hours) {
  const W = 58, n = hours.length, top = 78, span = 44;
  const ts = hours.map(h => h.temp), mn = Math.min(...ts), mx = Math.max(...ts);
  const y = t => top + span - (t - mn) / ((mx - mn) || 1) * span;
  const x = i => i * W + W / 2;
  const pts = hours.map((h, i) => `${x(i)},${y(h.temp).toFixed(1)}`).join(' ');
  let s = `<svg class="chart" width="${n * W}" height="196" viewBox="0 0 ${n * W} 196" role="img" aria-label="Pronóstico por hora">`;
  hours.forEach((h, i) => {
    if (h.hail >= 1) s += `<rect x="${i * W + 3}" y="1" width="${W - 6}" height="194" rx="10" fill="${COLOR[h.hail]}" fill-opacity=".08" stroke="${COLOR[h.hail]}" stroke-width="2"/>`;
    const bar = Math.round((h.pp ?? 0) / 100 * 30);
    s += `<text x="${x(i)}" y="19" class="c-muted">${i === 0 ? 'Ahora' : fmtH(h.t).slice(0, 2) + ' h'}</text>
       <svg x="${x(i) - 17}" y="25" width="34" height="34" viewBox="0 0 64 64">${wxIcon(h.wc, h.day, 64).replace(/^<svg[^>]*>|<\/svg>$/g, '')}</svg>
      <rect x="${x(i) - 9}" y="${170 - bar}" width="18" height="${bar}" rx="4" fill="var(--accent)" opacity=".75"/>
      <text x="${x(i)}" y="186" class="c-rain">${h.pp ?? 0}%</text>`;
  });
  s += `<polyline points="${pts}" fill="none" stroke="var(--line2)" stroke-width="2.5" stroke-linejoin="round"/>`;
  hours.forEach((h, i) => s += `<circle cx="${x(i)}" cy="${y(h.temp).toFixed(1)}" r="3.5" fill="var(--card)" stroke="var(--text)" stroke-width="2"/>
    <text x="${x(i)}" y="${(y(h.temp) - 9).toFixed(1)}" class="c-temp">${Math.round(h.temp)}°</text>`);
  return s + '</svg>';
}

function render(place, f, smnData, smnErr, quakes, qErr, coords, fromCache, rayData, rayErr) {
  const a = analyze(f), c = f.current, day = c.is_day ?? 1;
  let ray = null;
  try { if (!rayErr && rayData) ray = rayosNear(rayData, coords.lat, coords.lon); } catch { ray = null; }
  const rayLvl = ray && ray.age <= 20 ? ray.lvl : 0;
  // Datos SMN con error o con más de 2 h sin actualizar: no afirmar "sin alertas".
  if (!smnErr && (smnData?.error || !smnData?.updated || Date.now() - Date.parse(smnData.updated) > 2 * 3600e3)) smnErr = true;
  const hits = smnErr ? [] : smnFor(smnData, coords.lat, coords.lon, place.prov);
  const acpStale = !smnErr && (smnData.acp_error || Date.now() - Date.parse(smnData.updated) > 30 * 60e3);
  const acp = acpStale ? [] : hits.filter(x => x.kind === 'acp');
  const now = Date.now(), onT = x => x.onset ? Date.parse(x.onset) : 0;
  const smn = hits.filter(x => x.kind !== 'acp').sort((p, q) => (onT(p) > now) - (onT(q) > now) || onT(p) - onT(q) || (q.level || 1) - (p.level || 1));
  // Las fichas de riesgo también toman las alertas oficiales de las próximas 24 h (si son más altas que el pronóstico)
  const rk = { hail: { ...a.hail }, storm: { ...a.storm }, wind: { ...a.wind } };
  for (const x of smn) {
    const on = onT(x), lv = x.level || 1;
    if (on > now + 24 * 3600e3 || isAdv(x)) continue;
    const t = norm(x.event + ' ' + x.headline), keys = [];
    if (/tormenta/.test(t)) keys.push('storm');
    if (/viento|zonda/.test(t)) keys.push('wind');
    if (/granizo/.test(t + ' ' + norm(x.description))) keys.push('hail');
    for (const k of keys) if (lv > rk[k].lvl) rk[k] = { lvl: lv, at: new Date(Math.max(on, now)), smn: on <= now ? 'ahora' : 'luego' };
  }
  const smnMax = smn.reduce((m, x) => isAdv(x) ? m : Math.max(m, x.level || 1), 0);
  const top = Math.max(a.hail.lvl, a.storm.lvl, a.wind.lvl, smnMax, acp.length ? 3 : 0, rayLvl);
  levels[place.id] = top; renderChips();

  const head = acp.length ? 'Tormenta fuerte en curso en tu zona'
    : rayLvl ? `${ray.near ? 'Rayos ' + distTxt(ray.near) : 'Rayos cerca'}: riesgo ${LVL[rayLvl].toLowerCase()} de granizo`
    : a.hail.lvl ? `Riesgo ${LVL[a.hail.lvl].toLowerCase()} de granizo ${fmtWhen(a.hail.at)}`
    : a.storm.lvl ? `Riesgo ${LVL[a.storm.lvl].toLowerCase()} de tormenta ${fmtWhen(a.storm.at)}`
    : a.wind.lvl ? `Ráfagas fuertes ${fmtWhen(a.wind.at)}`
    : smnMax ? 'Alerta oficial vigente' : 'Sin riesgos a la vista en 24 h';

  let html = '';
  if (fromCache) html += `<div class="card muted">Sin conexión: mostrando datos guardados ${fmtAgo(fromCache)}.</div>`;

  const where = place.gps ? (gpsName.name ? [gpsName.name, gpsName.prov].filter(Boolean).join(', ') : 'Tu ubicación') : (place.full || place.name);
  html += `<section class="hero ${skyClass(c.weather_code, day)}">
    <div class="hero-place">${place.gps ? '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z" fill="currentColor"/></svg>' : ''}
      <span>${esc(where)}</span>${place.gps ? '<span class="hero-sub">Ubicación actual</span>' : ''}</div>
    <div class="hero-top"><div><div class="hero-t">${Math.round(c.temperature_2m)}°</div>
      <div class="hero-d">${esc(WMO[c.weather_code] || '')}</div></div>${wxIcon(c.weather_code, day, 112)}</div>
    <div class="hero-head"><span class="dotb" style="background:${COLOR[top]}"></span>${esc(head)}</div>
    <div class="hero-meta"><span>Sensación <b>${Math.round(c.apparent_temperature)}°</b></span>
      <span>Viento <b>${Math.round(c.wind_speed_10m)}</b> km/h</span><span>Ráfagas <b>${Math.round(c.wind_gusts_10m)}</b></span>
      <span>Humedad <b>${c.relative_humidity_2m}%</b></span></div>
  </section>`;

  // Avisos a muy corto plazo (tormenta ya en curso, detectada por radar)
  acp.forEach(x => html += `<section class="card acp"><div class="acp-tag"><span class="pulse"></span>AVISO A MUY CORTO PLAZO · SMN</div>
    <h3>${esc(x.event || x.headline)}</h3>
    ${x.description ? `<p>${esc(x.description)}</p>` : ''}
    <p class="muted">${x.expires ? 'Válido hasta ' + fmtWhen(new Date(x.expires)) + '. ' : ''}${x.area ? 'Zona: ' + esc(x.area.slice(0, 160)) + '.' : ''}</p>
    ${x.instruction ? `<details><summary class="muted">Qué hacer</summary><p>${esc(x.instruction)}</p></details>` : ''}</section>`);

  // Rayos cerca (ahora)
  html += rayosCard(ray, rayErr || !ray);

  // Riesgo estimado
  html += `<section class="card"><h3>Riesgo estimado · próximas 24 h</h3>
    <div class="tiles">${riskTile('Granizo', 'hail', rk.hail)}${riskTile('Tormenta', 'storm', rk.storm)}${riskTile('Viento', 'wind', rk.wind)}</div>
    <p class="muted small">Estimación propia según el pronóstico y las alertas del SMN. No reemplaza los avisos oficiales.</p></section>`;

  // Alertas oficiales
  html += `<section class="card alert lvl-${smnMax}"><h3 class="h-sub">Alertas oficiales<small>Servicio Meteorológico Nacional (SMN)</small></h3>`;
  if (smnErr) html += `<p class="muted">No se pudieron leer las alertas del SMN. <a href="https://www.smn.gob.ar/alertas" target="_blank" rel="noopener">Ver en smn.gob.ar</a></p>`;
  else {
    if (!smn.length) html += `<p class="muted">Sin alertas vigentes para este lugar.</p>`;
    else html += `<ul class="list">${smn.map(x => `<li>
      <div class="row"><b>${esc(x.event)}</b>${isAdv(x) ? '<span class="badge b-adv">Advertencia</span>' : `<span class="badge b-${x.level || 1}">${SMN_LVL[x.level] || esc(x.severity)}</span>`}</div>
      ${isAdv(x) ? '' : `<div class="small t-${x.level || 1}"><b>${(/temperatura|calor|frio/.test(norm(x.event)) ? SMN_HEALTH : SMN_DO)[x.level || 1]}</b></div>`}
      <div class="muted">${onT(x) <= now ? '<b class="' + (isAdv(x) ? 't-adv' : 't-' + (x.level || 1)) + '">Vigente ahora</b>' : 'Desde ' + fmtWhen(new Date(x.onset))}${x.expires ? ' · hasta ' + fmtWhen(new Date(x.expires)) : ''}</div>
      ${x.description ? `<details><summary class="muted">Detalle</summary><p>${esc(x.description)}</p></details>` : ''}
    </li>`).join('')}</ul>`;
    html += `<p class="muted small">${acp.length ? '' : acpStale ? 'Avisos a muy corto plazo: no disponibles ahora. ' : 'Sin avisos a muy corto plazo en tu zona. '}Actualizado ${fmtAgo(Date.parse(smnData.updated))} ·
      <a href="https://www.smn.gob.ar/alertas" target="_blank" rel="noopener">smn.gob.ar</a></p>`;
  }
  html += `</section>`;

  // Por hora
  html += `<section class="card"><h3>Por hora</h3><div class="scroll">${hourChart(a.hours)}</div>
    <p class="muted small">Barras azules: probabilidad de lluvia. Recuadro de color: horas con riesgo de granizo (amarillo bajo, naranja moderado, rojo alto).</p></section>`;

  // Próximos días
  const D = f.daily, lo = Math.min(...D.temperature_2m_min), hi = Math.max(...D.temperature_2m_max), rng = (hi - lo) || 1;
  html += `<section class="card"><h3>Próximos días</h3><ul class="list days">${D.time.map((t, i) => {
    const hl = a.dayHail[t] || 0, mn = D.temperature_2m_min[i], mx = D.temperature_2m_max[i];
    return `<li><span class="d-name"><span>${i === 0 ? 'Hoy' : fmtDay(new Date(t + 'T12:00'))}</span>${hl ? `<span class="badge d-hail b-${hl}">🧊 ${LVL[hl]}</span>` : ''}</span>${wxIcon(D.weather_code[i], 1, 34)}
      <span class="d-rain">${D.precipitation_probability_max[i] ?? 0}%</span>
      <span class="d-min">${Math.round(mn)}°</span>
      <span class="d-bar"><i style="left:${((mn - lo) / rng * 100).toFixed(0)}%;width:${Math.max(6, (mx - mn) / rng * 100).toFixed(0)}%"></i></span>
      <b class="d-max">${Math.round(mx)}°</b></li>`; }).join('')}</ul>
    <p class="muted small">% de lluvia · 🧊 riesgo estimado de granizo ese día.</p></section>`;

  // Sismos
  html += `<section class="card"><h3>Sismos cercanos · últimos 7 días</h3>`;
  if (qErr) html += `<p class="muted">No se pudieron leer los sismos.</p>`;
  else {
    const list = (quakes?.features || []).map(q => ({
      mag: q.properties.mag, t: q.properties.time,
      km: distKm(coords.lat, coords.lon, q.geometry.coordinates[1], q.geometry.coordinates[0])
    }));
    html += !list.length ? `<p class="muted">Sin sismos de magnitud 2,5 o más a menos de 400 km.</p>` :
      `<ul class="list">${list.map(q => `<li class="row"><span><span class="badge b-${q.mag >= 5 ? 3 : q.mag >= 4 ? 2 : 1}">M ${q.mag.toFixed(1)}</span>
        a ${Math.round(q.km)} km</span><span class="muted">${fmtAgo(q.t)}</span></li>`).join('')}</ul>`;
  }
  html += `</section>`;

  if (!place.gps) html += `<p class="center"><button class="btn ghost small" id="rmPlace">Quitar “${esc(place.name)}”</button></p>`;

  $('#main').innerHTML = html;
  const rm = $('#rmPlace'); if (rm) rm.onclick = () => removePlace(place.id);
}

function showMsg(msg, retry) {
  $('#main').innerHTML = `<div class="card center"><p>${esc(msg)}</p>
    ${retry ? '<p><button class="btn" id="retry">Reintentar</button></p>' : ''}
    <p class="muted">También podés agregar un lugar a mano con “＋ Lugar”.</p></div>`;
  const b = $('#retry'); if (b) b.onclick = load;
}

let loadSeq = 0;
async function load() {
  const seq = ++loadSeq;
  const place = allPlaces().find(p => p.id === selected) || allPlaces()[0];
  $('#refresh').classList.add('spin');
  $('#main').innerHTML = '<p class="muted center">Cargando…</p>';
  try {
    let coords;
    if (place.gps) {
      try { coords = gpsCoords = await getGPS(); }
      catch (e) { if (!gpsCoords) throw Object.assign(e, { retry: true }); coords = gpsCoords; }
      try {
        const g = await placeName(coords.lat, coords.lon);
        if (g.name) { gpsName = g; place.name = '📍 ' + g.name; place.prov = g.prov; renderChips(); }
      } catch { }
    } else coords = { lat: place.lat, lon: place.lon };

    const [f, smn, q, ry] = await Promise.allSettled([
      getJSON(forecastURL(coords.lat.toFixed(3), coords.lon.toFixed(3))), getSMN(),
      getJSON(quakesURL(coords.lat.toFixed(3), coords.lon.toFixed(3))), getRayos()]);
    if (seq !== loadSeq) return;

    if (f.status === 'fulfilled') {
      ls.set(LS_CACHE + place.id, { t: Date.now(), f: f.value, coords, smn: smn.value, q: q.value, ry: raySub(ry.value, coords.lat, coords.lon) });
      render(place, f.value, smn.value, smn.status === 'rejected', q.value, q.status === 'rejected', coords, 0, ry.value, ry.status === 'rejected');
    } else {
      const c = ls.get(LS_CACHE + place.id);
      if (c) render(place, c.f, c.smn, !c.smn, c.q, !c.q, c.coords, c.t, c.ry, !c.ry);
      else showMsg('No se pudo cargar el pronóstico. Revisá la conexión.', true);
    }
  } catch (e) {
    if (seq !== loadSeq) return;
    showMsg(e.message, e.retry);
  } finally {
    if (seq === loadSeq) $('#refresh').classList.remove('spin');
  }
}

$('#refresh').onclick = () => { smnCache = null; load(); };
document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });

/* ---------- Tema: automático / claro / oscuro ---------- */
const LS_THEME = 'ac.theme';
const AUTO_ICON = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor"/></svg>';
const THEMES = [[null, AUTO_ICON, 'Tema automático (según el celular)'], ['light', '☀️', 'Tema claro'], ['dark', '🌙', 'Tema oscuro']];
let toastT;
function toast(msg) {
  const t = $('#toast'); t.textContent = msg; t.classList.add('on');
  clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('on'), 1600);
}
function applyTheme(announce) {
  const cur = ls.get(LS_THEME, null);
  const [, icon, label] = THEMES.find(x => x[0] === cur) || THEMES[0];
  if (cur) document.documentElement.dataset.theme = cur; else delete document.documentElement.dataset.theme;
  const dark = cur ? cur === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  document.querySelectorAll('meta[name=theme-color]').forEach(m => { m.removeAttribute('media'); m.content = dark ? '#111315' : '#f4f6f8'; });
  document.documentElement.classList.toggle('is-dark', dark);
  const b = $('#theme'); b.innerHTML = icon; b.setAttribute('aria-label', label); b.title = label;
  if (announce) toast(label);
}
$('#theme').onclick = () => {
  const cur = ls.get(LS_THEME, null), i = THEMES.findIndex(x => x[0] === cur);
  ls.set(LS_THEME, THEMES[(i + 1) % THEMES.length][0]); applyTheme(true);
};
matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => applyTheme(false));
applyTheme(false);

/* ---------- Novedades (historial de versiones para el usuario) ---------- */
const NEWS = [
  ['1.13', '14/11/2026', ['Cada alerta dice qué hacer según su color, como lo indica el SMN: Informate, Preparate o Seguí las instrucciones oficiales.', 'Las advertencias (niebla, ceniza, polvo, humo) se muestran en violeta.']],
  ['1.12', '14/11/2026', ['Las alertas del SMN muestran primero la que está vigente y después las próximas.', 'Las fichas de riesgo también tienen en cuenta las alertas oficiales del SMN.']],
  ['1.11', '13/11/2026', ['Nuevo: "Rayos cerca". Muestra si el satélite detecta rayos a tu alrededor y estima el riesgo de granizo en ese momento. Tocá la fila para ver el detalle.']],
  ['1.10', '13/11/2026', ['Las novedades de cada versión se ven dentro de la app.']],
  ['1.9', '13/11/2026', ['La tarjeta de alertas indica que las emite el Servicio Meteorológico Nacional (SMN).']],
  ['1.8', '13/11/2026', ['Niveles de granizo más fáciles de distinguir: bajo en amarillo, moderado en naranja y alto en rojo.',
    'El gráfico por hora también marca las horas con riesgo bajo.']],
  ['1.7', '13/11/2026', ['Modo claro más legible: mejor contraste en fichas, textos y colores.',
    'La ficha de granizo y las horas con riesgo se destacan en naranja o rojo.']],
  ['1.6', '13/11/2026', ['La pestaña de tu ubicación muestra el nombre del lugar.',
    'La cabecera indica la localidad de cada lugar guardado.']],
  ['1.5', '13/11/2026', ['Botón para elegir tema automático, claro u oscuro.']],
  ['1.4', '13/11/2026', ['Aviso para instalar la app en el celular.']],
  ['1.3', '13/11/2026', ['El buscador de lugares muestra solo localidades de Argentina.']],
  ['1.2', '13/11/2026', ['Avisos a muy corto plazo del SMN: tormentas fuertes en curso en tu zona.',
    'Alertas actualizadas con más frecuencia.', 'Nuevo diseño con íconos animados, gráfico por hora y pronóstico a 7 días.']],
  ['1.0', '13/11/2026', ['Primera versión: riesgo de granizo, tormenta y viento, alertas oficiales del SMN, pronóstico y sismos cercanos.']]
];
$('#newsBtn').onclick = () => {
  $('#newsList').innerHTML = NEWS.map(([v, d, items]) => `<section class="news-item"><div class="row"><b>Versión ${v}</b><span class="muted small">${d}</span></div>
    <ul>${items.map(t => `<li>${esc(t)}</li>`).join('')}</ul></section>`).join('');
  $('#newsDlg').showModal();
};
$('#newsClose').onclick = () => $('#newsDlg').close();

/* ---------- Instalar como app ---------- */
const LS_INSTALL = 'ac.installHidden';
let installEvt = null;
const isStandalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
const SHARE_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" style="vertical-align:-3px" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 11v9h14v-9"/></svg>';
function renderInstall() {
  const box = $('#install');
  if (isStandalone() || ls.get(LS_INSTALL, false) || (!installEvt && !isIOS())) { box.hidden = true; return; }
  box.hidden = false;
  box.innerHTML = installEvt
    ? `<span>📲 Instalá Atento Clima en tu celular</span><span class="row"><button class="btn small" id="doInstall">Instalar</button><button class="icon-btn x" id="hideInstall" aria-label="Cerrar">✕</button></span>`
    : `<span>📲 Para instalarla: en Safari tocá ${SHARE_ICON} <b>Compartir</b> y después <b>Agregar a inicio</b>.</span><button class="icon-btn x" id="hideInstall" aria-label="Cerrar">✕</button>`;
  $('#hideInstall').onclick = () => { ls.set(LS_INSTALL, true); box.hidden = true; };
  const b = $('#doInstall');
  if (b) b.onclick = async () => {
    installEvt.prompt();
    try { await installEvt.userChoice; } catch { }
    installEvt = null; renderInstall();
  };
}
window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); installEvt = e; renderInstall(); });
window.addEventListener('appinstalled', () => { installEvt = null; renderInstall(); });
renderInstall();

if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => { });

renderChips();
load();
