# Buscador de Convalidaciones — Plan de trabajo del equipo

> Este documento dice **qué vamos a hacer, en qué orden y cómo nos organizamos**. Los detalles técnicos (endpoints, modelos, decisiones de diseño) están en `referencia_tecnica.md`; aquí se enlazan cuando hacen falta. Si algo de los dos documentos no cuadra, se corrige aquí primero.

## 1. Qué estamos construyendo

Un alumno de la UC3M que se va de **movilidad no europea (MNE)** tiene que proponerle a su tutor qué asignaturas de la universidad de destino convalidan las suyas. Hoy eso se hace a mano, leyendo guías docentes en otro idioma y en formatos distintos.

Vamos a construir un **buscador** que, dado un grado de la UC3M y una universidad de destino, devuelve las equivalencias más probables con una puntuación, marcando cuáles **ya se aprobaron en el pasado** (precedente) y cuáles **sugiere la IA**. El alumno marca las que le interesan y descarga una propuesta en PDF para su tutor, que es quien decide.

**MVP (lo que haremos en estos dos meses):** un solo grado de la UC3M y una sola universidad de destino, elegidos con datos en el Bloque A. Todo con **presupuesto 0 €**: software libre, planes gratuitos y nuestros portátiles.

**Queda fuera del MVP:** el resto de grados y universidades, combinaciones de varias asignaturas, el grafo entre universidades y el crowdsourcing de contratos. Están descritos como fases futuras en la referencia técnica (Sección 7).

## 2. Cómo funciona por dentro, en 5 pasos

Cada paso es un script que se ejecuta en nuestros portátiles. En la web publicada no hay modelo ni servidor: solo ficheros JSON ya calculados.

1. **Recoger datos.** Descargamos las fichas de las asignaturas de la UC3M (nombre, objetivos, programa, créditos), el catálogo de la universidad de destino y los Excel oficiales con las convalidaciones aprobadas en años anteriores. → `referencia_tecnica.md` §5, Paso 1.
2. **Enlazar.** Los Excel solo traen nombres y códigos, así que hay que casar cada fila con una asignatura real del catálogo del destino, y los códigos antiguos de la UC3M con los del plan vigente. Sin esto el histórico no sirve. → Paso 1 (enlace) y Paso 2 (reconciliación).
3. **Convertir temarios en vectores.** Un modelo de lenguaje multilingüe (gratis, se ejecuta en CPU) convierte cada temario en un *embedding*: una lista de números tal que dos asignaturas parecidas tienen vectores parecidos, aunque estén en idiomas distintos. → Paso 3.
4. **Calibrar y emparejar.** Miramos cuánto se parecen los pares que ya se aprobaron y fijamos el umbral a partir de ellos, no a ojo. Luego, para cada asignatura de la UC3M, buscamos las del destino más parecidas y las etiquetamos como precedente o sugerencia. → Paso 4.
5. **Publicar.** Exportamos un JSON por combinación grado × universidad, una web en Streamlit lo lee y genera el PDF. → Paso 5.

## 3. Cómo trabajamos

### Organización
- **Reunión semanal corta** (30 min): cada uno cuenta qué ha hecho y dónde se ha atascado, y coge **1 o 2 tareas** del tablero para la semana siguiente.
- Las tareas viven en **GitHub Issues** (tablero *Projects* con columnas Pendiente / En curso / En revisión / Hecho). Cada tarea tiene un **entregable** y un **"hecho cuando"**: si no se cumple, no está hecha.
- Cada tarea se hace en una **rama** y se entrega con una **Pull Request** que revisa **otra persona**. La revisión es también la forma de que todos conozcamos todas las partes.
- Las tareas **L** se hacen **en pareja**.
- Si algo se atasca más de dos días, se cuenta en el grupo: no hay que resolverlo solo.

### Herramientas de IA (las de la guía de IA gratis)

| Herramienta | Úsala para | Ojo |
|---|---|---|
| **Antigravity** (Claude Opus 4.6, Claude Sonnet 4.6, Gemini 3.1 Pro) | Planificar una tarea antes de escribir código (modo Plan), entender un trozo de código o un concepto, diseñar la estructura de un módulo | La cuota es **semanal**: resérvalo para pensar, no para cada línea |
| **OpenCode + Copilot Auto** | Programar en el día a día: escribir funciones, tests, arreglar errores | Copilot elige el modelo; no se puede fijar a mano |
| **OpenCode + modelos Free de Zen** | Boilerplate, tests repetitivos, docstrings, cuando se acaben los créditos de Copilot | Son modelos más flojos: revisa más lo que hacen |
| **Gemini (Google AI Plus)** | Estudiar: "explícame qué es la similitud coseno con un ejemplo", resumir documentación | Para aprender, no para programar en el repo |

