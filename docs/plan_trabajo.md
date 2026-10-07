# Buscador de Convalidaciones — Plan de trabajo del equipo

> Este documento dice **qué vamos a hacer, en qué orden y cómo nos organizamos**. Los detalles técnicos (endpoints, modelos, decisiones de diseño) están en `referencia_tecnica.md`; aquí se enlazan cuando hacen falta. Si algo de los dos documentos no cuadra, se corrige aquí primero.

## 1. Qué estamos construyendo

Un alumno de la UC3M que se va de **movilidad no europea (MNE)** tiene que proponerle a su tutor qué asignaturas de la universidad de destino convalidan las suyas. Hoy eso se hace a mano, leyendo guías docentes en otro idioma y en formatos distintos.

Vamos a construir un **buscador** que, dado un grado de la UC3M y una universidad de destino, devuelve las equivalencias más probables con una puntuación, marcando cuáles **ya se aprobaron en el pasado** (precedente) y cuáles **sugiere la IA**. El alumno marca las que le interesan y descarga una propuesta en PDF para su tutor, que es quien decide.

**MVP (lo que haremos en estos dos meses):** un solo grado de la UC3M y una sola universidad de destino, elegidos con datos en la Semana 1. Todo con **presupuesto 0 €**: software libre, planes gratuitos y nuestros portátiles.

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
- **Reunión semanal corta** (30 min, viernes): cada pareja enseña su entregable, cuenta dónde se ha atascado y confirma la tarea de la semana siguiente.
- Las tareas viven en **GitHub Issues** (tablero *Projects* con columnas Pendiente / En curso / En revisión / Hecho). Cada tarea tiene un **entregable** y un **"hecho cuando"**: si no se cumple, no está hecha.
- Cada tarea se hace en una **rama** y se entrega con una **Pull Request** que revisa **otra persona**. La revisión es también la forma de que todos conozcamos todas las partes.
- Se trabaja en **tres parejas fijas** (datos históricos, scraping y matching, web); cada pareja tiene **una tarea por semana** con su entregable.
- **Regla de independencia:** dentro de la semana, ningún grupo depende de lo que otro grupo haga esa misma semana. Lo que haga falta de otros está hecho la semana anterior.
- Si una semana una pareja no tiene tarea crítica, hace algo útil que no bloquea a nadie, o descansa. No hace falta que los seis estén siempre.
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

## 4. Calendario: una tarea por grupo y semana

No trabajamos a tiempo completo, así que el plan son **8 semanas** más una **semana 9 de buffer**. La unidad de trabajo es **un grupo, una semana, un entregable**. Hay tres parejas fijas, que así acumulan contexto:

- **P1 + P2 · Datos históricos:** los Excel de convalidaciones, de leerlos a calibrar con ellos.
- **P3 + P4 · Scraping y matching:** las fichas de la UC3M, el catálogo del destino y, con esos datos en la mano, los embeddings y el matcher.
- **P5 + P6 · Web:** bocetos, web, PDF y prueba con usuarios.

**Regla:** dentro de una semana, ningún grupo depende de lo que otro grupo haga esa misma semana. Lo que haga falta de otros ya está hecho la semana anterior. Si una semana un grupo no tiene tarea crítica, hace algo útil que no dependa de nadie (marcado en cursiva) o descansa: no hace falta que los seis estén siempre.

| Sem | P1 + P2 · Datos históricos | P3 + P4 · Scraping y matching | P5 + P6 · Web |
|---|---|---|---|
| **1** | **EDA** de los Excel + revisar las 6 candidatas | **SQLite + scraper UC3M** del plan vigente | **Pydantic + frontend**: modelos, JSON de ejemplo, bocetos, web mínima |
| | ◆ **Viernes: piloto elegido** | | |
| **2** | **Histórico → SQLite**: loader con dedup y n:m | **Scraper del destino** piloto + YAML + ECTS | **Web completa** según los bocetos + despliegue |
| **3** | **Reconciliación** de códigos viejos → vigentes | **Fichas antiguas** de la UC3M a la BD + destino terminado | **PDF** con `reportlab` sobre el JSON de ejemplo |
| | ◆ **Datos del piloto completos en SQLite** | | |
| **4** | **Enlace** histórico ↔ destino, tasa de enlace y revisión manual (los 4 juntos) | ↑ (con P1 + P2) | *Pulir la web: página "cómo funciona", estados vacíos, tests* |
| | ◆ **Sabemos cuántos pares de calibración hay** | | |
| **5** | *Preparar la calibración: notebook con split y filtro de outliers; revisión de 20 reconciliaciones* | **Embeddings**: encoder, embeber ambos catálogos, top-K | *README de usuario y guion de la prueba con usuarios* |
| **6** | **Calibración + evaluación**: umbral, Recall@5, 50 sugerencias a mano | **Matcher + export del JSON real** | *Tests end-to-end de la web con un JSON grande; preparar la demo* |
| | ◆ **JSON real disponible** | | |
| **7** | **Tests + README + script de refresco** (los 4 juntos) | ↑ (con P1 + P2) | **Integración**: web y PDF con el JSON real, redespliegue |
| **8** | **Prueba con 3-5 usuarios y arreglos** (todos) | | |
| **9** | Buffer | | |

