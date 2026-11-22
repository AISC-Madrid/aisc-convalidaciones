# Revisión del enlace y de la reconciliación

Hoja de la semana 5 (tarea 5A). En la semana 4 queda en blanco: hay que revisar a mano
20 enlaces y 20 reconciliaciones del piloto, y abrir un issue por cada fallo.

## Enlaces

Muestra de Georgia Tech (`historico.sqlite`, 239 filas enlazadas y 5 sin enlazar): todos los
enlaces por `alias` y por `name`, un `unlinked` que sí tiene pareja y los `code` cuyo nombre
se parece menos al del catálogo (`token_set_ratio`), que es donde un código mal copiado se
notaría. Resultado: 19 de 20 correctos; un fallo (#55) y un problema de calibración (#56).

| # | Código histórico | Nombre histórico | Código catálogo | Nombre catálogo | Método | ¿Correcto? | Nota |
|---|---|---|---|---|---|---|---|
| 1 | AE4699ROM | Undergraduate Research | AE 4699 | Undergraduate Research | alias | Sí | Errata `ROM` quitada. El enlace es bueno, pero la UC3M lo cambia por transversales: ver #56. Sin ECTS en el catálogo (créditos variables). |
| 2 | BIOS7210 | Computational Genomics | BIOL 7210 | Computational Genomics | alias | Sí | Biomédica. `BIOS` → `BIOL`: mismo nombre. |
| 3 | PHYS3211 | Electronics I | PHYS 3209 | Electronics I | name | Sí | El código del Excel es una errata; el nombre lo arregla. |
| 4 | BMED3250 | Biomedical systems and modeling | BMED 3520 | Biomedical Systems and Modeling | name | Sí | Cifras traspuestas en el Excel; el nombre lo arregla. |
| 5 | PHYS3211 | Electronics 1 | — | — | unlinked | No | Debería enlazar con PHYS 3209: `1` y `I` no cuentan como el mismo ordinal. Issue #55. |
| 6 | CS4290 | Advanced Operating Systems | CS 4290 | Advanced Computer Organization | code | Sí | El nombre del Excel está mal; el código y la asignatura UC3M (Arquitectura de Computadores) cuadran con Computer Organization. |
| 7 | ME3180 | Mechanical Design and Analysis | ME 3180 | Machine Design | code | Sí | Nombre antiguo del mismo curso. |
| 8 | ECE3043 | Circuit Electronic Lab | ECE 3043 | Measurements, Circuits, and Microelectronics Laboratory | code | Sí | Nombre abreviado. ECTS distintos (catálogo 4, histórico 3 o 6): lo cubre el aviso de ECTS. |
| 9 | MSE2001 | Prin&Appl-Engr Materials | MSE 2001 | Principles and Applications of Engineering Materials | code | Sí | Nombre abreviado. |
| 10 | CS4240 | Compilers & Interpreters | CS 4240 | Compilers, Interpreters, and Program Analyzers | code | Sí | Nombre abreviado. |
| 11 | PHYS4751 | Laser Theory&Application | PHYS 4751 | Laser Theory and Applications | code | Sí |  |
| 12 | PHYS4782 | Quantum Info&Quant Comp | PHYS 4782 | Quantum Information and Quantum Computing | code | Sí |  |
| 13 | ECE4350 | Electromag Applications | ECE 4350 | Electromagnetic and Microwave Applications | code | Sí |  |
| 14 | BMED3500 | Sensors& Instrumentation | BMED 3500 | Biomedical Sensors and Instrumentation | code | Sí | Biomédica. |
| 15 | BMED3520 | Biomed Sys & Modeling | BMED 3520 | Biomedical Systems and Modeling | code | Sí | Biomédica. |
| 16 | ME3210 | Design and Manufacture | ME 3210 | Design, Materials, and Manufacture | code | Sí |  |
| 17 | BIOS3756 | Physiology lab | BIOS 3756 | Physiology Laboratory | code | Sí | Biomédica. `BIOS` existe como prefijo propio: no se aplica el alias. |
| 18 | MATH4640 | Numerical Analysis I | MATH 4640 | Introduction to Numerical Analysis | code | Sí |  |
| 19 | AE4312 | Aircraft Design II | AE 4312 | Aircraft Design II: Preliminary Design | code | Sí |  |
| 20 | ME6753 | Principles of Management for Engineering | ME 6753 | Principles of Management for Engineers | code | Sí | Curso de posgrado (6xxx); el enlace es correcto. |

## Reconciliaciones

Muestra de los 128 códigos UC3M que aparecen en filas de Georgia Tech (`old_to_new`: 517
por `code`, 0 por `exact` y 6 sin resolver en total). Los 126 resueltos por `code` tienen el
mismo nombre y los mismos ECTS en 2026/2027, así que la muestra se centra en los dos sin
resolver, los transversales, Biomédica y los códigos que cambian de plan. Resultado: 18 de
20 correctos; los dos sin resolver tienen candidato claro en el plan nuevo (#57).

| # | Código antiguo | Código vigente | Método | ¿Correcto? | Nota |
|---|---|---|---|---|---|
| 1 | 18274 | — | sin resolver | No | Estadística, plan 433 de Matemática Aplicada (ya no está en 2026/2027). Candidato: 20563 Inferencia Estadística (mismo curso, cuatrimestre y ECTS). Issue #57. |
| 2 | 18276 | — | sin resolver | No | Ampliación de cálculo numérico, plan 433. Candidatos: 20567 o 20561, según el temario. Issue #57. |
| 3 | 14528 | 14528 | code | Sí | Dos nombres en el Excel («Habilidades Profesionales» y «… movilidad»): es la misma asignatura. Transversal: #56. |
| 4 | 14155 | 14155 | code | Sí | Técnicas de búsqueda y uso de la información, 1,5 ECTS. Transversal: #56. |
| 5 | 17881 | 17881 | code | Sí | Hojas de cálculo. Nivel avanzado, 1,5 ECTS. Transversal: #56. |
| 6 | 14159 | 14159 | code | Sí | Biomédica. Biología Computacional, mismo nombre y ECTS. |
| 7 | 14156 | 14156 | code | Sí | Biomédica. Fisiología Médica I. |
| 8 | 14157 | 14157 | code | Sí | Biomédica. Fisiología Médica II. |
| 9 | 14158 | 14158 | code | Sí | Biomédica. Procesamiento de imágenes médicas. |
| 10 | 15535 | 15535 | code | Sí | Biomédica. «Estadística» se repite en muchos grados; el código lo resuelve sin ambigüedad (al contrario que 18274). |
| 11 | 15553 | 15553 | code | Sí | Biomédica. Introducción a los Biomateriales. |
| 12 | 15554 | 15554 | code | Sí | Biomédica. Introducción al diseño de instrumentación médica. |
| 13 | 15555 | 15555 | code | Sí | Biomédica. Fundamentos de ingeniería de tejidos y medicina regenerativa. |
| 14 | 15547 | 15547 | code | Sí | Biomédica. Fenómenos de transporte en biomedicina. |
| 15 | 15543 | 15543 | code | Sí | Biomédica. Métodos numéricos en biomedicina. |
| 16 | 19896 | 19896 | code | Sí | Biomédica. Fundamentos de gestión empresarial, 3 ECTS. |
| 17 | 18272 | 18272 | code | Sí | Arquitectura de Computadores: el código pasa del plan 433 al 567 y sigue siendo la misma asignatura. |
| 18 | 18280 | 18280 | code | Sí | Técnicas de verificación de software: mismo caso que 18272 (planes 433 y 567). |
| 19 | 18319 | 18319 | code | Sí | Biofísica 2 (Ingeniería Física), mismo nombre y ECTS. |
| 20 | 18317 | 18317 | code | Sí | Fundamentos de ingeniería electrónica (Ingeniería Física y doble grado), mismo nombre y ECTS. |