### Reglas con la IA
1. El repo lleva un `AGENTS.md` con la descripción del proyecto y las convenciones. Así cualquier agente sabe dónde está.
2. **Pide siempre que te explique lo que ha hecho** y por qué. Si no lo entiendes, pregunta hasta entenderlo.
3. **No mergees lo que no entiendes.** Quien revisa la PR puede preguntar "¿qué hace esta línea?" y hay que saber contestarlo.
4. **Los tests son la forma de comprobar que el código generado funciona.** Toda tarea de código lleva al menos un test.
5. Trabaja en pasos pequeños: pide una función, pruébala, sigue. Si le pides "hazme el scraper entero" no vas a aprender nada y además saldrá mal.
6. Los Excel y las fichas de la UC3M son públicos: no hay problema en pasárselos a los modelos. No pegues datos personales de nadie.

### Convenciones
- Python 3.11, dependencias en `pyproject.toml`, formato y lint con `ruff`, tests con `pytest`.
- Ramas `tarea/<numero>-<nombre-corto>`. Un commit explica *por qué*, no *qué*.
- La caché de HTML descargado y los datos procesados **no se suben al repo** (`.gitignore`).

## 4. Calendario: 4 bloques de 2 semanas

No trabajamos a tiempo completo, así que el plan son **8 semanas** más una **semana 9 de buffer**. Cada bloque termina con un **hito** que se puede comprobar.

| Bloque | Semanas | Objetivo | Hito: sabemos que está si… |
|---|---|---|---|
| **A · Arrancar** | 1-2 | Repo listo, todos han ejecutado algo, histórico cargado, piloto elegido | Hay una tabla de pares históricos por grado × universidad y hemos **elegido el grado y la universidad piloto**; 5 fichas UC3M se parsean con tests que pasan |
| **B · Datos** | 3-4 | Catálogo UC3M del grado y catálogo del destino en SQLite; histórico enlazado y reconciliado | Sabemos **cuántos pares de calibración** tenemos; la web mock está desplegada en Streamlit Community Cloud |
| **C · Matching** | 5-6 | Embeddings, umbral calibrado, top-K real | Tenemos **Recall@5 y precisión estimada** medidos (aunque sean orientativos) y la web ya enseña resultados reales |
| **D · Producto** | 7-8 | JSON finales, web publicada, PDF, tests, demo | Un alumno **elige grado y universidad, ve los resultados y descarga el PDF**; 3-5 personas lo han probado |
| Buffer | 9 | Absorber retrasos | — |

Las tareas de la **web** empiezan en el Bloque A con datos inventados, para que quien no esté en la parte de datos tenga trabajo en paralelo y para que, cuando lleguen los datos reales, la web ya exista.

## 5. Backlog de tareas

Formato: **Tamaño** (S: una tarde · M: una semana a ratos · L: dos semanas o en pareja) · **Entregable** · **Hecho cuando** · **Qué aprendes** · **Pista para empezar**.

### Bloque A · Arrancar (semanas 1-2)

**A1. Setup personal** · S · *todos*
- Entregable: Python 3.11, Git, OpenCode con Copilot conectado y Antigravity instalados; el repo clonado y `pytest` ejecutado.
- Hecho cuando: has abierto una PR de prueba (añadir tu nombre al README) y te la han mergeado.
- Aprendes: flujo básico de Git y PR; a usar OpenCode.
- Pista: sigue la guía de IA gratis; pídele a OpenCode `/init` en el repo para ver cómo lo describe.

**A2. Crear el repositorio** · S
- Entregable: repo en la organización de AISC con `pyproject.toml`, `ruff`, `pytest`, `.gitignore` (excluye `data/raw` y `data/processed`), estructura de carpetas de `referencia_tecnica.md` §6 y un `AGENTS.md`.
- Hecho cuando: la CI de GitHub Actions pasa lint y tests en una PR.
- Aprendes: estructura de un proyecto Python; GitHub Actions.
- Pista: pídele a Antigravity que te explique qué hace cada archivo antes de crearlo.

**A3. Cargar los Excel históricos** · S
- Entregable: notebook `01_eda_historical.ipynb` que descarga los 3 XLS (enlaces en `referencia_tecnica.md` §3.2) y los carga con `pandas` + `xlrd`.
- Hecho cuando: imprime el número de filas por fichero y las columnas.
- Aprendes: pandas básico; formato Excel antiguo.
- Pista: `pd.read_excel(ruta, engine="xlrd")`.