## 5. Tareas por semana

Formato de cada tarea: **Entregable** · **Hecho cuando** · **Qué aprendes** · **Pista para empezar**. Todas son de una semana para una pareja.

### Antes de la reunión de arranque (coordinador)

**S0. Repositorio y tablero listos** · *hecho: repo, estructura, CI, README y AGENTS.md ya están; falta el tablero de issues*
- Entregable: repo en la organización de AISC con `pyproject.toml`, `ruff`, `pytest`, `.gitignore` (excluye `data/raw` y `data/processed`), la estructura de carpetas de `referencia_tecnica.md` §6 (carpetas vacías con un `.gitkeep`), un test trivial, CI de GitHub Actions (lint + pytest), un `README` con el enlace a este plan y un `AGENTS.md` que describa el proyecto en 10 líneas. Tablero de *Projects* con una issue por cada tarea de las Semanas 1 y 2, asignada a su pareja.
- Hecho cuando: la CI está en verde y los seis tienen permisos de escritura.

**S0 · Todos. Setup personal** (antes o durante la primera semana)
- Entregable: Python 3.11, Git, OpenCode con Copilot conectado y Antigravity instalados; el repo clonado y `pytest` ejecutado.
- Hecho cuando: has abierto una PR de prueba (añadir tu nombre al README) y te la han mergeado.
- Pista: sigue la guía de IA gratis; pídele a OpenCode `/init` en el repo para ver cómo lo describe.

### Semana 1 · Tres grupos, tres cimientos

**1A · P1 + P2. EDA de los Excel + candidatas**
- Entregable: notebook `01_eda_historical.ipynb` que descarga los 3 XLS (enlaces en `referencia_tecnica.md` §3.2), los carga con `pandas` + `xlrd` y responde a dos preguntas. **¿Dónde hay más datos?**: pares por **grado × universidad** deduplicando cursos, top 10 universidades, top 10 grados. **¿Qué nos va a dar problemas?**: filas repetidas entre cursos, relaciones **n:m** (una asignatura UC3M → varias del destino o al revés), filas sin código de destino, universidades escritas de varias formas. Después, para las **6 universidades con más pares**, una ficha de 5 líneas en `docs/candidatas.md`: URL del catálogo, ¿publica descripciones?, ¿HTML normal o JavaScript?, ¿créditos y equivalencia a ECTS?, ¿idioma?
- Hecho cuando: la tabla grado × universidad está en un `.csv` en `data/processed`, cada problema del dato tiene un ejemplo y un recuento, y `docs/candidatas.md` tiene las 6 fichas con una recomendación. Se presenta el viernes y se **elige el piloto** (criterio: muchos pares, datos limpios y catálogo con descripciones accesibles).
- Aprendes: pandas básico (`read_excel`, `groupby`, `value_counts`, `duplicated`); a desconfiar de los datos; a mirar una web con F12 y distinguir HTML estático de una SPA.
- Pista: `pd.read_excel(ruta, engine="xlrd")`. Normaliza nombres (tildes, mayúsculas, espacios) antes de agrupar. Repartíos: uno el EDA, otro las candidatas, y cambiad a mitad de semana para que los dos toquéis las dos cosas.

**1B · P3 + P4. SQLite + scraper UC3M del plan vigente**
- Entregable: (1) esquema de la BD `data/processed/uc3m.sqlite` con la tabla `subjects` (código, nombre, plan, curso académico, tipo, créditos, curso, cuatrimestre, objetivos, programa, idioma, url, fecha de actualización) documentado en `docs/esquema_bd.md`; (2) `src/scrapers/uc3m.py` con enumeración de planes y asignaturas (`findPlanes.ajax`, `findAsignaturas.ajax`), descarga de `generaFicha` en ES y EN con **caché en disco** y pausa de 1,5 s, `parse_ficha(html)` que saca todos los campos, y carga en la BD; (3) 5 fichas como fixtures en `tests/fixtures/uc3m/` (una sin Objetivos y una de Humanidades) con tests del parser.
- Hecho cuando: todas las asignaturas del curso actual están en la BD con Programa relleno, deduplicadas por código; los tests pasan; ejecutar el script dos veces no vuelve a descargar nada.
- Aprendes: `requests`, BeautifulSoup, SQLite, caché, por qué respetar a la web de destino.
- Pista: todo lo que hay que saber de la web está en `referencia_tecnica.md` §5, Paso 1. Uno hace la enumeración + descarga con caché y el otro el parser con las fixtures; se juntan el miércoles y lanzan la descarga completa (unas horas desatendidas; si se corta, se retoma).

