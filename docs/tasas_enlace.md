# Tasas de enlace (Georgia Tech)

Calculadas sobre `historical_matches` después de enlazar con el catálogo.
Una fila está enlazada si `link_method` es `code`, `alias` o `name`.
`unlinked` entra en el denominador y no calibra. Las filas de otras
universidades tienen `link_method` vacío y no entran.

El plan cita 49/50 en Biomédica y 263/276 en Georgia Tech: es el recuento
a mano del EDA, antes de deduplicar y con el catálogo entero. Aquí el
denominador es la tabla ya deduplicada, y solo enlaza lo que está en
`dest_subjects`.

## Biomédica

39/39 (100.0%)

Por encima del 50 %: la semana 5 puede calibrar sin corregir el enlace antes.

## Georgia Tech

239/244 (98.0%)

0 de 5 no enlazadas tienen un prefijo que no está en el catálogo. Todas tienen su departamento cargado, pero el código no está en el catálogo 2026-27 y ningún nombre se parece. El motivo de cada una está en `docs/enlace_pendiente.md`.

## Por grado

Grados con al menos 20 pares enlazados, el mínimo para
un umbral propio en la fase 2: 4 de 13.

| Grado | Enlazadas | Total | Tasa | Umbral propio |
|---|---|---|---|---|
| Doble Grado en Ingeniería Física e Ingeniería en Tecnologías Industriales | 42 | 42 | 42/42 (100.0%) | sí |
| Grado en Ingeniería Biomédica | 39 | 39 | 39/39 (100.0%) | sí |
| Grado en Ingeniería Física | 34 | 36 | 34/36 (94.4%) | sí |
| Grado en Ingeniería Informática | 20 | 21 | 20/21 (95.2%) | sí |
| Grado en Ingeniería Aeroespacial | 16 | 16 | 16/16 (100.0%) | no |
| Grado en Ingeniería Robótica | 14 | 14 | 14/14 (100.0%) | no |
| Grado en Ingeniería en Tecnologías Industriales | 14 | 14 | 14/14 (100.0%) | no |
| Doble Grado Ciencia e Ingeniería de Datos - Ingeniería en Tecnologías de Telecomunicación | 12 | 12 | 12/12 (100.0%) | no |
| Grado en Ingeniería de la Energía | 12 | 12 | 12/12 (100.0%) | no |
| Grado en Matemática Aplicada y Computación | 10 | 11 | 10/11 (90.9%) | no |
| Doble Grado en Ingeniería Informática y Administración de Empresas | 9 | 9 | 9/9 (100.0%) | no |
| Grado en Matemáticas y Computación | 9 | 10 | 9/10 (90.0%) | no |
| Grado en Ingeniería Telemática | 8 | 8 | 8/8 (100.0%) | no |

## Tabla de calibración

Pares de Biomédica reconciliados y enlazados. La semana 5 los lee con
`tabla_calibracion(cargar_filas())`.

- Pares: 39
- Asignaturas UC3M distintas: 18
- Enlazadas del piloto fuera de la tabla, con el código UC3M pendiente: 0

