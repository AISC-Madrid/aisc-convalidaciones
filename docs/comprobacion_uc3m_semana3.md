# UC3M: comprobación de la Semana 3

## Fuentes y cursos

Se verificaron los tres XLS oficiales enlazados en `referencia_tecnica.md`: sus hojas
son 2024-2025, 2025-2026 y 2026-2027 (4.991, 5.198 y 4.333 filas, respectivamente).
La issue #24 pide 2023-2024 a 2025-2026. Se conservan los cuatro cursos de la BD
compartida para cubrir ambos intervalos; el plan y los ejemplos se ajustan a los XLS.

La publicación `uc3m-2026-10-26-destino` ya contenía las fichas UC3M de los cuatro
cursos. No hubo que implementar de nuevo `--anio` ni `--solo-en`: ambas opciones
existían, junto con la caché y el respaldo ES cuando falta programa en EN.

## Datos conservados

- Base de partida: `uc3m-2026-10-26-destino`, con 2.414 filas en `dest_subjects`.
- Caché y fixtures: `uc3m-2026-10-12`. La publicación del destino solo incluye BD;
  no admite `--todo`. Hay que recuperar caché y fixtures desde la publicación anterior.
- Se incorporaron localmente las 523 filas de `old_to_new` de
  `uc3m-2026-10-27-reconciliacion`. Esta publicación solo tenía 682 filas de destino:
  sustituir la BD completa habría reducido el catálogo de Alejandra.
- El contenido completo de `dest_subjects` se comparó antes y después de la carga:
  se conservan sus 2.414 filas sin modificaciones. `PRAGMA integrity_check` devuelve `ok`.
- Las bases, copias de seguridad, caché y logs quedan en `data/`, fuera del código publicado.

## Cobertura observada

Una asignatura se cuenta una vez por código y curso. «ES de respaldo» indica que no
tiene programa EN y sí ES. «Sin programa» significa que la BD tiene ficha pero no
contenido de programa en ninguno de sus idiomas; no se inventa ni se rellena por año.

| Curso | Códigos con ficha | Con programa EN | Con programa solo ES | Sin programa |
|---|---:|---:|---:|---:|
| 2023/2024 | 2.194 | 2.020 | 15 | 159 |
| 2024/2025 | 2.280 | 2.099 | 16 | 165 |
| 2025/2026 | 2.477 | 2.276 | 12 | 189 |
| 2026/2027 | 2.737 | 2.408 | 12 | 317 |

Además hay códigos enumerados en `subject_plans` sin fila en `subjects`: 137 en
2023/2024, 111 en 2024/2025 y 8 en 2025/2026. En los 256 casos, la caché compartida
contiene la página explícita de «sin ficha» de UC3M tanto en EN como en ES. Se verificó
esa clasificación sobre los archivos, sin repetir las peticiones a la web.
La presencia de los cursos en la BD no implica que todas las asignaturas tengan temario.

## Ocho estados parciales revisados

Se relanzaron los ocho planes marcados como parciales, usando la caché: 20 peticiones
HTTP en total, con pausa de 1,5 segundos y sin volver a descargar las fichas válidas.

| Curso | Planes revisados | Fichas EN que devuelven cuerpo vacío |
|---|---|---|
| 2023/2024 | 435 | 18391 |
| 2024/2025 | 435, 504, 478 | 18391, 19614, 19133 |
| 2025/2026 | 573, 478 | 18391, 19133 |
| 2026/2027 | 573, 597 | 18391, 19133 |

Los ocho casos tienen ficha ES con programa en la BD: Globalización (18391),
Conflicto y Violencia (19614) y Marco laboral de la robótica (19133).
Se conserva el estado `parcial`: la respuesta EN vacía sigue siendo una incidencia,
aunque el respaldo ES cubre el contenido. Las respuestas inesperadas no se guardan
como fichas válidas en caché y podrán reintentarse.

## Validación

- Prueba real: tres fichas por cada curso 2024, 2025 y 2026, con programa EN.
  Una segunda ejecución reutilizó las nueve fichas de caché y no duplicó filas.
- Nuevas pruebas: coexistencia de cursos y conservación del destino; EN con programa
  evita pedir ES; una ficha EN válida sin programa activa el respaldo ES.
- 148 pruebas de datos, modelos y scrapers, con las fixtures reales recuperadas;
  12 pruebas de interfaz. Total: 160 correctas. `ruff check .` sin avisos.

## Reproducir la recuperación

Primero guardar una copia de cualquier BD local que se quiera conservar.

```bash
python -m src.sync.datos descargar --tag uc3m-2026-10-26-destino
python -m src.sync.datos descargar --tag uc3m-2026-10-12 --paquete cache fixtures
```

No usar `--forzar` sobre trabajo local sin copia: la descarga sustituye la BD completa,
no combina tablas. La incorporación de `old_to_new` descrita arriba es una combinación
local de tablas, no un comportamiento del comando de sincronización.

Para reintentar únicamente las incidencias UC3M:

```bash
python -m src.scrapers.uc3m --anio 2023 --plan 435 --solo-en
python -m src.scrapers.uc3m --anio 2024 --plan 435 504 478 --solo-en
python -m src.scrapers.uc3m --anio 2025 --plan 573 478 --solo-en
python -m src.scrapers.uc3m --anio 2026 --plan 573 597
```