**1C · P5 + P6. Pydantic + frontend**
- Entregable: (1) `src/models/` con las clases Pydantic `Subject`, `HistoricalMatch` y `Match` y un test por clase (a partir de la Semana 2 todos las usan); (2) `public/data/ejemplo.json` inventado con el esquema de `referencia_tecnica.md` §5, Paso 5 (5-6 resultados, con un precedente, una sugerencia y un aviso de ECTS), validado con `Match`; (3) bocetos en `docs/diseno/` de la **pantalla de resultados** y de la **propuesta en PDF** para el tutor (Figma, Excalidraw, HTML estático o papel); (4) `src/ui/app.py` en Streamlit que lee el JSON y enseña una tabla con desplegable de grado y universidad.
- Hecho cuando: los tests de los modelos pasan, el JSON está mergeado, los bocetos están en el repo con 5-10 decisiones de interfaz escritas, y `streamlit run src/ui/app.py` muestra la tabla con datos inventados. A partir de aquí **nadie cambia el esquema del JSON sin avisar al grupo**.
- Aprendes: Pydantic; Streamlit; a pensar primero qué ve el usuario; por qué un "contrato" permite que web y datos avancen en paralelo.
- Pista: uno hace modelos + JSON y el otro bocetos + web mínima; se cruzan el jueves para comprobar que el JSON contiene todo lo que aparece en los bocetos. Empieza con `st.selectbox` y `st.dataframe`.

### Semana 2 · Sobre los cimientos

**2A · P1 + P2. Histórico → SQLite**
- Entregable: `src/loaders/historical_xls.py`: lee los 3 XLS, valida cada fila con `HistoricalMatch` (1C), normaliza textos y códigos, deduplica entre cursos, agrupa las n:m con un `group_id` y guarda la tabla `historical_matches` en `data/processed/historico.sqlite`. Se limpia justo lo que encontrasteis en el EDA.
- Hecho cuando: la tabla está cargada con los 3 ficheros y hay un test con 10 filas inventadas que incluye una duplicada y una n:m.
- Aprendes: limpieza de datos real; SQLite desde Python.
- Pista: cargad un solo XLS sin limpiar y guardadlo; luego añadid normalización y deduplicación paso a paso, con un test por paso.

**2B · P3 + P4. Scraper del destino piloto**
- Entregable: `config/scrapers/<uni>.yaml` (URLs, selectores, `credits_to_ects`, rate limit) + `src/scrapers/destination.py`, que saca nombre, código, descripción y créditos (convertidos a ECTS) de cada asignatura y los guarda en la tabla `dest_subjects` de la BD. Factor de créditos confirmado con la web de la universidad o la ORI.
- Hecho cuando: una parte del catálogo (al menos el departamento o facultad del grado piloto) está en la BD y 10 asignaturas comprobadas a mano coinciden con la web.
- Aprendes: scraping de una web que no controlamos; selectores CSS; Playwright si hace falta.
- Pista: primero `requests`; solo si la página carga con JavaScript, Playwright. Ejemplo de YAML en `referencia_tecnica.md` §5, Paso 1. Usad la ficha de `docs/candidatas.md`.

**2C · P5 + P6. Web completa + despliegue**
- Entregable: la pantalla de resultados de los bocetos: filtros, tabla con score y etiqueta ✅/🤖, checkbox de selección, resumen de ECTS seleccionados, aviso de ECTS dispares; desplegada en **Streamlit Community Cloud** leyendo `ejemplo.json`.
- Hecho cuando: hay una URL pública que cualquiera puede abrir y hace lo que dice el boceto.
- Aprendes: Streamlit a fondo; desplegar una app gratis desde GitHub.

### Semana 3 · Cerrar los datos de la UC3M y del destino

