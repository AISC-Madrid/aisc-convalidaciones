# Informe del corpus — Semana 4

Relacionado con la issue #34. Resultados de Georgia Tech obtenidos el 3 de noviembre
de 2026. Pendiente de incorporar UC3M y la comparación entre ambos catálogos.

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

## Reproducción y comprobaciones

Con la base local disponible, desde la carpeta principal del repositorio:

```powershell
python -m src.embeddings.generar_corpus_destino
python -m pytest tests/test_embedding_texts.py
```

Ahora prepararemos el generador para poder reutilizarlo desde otros archivos. 
Actualmente se ejecuta entero en cuanto alguien lo importa; queremos que genere 
el corpus solo cuando se lo pidamos.

Las cinco pruebas ejecutadas durante la preparación cubren la eliminación
de una referencia cruzada, la conservación de una descripción académica,
los valores ausentes y la construcción del texto con y sin descripción.
Las cinco pasaron.

## Pendiente: UC3M y comparación

Falta incorporar el corpus del plan vigente del grado piloto, los recuentos
de campos vacíos y las longitudes de objetivos y programa. La comparación
deberá medir también los textos completos preparados de ambos catálogos
con el mismo criterio de conteo.

Todavía no se ha cuantificado la diferencia de longitudes UC3M–Georgia Tech
ni se han calculado embeddings. Este informe es parcial hasta completar
esa comparación.
