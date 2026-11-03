# Informe del corpus — Semana 4

Relacionado con la issue #34. Resultados de ambos catálogos obtenidos el 3 de
noviembre de 2026.

## Fuente y formato

Se ha generado `data/processed/corpus_gatech.jsonl` a partir de la tabla
`dest_subjects` de `data/processed/uc3m.sqlite`, filtrando por `universidad = 'GATECH'`.
El archivo contiene un objeto JSON por línea, con identificador, universidad,
código, nombre, texto preparado y una marca de descripción original vacía.

El texto sigue el formato `query: {nombre}. {descripcion limpia}`. Cuando falta
la descripción, se conserva `query: {nombre}` y se marca `descripcion_vacia = true`.
Los datos originales permanecen en la base; el corpus se guarda en local.

## Revisión y limpieza

Se revisó una muestra reproducible de 20 descripciones, seleccionada con
`random.Random(34)` sobre las descripciones no vacías ordenadas por código.
Se identificaron referencias de catálogo como `Crosslisted with ME 6769.`,
que no describen el contenido académico y se eliminan del texto preparado.
La regla admite espacios antes del punto y diferencias de mayúsculas.

La limpieza también normaliza los espacios. En total, 182 descripciones
presentaron cambios por alguna de estas operaciones; esta cifra no equivale
necesariamente al número de referencias eliminadas. Se revisaron los primeros
10 ejemplos modificados mostrados por el script y no se observaron errores.
No se ha realizado una revisión manual de los 182 casos.

Las descripciones breves o genéricas se conservan. Por ejemplo, la descripción
de ME 4843 indica que incluye laboratorio, aunque apenas detalle los temas.
No se aplican por ahora reglas generales para eliminar prerrequisitos u otras
frases sobre la organización docente.

## Longitudes y campos vacíos

Las longitudes cuentan palabras mediante `split()` en la descripción limpia,
sin incluir el nombre ni el prefijo `query:`. No son recuentos de tokens del
modelo. Las descripciones vacías se incluyen con longitud cero.

| Medida | Resultado |
|---|---:|
| Asignaturas exportadas | 2.414 |
| Descripciones originales vacías | 81 |
| Descripciones vacías tras limpiar | 81 |
| Descripciones que quedaron vacías por la limpieza | 0 |
| Descripciones limpias de 1 a 9 palabras | 104 |
| Longitud mínima | 0 palabras |
| Mediana de longitud | 23 palabras |
| Longitud máxima | 105 palabras |

Se adopta provisionalmente el intervalo de 1 a 9 palabras para señalar
descripciones muy cortas. Es un criterio de revisión, no de exclusión.
Los 104 casos cortos no incluyen las 81 descripciones vacías.

La mediana indica que al menos la mitad de las descripciones tiene 23 palabras
o menos. La limpieza no dejó vacía ninguna descripción originalmente no vacía;
esto no sustituye la revisión de que se conserve el contenido académico.

## Corpus UC3M

El corpus UC3M se genera con
`src/embeddings/generar_corpus_uc3m.py`. La consulta une `subjects` con
`subject_plans` y filtra el plan piloto `456`, el curso `2026/2027` y la ficha
en inglés (`EN`). Usa `DISTINCT` y la unicidad de la tabla para evitar
duplicados. El texto sigue el formato:

```text
query: {nombre}. {objetivos}. {programa}
```

Los objetivos son opcionales; el programa se conserva aunque falten objetivos.
Cada registro indica si los objetivos o el programa estaban vacíos. Las
longitudes se cuentan con `split()` por separado para objetivos, programa y
texto preparado, sin interpretarlas como tokens del modelo.

Con la base real disponible, el corpus del plan piloto contiene 135
asignaturas. Los resultados son:

| Medida | Objetivos | Programa | Contenido preparado* |
|---|---:|---:|---:|
| Campos/fichas vacías | 19 objetivos | 12 programas | 12 ambos |
| Mínimo | 0 | 0 | 0 |
| Mediana | 103 | 95 | 240 |
| Máximo | 654 | 603 | 849 |
| De 1 a 9 palabras | — | — | 0 |

*El contenido preparado es el texto completo menos el prefijo `query:` y el
nombre de la asignatura. Por tanto, suma objetivos y programa después de la
normalización. De las 12 fichas sin programa, las 12 tienen también los
objetivos vacíos: hay 12 fichas con ambos campos vacíos y ninguna ficha con
programa vacío pero objetivos presentes.

## Reproducción y comprobaciones

Con la base local disponible, desde la carpeta principal del repositorio:

```powershell
python -m src.embeddings.generar_corpus_destino
python -m src.embeddings.generar_corpus_uc3m
python -m pytest tests/test_embedding_texts.py tests/test_embedding_corpus_uc3m.py
```

El generador UC3M falla explícitamente si no existe `data/processed/uc3m.sqlite`
y abre la base en modo solo lectura. La base debe obtenerse mediante el flujo
de datos del proyecto; este trabajo no la descarga ni la modifica.

Los tests cubren la construcción de textos con ficha completa y sin objetivos,
el filtrado de plan, curso e idioma, la ausencia de duplicados y las
estadísticas de campos vacíos y longitudes.

## Comparación UC3M–Georgia Tech

La comparación principal usa el mismo criterio en ambos corpus: palabras del
texto preparado excluyendo `query:` y el nombre. Para completar la revisión
también se cuenta el texto JSONL completo con esos elementos incluidos:

| Medida | UC3M | Georgia Tech |
|---|---:|---:|
| Asignaturas | 135 | 2.414 |
| Contenido vacío | 12 | 81 |
| Contenido mínimo | 0 | 0 |
| Mediana de contenido | 240 | 23 |
| Contenido máximo | 849 | 105 |
| Contenido de 1 a 9 palabras | 0 | 104 |
| Texto completo mínimo | 2 | 3 |
| Mediana de texto completo | 243 | 27 |
| Texto completo máximo | 856 | 111 |

El texto completo se ha calculado leyendo `corpus_uc3m.jsonl` y
`corpus_gatech.jsonl` y aplicando `len(texto.split())`; no es un recuento de
tokens. En Georgia Tech se ejecutó el generador existente sin modificarlo y
se calculó después esta métrica adicional a partir del JSONL generado.

La asimetría es considerable: la mediana del contenido UC3M (240 palabras) es
aproximadamente 10,4 veces la de Georgia Tech (23 palabras), y el máximo es
849 frente a 105. Georgia Tech ofrece descripciones breves de catálogo,
mientras que la UC3M combina objetivos y programa de la guía docente. Además,
el 4,3 % de las fichas UC3M no tiene programa (12 de 135), frente al 3,4 % de
descripciones vacías en Georgia Tech (81 de 2.414); en ambos casos el nombre
permite conservar un texto preparado no vacío.

Esta diferencia puede reducir la similitud si se comparan directamente textos
de granularidad distinta. Para la semana siguiente habrá que usar chunking y
normalización L2, manteniendo el mismo criterio de campos en ambos lados.
Los textos UC3M más largos pueden superar el límite de contexto elegido para
cada chunk, por lo que habrá que comprobar que la media de chunks no diluya
los conceptos importantes. No se calculan embeddings en esta tarea.
