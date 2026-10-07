# AGENTS.md

Contexto para los asistentes de IA (OpenCode, Antigravity…) que trabajen en este repo.

- **Qué es:** buscador de convalidaciones para alumnos de la UC3M en movilidad no europea. Dado un grado y una universidad de destino, propone equivalencias entre asignaturas con un score, etiquetadas como `PRECEDENTE_APROBADO` (ya se convalidó antes) o `SUGERENCIA_IA`, y exporta una propuesta en PDF para el tutor.
- **Cómo funciona:** pipeline offline en 5 pasos (scraping UC3M y destino + Excel histórico → reconciliación de códigos → embeddings con `multilingual-e5-small` → calibración del umbral con los pares aprobados + matching → export de JSON estáticos). En producción solo hay JSON y una web en Streamlit; no hay modelo ni servidor.
- **Documentos:** `docs/plan_trabajo.md` (qué hace cada pareja cada semana) y `docs/referencia_tecnica.md` (fuentes de datos, endpoints de la UC3M, esquema del JSON, decisiones). Léelos antes de proponer cambios de diseño.
- **Estructura:** `src/` por paso del pipeline (`scrapers`, `loaders`, `reconciliation`, `embeddings`, `matching`, `export`, `ui`), `src/models/` con las clases Pydantic, `tests/` con fixtures en `tests/fixtures/`, `public/data/` con los JSON publicados, `data/` solo local.
- **Convenciones:** Python 3.11, `ruff` (línea 100), `pytest`. Toda tarea de código lleva tests. Las fichas HTML descargadas y las bases de datos van a `data/` y no se suben al repo.
- **Scraping:** caché en disco siempre, pausa de 1,5 s entre peticiones, respeto a `robots.txt`. No publicar los temarios scrapeados: en el repo y los JSON solo nombres, códigos, créditos, scores y enlaces.
- **Presupuesto 0 €:** sin APIs de pago ni servicios con tarjeta. Si una solución necesita pagar, no es la solución.
- **Comandos:** `pip install -e ".[dev]"` · `pytest` · `ruff check .` · `streamlit run src/ui/app.py`.