**3A · P1 + P2. Reconciliación de códigos viejos → vigentes**
- Entregable: `src/reconciliation/old_to_new.py` con los niveles 1 y 2 de la cascada de `referencia_tecnica.md` §5, Paso 2 (mismo código en el plan vigente → mismo nombre normalizado); tabla `old_code → new_code` con la columna `method`; los casos sin resolver, listados en `docs/reconciliacion_pendiente.md` (el nivel 3, por contenido, llega en la Semana 6 con los embeddings).
- Hecho cuando: cada código UC3M del histórico tiene fila en la tabla, con `method` o marcado como pendiente; test con 5 casos inventados.
- Aprendes: que los datos cambian con el tiempo; a diseñar un proceso en cascada.
- Pista: usa la tabla `subjects` de 1B. Empieza contando cuántos códigos del histórico existen tal cual en el plan vigente.

**3B · P3 + P4. Fichas antiguas + destino terminado**
- Entregable: (1) el scraper de 1B con el parámetro `anio`: fichas de los cursos **2025-26, 2024-25 y 2023-24** (los del Excel) en la tabla `subjects` con su curso académico, solo en EN (ES si la EN viene vacía), con caché; (2) el scraper del destino completo: todo el catálogo relevante en `dest_subjects`.
- Hecho cuando: los tres cursos anteriores están en la BD; el catálogo del destino está completo y 10 asignaturas más comprobadas a mano coinciden.
- Aprendes: a extender tu propio código; a dejar correr descargas largas con caché.
- Pista: uno extiende el scraper UC3M con `anio` y el otro termina el destino. Lanzad las descargas el lunes.

**3C · P5 + P6. Generador de PDF**
- Entregable: `src/ui/pdf.py` con `reportlab`, siguiendo el boceto: cabecera con alumno, grado y universidad; tabla de asignaturas seleccionadas con ECTS de cada lado y etiqueta; nota de que es orientativo; fecha. Botón "Generar PDF" en la web que lo descarga.
- Hecho cuando: desde la web pública, seleccionar asignaturas y pulsar el botón descarga un PDF legible.
- Aprendes: generar documentos desde Python.

### Semana 4 · Juntar el histórico con el destino

**4AB · P1 + P2 + P3 + P4. Enlace histórico ↔ destino y revisión manual**
- Entregable: `src/loaders/link_catalog.py`: para cada fila del histórico del piloto, buscar su asignatura en `dest_subjects` por código normalizado (`CS 1332` = `CS1332`) y, si falla, por nombre aproximado (`rapidfuzz` ≥ 90); lo que no enlaza se marca `unlinked`. Notebook que imprime la **tasa de enlace**. Revisión manual: 20 enlaces y 20 reconciliaciones en una hoja de `docs/` con acierto/fallo.
- Hecho cuando: `dest_subject_id` relleno en las filas enlazadas, tasa de enlace conocida y hoja de revisión con los fallos convertidos en issues. **Viernes:** si la tasa es menor del 50 %, se decide si mejorar el enlace o seguir con los pares que hay (métricas marcadas como orientativas).
- Aprendes: fuzzy matching; a evaluar la calidad de un proceso automático.
- Pista: P1 + P2 programan el enlace (conocen el histórico); P3 + P4 hacen la revisión manual (conocen el catálogo) y ajustan la normalización de códigos del destino si hace falta.

**4C · P5 + P6. Pulir la web** *(no bloquea a nadie)*
- Entregable: página o pestaña "Cómo funciona" (qué es un precedente, qué es una sugerencia, qué significa el score, en lenguaje llano); estados vacíos y de error (sin selección, JSON que no existe); tests de la web con `pytest` sobre las funciones de carga y filtrado.
- Hecho cuando: la URL pública tiene la ayuda, no se rompe sin datos y los tests pasan en la CI.

### Semana 5 · Embeddings

**5B · P3 + P4. Encoder, embeddings y top-K**
- Entregable: `src/embeddings/encoder.py`: texto `"query: {nombre}. {Objetivos}. {Programa}"`, troceado en ~400 tokens, media de los trozos y normalización L2, con `multilingual-e5-small`; embeddings de todas las asignaturas UC3M del piloto y del destino guardados en `data/processed`; `src/embeddings/index.py` con búsqueda top-K por producto matricial `numpy`.
- Hecho cuando: un test comprueba que dos textos iguales dan similitud 1 y que un texto largo se trocea; para "Estructuras de Datos" el top-5 del destino tiene sentido a ojo.
- Aprendes: qué es un embedding y por qué se normaliza; `sentence-transformers`; álgebra básica con numpy.
- Pista: pídele a Antigravity que te explique la similitud coseno con dos asignaturas de ejemplo antes de programar. Detalle en `referencia_tecnica.md` §5, Paso 3. Si el portátil va lento, Google Colab gratis.

