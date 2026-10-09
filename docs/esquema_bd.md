# Base de datos UC3M y scraper de fichas

La base de datos local se guarda en `data/processed/uc3m.sqlite` y la caché de fichas HTML en
`data/raw/uc3m/<año>/<asignatura>_<ES|EN>.html`. Ninguna de las dos se sube al repo.

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
grados están completos.

## Consultas útiles

```sql
SELECT curso_academico, idioma, COUNT(*) FROM subjects GROUP BY 1, 2;
SELECT COUNT(*) FROM subjects WHERE programa IS NULL;
SELECT s.nombre FROM subjects s JOIN subject_plans p USING (codigo, curso_academico)
WHERE p.plan = '456' AND s.idioma = 'ES';
```
