# Calibración granizo vs. rayos (GLM)

Modo: piloto. Tandas completas: 2/2. Horas sin datos satelitales: 0.

Casos METAR en el período (todo el país, sin Patagonia austral): granizo {'resto': 147, 'cuyo': 48} | tormentas sin granizo {'resto': 9311, 'cuyo': 902}

## Aeropuertos – cuyo: 4 granizadas vs 4 tormentas sin granizo (muestra)

- Radio 10 km: AUC rayos máx. en 10 min = 0.81; AUC rayos 30 min previos = 0.75; granizadas sin ningún rayo cerca: 0%
- Radio 20 km: AUC rayos máx. en 10 min = 0.56; AUC rayos 30 min previos = 0.56; granizadas sin ningún rayo cerca: 0%
- Radio 30 km: AUC rayos máx. en 10 min = 0.56; AUC rayos 30 min previos = 0.50; granizadas sin ningún rayo cerca: 0%

Umbrales (radio 20 km, máximo de rayos en 10 min) – detecta / falsa alarma / probabilidad real de granizo si avisa:
  ≥  1: detecta 100% | falsa alarma 100% | prob. granizo 5%
  ≥  3: detecta 100% | falsa alarma 100% | prob. granizo 5%
  ≥  5: detecta 100% | falsa alarma 100% | prob. granizo 5%
  ≥ 10: detecta 100% | falsa alarma 75% | prob. granizo 7%
  ≥ 20: detecta 75% | falsa alarma 75% | prob. granizo 5%
  ≥ 40: detecta 50% | falsa alarma 25% | prob. granizo 10%
  ≥ 80: detecta 50% | falsa alarma 25% | prob. granizo 10%
  ≥160: detecta 25% | falsa alarma 25% | prob. granizo 5%
  ≥320: detecta 0% | falsa alarma 0% | prob. granizo 0%

Salto brusco de rayos (radio 20 km, 60 min antes del granizo):
  activación ≥1 rayos/min: detecta 100% | falsa alarma 75% | prob. granizo 7% | anticipación mediana 36 min
  activación ≥2 rayos/min: detecta 100% | falsa alarma 75% | prob. granizo 7% | anticipación mediana 19 min
  activación ≥4 rayos/min: detecta 50% | falsa alarma 75% | prob. granizo 3% | anticipación mediana 27 min
  activación ≥8 rayos/min: detecta 50% | falsa alarma 25% | prob. granizo 10% | anticipación mediana 16 min

## Aeropuertos – todos: 8 granizadas vs 8 tormentas sin granizo (muestra)

- Radio 10 km: AUC rayos máx. en 10 min = 0.77; AUC rayos 30 min previos = 0.81; granizadas sin ningún rayo cerca: 0%
- Radio 20 km: AUC rayos máx. en 10 min = 0.70; AUC rayos 30 min previos = 0.75; granizadas sin ningún rayo cerca: 0%
- Radio 30 km: AUC rayos máx. en 10 min = 0.70; AUC rayos 30 min previos = 0.69; granizadas sin ningún rayo cerca: 0%

Umbrales (radio 20 km, máximo de rayos en 10 min) – detecta / falsa alarma / probabilidad real de granizo si avisa:
  ≥  1: detecta 100% | falsa alarma 100% | prob. granizo 2%
  ≥  3: detecta 100% | falsa alarma 62% | prob. granizo 3%
  ≥  5: detecta 100% | falsa alarma 62% | prob. granizo 3%
  ≥ 10: detecta 100% | falsa alarma 50% | prob. granizo 4%
  ≥ 20: detecta 88% | falsa alarma 50% | prob. granizo 3%
  ≥ 40: detecta 75% | falsa alarma 25% | prob. granizo 5%
  ≥ 80: detecta 62% | falsa alarma 25% | prob. granizo 5%
  ≥160: detecta 12% | falsa alarma 25% | prob. granizo 1%
  ≥320: detecta 0% | falsa alarma 0% | prob. granizo 0%

Salto brusco de rayos (radio 20 km, 60 min antes del granizo):
  activación ≥1 rayos/min: detecta 100% | falsa alarma 62% | prob. granizo 3% | anticipación mediana 43 min
  activación ≥2 rayos/min: detecta 100% | falsa alarma 50% | prob. granizo 4% | anticipación mediana 31 min
  activación ≥4 rayos/min: detecta 75% | falsa alarma 50% | prob. granizo 3% | anticipación mediana 32 min
  activación ≥8 rayos/min: detecta 62% | falsa alarma 25% | prob. granizo 5% | anticipación mediana 21 min

