'use strict';
/* Atento Clima — alertas por ubicación. Sin servidor: Open-Meteo, USGS y SMN (vía data/alerts.json). */

const LS_PLACES = 'ac.places', LS_SEL = 'ac.sel', LS_CACHE = 'ac.cache.';
const LVL = ['Sin riesgo', 'Bajo', 'Moderado', 'Alto'];
const SMN_LVL = { 1: 'Amarillo', 2: 'Naranja', 3: 'Rojo' };

const WMO = {
  0: 'Despejado', 1: 'Mayormente despejado', 2: 'Parcialmente nublado', 3: 'Nublado',
  45: 'Niebla', 48: 'Niebla con escarcha', 51: 'Llovizna débil', 53: 'Llovizna', 55: 'Llovizna intensa',
  56: 'Llovizna helada', 57: 'Llovizna helada intensa', 61: 'Lluvia débil', 63: 'Lluvia', 65: 'Lluvia intensa',
  66: 'Lluvia helada', 67: 'Lluvia helada intensa', 71: 'Nevada débil', 73: 'Nevada', 75: 'Nevada intensa',
  77: 'Granos de nieve', 80: 'Chaparrones débiles', 81: 'Chaparrones', 82: 'Chaparrones fuertes',
  85: 'Chaparrones de nieve', 86: 'Chaparrones de nieve fuertes', 95: 'Tormenta',
  96: 'Tormenta con granizo', 99: 'Tormenta fuerte con granizo'
};
const ICON = c => c === 0 ? '☀️' : c <= 2 ? '🌤️' : c === 3 ? '☁️' : c <= 48 ? '🌫️' : c <= 67 ? '🌧️' :
  c <= 77 ? '🌨️' : c <= 82 ? '🌦️' : c <= 86 ? '🌨️' : '⛈️';

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
function allPlaces() { return [{ id: 'gps', name: '📍 Mi ubicación', gps: true }, ...places]; }

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
    const r = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(q)}&count=8&language=es&format=json`);
    const j = await r.json();
    const res = (j.results || []).sort((a, b) => (b.country_code === 'AR') - (a.country_code === 'AR'));
    if (!res.length) { ul.innerHTML = '<li class="muted">Sin resultados</li>'; return; }
    ul.innerHTML = res.map((p, i) =>
      `<li tabindex="0" data-i="${i}"><b>${esc(p.name)}</b> <span class="muted">${esc([p.admin2, p.admin1, p.country].filter(Boolean).join(', '))}</span></li>`).join('');
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

/* ---------- Datos ---------- */
async function getJSON(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}

function forecastURL(lat, lon) {
  const h = 'temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m,cape,lifted_index,freezing_level_height,uv_index';
  const d = 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_gusts_10m_max,uv_index_max';
  const c = 'temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_gusts_10m';
  return `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=${c}&hourly=${h}&daily=${d}&timezone=auto&forecast_days=3&forecast_hours=48`;
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
  const H = f.hourly, now = Date.now();
  const hours = H.time.map((t, i) => ({
    t: new Date(t + ':00' + offsetStr(f.utc_offset_seconds)), wc: H.weather_code[i], temp: H.temperature_2m[i],
    pp: H.precipitation_probability[i], mm: H.precipitation[i], wind: H.wind_speed_10m[i], gust: H.wind_gusts_10m[i],
    cape: H.cape?.[i], li: H.lifted_index?.[i], fl: H.freezing_level_height?.[i], uv: H.uv_index?.[i]
  })).filter(h => h.t.getTime() > now - 3600e3).slice(0, 24);
  const risk = (fn, key) => {
    let best = { lvl: 0, at: null };
    hours.forEach(h => { const l = fn(key ? h[key] ?? 0 : h); if (l > best.lvl) best = { lvl: l, at: h.t }; });
    return best;
  };
  hours.forEach(h => h.hail = hailLevel(h));
  return { hours, hail: risk(hailLevel), storm: risk(stormLevel), wind: risk(windLevel, 'gust') };
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

/* ---------- Render ---------- */
const fmtH = d => d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hour12: false });
const fmtDay = d => d.toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric' });
const fmtWhen = d => {
  if (!d) return '';
  const today = new Date().toDateString() === d.toDateString();
  return (today ? 'hoy' : fmtDay(d)) + ' ' + fmtH(d) + ' h';
};
const fmtAgo = ms => { const m = Math.round((Date.now() - ms) / 60e3); return m < 60 ? `hace ${m} min` : m < 1440 ? `hace ${Math.round(m / 60)} h` : `hace ${Math.round(m / 1440)} d`; };

function riskRow(name, icon, r) {
  return `<li class="row"><span>${icon} ${name}</span><span>${r.lvl ? `<span class="muted">${fmtWhen(r.at)}</span> ` : ''}<span class="badge b-${r.lvl}">${LVL[r.lvl]}</span></span></li>`;
}

function render(place, f, smnData, smnErr, quakes, qErr, coords, fromCache) {
  const a = analyze(f), c = f.current;
  // Datos SMN con error o con más de 2 h sin actualizar: no afirmar "sin alertas".
  if (!smnErr && (smnData?.error || !smnData?.updated || Date.now() - Date.parse(smnData.updated) > 2 * 3600e3)) smnErr = true;
  const smn = smnErr ? [] : smnFor(smnData, coords.lat, coords.lon, place.prov);
  const smnMax = smn.reduce((m, x) => Math.max(m, x.level || 1), 0);
  const top = Math.max(a.hail.lvl, a.storm.lvl, a.wind.lvl, smnMax);
  levels[place.id] = top; renderChips();

  let html = '';
  if (fromCache) html += `<div class="card muted">Sin conexión: mostrando datos guardados ${fmtAgo(fromCache)}.</div>`;

  html += `<section class="card now">
    <div><div class="t">${Math.round(c.temperature_2m)}°</div><div class="muted">Sensación ${Math.round(c.apparent_temperature)}°</div></div>
    <div class="d"><div style="font-size:2rem">${ICON(c.weather_code)}</div>${esc(WMO[c.weather_code] || '')}<br>
    Viento ${Math.round(c.wind_speed_10m)} km/h · ráfagas ${Math.round(c.wind_gusts_10m)}<br>Humedad ${c.relative_humidity_2m}%</div>
  </section>`;

  // Alertas oficiales
  html += `<section class="card alert lvl-${smnMax}"><h3>Alertas oficiales SMN</h3>`;
  if (smnErr) html += `<p class="muted">No se pudieron leer las alertas del SMN. <a href="https://www.smn.gob.ar/alertas" target="_blank" rel="noopener">Ver en smn.gob.ar</a></p>`;
  else if (!smn.length) html += `<p class="muted">Sin alertas vigentes para este lugar.${smnData?.updated ? ` Actualizado ${fmtAgo(Date.parse(smnData.updated))}.` : ''}</p>`;
  else html += `<ul class="list">${smn.map(x => `<li>
      <div class="row"><b>${esc(x.event)}</b><span class="badge b-${x.level || 1}">${SMN_LVL[x.level] || esc(x.severity)}</span></div>
      <div class="muted">${x.onset ? 'Desde ' + fmtWhen(new Date(x.onset)) : ''}${x.expires ? ' · hasta ' + fmtWhen(new Date(x.expires)) : ''}</div>
      ${x.description ? `<details><summary class="muted">Detalle</summary><p>${esc(x.description)}</p></details>` : ''}
    </li>`).join('')}</ul><p class="muted"><a href="https://www.smn.gob.ar/alertas" target="_blank" rel="noopener">Ver en smn.gob.ar</a></p>`;
  html += `</section>`;

  // Riesgo estimado
  html += `<section class="card alert lvl-${Math.max(a.hail.lvl, a.storm.lvl, a.wind.lvl)}"><h3>Riesgo estimado · próximas 24 h</h3>
    <ul class="list">${riskRow('Granizo', '🧊', a.hail)}${riskRow('Tormenta', '⛈️', a.storm)}${riskRow('Viento fuerte', '💨', a.wind)}</ul>
    <p class="muted">Estimación propia según el pronóstico. No reemplaza las alertas oficiales.</p></section>`;

  // Por hora
  html += `<section class="card"><h3>Por hora</h3><div class="hours">${a.hours.map(h => `
    <div class="h ${h.hail >= 2 ? 'risk' : ''}" title="${esc(WMO[h.wc] || '')}">
      <div class="muted">${fmtH(h.t).slice(0, 2)} h</div><div>${ICON(h.wc)}</div><b>${Math.round(h.temp)}°</b>
      <div class="rain">${h.pp ?? 0}%</div><div class="muted">${Math.round(h.gust)}</div></div>`).join('')}
    </div><p class="muted">💧 probabilidad de lluvia · abajo, ráfagas en km/h. En naranja, horas con riesgo de granizo.</p></section>`;

  // Próximos días
  const D = f.daily;
  html += `<section class="card"><h3>Próximos días</h3><ul class="list">${D.time.map((t, i) => `
    <li class="row"><span>${ICON(D.weather_code[i])} ${i === 0 ? 'Hoy' : fmtDay(new Date(t + 'T12:00'))}</span>
    <span class="muted">${D.precipitation_probability_max[i] ?? 0}% · ${(D.precipitation_sum[i] ?? 0).toFixed(1)} mm · UV ${Math.round(D.uv_index_max?.[i] ?? 0)}</span>
    <span><b>${Math.round(D.temperature_2m_max[i])}°</b> / ${Math.round(D.temperature_2m_min[i])}°</span></li>`).join('')}</ul></section>`;

  // Sismos
  html += `<section class="card"><h3>Sismos cercanos · últimos 7 días</h3>`;
  if (qErr) html += `<p class="muted">No se pudieron leer los sismos.</p>`;
  else {
    const list = (quakes?.features || []).map(q => ({
      mag: q.properties.mag, place: q.properties.place, t: q.properties.time, url: q.properties.url,
      km: distKm(coords.lat, coords.lon, q.geometry.coordinates[1], q.geometry.coordinates[0])
    }));
    html += !list.length ? `<p class="muted">Sin sismos de magnitud 2,5 o más a menos de 400 km.</p>` :
      `<ul class="list">${list.map(q => `<li class="row"><span><span class="badge b-${q.mag >= 5 ? 3 : q.mag >= 4 ? 2 : 1}">M ${q.mag.toFixed(1)}</span>
        ${Math.round(q.km)} km</span><span class="muted">${fmtAgo(q.t)}</span></li>`).join('')}</ul>`;
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
    } else coords = { lat: place.lat, lon: place.lon };

    const [f, smn, q] = await Promise.allSettled([
      getJSON(forecastURL(coords.lat.toFixed(3), coords.lon.toFixed(3))), getSMN(),
      getJSON(quakesURL(coords.lat.toFixed(3), coords.lon.toFixed(3)))]);
    if (seq !== loadSeq) return;

    if (f.status === 'fulfilled') {
      ls.set(LS_CACHE + place.id, { t: Date.now(), f: f.value, coords, smn: smn.value, q: q.value });
      render(place, f.value, smn.value, smn.status === 'rejected', q.value, q.status === 'rejected', coords, 0);
    } else {
      const c = ls.get(LS_CACHE + place.id);
      if (c) render(place, c.f, c.smn, !c.smn, c.q, !c.q, c.coords, c.t);
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

if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => { });

renderChips();
load();