| Código vigente | Código antiguo | Asignatura UC3M | Reconciliación | Código histórico | Nombre histórico | Código catálogo | Nombre catálogo | Método | Grupo |
|---|---|---|---|---|---|---|---|---|---|
| 14156 | 14156 | Fisiología Médica I | code | BIOS3753 | Human Anatomy | BIOS 3753 | Fundamentals of Human Anatomy | code | — |
| 14156 | 14156 | Fisiología Médica I | code | BIOS3755 | Human Physiology | BIOS 3755 | Human Physiology | code | 774 |
| 14156 | 14156 | Fisiología Médica I | code | BIOS3756 | Physiology lab | BIOS 3756 | Physiology Laboratory | code | 774 |
| 14156 | 14156 | Fisiología Médica I | code | BMED3100 | Systems Physiology | BMED 3100 | Systems Physiology | code | — |
| 14157 | 14157 | Fisiología Médica II | code | BIOS3755 | Human Physiology | BIOS 3755 | Human Physiology | code | — |
| 14157 | 14157 | Fisiología Médica II | code | BIOS3756 | Physiology lab | BIOS 3756 | Physiology Laboratory | code | — |
| 14158 | 14158 | Procesamiento de imágenes médicas | code | BMED4783 | Introduction to medical image | BMED 4783 | Introduction to Medical Image Processing | code | 776 |
| 14158 | 14158 | Procesamiento de imágenes médicas | code | BMED6780 | Medical image processing | BMED 6780 | Medical Image Processing | code | 776 |
| 14159 | 14159 | Biología Computacional | code | BIOS7210 | Computational Genomics | BIOL 7210 | Computational Genomics | alias | 777 |
| 14159 | 14159 | Biología Computacional | code | BIOL7210 | Computational Genomics | BIOL 7210 | Computational Genomics | code | 777 |
| 14159 | 14159 | Biología Computacional | code | BIOS4150 | Genomics and Appl Bionfor | BIOS 4150 | Genomics and Applied Bioinformatics | code | 592 |
| 14159 | 14159 | Biología Computacional | code | BMED3211 | Introduction to Bioinformatics | BMED 3211 | Introduction to Bioinformatics | code | — |
| 14159 | 14159 | Biología Computacional | code | BMED3520 | Biomed Sys & Modeling | BMED 3520 | Biomedical Systems and Modeling | code | 777 |
| 14159 | 14159 | Biología Computacional | code | BMED4813 | Special Topics (Biomedical and Health Informatics) | BMED 4813 | Special Topics | code | 592 |
| 14528 | 14528 | Habilidades Profesionales | code | BMED4602 | Capstone design | BMED 4602 | Capstone Design | code | 778 |
| 14528 | 14528 | Habilidades Profesionales | code | ME6753 | Principles of Management for Engineering | ME 6753 | Principles of Management for Engineers | code | 778 |
| 14528 | 14528 | Habilidades profesionales movilidad | code | PHIL3127 | Science, Technology and Human Values | PHIL 3127 | Science, Technology, and Human Values | code | — |
| 15535 | 15535 | Estadística | code | BMED2400 | Introduction to Bioengineering Statistics | BMED 2400 | Introduction to Bioengineering Statistics | code | 593 |
| 15535 | 15535 | Estadística | code | MATH3235 | Probability Theory | MATH 3235 | Probability Theory | code | 593 |
| 15541 | 15541 | Ciencia e ingeniería de materiales | code | MSE2001 | Prin&Appl-Engr Materials | MSE 2001 | Principles and Applications of Engineering Materials | code | — |
| 15543 | 15543 | Métodos numéricos en biomedicina | code | MATH4640 | Numerical Analysis I | MATH 4640 | Introduction to Numerical Analysis | code | — |
| 15547 | 15547 | Fenómenos de transporte en biomedicina | code | BMED3310 | Biotransport | BMED 3310 | Biotransport | code | — |
| 15547 | 15547 | Fenómenos de transporte en biomedicina | code | BMED4757 | Biofluid Mechanics | BMED 4757 | Biofluid Mechanics | code | — |
| 15548 | 15548 | Ingeniería de Control | code | BMED4739 | Medical Robotics | BMED 4739 | Medical Robotics | code | 595 |
| 15548 | 15548 | Ingeniería de Control | code | ME4452 | Control of Dynamic Systems | ME 4452 | Control of Dynamic Systems | code | 595 |
| 15549 | 15549 | Robótica | code | BMED4739 | Medical Robotics | BMED 4739 | Medical Robotics | code | — |
| 15549 | 15549 | Robótica | code | BMED6739 | Medical Robotics | BMED 6739 | Medical Robotics | code | — |
| 15550 | 15550 | Instrumentación de Medida | code | BMED3500 | Sensors& Instrumentation | BMED 3500 | Biomedical Sensors and Instrumentation | code | — |
| 15553 | 15553 | Introducción a los Biomateriales | code | BMED4751 | Intro to Biomaterials | BMED 4751 | Introduction to Biomaterials | code | — |
| 15553 | 15553 | Introducción a los Biomateriales | code | MSE4335 | Soft Nano & Bio Materials | MSE 4335 | Soft Nano and Bio Materials | code | — |
| 15553 | 15553 | Introducción a los Biomateriales | code | MSE4751 | Introduction to Biomaterials | MSE 4751 | Introduction to Biomaterials | code | — |
| 15554 | 15554 | Introducción al diseño de Instrumentación médica | code | BMED2310 | Introduction to Biomedical Engineering Design | BMED 2310 | Intro to Biomedical Engineering Design | code | — |
| 15554 | 15554 | Introducción al diseño de Instrumentación médica | code | BMED4781 | Biomed Instrumentation | BMED 4781 | Biomedical Instrumentation | code | — |
| 15555 | 15555 | Fundamentos de ingeniería de tejidos y medicina regenerativa | code | BMED6794 | Tissue Engineering | BMED 6794 | Tissue Engineering | code | — |
| 15555 | 15555 | Fundamentos de ingeniería de tejidos y medicina regenerativa | code | ME6794 | Tissue Engineering | ME 6794 | Tissue Engineering | code | — |
| 16432 | 16432 | Bioética | code | PHIL3127 | Science, Technology and Human Values | PHIL 3127 | Science, Technology, and Human Values | code | — |
| 19896 | 19896 | Fundamentos de gestión empresarial | code | BMED4602 | Capstone design | BMED 4602 | Capstone Design | code | 1570 |
| 19896 | 19896 | Fundamentos de gestión empresarial | code | ME6753 | Principles of Management for Engineering | ME 6753 | Principles of Management for Engineers | code | — |
| 19897 | 19897 | Proyectos e innovación en Bioingeniería | code | BMED4602 | Capstone design | BMED 4602 | Capstone Design | code | 1570 |

