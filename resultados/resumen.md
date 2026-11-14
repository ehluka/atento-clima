# Calibración granizo vs. rayos (GLM)

Modo: completo. Tandas completas: 15/15. Horas sin datos satelitales: 7.

Casos METAR en el período (todo el país, sin Patagonia austral): granizo {'resto': 147, 'cuyo': 48} | tormentas sin granizo {'resto': 9311, 'cuyo': 902}

## Aeropuertos – cuyo: 48 granizadas vs 900 tormentas sin granizo (muestra)

- Radio 10 km: AUC rayos máx. en 10 min = 0.83; AUC rayos 30 min previos = 0.87; granizadas sin ningún rayo cerca: 0%
- Radio 20 km: AUC rayos máx. en 10 min = 0.79; AUC rayos 30 min previos = 0.82; granizadas sin ningún rayo cerca: 0%
- Radio 30 km: AUC rayos máx. en 10 min = 0.76; AUC rayos 30 min previos = 0.78; granizadas sin ningún rayo cerca: 0%

Umbrales (radio 20 km, máximo de rayos en 10 min) – detecta / falsa alarma / probabilidad real de granizo si avisa:
  ≥  1: detecta 100% | falsa alarma 89% | prob. granizo 6%
  ≥  3: detecta 98% | falsa alarma 82% | prob. granizo 6%
  ≥  5: detecta 98% | falsa alarma 75% | prob. granizo 6%
  ≥ 10: detecta 96% | falsa alarma 63% | prob. granizo 7%
  ≥ 20: detecta 92% | falsa alarma 48% | prob. granizo 9%
  ≥ 40: detecta 75% | falsa alarma 32% | prob. granizo 11%
  ≥ 80: detecta 54% | falsa alarma 17% | prob. granizo 14%
  ≥160: detecta 29% | falsa alarma 7% | prob. granizo 17%
  ≥320: detecta 2% | falsa alarma 1% | prob. granizo 10%

Salto brusco de rayos (radio 20 km, 60 min antes del granizo):
  activación ≥1 rayos/min: detecta 98% | falsa alarma 72% | prob. granizo 7% | anticipación mediana 41 min
  activación ≥2 rayos/min: detecta 92% | falsa alarma 51% | prob. granizo 9% | anticipación mediana 31 min
  activación ≥4 rayos/min: detecta 77% | falsa alarma 32% | prob. granizo 11% | anticipación mediana 25 min
  activación ≥8 rayos/min: detecta 56% | falsa alarma 16% | prob. granizo 15% | anticipación mediana 19 min

## Aeropuertos – todos: 194 granizadas vs 1300 tormentas sin granizo (muestra)

- Radio 10 km: AUC rayos máx. en 10 min = 0.77; AUC rayos 30 min previos = 0.78; granizadas sin ningún rayo cerca: 11%
- Radio 20 km: AUC rayos máx. en 10 min = 0.75; AUC rayos 30 min previos = 0.76; granizadas sin ningún rayo cerca: 7%
- Radio 30 km: AUC rayos máx. en 10 min = 0.75; AUC rayos 30 min previos = 0.76; granizadas sin ningún rayo cerca: 5%

Umbrales (radio 20 km, máximo de rayos en 10 min) – detecta / falsa alarma / probabilidad real de granizo si avisa:
  ≥  1: detecta 93% | falsa alarma 88% | prob. granizo 2%
  ≥  3: detecta 92% | falsa alarma 80% | prob. granizo 2%
  ≥  5: detecta 91% | falsa alarma 73% | prob. granizo 2%
  ≥ 10: detecta 88% | falsa alarma 60% | prob. granizo 3%
  ≥ 20: detecta 82% | falsa alarma 45% | prob. granizo 3%
  ≥ 40: detecta 72% | falsa alarma 31% | prob. granizo 4%
  ≥ 80: detecta 55% | falsa alarma 17% | prob. granizo 6%
  ≥160: detecta 30% | falsa alarma 8% | prob. granizo 7%
  ≥320: detecta 6% | falsa alarma 1% | prob. granizo 9%

Salto brusco de rayos (radio 20 km, 60 min antes del granizo):
  activación ≥1 rayos/min: detecta 89% | falsa alarma 70% | prob. granizo 2% | anticipación mediana 39 min
  activación ≥2 rayos/min: detecta 80% | falsa alarma 49% | prob. granizo 3% | anticipación mediana 33 min
  activación ≥4 rayos/min: detecta 72% | falsa alarma 31% | prob. granizo 4% | anticipación mediana 27 min
  activación ≥8 rayos/min: detecta 54% | falsa alarma 17% | prob. granizo 6% | anticipación mediana 21 min

## Contingencias Mendoza: 2521 lugares con granizo (radar) vs 1840 con lluvia sin granizo

- Radio 10 km: AUC máx. 10 min = 0.66; AUC total = 0.66
- Radio 20 km: AUC máx. 10 min = 0.65; AUC total = 0.66
- Radio 30 km: AUC máx. 10 min = 0.65; AUC total = 0.65

Umbrales (radio 20 km, máximo en 10 min):
  ≥  1: granizo 69% | lluvia sin granizo 58%
  ≥  3: granizo 68% | lluvia sin granizo 56%
  ≥  5: granizo 66% | lluvia sin granizo 50%
  ≥ 10: granizo 63% | lluvia sin granizo 42%
  ≥ 20: granizo 59% | lluvia sin granizo 33%
  ≥ 40: granizo 51% | lluvia sin granizo 21%
  ≥ 80: granizo 38% | lluvia sin granizo 10%
  ≥160: granizo 17% | lluvia sin granizo 3%
  ≥320: granizo 3% | lluvia sin granizo 0%

Cuartiles máx. 10 min (20 km): granizo [0.0, 42.0, 126.0] | lluvia [0.0, 5.0, 31.0]