**A4. EDA del histórico** · M
- Entregable: tabla ordenada de **pares por grado × universidad** (deduplicando cursos) y gráfico de las 10 universidades con más pares.
- Hecho cuando: la tabla está en el notebook y en un `.csv` en `data/processed`.
- Aprendes: `groupby`, limpiar texto (tildes, mayúsculas, espacios).
- Pista: normaliza los nombres antes de agrupar; si no, "Georgia Tech" y "GEORGIA TECH" cuentan aparte.

**A5. Revisar los catálogos candidatos** · M · *se reparte: una universidad por persona*
- Entregable: ficha de 5 líneas por cada una de las 5-6 universidades con más pares: URL del catálogo, ¿publica descripciones de las asignaturas?, ¿HTML normal o carga con JavaScript?, ¿créditos y su equivalencia a ECTS?, ¿idioma?
- Hecho cuando: hay una tabla comparativa en `docs/candidatas.md`.
- Aprendes: a mirar una web con las herramientas de desarrollador (F12) y a distinguir HTML estático de una SPA.
- Pista: si al desactivar JavaScript la página sigue mostrando las asignaturas, es estática.

**A6. Elegir el piloto** · S · *decisión en reunión*
- Entregable: grado y universidad piloto apuntados en el README, con el motivo.
- Hecho cuando: hay acuerdo en la reunión. Criterio: **muchos pares históricos y catálogo con descripciones accesibles**. Muchos pares sin catálogo no sirven.
- Aprendes: a decidir con datos.

**A7. Descargar 5 fichas UC3M como fixtures** · S
- Entregable: 5 fichas (ES y EN) guardadas en `tests/fixtures/uc3m/` con la URL de origen en un `README`.
- Hecho cuando: están las 10 ficheros HTML y se pueden abrir en el navegador.
- Aprendes: qué es una fixture; cómo se construye la URL `generaFicha` (`referencia_tecnica.md` §5, Paso 1).
- Pista: usa `requests.get(url).text` y guarda el texto.

**A8. Parser de una ficha UC3M** · M
- Entregable: `src/scrapers/uc3m.py` con una función `parse_ficha(html) -> Subject` que saca nombre, código, créditos, tipo, curso, cuatrimestre, Objetivos y Programa.
- Hecho cuando: los tests sobre las 5 fixtures pasan, incluida una ficha **sin** Objetivos.
- Aprendes: BeautifulSoup; a escribir tests con fixtures.
- Pista: las secciones se buscan por su título (ES/EN), no por posición. Tabla de dónde está cada dato en `referencia_tecnica.md` §5, Paso 1.

**A9. Modelos de datos** · S
- Entregable: `src/models/` con las clases Pydantic `Subject`, `HistoricalMatch` y `Match`.
- Hecho cuando: hay un test que crea cada una y falla si falta un campo obligatorio.
- Aprendes: Pydantic; a pensar qué campos necesita cada cosa.

**A10. Contrato JSON + web mínima** · M
- Entregable: esquema del JSON de resultados (`referencia_tecnica.md` §5, Paso 5) con un fichero de ejemplo inventado en `public/data/`, y una app Streamlit que lo lee y enseña una tabla.
- Hecho cuando: `streamlit run src/ui/app.py` muestra la tabla con los datos inventados.
- Aprendes: Streamlit; por qué un "contrato" permite que web y datos avancen en paralelo.
- Pista: empieza con `st.selectbox` para grado y universidad y `st.dataframe` para los resultados.

### Bloque B · Datos (semanas 3-4)

**B1. Enumerar las asignaturas de un plan** · S
- Entregable: función que, dado un plan, devuelve la lista de asignaturas usando `findPlanes.ajax` y `findAsignaturas.ajax`.
- Hecho cuando: para el grado piloto devuelve el mismo número de asignaturas que la web.
- Aprendes: llamar a endpoints POST con `requests` y leer JSON.

**B2. Scraper UC3M completo del grado piloto** · M
- Entregable: script que recorre todas las asignaturas del grado (ES y EN), con **caché en disco** y una pausa de 1,5 s entre peticiones, y guarda los `Subject` en SQLite.
- Hecho cuando: todas las asignaturas del grado están en la BD con Programa relleno; ejecutarlo dos veces no vuelve a descargar.
- Aprendes: SQLite con Python; por qué cachear y respetar a la web de destino.

**B3. Cargar el histórico en SQLite** · M
- Entregable: `src/loaders/historical_xls.py`: valida con Pydantic, normaliza textos y códigos, deduplica entre cursos y conserva las relaciones n:m con un `group_id`.
- Hecho cuando: tabla `historical_matches` cargada y un test con 10 filas inventadas (incluida una duplicada y una n:m).
- Aprendes: limpieza de datos real; qué es una relación n:m.