## Vistazo de 10 enlaces

Alias y nombre primero: son los que no salen de una coincidencia de código.
La lectura está en `notebooks/02_enlace_gatech.ipynb`.

| id | Grado | Código histórico | Nombre histórico | Código catálogo | Nombre catálogo | Método |
|---|---|---|---|---|---|---|
| 6533 | Grado en Ingeniería Biomédica | BIOS7210 | Computational Genomics | BIOL 7210 | Computational Genomics | alias |
| 2662 | Grado en Ingeniería Aeroespacial | AE4699ROM | Undergraduate Research | AE 4699 | Undergraduate Research | alias |
| 6544 | Grado en Ingeniería Física | PHYS3211 | Electronics I | PHYS 3209 | Electronics I | name |
| 9529 | Grado en Ingeniería Física | BMED3250 | Biomedical systems and modeling | BMED 3520 | Biomedical Systems and Modeling | name |
| 2677 | Grado en Ingeniería Biomédica | BMED3100 | Systems Physiology | BMED 3100 | Systems Physiology | code |
| 2678 | Grado en Ingeniería Biomédica | BIOS3755 | Human Physiology | BIOS 3755 | Human Physiology | code |
| 2679 | Grado en Ingeniería Biomédica | BMED3211 | Introduction to Bioinformatics | BMED 3211 | Introduction to Bioinformatics | code |
| 2680 | Grado en Ingeniería Biomédica | MSE2001 | Prin&Appl-Engr Materials | MSE 2001 | Principles and Applications of Engineering Materials | code |
| 2681 | Grado en Ingeniería Biomédica | BMED3310 | Biotransport | BMED 3310 | Biotransport | code |
| 2682 | Grado en Ingeniería Biomédica | BMED4739 | Medical Robotics | BMED 4739 | Medical Robotics | code |
