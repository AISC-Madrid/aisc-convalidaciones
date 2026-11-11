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
- Cada tarea se hace en una **rama** y se entrega con una **Pull Request** con la CI en verde, que revisa **Fran** o la pareja que toque. La revisión es también la forma de que todos conozcamos todas las partes.
- Se trabaja en **tres equipos de dos** (datos históricos, scraping y matching, web), con **rotación semanal**: una persona se queda para mantener el contexto y la otra pasa a un equipo que todavía no ha hecho, con alguien con quien no ha trabajado. Cada equipo tiene **una tarea por semana** con su entregable.
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

No trabajamos a tiempo completo, así que el plan son **8 semanas** más una **semana 9 de buffer**. La unidad de trabajo es **un grupo, una semana, un entregable**. Hay tres equipos de dos con rotación. Las parejas de la Semana 1 fueron:

- **Alejandra (3º Datos) + Ángela (2º Datos y Teleco) · Datos históricos:** los Excel de convalidaciones, de leerlos a calibrar con ellos.
- **Fran (5º Teleco y Datos) + Mercedes (2º Datos y Teleco) · Scraping y matching:** las fichas de la UC3M, el catálogo del destino y, con esos datos en la mano, los embeddings y el matcher. Fran coordina además.
- **Héctor (4º Informática) + Víctor (2º Sonido e Imagen) · Web:** bocetos, web, PDF y prueba con usuarios.

**Rotación semanal.** La Semana 2 se cerró en la reunión del 14/10. Desde la Semana 3, cada semana rota una persona de la pareja y se queda la otra. Quien rota va, siempre que se puede, a un equipo que todavía no ha hecho y con alguien con quien no ha trabajado: el objetivo es pasar por datos, scraping y web y ser pareja de las otras cinco. Una pareja coincide como mucho en dos semanas, y no seguidas. En cada equipo, a partir de la Semana 2, el primer nombre es quien se queda con el contexto y el segundo quien acaba de llegar. La Semana 8 es de todos y la 9 es buffer.

| Semana | Datos históricos | Scraping y matching | Web |
|---|---|---|---|
| **1** | Alejandra + Ángela | Fran + Mercedes | Héctor + Víctor |
| **2** | Ángela + Héctor | Fran + Alejandra | Víctor + Mercedes |
| **3** | Ángela + Fran | Alejandra + Víctor | Mercedes + Héctor |
| **4** | Fran + Héctor | Víctor + Ángela | Mercedes + Alejandra |
| **5** | Fran + Víctor | Ángela + Mercedes | Alejandra + Héctor |
| **6** | Víctor + Mercedes | Ángela + Héctor | Alejandra + Fran |
| **7** | Víctor + Alejandra | Héctor + Mercedes | Fran + Ángela |