**B4. Scraper del destino piloto** · L · *en pareja*
- Entregable: `config/scrapers/<uni>.yaml` + `src/scrapers/destination.py`, que saca nombre, código, descripción y créditos (convertidos a ECTS) de cada asignatura y los guarda en SQLite.
- Hecho cuando: el catálogo está en la BD y una muestra de 10 asignaturas revisada a mano coincide con la web.
- Aprendes: scraping de una web que no controlamos; selectores CSS; Playwright si hace falta.
- Pista: primero `requests`; solo si la página carga con JavaScript, Playwright. Ejemplo de YAML en `referencia_tecnica.md` §5, Paso 1.

**B5. Enlazar el histórico con el catálogo del destino** · M
- Entregable: `src/loaders/link_catalog.py`: primero por código normalizado, después por nombre aproximado (`rapidfuzz` ≥ 90); lo que no enlaza se marca `unlinked`.
- Hecho cuando: la BD tiene `dest_subject_id` en las filas enlazadas y el notebook imprime la **tasa de enlace**.
- Aprendes: fuzzy matching; por qué hay que registrar lo que falla.

**B6. Reconciliar plan antiguo → plan vigente** · L · *en pareja*
- Entregable: `src/reconciliation/old_to_new.py` con la cascada de `referencia_tecnica.md` §5, Paso 2 (código → nombre → contenido → manual).
- Hecho cuando: tabla `old_code → new_code` con la columna `method`; los casos dudosos están listados para revisar.
- Aprendes: que los datos cambian con el tiempo; a diseñar un proceso en cascada.
- Pista: el paso por contenido necesita embeddings (C1); hasta entonces se deja la columna preparada y se cubren los dos primeros niveles.

**B7. Revisión manual de enlace y reconciliación** · S · *se reparte*
- Entregable: 20 pares de enlace y 20 de reconciliación revisados en una hoja, con acierto/fallo y comentario.
- Hecho cuando: la hoja está en `docs/` y los fallos tienen una issue abierta.
- Aprendes: a evaluar la calidad de un proceso automático.

**B8. Web completa contra datos inventados + despliegue** · M
- Entregable: filtros, selección con checkbox, resumen de ECTS seleccionados y despliegue en **Streamlit Community Cloud**.
- Hecho cuando: hay una URL pública que cualquiera puede abrir.
- Aprendes: desplegar una app gratis desde GitHub.

### Bloque C · Matching (semanas 5-6)

**C1. Encoder de embeddings** · M
- Entregable: `src/embeddings/encoder.py`: texto `"query: {nombre}. {Objetivos}. {Programa}"`, troceado en ~400 tokens, media de los trozos y normalización L2, con `multilingual-e5-small`.
- Hecho cuando: un test comprueba que dos textos iguales dan similitud 1 y que un texto largo no se trunca (se trocea).
- Aprendes: qué es un embedding y por qué se normaliza; `sentence-transformers`.
- Pista: pídele a Antigravity que te explique la similitud coseno con dos asignaturas de ejemplo antes de programar nada.

**C2. Embeber los dos catálogos e indexar** · S
- Entregable: embeddings de todas las asignaturas UC3M y destino guardados en `data/processed` + `src/embeddings/index.py` con búsqueda top-K por producto matricial `numpy`.
- Hecho cuando: para "Estructuras de Datos" el top-5 del destino tiene sentido a ojo.
- Aprendes: álgebra básica con numpy.

**C3. Terminar la reconciliación por contenido** · S
- Entregable: nivel 3 de la cascada de B6 usando el encoder, con umbrales iniciales 0,85 / 0,65.
- Hecho cuando: la columna `method` tiene valores `embedding` y los casos entre umbrales están en la lista de revisión.

**C4. Calibrar el umbral** · L · *en pareja*
- Entregable: notebook `04_calibration.ipynb`: pares enlazados y reconciliados → split 80/20 por asignatura UC3M → coseno de cada par → filtro de outliers (mediana − 3·MAD) → umbral = percentil 5-10.
- Hecho cuando: el umbral está documentado en el notebook con el número de pares usado y la lista de outliers descartados.
- Aprendes: por qué no se fija un umbral a ojo; percentiles y MAD; fuga de información en un split.
- Detalle en `referencia_tecnica.md` §5, Paso 4.

**C5. Evaluar** · M
- Entregable: `src/matching/evaluation.py` con Recall@1, Recall@5 y MRR sobre el hold-out.
- Hecho cuando: las métricas se imprimen con el tamaño de la muestra; si hay < 30 pares, se marcan como orientativas.
- Aprendes: métricas de ranking; que con pocos datos hay que ser prudente.

