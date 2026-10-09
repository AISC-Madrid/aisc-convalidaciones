# Esquema de la base de datos UC3M

La base de datos local se guarda en `data/processed/uc3m.sqlite`. El módulo
`src/scrapers/uc3m.py` crea el directorio y la tabla `subjects` si no existen.
Puede ejecutarse desde la raíz del repositorio con:

```bash
python -m src.scrapers.uc3m
```

La tabla contiene estas columnas, en este orden:

| Columna | Tipo SQLite | Uso |
|---|---|---|
| `código` | `TEXT` | Código de la asignatura |
| `nombre` | `TEXT` | Nombre de la asignatura |
| `plan` | `TEXT` | Código del plan de estudios |
| `curso_academico` | `TEXT` | Curso académico de la ficha |
| `tipo` | `TEXT` | Tipo normalizado de asignatura |
| `creditos` | `REAL` | Número de créditos |
| `curso` | `INTEGER` | Curso de la titulación |
| `cuatrimestre` | `TEXT` | Cuatrimestre |
| `objetivos` | `TEXT` | Objetivos de la asignatura; puede estar vacío |
| `programa` | `TEXT` | Programa o descripción de contenidos |
| `idioma` | `TEXT` | Idioma de la ficha (`ES` o `EN`) |
| `url` | `TEXT` | URL de la ficha |
| `fecha_actualizacion` | `TEXT` | Fecha de última actualización de la ficha |

La creación usa `IF NOT EXISTS`, por lo que ejecutar el módulo de nuevo no
borra ni reemplaza los datos existentes.
