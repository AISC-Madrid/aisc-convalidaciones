# AGENTS.md

## Estructura
- `assets/`: recursos comunes (`aisc_logo.png`, `report.pdf` = referencia del estilo AISC).
- `convalidaciones/`: proyecto Buscador de Convalidaciones (fuentes HTML/MD) y `pdf/` con los PDF generados.
- `guia_ia_gratis/`: guía de IA gratis para estudiantes (fuente HTML) y `pdf/` con el PDF generado.
- `build_pdf.py` (raíz): genera todos los PDF.

## Proyecto convalidaciones
- `convalidaciones/plan_trabajo.md`: **fuente de verdad del calendario, las tareas y la forma de trabajar**. Para un equipo de 6 personas junior a tiempo parcial: ~8 semanas en 4 bloques de 2 + buffer, tareas sueltas (issues) con tamaño / entregable / "hecho cuando" / qué aprendes / pista. Lenguaje llano, sin justificaciones históricas. Incluye qué herramienta de IA usar para qué (las de `guia_ia_gratis`).
- `convalidaciones/referencia_tecnica.md`: **fuente de verdad técnica** (fuentes de datos, pipeline, decisiones, fases post-MVP, costes, riesgos). Sin historial de versiones ni comparativas "respecto a vX".
- `convalidaciones/report_final_template.html`: propuesta en formato AISC (estilo de `assets/report.pdf`). `convalidaciones/slides_template.html`: presentación 16:9 centrada en la Fase 1 / MVP (12 slides: alcance, pipeline, un slide por paso, timeline de 4 bloques, cómo trabajamos, riesgos, cierre). Ambos deben ser coherentes con `plan_trabajo.md` y `referencia_tecnica.md`.
- Fichas UC3M: `GET https://aplicaciones.uc3m.es/cpa/generaFicha?est=&plan=&asig=&anio=&idioma=1|2` (HTML estático). Enumeración: POST `/cpa/findPlanes.ajax`, `/cpa/findAsignaturas.ajax` (`codPlan`, `ano`), `/cpa/findAnos.ajax` (JSON). Detalle en `referencia_tecnica.md`, §5 Paso 1.

## Guía IA gratis
- `guia_ia_gratis/guia_ia_gratis_estudiantes.html`: guía independiente (mismo estilo AISC) sobre modelos de IA gratis para estudiantes (OpenCode + Copilot Student + Zen, Google AI Plus, Antigravity como extra y trucos de OpenCode al final). Formato escueto: por herramienta solo "qué es", "modelos que ofrece" y pasos de instalación; sin historia, fuentes ni "otras ofertas".

## PDF
- Regenerar: `python build_pdf.py` (todos) o `python build_pdf.py report|slides|guia` (inyecta `assets/aisc_logo.png` en `__LOGO_B64__` e imprime con Edge/Chrome headless; necesita Chromium ≥ 131 para las cajas de margen `@page`). Los PDF se escriben en la carpeta `pdf/` de cada proyecto.
- Verificar maquetación: `pdftoppm -r 50 -png "<pdf>" out/p` (MiKTeX) y revisar que no haya páginas casi vacías.