Con la Semana 5 se completan las 15 parejas posibles: cada persona ha trabajado con las otras cinco. Las Semanas 6 y 7 repiten parejas de las Semanas 2 y 3 (ninguna seguida), y al acabar la 7 todos han pasado por datos, scraping y web. Las issues de GitHub (#33-#44) son la fuente de las parejas y los entregables.

**Regla:** dentro de una semana, ningún grupo depende de lo que otro grupo haga esa misma semana. Lo que haga falta de otros ya está hecho la semana anterior. Si una semana un grupo no tiene tarea crítica, hace algo útil que no dependa de nadie (marcado en cursiva) o descansa: no hace falta que los seis estén siempre.

| Sem | Datos históricos | Scraping y matching | Web |
|---|---|---|---|
| **1** | **EDA** de los Excel + revisar las 6 candidatas | **SQLite + scraper UC3M** del plan vigente | **Pydantic + frontend**: modelos, JSON de ejemplo, bocetos, web mínima |
| | ◆ **Viernes: piloto elegido** | | |
| **2** | **Histórico → SQLite**: loader con dedup y n:m | **Scraper del destino** piloto + YAML + ECTS | **Web completa** según los bocetos + despliegue |
| **3** | **Reconciliación** de códigos viejos → vigentes | **Fichas antiguas** de la UC3M a la BD + destino terminado | **PDF** con `reportlab` sobre el JSON de ejemplo |
| | ◆ **Datos del piloto completos en SQLite** | | |
| **4** | **Enlace** histórico ↔ destino y tasas de enlace | **Corpus de textos** y buscador top-K en seco | **Web en el servidor** con el catálogo real |
| | ◆ **Sabemos cuántos pares de calibración hay** | | |
| **5** | *Revisión del enlace + notebook de calibración con cosenos inventados* | **Embeddings**: encoder, embeber ambos catálogos, top-K | *Web lista para más de un JSON + README de usuario y guion de la prueba* |
| **6** | **Calibración + evaluación**: umbral, Recall@5, 50 sugerencias a mano; reconciliación por contenido | **Matcher + export** con umbral y embeddings de fixture | *Pantalla de resultados a tamaño real (200 filas) y guion de la demo* |
| | ◆ **Umbral calibrado y export probado** | | |
| **7** | *Documentación técnica: README y `architecture.md`* | *Refresco (`make refresh`) y test end-to-end del pipeline* | **JSON real en el servidor**: export con el umbral de 6A, redespliegue |
| | ◆ **JSON real disponible** | | |
| **8** | **Prueba con 3-5 usuarios y arreglos** (todos) | | |
| **9** | Buffer | | |

## 5. Tareas por semana

Formato de cada tarea: **Entregable** · **Hecho cuando** · **Qué aprendes** · **Pista para empezar**. Todas son de una semana para una pareja.

### Antes de la reunión de arranque (coordinador)

**S0. Repositorio y tablero listos** · *hecho: repo, estructura, CI, README, AGENTS.md y las issues de las Semanas 1 y 2 asignadas a cada pareja*
- Entregable: repo en la organización de AISC con `pyproject.toml`, `ruff`, `pytest`, `.gitignore` (excluye `data/raw` y `data/processed`), la estructura de carpetas de `referencia_tecnica.md` §6 (carpetas vacías con un `.gitkeep`), un test trivial, CI de GitHub Actions (lint + pytest), un `README` con el enlace a este plan y un `AGENTS.md` que describa el proyecto en 10 líneas. Tablero de *Projects* con una issue por cada tarea de las Semanas 1 y 2, asignada a su pareja.
- Hecho cuando: la CI está en verde y los seis tienen permisos de escritura.

**S0 · Todos. Setup personal** (antes o durante la primera semana)
- Entregable: Python 3.11, Git, OpenCode con Copilot conectado y Antigravity instalados; el repo clonado y `pytest` ejecutado.
- Hecho cuando: has abierto una PR de prueba (añadir tu nombre al README) y te la han mergeado.
- Pista: sigue la guía de IA gratis; pídele a OpenCode `/init` en el repo para ver cómo lo describe.

### Semana 1 · Tres grupos, tres cimientos

**1A · Alejandra + Ángela. EDA de los Excel + candidatas**
- Entregable: notebook `01_eda_historical.ipynb` que descarga los 3 XLS (enlaces en `referencia_tecnica.md` §3.2), los carga con `pandas` + `xlrd` y responde a dos preguntas. **¿Dónde hay más datos?**: pares por **grado × universidad** deduplicando cursos, top 10 universidades, top 10 grados. **¿Qué nos va a dar problemas?**: filas repetidas entre cursos, relaciones **n:m** (una asignatura UC3M → varias del destino o al revés), filas sin código de destino, universidades escritas de varias formas. Después, para las **6 universidades con más pares**, una ficha de 5 líneas en `docs/candidatas.md`: URL del catálogo, ¿publica descripciones?, ¿HTML normal o JavaScript?, ¿créditos y equivalencia a ECTS?, ¿idioma?
- Hecho cuando: la tabla grado × universidad está en un `.csv` en `data/processed`, cada problema del dato tiene un ejemplo y un recuento, y `docs/candidatas.md` tiene las 6 fichas con una recomendación. Se presenta el viernes y se **elige el piloto** (criterio: muchos pares, datos limpios y catálogo con descripciones accesibles).
- Aprendes: pandas básico (`read_excel`, `groupby`, `value_counts`, `duplicated`); a desconfiar de los datos; a mirar una web con F12 y distinguir HTML estático de una SPA.
- Pista: `pd.read_excel(ruta, engine="xlrd")`. Normaliza nombres (tildes, mayúsculas, espacios) antes de agrupar. Repartíos: uno el EDA, otro las candidatas, y cambiad a mitad de semana para que los dos toquéis las dos cosas.

**1B · Fran + Mercedes. SQLite + scraper UC3M del plan vigente**
- Entregable: (1) esquema de la BD `data/processed/uc3m.sqlite` con la tabla `subjects` (código, nombre, plan, curso académico, tipo, créditos, curso, cuatrimestre, objetivos, programa, idioma, url, fecha de actualización) documentado en `docs/esquema_bd.md`; (2) `src/scrapers/uc3m.py` con enumeración de planes y asignaturas (`findPlanes.ajax`, `findAsignaturas.ajax`), descarga de `generaFicha` en ES y EN con **caché en disco** y pausa de 1,5 s, `parse_ficha(html)` que saca todos los campos, y carga en la BD; (3) 5 fichas como fixtures en `tests/fixtures/uc3m/` (una sin Objetivos y una de Humanidades) con tests del parser.
- Hecho cuando: todas las asignaturas del curso actual están en la BD con Programa relleno, deduplicadas por código; los tests pasan; ejecutar el script dos veces no vuelve a descargar nada.
- Aprendes: `requests`, BeautifulSoup, SQLite, caché, por qué respetar a la web de destino.
- Pista: todo lo que hay que saber de la web está en `referencia_tecnica.md` §5, Paso 1. Uno hace la enumeración + descarga con caché y el otro el parser con las fixtures; se juntan el miércoles y lanzan la descarga completa (unas horas desatendidas; si se corta, se retoma).

**1C · Héctor + Víctor. Pydantic + frontend**
- Entregable: (1) `src/models/` con las clases Pydantic `Subject`, `HistoricalMatch` y `Match` y un test por clase (a partir de la Semana 2 todos las usan); (2) `public/data/ejemplo.json` inventado con el esquema de `referencia_tecnica.md` §5, Paso 5 (5-6 resultados, con un precedente, una sugerencia y un aviso de ECTS), validado con `Match`; (3) bocetos en `docs/diseno/` de la **pantalla de resultados** y de la **propuesta en PDF** para el tutor (Figma, Excalidraw, HTML estático o papel); (4) `src/ui/app.py` en Streamlit que lee el JSON y enseña una tabla con desplegable de grado y universidad.
- Hecho cuando: los tests de los modelos pasan, el JSON está mergeado, los bocetos están en el repo con 5-10 decisiones de interfaz escritas, y `streamlit run src/ui/app.py` muestra la tabla con datos inventados. A partir de aquí **nadie cambia el esquema del JSON sin avisar al grupo**.
- Aprendes: Pydantic; Streamlit; a pensar primero qué ve el usuario; por qué un "contrato" permite que web y datos avancen en paralelo.
- Pista: uno hace modelos + JSON y el otro bocetos + web mínima; se cruzan el jueves para comprobar que el JSON contiene todo lo que aparece en los bocetos. Empieza con `st.selectbox` y `st.dataframe`.

### Semana 2 · Sobre los cimientos

**2A · Ángela + Héctor. Histórico → SQLite**
- Entregable: `src/loaders/historical_xls.py`: lee los 3 XLS, valida cada fila con `HistoricalMatch` (1C), normaliza textos y códigos, deduplica entre cursos, agrupa las n:m con un `grupo` y guarda la tabla `historical_matches` en `data/processed/historico.sqlite`. Se limpia justo lo que encontrasteis en el EDA.
- Hecho cuando: la tabla está cargada con los 3 ficheros y hay un test con 10 filas inventadas que incluye una duplicada y una n:m.
- Aprendes: limpieza de datos real; SQLite desde Python.
- Pista: cargad un solo XLS sin limpiar y guardadlo; luego añadid normalización y deduplicación paso a paso, con un test por paso.

**2B · Fran + Alejandra. Scraper del destino piloto**
- Entregable: `config/scrapers/<uni>.yaml` (URLs, selectores, `credits_to_ects`, rate limit) + `src/scrapers/destination.py`, que saca nombre, código, descripción y créditos (convertidos a ECTS) de cada asignatura y los guarda en la tabla `dest_subjects` de la BD. Factor de créditos confirmado con la web de la universidad o la ORI.
- Hecho cuando: una parte del catálogo (al menos el departamento o facultad del grado piloto) está en la BD y 10 asignaturas comprobadas a mano coinciden con la web.
- Aprendes: scraping de una web que no controlamos; selectores CSS; Playwright si hace falta.
- Pista: primero `requests`; solo si la página carga con JavaScript, Playwright. Ejemplo de YAML en `referencia_tecnica.md` §5, Paso 1. El piloto recomendado en `docs/candidatas.md` es **Georgia Tech** (catálogo HTML estático con descripciones y créditos); usad su ficha.

**2C · Víctor + Mercedes. Web completa + despliegue**
- Entregable: la pantalla de resultados de los bocetos: filtros, tabla con score y etiqueta ✅/🤖, checkbox de selección, resumen de ECTS seleccionados, aviso de ECTS dispares; desplegada en **Streamlit Community Cloud** leyendo `ejemplo.json`.
- Hecho cuando: hay una URL pública que cualquiera puede abrir y hace lo que dice el boceto.
- Aprendes: Streamlit a fondo; desplegar una app gratis desde GitHub.

### Semana 3 · Cerrar los datos de la UC3M y del destino

**3A · Ángela + Fran. Reconciliación de códigos viejos → vigentes**
- Entregable: `src/reconciliation/old_to_new.py` con los niveles 1 y 2 de la cascada de `referencia_tecnica.md` §5, Paso 2 (mismo código en el plan vigente → mismo nombre normalizado); tabla `old_code → new_code` con la columna `method`; los casos sin resolver, listados en `docs/reconciliacion_pendiente.md` (el nivel 3, por contenido, llega en la Semana 6 con los embeddings).
- Hecho cuando: cada código UC3M del histórico tiene fila en la tabla, con `method` o marcado como pendiente; test con 5 casos inventados.
- Aprendes: que los datos cambian con el tiempo; a diseñar un proceso en cascada.
- Pista: usa la tabla `subjects` de 1B. Ángela trae los códigos del histórico y Fran esa tabla. Empieza contando cuántos códigos del histórico existen tal cual en el plan vigente.

**3B · Alejandra + Víctor. Fichas antiguas + destino terminado**
- Entregable: (1) el scraper de 1B con el parámetro `anio`: fichas de los cursos **2024-25, 2025-26 y 2026-27** (los del Excel) en la tabla `subjects` con su curso académico, solo en EN (ES si la EN viene vacía), con caché; (2) el scraper del destino completo: todo el catálogo relevante en `dest_subjects`.
- Aclaración de cursos (26/10/2026): los tres XLS oficiales enlazados en la referencia técnica tienen hojas `2024-2025`, `2025-2026` y `2026-2027`, con 4.991, 5.198 y 4.333 filas respectivamente entre los tres archivos. La issue #24 conserva el intervalo anterior, 2023-24 a 2025-26; se usa aquí el intervalo comprobado en los datos, también recogido en el notebook EDA.
- Hecho cuando: los tres cursos anteriores están en la BD; el catálogo del destino está completo y 10 asignaturas más comprobadas a mano coinciden.
- Aprendes: a extender tu propio código; a dejar correr descargas largas con caché.
- Pista: Alejandra termina el destino (lo empezó en la Semana 2) y Víctor extiende el scraper UC3M con `anio`. Lanzad las descargas el lunes.

**3C · Mercedes + Héctor. Generador de PDF**
- Entregable: `src/ui/pdf.py` con `reportlab`, siguiendo el boceto: cabecera con alumno, grado y universidad; tabla de asignaturas seleccionadas con ECTS de cada lado y etiqueta; nota de que es orientativo; fecha. Botón "Generar PDF" en la web que lo descarga. Incluye lo pendiente de la issue #22: cada grupo n:m es una sola propuesta y suma cada asignatura una vez en los totales, y la columna se llama «Etiqueta» (no «Tipo»).
- Hecho cuando: desde la web pública, seleccionar asignaturas y pulsar el botón descarga un PDF legible.
- Aprendes: generar documentos desde Python.

### Semana 4 · Juntar el histórico con el destino

**4A · Fran + Héctor. Enlace histórico ↔ destino** (#33)
- Entregable: `src/loaders/link_catalog.py`: para cada fila de Georgia Tech del histórico, buscar su asignatura en `dest_subjects` por `codigo_norm` (`CS 1332` = `CS1332`) y, si falla, por nombre (`rapidfuzz` ≥ 90). Cada fila guarda `dest_subject_id` y `link_method` (`code`, `alias`, `name` o `unlinked`). Los no enlazados, con su motivo, en `docs/enlace_pendiente.md`. Notebook con la tasa de Biomédica, la de todo Georgia Tech y cuántos grados tienen ≥ 20 pares enlazados; tabla de pares de Biomédica reconciliados y enlazados (entrada de 5A); hoja en blanco `docs/revision_enlace.md`.
- Hecho cuando: `dest_subject_id` y `link_method` están rellenos, las tres tasas y el tamaño de la tabla de calibración están anotados y cada no enlazado tiene su fila. **Viernes:** si la tasa de Biomédica es menor del 50 %, la semana 5 corrige el enlace antes del notebook.
- Aprendes: fuzzy matching; a medir un proceso automático.
- Pista: Fran viene de la reconciliación; Héctor entra en datos.

**4B · Víctor + Ángela. Corpus de textos y buscador en seco** (#34)
- Entregable: `src/embeddings/texts.py` (UC3M: `"query: {nombre}. {Objetivos}. {Programa}"`; destino: `"query: {nombre}. {descripcion}"`, sin las fórmulas repetidas del catálogo); el corpus en `data/processed` con un informe de fichas vacías, descripciones cortas y longitudes; `src/embeddings/index.py` con top-K por producto matricial, probado con vectores inventados.
- Hecho cuando: los tests pasan, el informe de longitudes está escrito y el top-K de vectores inventados devuelve el vector correcto.
- Aprendes: a medir la asimetría de los textos antes de embeber (`referencia_tecnica.md` §5, Paso 3).
- Pista: Víctor trae el catálogo y Ángela las fichas de la UC3M. Ángela se queda la semana 5 y embebe este corpus.

**4C · Mercedes + Alejandra. Web en el servidor, con el catálogo real** (#35)
- Entregable: la web en `web/` con su `Dockerfile` (puerto 8501, sin variables de entorno); pantalla Catálogo que lee el SQLite del servidor (código, nombre, ECTS y enlace; nunca temarios); en resultados, pestaña «Cómo funciona», precedentes primero, grupos n:m juntos, el PDF pide el nombre del alumno y aviso de datos de ejemplo; estados de error y tests.
- Hecho cuando: en la URL del servidor un alumno busca una asignatura real, lee «Cómo funciona», selecciona una propuesta de ejemplo y descarga el PDF.
- Pista: Mercedes se queda en la web (hizo el PDF); Alejandra trae el catálogo.

### Semana 5 · Embeddings

**5A · Fran + Víctor. Revisión del enlace y notebook de calibración** (#36) *(no bloquea a nadie)*
- Entregable: `docs/revision_enlace.md` con 20 enlaces y 20 reconciliaciones revisados a mano y los fallos como issues; notebook `04_calibration.ipynb` que parte de la tabla de 4A con **split 80/20 por asignatura UC3M** (no por fila), filtro de outliers (mediana − 3·MAD) y percentil, probados con cosenos inventados.
- Hecho cuando: la hoja tiene los 40 casos; el notebook corre de arriba abajo, produce un umbral y anota cuántos pares hay en train y en hold-out.
- Aprendes: por qué no se fija un umbral a ojo; fuga de información en un split; percentiles y MAD (`referencia_tecnica.md` §5, Paso 4).
- Pista: Fran se queda (programó el enlace); Víctor llega del catálogo y puede juzgar si un enlace es correcto.

**5B · Ángela + Mercedes. Encoder, embeddings y top-K** (#37)
- Entregable: `src/embeddings/encoder.py` sobre el corpus de 4B: troceado en ~400 tokens, media de los trozos y normalización L2, con `multilingual-e5-small`; embeddings de la UC3M del piloto y de todo Georgia Tech en `data/processed`, buscados con el `index.py` de 4B.
- Hecho cuando: un test comprueba que dos textos iguales dan similitud 1 y que un texto largo se trocea; para "Estructuras de Datos" el top-5 del destino tiene sentido a ojo.
- Aprendes: qué es un embedding y por qué se normaliza; `sentence-transformers`; álgebra básica con numpy.
- Pista: Ángela trae el corpus y el `index.py`; Mercedes entra en scraping y matching. Si el portátil va lento, Google Colab gratis.

**5C · Alejandra + Héctor. La web lista para más de un JSON** (#38) *(no bloquea a nadie)*
- Entregable: los desplegables de grado y universidad leen `public/data/index.json`; la tabla pagina o limita filas para que 200 resultados no la bloqueen; README de usuario escrito contra la URL del servidor y `docs/prueba_usuarios.md` con 4-5 tareas y un cuestionario corto.
- Hecho cuando: cambiar de combinación en el `index.json` cambia la tabla sin tocar código; una persona ajena completa el guion en la URL.
- Pista: Alejandra se queda en la web; Héctor vuelve a ella tras las semanas 1 y 3.

### Semana 6 · Calibrar y cerrar el pipeline

**6A · Víctor + Mercedes. Calibración, evaluación y reconciliación por contenido** (#39)
- Entregable: el notebook de 5A con los cosenos reales: umbral, outliers descartados, `src/matching/evaluation.py` con Recall@1, Recall@5 y MRR sobre el hold-out, y **50 sugerencias por encima del umbral revisadas a mano** (razonable / dudoso / no). Nivel 3 de la reconciliación para los códigos de `docs/reconciliacion_pendiente.md`: `embedding`, `manual` o «fase 2».
- Hecho cuando: umbral, tamaño de la muestra, Recall@5, MRR y precisión estimada están al final del notebook (orientativos si hay < 30 pares en el hold-out).
- Aprendes: métricas de ranking; que el histórico solo tiene positivos y por eso la precisión se estima a mano.
- Pista: Víctor se queda (el notebook es el de la semana 5); Mercedes trae los embeddings.

**6B · Ángela + Héctor. Matcher y export** (#40)
- Entregable: `src/matching/matcher.py` (top-10 por coseno, umbral como argumento, `PRECEDENTE_APROBADO` que se muestra siempre / `SUGERENCIA_IA`, aviso si los ECTS difieren más del 25 %) y `src/export/build_static.py`, que genera `public/data/<grado>__<uni>.json` e `index.json`. Se prueba con umbral 0,7 y embeddings de fixture.
- Hecho cuando: los tests cubren precedente, sugerencia y aviso de ECTS, y un JSON de fixture valida con `Match`.
- Pista: Ángela se queda (trae los embeddings); Héctor entra. Las reglas están en `referencia_tecnica.md` §5, Paso 4.

**6C · Alejandra + Fran. La pantalla de resultados, a tamaño real** (#41) *(no bloquea a nadie)*
- Entregable: un JSON inventado de 200 resultados cargado en el servidor; la cabecera muestra `generado` y `umbral`; test end-to-end (cargar, filtrar, seleccionar un grupo, sacar el PDF); guion de la demo de 5 minutos.
- Hecho cuando: la tabla de 200 filas se mueve bien en el servidor, el PDF descarga y el guion está en `docs/`.
- Pista: Alejandra se queda en la web; Fran entra en ella.

### Semana 7 · Integración y cierre técnico

**7A · Víctor + Alejandra. Documentación técnica** (#42) *(no bloquea a nadie)*
- Entregable: `README` técnico (instalar, ejecutar cada paso, añadir una universidad) y `docs/architecture.md`.
- Hecho cuando: una persona nueva ejecuta el pipeline siguiendo el README.
- Pista: Víctor se queda en datos; Alejandra trae la web.

**7B · Héctor + Mercedes. Refresco y test del pipeline** (#43) *(no bloquea a nadie)*
- Entregable: `test_e2e.py` que recorre el pipeline con datos pequeños en un directorio temporal y `make refresh`, que vuelve a scrapear, recalcula y regenera los JSON; cobertura hacia el 70 % en embeddings, matching y export.
- Hecho cuando: `make refresh` corre sobre el fixture y `pytest --cov` publica el número; si no llega al 70 %, el hueco queda en una issue para la semana 9.
- Pista: Héctor se queda (cerró el matcher); Mercedes llega de la calibración.

**7C · Fran + Ángela. JSON real en el servidor** (#44)
- Entregable: ejecutar el export de 6B con el umbral de 6A y dejar `public/data/<grado>__<uni>.json` e `index.json` en el repo y en el servidor; quitar el aviso de datos de ejemplo; ajustes que pida el dato real.
- Hecho cuando: en la URL del servidor un alumno elige Ingeniería Biomédica y Georgia Tech, ve los resultados reales, abre una ficha y descarga el PDF.
- Pista: Fran se queda en la web; Ángela programó el export y lo lanza con el número de 6A.

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
