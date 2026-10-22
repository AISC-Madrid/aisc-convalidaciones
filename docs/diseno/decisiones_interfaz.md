# Decisiones de interfaz

1. Situamos los desplegables de grado y universidad antes de los resultados
   para que el estudiante identifique qué combinación está consultando.

2. Mostramos las asignaturas de UC3M y destino una junto a otra para
   facilitar la comparación de nombres, códigos y créditos.

3. Incluimos los códigos de las asignaturas para distinguir materias
   con nombres similares.

4. Diferenciamos los precedentes aprobados y las sugerencias de IA
   mediante la columna «Etiqueta», sin depender únicamente del color.
   «Tipo» se reserva para el carácter de la asignatura (FB/OB/OP/HUM).

5. Mostramos la puntuación de similitud y aclaramos que no representa
   una probabilidad de aprobación de la convalidación.

6. Situamos los avisos de diferencia de créditos junto al resultado
   afectado para que se detecten antes de preparar la propuesta.

7. Incluimos enlaces a las fichas de destino para consultar la
   información académica original.

8. En el diseño completo, la selección de asignaturas actualiza
   por separado los totales de ECTS de origen y destino. Las filas con
   el mismo `grupo` forman una sola propuesta que se selecciona completa.
   En los totales se cuenta cada código de asignatura una sola vez por
   lado; los resultados con `grupo: null` son propuestas individuales.

9. El PDF recoge solo las asignaturas seleccionadas, junto con los
   datos del alumno, el grado, las universidades, la fecha y los avisos,
   para facilitar la revisión del tutor.
   Cada grupo conjunto se muestra en un único bloque con todas sus
   asignaturas de origen y destino. Por ejemplo, Programación (6 ECTS)
   frente a CS 1301 y CS 1331 (4,5 + 4,5 ECTS) suma 6 ECTS de origen
   y 9 de destino, y debe mostrar el aviso de diferencia de créditos.

10. Indicamos que la propuesta es orientativa y requiere revisión
    del tutor para evitar confundirla con una aprobación oficial.

## Alcance de la semana 1

Se implementan la lectura del JSON de ejemplo, los desplegables de
grado y universidad y la tabla de resultados.

La selección de asignaturas, los totales dinámicos y la generación
del PDF aparecen en los bocetos como funcionalidades posteriores.

## Correspondencia con el JSON

| Elemento de pantalla | Campo o cálculo |
| --- | --- |
| Grado y universidad | `grado`, `universidad` |
| Nombres, códigos y créditos | `origen` y `destino` |
| Similitud | `score` |
| Etiqueta de la propuesta | `etiqueta` |
| Aviso de créditos | `aviso_ects`, coherente con los totales del grupo |
| Ficha de destino | `destino.url` (opcional) |
| Propuesta conjunta | `grupo` |
| Selección | Estado de la interfaz, no un campo del JSON |
| Totales | Créditos de asignaturas seleccionadas, sin duplicar códigos por lado |

El nombre del alumno y la fecha de la propuesta se recogen o generan
al crear el PDF; no se confunden con la fecha `generado` del conjunto de datos.
