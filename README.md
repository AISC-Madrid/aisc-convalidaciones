# Buscador de Convalidaciones · AISC Madrid

Buscador de equivalencias de asignaturas para alumnos de la UC3M que se van de **movilidad no europea (MNE)**. Dado un grado y una universidad de destino, propone las asignaturas que probablemente convalidan, marca cuáles ya se aprobaron antes y cuáles sugiere la IA, y genera una propuesta en PDF para el tutor. Presupuesto: 0 €.

## Qué leer, en este orden

1. **[`docs/plan_trabajo.md`](docs/plan_trabajo.md)** — qué construimos, cómo trabajamos y qué hace cada pareja cada semana. **Empieza por aquí.**
2. **[`docs/Presentacion - Plan de trabajo.pdf`](docs/Presentacion%20-%20Plan%20de%20trabajo.pdf)** — lo mismo en 12 slides, para la reunión de arranque.
3. **[`docs/Guia - IA gratis para estudiantes.pdf`](docs/Guia%20-%20IA%20gratis%20para%20estudiantes.pdf)** — cómo instalar y usar OpenCode, Copilot Student, Antigravity y Google AI Plus, que son las herramientas con las que programamos.
4. **[`docs/referencia_tecnica.md`](docs/referencia_tecnica.md)** — para consultar cuando te toque una tarea: endpoints de la UC3M, esquema del JSON, decisiones técnicas.

## Equipo

Tres parejas fijas, una tarea por semana. Fran coordina además del trabajo de su pareja.

| Pareja | Quiénes | Qué lleva |
|---|---|---|
| **Datos históricos** | **Alejandra** (3º Datos) · **Ángela** (2º Datos y Teleco) | Los Excel de convalidaciones: EDA, carga, reconciliación, enlace, calibración |
| **Scraping y matching** | **Fran** (5º Teleco y Datos) · **Mercedes** (2º Datos y Teleco) | Fichas de la UC3M, catálogo del destino, embeddings, matcher, export |
| **Web** | **Héctor** (4º Informática) · **Víctor** (2º Sonido e Imagen) | Bocetos, Streamlit, PDF, prueba con usuarios |

**Piloto (grado + universidad):** se elige el viernes de la Semana 1 → _pendiente_.

## Empezar (Semana 1, todos)

```bash
git clone https://github.com/franjifer/aisc-convalidaciones.git
cd aisc-convalidaciones
python -m venv .venv
# Windows: .venv\Scripts\activate · macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest          # tiene que salir en verde
ruff check .    # tiene que salir sin avisos
```

Después abre una rama, añade tu usuario de GitHub junto a tu nombre en la tabla de arriba y abre una **Pull Request**. Cuando te la mergeen, tu setup está hecho.

Instala también OpenCode con Copilot Student y Antigravity siguiendo la guía de `docs/`.

## Estructura del repo

```
docs/            plan de trabajo, referencia técnica, presentación, guía de IA
src/
  models/        clases Pydantic (Subject, HistoricalMatch, Match)
  scrapers/      uc3m.py, destination.py
  loaders/       historical_xls.py, link_catalog.py
  reconciliation/ old_to_new.py
  embeddings/    encoder.py, index.py
  matching/      calibration.py, evaluation.py, matcher.py
  export/        build_static.py  →  public/data/*.json
  ui/            app.py (Streamlit), pdf.py (reportlab)
config/scrapers/ un YAML por universidad de destino
public/data/     JSON publicados (lo único que usa la web)
data/            Excel, caché HTML y bases de datos: solo en local, no se sube
tests/           pytest; fixtures en tests/fixtures/
notebooks/       EDA, reconciliación, benchmark, calibración
```

## Reglas cortas

- Una tarea = una rama = una Pull Request con la CI en verde, que revisa Fran o la pareja que toque.
- Toda tarea de código lleva tests. **No se mergea lo que no se entiende.**
- Dentro de la semana nadie depende de otro grupo: lo que haga falta de otros está hecho la semana anterior.
- Si te atascas más de dos días, cuéntalo en el grupo.
