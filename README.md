# Atento Clima

App web gratuita (instalable en el celular) con alertas según tu ubicación:
riesgo estimado de granizo, tormenta y viento, alertas oficiales del SMN, pronóstico por hora y sismos cercanos.

- Pronóstico y búsqueda de lugares: [Open-Meteo](https://open-meteo.com/)
- Sismos: [USGS](https://earthquake.usgs.gov/)
- Alertas oficiales: feed CAP del [SMN](https://www.smn.gob.ar/alertas), descargado cada 15 min por GitHub Actions a `data/alerts.json`

El riesgo de granizo es una estimación orientativa; ante todo, seguir las alertas oficiales del SMN.
App independiente, sin relación con el SMN.