**C6. Comparar modelos** · M · *opcional si vamos bien de tiempo*
- Entregable: notebook `03_model_benchmark.ipynb` con `e5-small` frente a `paraphrase-multilingual-MiniLM-L12-v2` y, si el portátil aguanta, `e5-base`.
- Hecho cuando: hay una tabla con Recall@5 por modelo y se ha elegido uno.
- Pista: si va lento, Google Colab gratis.

**C7. Revisión manual de 50 sugerencias** · S · *se reparte*
- Entregable: hoja con 50 pares por encima del umbral marcados como razonable / dudoso / no.
- Hecho cuando: hay una **precisión estimada** y está en el notebook.
- Aprendes: que el histórico solo tiene positivos y por eso no se puede medir la precisión automáticamente.

**C8. Primer export real** · S
- Entregable: `src/export/build_static.py` genera el JSON del piloto con el top-K real (sin etiquetas todavía) y la web lo lee.
- Hecho cuando: la URL pública enseña resultados reales.

### Bloque D · Producto (semanas 7-8)

**D1. Matcher con etiquetas y aviso de ECTS** · M
- Entregable: `src/matching/matcher.py`: filtra por umbral, etiqueta `PRECEDENTE_APROBADO` (se muestra siempre) o `SUGERENCIA_IA`, y avisa si los ECTS difieren más del 25 %.
- Hecho cuando: tests con pares inventados cubren los tres casos.

**D2. Export definitivo** · S
- Entregable: `build_static.py` con el matcher real genera `public/data/<grado>__<uni>.json` e `index.json`.
- Hecho cuando: el JSON cumple el contrato de A10 (un test lo valida).

**D3. Web final** · M
- Entregable: selección → resultados con etiqueta, score y ECTS → resumen de créditos; redesplegada.
- Hecho cuando: el hito del Bloque D se cumple salvo el PDF.

**D4. Generador de PDF** · M
- Entregable: `src/ui/pdf.py` con `reportlab`: cabecera con grado y universidad, tabla de asignaturas seleccionadas y pie con la fecha.
- Hecho cuando: el botón "Generar PDF" descarga un PDF legible.
- Aprendes: generar documentos desde Python.

**D5. Tests y cobertura** · M · *se reparte por módulo*
- Entregable: `pytest --cov` ≥ 70 % y un `test_e2e.py` que recorre el pipeline con datos pequeños.
- Hecho cuando: la CI está en verde con la cobertura publicada.

**D6. Script de refresco** · S
- Entregable: `make refresh` (o script) que vuelve a scrapear, recalcula y regenera los JSON.
- Hecho cuando: se ejecuta de principio a fin sin pasos manuales.

**D7. Documentación** · S
- Entregable: README (cómo instalar, ejecutar y añadir una universidad) y `docs/architecture.md`.
- Hecho cuando: una persona nueva puede ejecutar el pipeline siguiendo el README.

**D8. Prueba con usuarios** · S
- Entregable: 3-5 alumnos prueban la web; sus comentarios en `docs/feedback.md`.
- Hecho cuando: hay una lista priorizada de mejoras para la Fase 2.

## 6. Glosario

- **Scraper**: programa que descarga páginas web y extrae datos de ellas.
- **Fixture**: fichero de ejemplo guardado para que los tests no dependan de internet.
- **Embedding**: representación de un texto como vector de números; textos parecidos quedan cerca.
- **Similitud coseno**: medida de parecido entre dos vectores (1 = iguales, 0 = sin relación).
- **Umbral**: valor mínimo de similitud para considerar que dos asignaturas son equivalentes. Se calibra con los pares ya aprobados.
- **Precedente**: par de asignaturas que ya se convalidó en el pasado (sale de los Excel oficiales).
- **Hold-out**: parte de los datos que se aparta para evaluar, sin usarla para calibrar.
- **Recall@5**: porcentaje de veces que la asignatura correcta aparece entre las 5 primeras propuestas.
- **MRR**: media de 1/posición de la respuesta correcta (1 si siempre sale la primera).
- **Outlier**: dato anormalmente alejado del resto; aquí, un par aprobado con similitud muy baja.
- **n:m**: una asignatura convalidada por varias, o varias por una.
- **PR (Pull Request)**: propuesta de cambios que otra persona revisa antes de incorporarla.
- **CI**: comprobaciones automáticas (lint, tests) que se ejecutan en cada PR.
- **SPA**: web que carga su contenido con JavaScript; hace falta un navegador real (Playwright) para scrapearla.
