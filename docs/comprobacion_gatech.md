# Comprobación del catálogo de Georgia Tech (issue #5)

Catálogo 2026-2027, cargado el 21/10/2026 con `python -m src.scrapers.destination --uni gatech`.

## Qué hay en `dest_subjects`

| Departamento | Asignaturas |
|---|---|
| BMED | 116 |
| BIOS | 92 |
| ME | 192 |
| MSE | 100 |
| PHIL | 25 |
| MATH | 126 |
| BIOL | 31 |
| **Total** | **682** (40 con créditos variables, sin ECTS) |

Ningún título se quedó sin leer. Se descartan los comodines (`1XXX`), las de 0 créditos y las de
nivel 8000 o más (investigación y tesis).

**Pares del histórico Georgia Tech × Ingeniería Biomédica encontrados por código:** 49 de 50
(sección 6 de `notebooks/01_eda_historical.ipynb`). El que falta, `BIOS 7210 Computational
Genomics`, es la misma asignatura que `BIOL 7210`, que sí está: el Excel la trae con los dos
prefijos. El enlace por nombre de la semana 4 lo resolverá.

## 10 asignaturas comprobadas a mano

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