**5A · P1 + P2. Preparar la calibración** *(no bloquea a nadie)*
- Entregable: notebook `04_calibration.ipynb` con la parte que no necesita cosenos: lista de pares enlazados y reconciliados del piloto, **split 80/20 por asignatura UC3M** (no por fila), función del filtro de outliers (mediana − 3·MAD) y del percentil, probadas con números inventados; revisión manual de 20 reconciliaciones más.
- Hecho cuando: el notebook corre de arriba abajo con cosenos inventados y produce un umbral; el número de pares de train y de hold-out está anotado.
- Aprendes: por qué no se fija un umbral a ojo; fuga de información en un split; percentiles y MAD (`referencia_tecnica.md` §5, Paso 4).

**5C · P5 + P6. README de usuario y guion de la prueba** *(no bloquea a nadie)*
- Entregable: `README` de usuario (qué hace la web, cómo leer los resultados, qué hacer con el PDF) y `docs/prueba_usuarios.md` con 4-5 tareas que haremos hacer a los alumnos en la Semana 8 y un cuestionario corto.
- Hecho cuando: una persona ajena entiende para qué sirve la web leyendo el README.

### Semana 6 · Calibrar y producir el JSON real

**6A · P1 + P2. Calibración y evaluación**
- Entregable: el notebook de 5A con los cosenos reales (de 5B): umbral calibrado, lista de outliers descartados, `src/matching/evaluation.py` con Recall@1, Recall@5 y MRR sobre el hold-out, y hoja con **50 sugerencias por encima del umbral revisadas a mano** (razonable / dudoso / no) → precisión estimada. Con P3 + P4, el nivel 3 de la reconciliación (por contenido) para los códigos pendientes de 3A.
- Hecho cuando: umbral, Recall@5, MRR y precisión estimada están documentados con el tamaño de la muestra (orientativos si hay < 30 pares en el hold-out).
- Aprendes: métricas de ranking; que el histórico solo tiene positivos y por eso no se puede medir la precisión automáticamente.

**6B · P3 + P4. Matcher y export del JSON real**
- Entregable: `src/matching/matcher.py` (top-10 por coseno, filtro por el umbral de 6A, etiqueta `PRECEDENTE_APROBADO` que se muestra siempre / `SUGERENCIA_IA`, aviso si los ECTS difieren más del 25 %) y `src/export/build_static.py` que genera `public/data/<grado>__<uni>.json` e `index.json` con el esquema de 1C.
- Hecho cuando: tests con pares inventados cubren los tres casos; el JSON real valida con `Match` y está en `public/data/`.
- Aprendes: a cerrar un pipeline de principio a fin.
- Pista: el umbral de 6A llega a mitad de semana; hasta entonces, trabajad con uno provisional (0,7) y dejadlo parametrizado.

**6C · P5 + P6. Tests end-to-end y demo** *(no bloquea a nadie)*
- Entregable: un JSON inventado grande (200 resultados) para probar rendimiento y paginación; test end-to-end de la web; guion de la demo de 5 minutos.
- Hecho cuando: la web responde bien con el JSON grande y el guion está en `docs/`.

### Semana 7 · Integración y cierre técnico

**7C · P5 + P6. Integración con el JSON real**
- Entregable: la web y el PDF leyendo `public/data/<grado>__<uni>.json` e `index.json` reales; ajustes que pida el dato real (nombres largos, scores, avisos); redespliegue.
- Hecho cuando: en la URL pública, un alumno elige el grado y la universidad piloto, ve los resultados reales y descarga el PDF.

**7AB · P1 + P2 + P3 + P4. Tests, documentación y refresco**
- Entregable: `pytest --cov` ≥ 70 % con un `test_e2e.py` que recorre el pipeline con datos pequeños; `README` técnico (cómo instalar, ejecutar y añadir una universidad) y `docs/architecture.md`; script `make refresh` que vuelve a scrapear, recalcula y regenera los JSON sin pasos manuales.
- Hecho cuando: la CI está en verde con la cobertura publicada; una persona nueva puede ejecutar el pipeline siguiendo el README; `make refresh` corre de principio a fin.

### Semana 8 · Prueba con usuarios

**8 · Todos. Prueba con 3-5 alumnos y arreglos**
- Entregable: sesiones con 3-5 alumnos siguiendo el guion de 5C; comentarios en `docs/feedback.md`; arreglos de lo que bloquee el uso; lista priorizada de mejoras para la Fase 2.
- Hecho cuando: el hito del MVP se cumple con usuarios reales: eligen grado y universidad, ven resultados y descargan el PDF sin ayuda.

### Semana 9 · Buffer

Absorbe retrasos. Si no hace falta, se dedica a la lista de mejoras de la Semana 8.

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
