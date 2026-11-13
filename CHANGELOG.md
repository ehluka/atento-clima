# Historial de versiones — Atento Clima

App: https://ehluka.github.io/atento-clima/ · Repo: https://github.com/ehluka/atento-clima

## v1.9 — 13/11/2026
- La tarjeta de alertas se titula "Alertas oficiales" con el subtítulo "Servicio Meteorológico Nacional (SMN)".

## v1.8 — 13/11/2026
- Niveles de granizo bien diferenciados: bajo en amarillo, moderado en naranja, alto en rojo (fichas, etiquetas y gráfico por hora), en modo claro y oscuro.
- Etiquetas amarillas y naranjas con texto oscuro para que se lean bien.
- "Por hora" también marca las horas con riesgo bajo (amarillo).

## v1.7 — 13/11/2026
- Modo claro más legible: fondo más marcado, fichas con sombra y borde, colores de nivel más oscuros (contraste 4,5 o más).
- Cabecera con degradé más oscuro para que el texto blanco se lea bien.
- Granizo resaltado: la ficha de granizo y las horas con riesgo llevan contorno naranja o rojo; etiquetas llenas en "Próximos días".
- "Próximos días" con columnas alineadas; íconos con contorno en modo claro; punto de alerta de la pestaña con aro blanco.

## v1.6 — 13/11/2026
- La pestaña de ubicación muestra el nombre del lugar (ej. "📍 Maipú") y la cabecera dice "Maipú, Mendoza · Ubicación actual" (fuente: BigDataCloud).
- Los lugares guardados muestran la localidad real en la cabecera.
- Con la provincia del GPS, también se reconocen alertas oficiales que vienen sin zona dibujada.

## v1.5 — 13/11/2026
- Botón de tema: automático (sigue al celular) / claro / oscuro. Recuerda la elección.

## v1.4 — 13/11/2026
- Cartel para instalar la app: botón "Instalar" en Android; pasos (Compartir → Agregar a inicio) en iPhone.

## v1.3 — 13/11/2026
- El buscador de lugares muestra solo localidades de Argentina.
- Probado y descartado: granizo con 3 modelos (GFS, ECMWF, ICON) y mapa de radar (RainViewer). Se quitaron porque confundían y no quedaban bien.

## v1.2 — 13/11/2026
- Avisos a muy corto plazo del SMN (tormenta en curso detectada por radar), destacados en rojo.
- Alertas del SMN actualizadas cada 5 min (antes 15).
- Corrección: el SMN publica las horas en UTC rotuladas como -03:00; las alertas se mostraban vigentes 3 h de más.
- Rediseño: íconos del clima propios y animados, cabecera con color según el cielo, paneles de riesgo, gráfico por hora y pronóstico a 7 días con riesgo de granizo por día.

## v1.1 — 13/11/2026
- Descarga de alertas del SMN más confiable: reintentos y caché para no superar el límite de pedidos.

## v1.0 — 13/11/2026
- Primera versión: app web instalable y gratuita.
- Ubicación por GPS + lugares guardados.
- Riesgo estimado de granizo, tormenta y viento (Open-Meteo), alertas oficiales del SMN, pronóstico por hora y sismos cercanos (USGS).
- Tema automático claro/oscuro.

## Ideas pendientes
- Calidad del aire / índice UV.
- Incendios cercanos (NASA FIRMS, requiere clave gratuita).
- Sismos del INPRES (a verificar si hay datos accesibles).
