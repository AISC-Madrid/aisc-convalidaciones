# Guion de la demo (5 minutos) · pantalla de resultados

Demo sobre la web del servidor con el **JSON inventado de 200 resultados**.
Más adelante ese JSON se sustituye por el real, en la misma combinación y en el mismo
servidor, así que este guion sirve también para entonces.

>"URL a cambiar cuando se elija nombre del dominio."

- **URL:** `http://nrgpabvjso4mfw01d3cyuvgu.178.104.232.178.sslip.io/`  
- **Combinación:** Grado en Ingeniería Biomédica · Georgia Institute of Technology
- **Antes de empezar:** abrid la URL un par de minutos antes (la primera carga es más lenta)
  y tened a mano un visor de PDF.

## Qué es

> "Un alumno de la UC3M que se va de movilidad fuera de Europa elige su grado y su
> universidad de destino y ve qué asignaturas le podrían convalidar. Al final se lleva una
> propuesta en PDF para su tutor. Es orientativo: el tutor decide."

Señalad el aviso amarillo: los datos de hoy son de ejemplo.

## Elegir combinación y leer la cabecera

1. En **Grado UC3M**, elegid *Grado en Ingeniería Biomédica*. En **Universidad de destino**,
   *Georgia Institute of Technology*.
2. Leed la línea bajo los desplegables: **Generado el 25/11/2026 · Umbral de similitud: 0,71**.

> "La fecha dice de cuándo son los datos. El umbral es la similitud mínima para que la IA
> sugiera una asignatura; lo calibramos con las convalidaciones que ya se aprobaron."

## La tabla a tamaño real

1. Señalad *Propuestas 1-20 de 186*. Son 200 filas, pero los grupos n:m cuentan como una sola
   propuesta.
2. Pasad a la página 2 y luego a la última: la tabla responde al momento.
3. Explicad las columnas. **Etiqueta**: *Precedente aprobado* (ya se convalidó antes) o
   *Sugerencia IA*. **Similitud**: no es la probabilidad de que se apruebe. **Aviso**:
   *ECTS dispares* si los créditos difieren más de un 25 %.

> "Primero salen los precedentes y, dentro de cada tipo, de mayor a menor similitud."

## Filtrar y buscar

1. En **Tipo de resultado**, elegid *Sugerencias IA*: desaparecen los precedentes.
2. Volved a *Todas* y escribid `Biomecánica` en el buscador. Probad también un código, por
   ejemplo `BMED`. Sin tildes también funciona (`biomecanica`).
3. Borrad la búsqueda.

> "Si un grupo coincide con la búsqueda, sale entero: nunca se parte."

## Seleccionar y sacar el PDF

1. Marcad dos o tres propuestas 1:1 y **un grupo n:m** (los que muestran varias asignaturas
   separadas por comas). Mirad cómo cambian los totales **ECTS UC3M** y **ECTS destino**.
2. Escribid algo en el buscador que oculte una de las marcadas. Señalad el aviso de que
   sigue incluida en el PDF. Borrad la búsqueda.
3. Escribid un nombre largo en **Nombre del alumno**, por ejemplo
   *María de los Ángeles Fernández-Villaverde Rodríguez*.
4. Pulsad **Descargar propuesta PDF** y abridlo. Enseñad que solo están las seleccionadas,
   que el grupo va en un único bloque y que los nombres largos no se cortan.

## Cierre

- **Hoy:** la pantalla aguanta el volumen real (200 resultados, nombres largos, grupos n:m)
  y el PDF sale.
- **Semana 7:** cambiamos este JSON por el real del pipeline y quitamos el aviso de ejemplo.
- **Semana 8:** prueba con 3-5 alumnos.
- Preguntas.

## Si algo falla en directo

- **La web no carga:** recargad; si el servidor estaba dormido tarda unos segundos. Plan B:
  `streamlit run web/app.py` en local con el mismo JSON.
- **El botón del PDF está gris:** falta marcar alguna propuesta o escribir el nombre (la web
  lo dice encima del botón).

## Cómo regenerar el JSON de ejemplo

```bash
python scripts/generar_ejemplo_200.py   # reescribe public/data/ejemplo_200.json
pytest tests/test_ejemplo_200.py web/tests/test_e2e_200.py
```