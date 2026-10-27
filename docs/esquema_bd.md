# Base de datos UC3M y scraper de fichas

La base de datos local se guarda en `data/processed/uc3m.sqlite` y la caché de fichas HTML en
`data/raw/uc3m/<año>/<asignatura>_<ES|EN>.html`. Ninguna de las dos se sube al repo.

## Compartir los datos en el equipo

La BD, la caché HTML y las fichas reales de los tests contienen temarios, así que no pueden ir a
este repo (público). Se comparten como *assets* de los Releases del repo **privado**
[`AISC-Madrid/aisc-convalidaciones-data`](https://github.com/AISC-Madrid/aisc-convalidaciones-data),
que ven todos los miembros de la organización. No hace falta volver a scrapear.

Requisito: [`gh`](https://cli.github.com/) instalado y `gh auth login` hecho. Desde la raíz:

```bash
python -m src.sync.datos descargar            # solo data/processed/uc3m.sqlite (~9 MB)
python -m src.sync.datos descargar --todo     # + caché HTML (~53 MB) + fichas de los tests
python -m src.sync.datos descargar --tag uc3m-2026-10-12 --forzar   # versión concreta, pisa la BD
python -m src.sync.datos publicar uc3m-AAAA-MM-DD   # tras un scraping nuevo: sube un release
```

- Por defecto baja el último release y comprueba el SHA-256 de cada zip con `manifest.json`.
- No sustituye una `uc3m.sqlite` local salvo con `--forzar`.
- `publicar` copia la BD con `VACUUM INTO` (se puede publicar aunque esté abierta) y deja en las
  notas del release el número de fichas por curso y el estado de las descargas.
- Paquetes sueltos: `--paquete bd cache fixtures`.

## Cómo se ejecuta

Desde la raíz del repositorio:

```bash
python -m src.scrapers.uc3m --anio 2026 --plan 456      # un grado (prueba, ~7 min)
python -m src.scrapers.uc3m --anio 2026                 # todos los grados activos (horas)
python -m src.scrapers.uc3m --anio 2025 2024 2023 --solo-en   # cursos del Excel histórico
```

Opciones: `--plan` (uno o varios planes), `--limite N` (máximo de asignaturas, para pruebas),
`--solo-en` (solo la ficha en inglés; pide la española si la inglesa no tiene programa),
`--pausa S` (segundos entre peticiones, por defecto 1,5), `--db RUTA`.

- **Reanudable:** si se corta, se vuelve a lanzar el mismo comando. Las fichas que ya están en la
  caché no se descargan otra vez (el log muestra el número de peticiones reales).
- **Volumen:** 152 grados activos; cada asignatura se descarga una vez por idioma aunque esté en
  varios grados. Con 1,5 s por petición, el curso actual completo son varias horas.
- **Cada ficha, con su plan:** se pide con el plan y el estudio donde aparece la asignatura ese
  curso. Con otro plan la web devuelve una página vacía, que cuenta como `sin_ficha`.
- **Qué se guarda en caché:** solo las fichas y la página de "Error al generar la ficha" con la que
  la UC3M responde (HTTP 200, ~2,8 KB) cuando no hay ficha para ese plan, año e idioma; esta
  cuenta como `sin_ficha`. Cualquier otra respuesta (vacía, cortada, de mantenimiento…) cuenta como
  error, no se guarda y se vuelve a pedir al relanzar. Si la caché tiene una respuesta así de una
  versión anterior, también se vuelve a pedir.
- **Cortesía:** pausa antes de cada petición, reintentos con espera creciente y, si la web
  responde 429, se duplica la pausa automáticamente.

## Módulos

| Módulo | Qué hace |
|---|---|
| `src/scrapers/uc3m_client.py` | Endpoints `findPlanes`, `findAsignaturas` (por año) y descarga de `generaFicha` con caché |
| `src/scrapers/uc3m_parser.py` | `parse_ficha(html)`: saca los campos de una ficha (ES o EN) |
| `src/scrapers/uc3m.py` | Esquema de la BD, `cargar_curso()` y la línea de comandos |

## Tablas

### `subjects` — una fila por asignatura, curso académico e idioma

`UNIQUE (codigo, curso_academico, idioma)`: volver a cargar reemplaza la fila, no la duplica.

| Columna | Tipo | Uso |
|---|---|---|
| `codigo` | `TEXT` | Código de la asignatura |
| `nombre` | `TEXT` | Nombre de la asignatura |
| `plan` | `TEXT` | Plan de estudios desde el que se descargó la ficha |
| `estudio` | `TEXT` | Código de estudio (`est` de la URL) |
| `curso_academico` | `TEXT` | Curso de la ficha, p. ej. `2026/2027` |
| `tipo` | `TEXT` | `FB`, `OB`, `OP`, `HUM` (o el texto original si es otro) |
| `creditos` | `REAL` | Créditos ECTS |
| `curso` | `INTEGER` | Curso de la titulación (puede ser nulo) |
| `cuatrimestre` | `INTEGER` | Cuatrimestre (nulo si no es numérico) |
| `coordinador` | `TEXT` | Coordinador/a |
| `departamento` | `TEXT` | Departamento |
| `rama` | `TEXT` | Rama de conocimiento (solo aparece en algunos grados) |
| `objetivos` | `TEXT` | Objetivos; puede estar vacío |
| `programa` | `TEXT` | Descripción de contenidos: programa |
| `idioma` | `TEXT` | `ES` o `EN` |
| `url` | `TEXT` | URL de la ficha |
| `fecha_actualizacion` | `TEXT` | "Última actualización" de la ficha |
| `hash_texto` | `TEXT` | SHA-256 de objetivos + programa, para detectar cambios |

### `subject_plans` — en qué grados está cada asignatura

Clave `(codigo, plan, curso_academico)`, más `estudio`.

### `descargas` — qué se ha terminado de cargar

Clave `(curso_academico, plan, idioma)`, más `estado` y `fecha`. Sirve para saber qué cursos y
grados están completos. `estado` es uno de:

- `completo`: todas las asignaturas del grado procesadas sin errores. Que la UC3M no publique
  ficha de una asignatura (página vacía) no cuenta como error.
- `parcial`: errores sueltos o asignaturas sin procesar (por ejemplo, con `--limite`).
- `fallido`: hay errores y ninguna asignatura del grado ha dado ficha.

Si un grado no queda `completo`, se vuelve a lanzar el mismo comando: la caché evita repetir lo
que ya se descargó y el estado se actualiza.

### `dest_subjects` — una fila por asignatura de la universidad de destino

`UNIQUE (universidad, codigo)`: volver a cargar actualiza la fila (nombre, descripción y ECTS) sin
duplicarla y **sin cambiar su `id`**, para no romper las referencias desde el histórico
(`historical_matches.dest_subject_id`, semana 4).

| Columna | Tipo | Uso |
|---|---|---|
| `id` | `INTEGER` | Identificador de la fila; no cambia al recargar |
| `universidad` | `TEXT` | Código de la universidad (`university_code` del YAML), p. ej. `GATECH` |
| `codigo` | `TEXT` | Código de la asignatura tal como aparece en el catálogo, p. ej. `BMED 2110` |
| `codigo_norm` | `TEXT` | Código sin espacios y en mayúsculas (`BMED2110`), igual que `destino_codigo` del histórico; con índice para el enlace de la semana 4 |
| `nombre` | `TEXT` | Nombre de la asignatura |
| `descripcion` | `TEXT` | Descripción del catálogo |
| `ects` | `REAL` | Créditos convertidos a ECTS con `credits_to_ects` del YAML; nulo si los créditos son variables (p. ej. `1-12`) |

Se carga con `python -m src.scrapers.destination --uni gatech` y vive en `data/processed/uc3m.sqlite`,
junto a `subjects`. Si la tabla se creó sin `codigo_norm`, el scraper añade la columna y la rellena
al volver a ejecutarse (la caché evita descargar de nuevo). Antes de descargar nada comprueba el
`robots.txt` de la universidad. Comprobación manual y factor de créditos de Georgia Tech:
`docs/comprobacion_gatech.md`.

### `old_to_new` — código antiguo del histórico → código del plan vigente

Una fila por `uc3m_codigo` distinto del histórico, no por fila del Excel. La escribe
`python -m src.reconciliation.old_to_new` en esta misma base. Volver a ejecutarla sustituye
solo las filas de esta tabla: no borra `subjects` ni el resto.

| Columna | Tipo | Uso |
|---|---|---|
| `old_code` | `TEXT` | Código UC3M del histórico. Clave primaria |
| `new_code` | `TEXT` | Código en `subjects` del curso `2026/2027`. NULL si no se resolvió |
| `method` | `TEXT` | `code`, `exact`, `embedding` o `manual`. NULL si sigue pendiente |

`code`: el código antiguo sigue en el plan vigente, aunque el nombre haya cambiado. `exact`: no está
el código, pero el nombre normalizado coincide con un único código vigente en español. Los casos
NULL están listados en `docs/reconciliacion_pendiente.md`. `embedding` y `manual` quedan para la
semana 6.

## Migración desde el esquema anterior

Si `data/processed/uc3m.sqlite` se creó con el esquema de la PR #14 (columna `código` con tilde) o
le faltan columnas, al ejecutar el scraper la tabla `subjects` se migra sola: la vieja se renombra a
`subjects_antigua_<fecha>` (no se borra) y sus filas se copian a la nueva, salvo las que no tienen
código, curso o idioma. Si se prefiere empezar de cero, basta con borrar el `.sqlite`: la caché
HTML de `data/raw/uc3m/` se reutiliza y la recarga no vuelve a descargar nada.

## Consultas útiles

```sql
SELECT curso_academico, idioma, COUNT(*) FROM subjects GROUP BY 1, 2;
SELECT COUNT(*) FROM subjects WHERE programa IS NULL;
SELECT s.nombre FROM subjects s JOIN subject_plans p USING (codigo, curso_academico)
WHERE p.plan = '456' AND s.idioma = 'ES';
SELECT universidad, COUNT(*), SUM(ects IS NULL) AS sin_ects FROM dest_subjects GROUP BY 1; -- asignaturas por universidad y cuántas sin ECTS
SELECT * FROM dest_subjects WHERE universidad = 'GATECH' AND codigo_norm = 'BMED2110';
SELECT method, COUNT(*) FROM old_to_new GROUP BY 1; -- code, exact o NULL (pendiente)
```
