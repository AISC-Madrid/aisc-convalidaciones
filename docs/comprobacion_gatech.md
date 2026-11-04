# Comprobación del catálogo de Georgia Tech (issues #5 y #24)

Catálogo 2026-2027, cargado con `python -m src.scrapers.destination --uni gatech`: los 7
departamentos de Biomédica el 21/10/2026 (#5) y el catálogo completo el 26/10/2026 (#24). Está en
la release `uc3m-2026-10-28-semana3`.

## Qué hay en `dest_subjects`

Los departamentos son los prefijos de los 276 pares de Georgia Tech del histórico, de todos los
grados (sección 7 de `notebooks/01_eda_historical.ipynb`).

| Departamento | Asignaturas | Sin ECTS (créditos variables) | Sin descripción |
|---|---|---|---|
| BMED | 116 | 7 | 7 |
| BIOS | 92 | 7 | 0 |
| ME | 192 | 8 | 5 |
| MSE | 100 | 5 | 2 |
| PHIL | 25 | 5 | 2 |
| MATH | 126 | 7 | 2 |
| BIOL | 31 | 1 | 1 |
| AE | 123 | 6 | 2 |
| CEE | 186 | 8 | 7 |
| COE | 9 | 0 | 2 |
| CS | 272 | 12 | 8 |
| EAS | 117 | 10 | 9 |
| ECE | 270 | 18 | 30 |
| ECON | 104 | 6 | 1 |
| HTS | 142 | 12 | 2 |
| ISYE | 139 | 5 | 0 |
| MGT | 265 | 10 | 0 |
| PHYS | 105 | 7 | 1 |
| **Total** | **2.414** | **134** | **81** |

Ningún título se quedó sin leer. Se descartan los comodines (`1XXX`), las de 0 créditos y las de
nivel 8000 o más (investigación y tesis). Las 81 sin descripción tampoco la tienen en el catálogo
web.

Si un departamento no se puede descargar, el scraper sigue con el resto, pero al final lista los
que faltan y termina con error: así no se publica sin querer un catálogo incompleto.

**Pares del histórico Georgia Tech encontrados por código:** 263 de 276. Los 13 restantes son
7 códigos: `AE 4699 ROM` (3 filas; el Excel añade el sufijo `ROM`, y `AE 4699` sí está) y
`PHYS 3211`, `PHYS 3225`, `BMED 3250`, `CS 4320`, `CS 4560` y `BIOS 7210` (10 filas), que no
están en el catálogo 2026-27. `BIOS 7210` es la misma asignatura que `BIOL 7210`. El enlace de la
semana 4 (`src/loaders/link_catalog.py`) resuelve los alias y prueba por nombre.

## 10 asignaturas comprobadas a mano (semana 2, departamentos de Biomédica)

Se comparó la BD con la página pública `catalog.gatech.edu/coursesaz/<prefijo>/` (21/10/2026):
código, nombre, créditos (ECTS = créditos × 2) y comienzo de la descripción.

| Código | Nombre | Créditos web | ECTS en BD | ¿Coincide? |
|---|---|---|---|---|
| BMED 2110 | Conservation Principles in Biomedical Engineering | 3 | 6 | Sí |
| BMED 3110 | Quantitative Engineering Physiology Laboratory I | 2 | 4 | Sí |
| BMED 3600 | Physiology of Cellular and Molecular Systems | 3 | 6 | Sí |
| BMED 4757 | Biofluid Mechanics | 3 | 6 | Sí |
| BMED 6780 | Medical Image Processing | 3 | 6 | Sí |
| MATH 2551 | Multivariable Calculus | 4 | 8 | Sí |
| MATH 3670 | Probability and Statistics with Applications | 3 | 6 | Sí |
| MSE 2001 | Principles and Applications of Engineering Materials | 3 | 6 | Sí |
| BIOS 4150 | Genomics and Applied Bioinformatics | 3 | 6 | Sí |
| PHIL 3109 | Engineering Ethics | 3 | 6 | Sí |

## 10 asignaturas más comprobadas (semana 3, departamentos nuevos)

Sorteo reproducible (`random.Random(31)`): 5 de los 11 departamentos nuevos y 2 asignaturas de
cada uno. Se comparó la BD de `uc3m-2026-10-28-semana3` con la página pública
`catalog.gatech.edu/coursesaz/<prefijo>/` (04/11/2026): código, nombre, créditos
(ECTS = créditos × 2) y descripción completa.

| Código | Nombre | Créditos web | ECTS en BD | Descripción | ¿Coincide? |
|---|---|---|---|---|---|
| AE 2221 | 3D Dynamics | 1 | 2 | Igual | Sí |
| AE 6373 | Advanced Design Methods I | 4 | 8 | Igual | Sí |
| CEE 4115 | Construction Scheduling | 3 | 6 | Igual | Sí |
| CEE 4170 | Construction Law | 3 | 6 | Igual | Sí |
| ECON 4232 | Labor Economics | 3 | 6 | Igual | Sí |
| ECON 6140 | Econometrics I | 3 | 6 | Igual | Sí |
| HTS 2803 | Special Topics | 3 | 6 | Igual | Sí |
| HTS 2823 | Special Topics | 3 | 6 | Igual | Sí |
| ISYE 3030 | Basic Statistical Methods | 3 | 6 | Igual | Sí |
| ISYE 3232 | Stochastic Manufacturing and Service Systems | 3 | 6 | Igual | Sí |

## Factor de créditos: 1 credit hour = 2 ECTS

- **UC3M:** en el doble título con Stevens usa "6 ECTS = 3 horas crédito estadounidenses"
  (https://www.uc3m.es/master/finanzas).
- **Histórico:** en los pares Georgia Tech × Biomédica, la mediana de ECTS UC3M / créditos GT es
  2,0. 39 pares son 6 ECTS ↔ 3 créditos, 16 son 3 ECTS ↔ 3 créditos (asignaturas UC3M pequeñas
  convalidadas por un curso entero) y 3 son 6 ECTS ↔ laboratorios de 1 crédito (n:m).
- **Georgia Tech** usa 1 crédito GT = 1,4 ECTS para *sus* alumnos que vuelven de Europa
  (https://ea.oie.gatech.edu/exchange-credit-transfer-instructions). Es la regla en el sentido
  contrario y no la aplica la UC3M, así que no se usa.

El factor solo sirve para el aviso de ECTS dispares; quien decide es el tutor.
