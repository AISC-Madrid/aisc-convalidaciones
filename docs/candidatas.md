# Universidades candidatas para el piloto

Conclusión de las 6 universidades con más pares en los Excel de convalidaciones. Catálogos revisados el 12/10/2026; datos del notebook `01_eda_historical.ipynb`. 

- "HTML estático" = las descripciones aparecen en el HTML que devuelve la página sin ejecutar JavaScript 
- "SPA" = la página es un cascarón que carga el contenido con JavaScript.

| # | Universidad | Pares | % n:m | % sin código destino | Descripciones | Web | Idioma | Veredicto |
|---|---|---|---|---|---|---|---|---|
| 1 | University of California | 1.498 | 64,0 | 0,0 | Sí (según campus) | Mixta: Berkeley SPA, UCI estático | Inglés | Descartada: campus sin identificar y n:m más alto |
| 2 | Baruch College (CUNY) | 460 | 52,4 | 0,0 | Sí | Probable SPA (Coursedog) | Inglés | Dudosa |
| 3 | Purdue University | 361 | 29,7 | 0,0 | Sí (2014 en adelante) | Por confirmar | Inglés | Candidata si el catálogo es estático |
| 4 | Universidad Torcuato Di Tella | 280 | 38,5 | 5,7 | No verificado por materia | HTML estático | Español (algunos cursos en inglés) | Plan B |
| 5 | Georgia Institute of Technology | 276 | 32,2 | 0,0 | Sí | HTML estático | Inglés | **Recomendada** |
| 6 | University of Maryland | 272 | 35,0 | 0,0 | Sí | HTML estático | Inglés | Segunda opción |

Cómo leer las cifras:
- "pares" son los pares deduplicados entre cursos (grado × asignatura UC3M × asignatura destino). 
- "% n:m" es el porcentaje de asignaturas UC3M que aparecen relacionadas con varias del destino, lo que dificulta el emparejamiento automático. 
- Los pares repetidos entre cursos se eliminan al deduplicar; un porcentaje alto (Maryland 50,8 %, Purdue 42,7 %) solo indica que el par se mantiene de un año a otro.

## 1. University of California
- **Catálogo:** no hay uno solo, cada campus tiene el suyo. Ejemplos: https://undergraduate.catalog.berkeley.edu/courses (Berkeley) y https://catalogue.uci.edu (Irvine).
- **Descripciones:** sí, en ambos ejemplos.
- **HTML o JS:** depende del campus. Berkeley usa Coursedog (plataforma que carga con JavaScript, por confirmar con F12); el catálogo de Irvine se lee como HTML normal.
- **Créditos y ECTS:** unidades UC, sin equivalencia a ECTS publicada. Cuidado: no todos los campus usan el mismo sistema (trimestres vs semestres), así que la conversión no es única.
- **Idioma:** inglés.
- **Nota:** el nombre "University of California" es un sistema, no una universidad, y el notebook confirma que los datos no dicen el campus. Sus 1.498 pares mezclan varios catálogos y tiene el mayor porcentaje de n:m (64 %).

## 2. Baruch College (CUNY)
- **Catálogo:** https://baruch-undergraduate.catalog.cuny.edu/courses (también hay boletines antiguos en PDF en enrollmentmanagement.baruch.cuny.edu).
- **Descripciones:** sí, cada curso tiene su ficha.
- **HTML o JS:** probable SPA (Coursedog).
- **Créditos y ECTS:** créditos CUNY (normalmente 3 por curso); sin equivalencia a ECTS publicada.
- **Idioma:** inglés.
- **Nota:** el 52 % de n:m hace el emparejamiento más difícil. Los boletines antiguos en PDF sirven de plan B para cursos de años pasados, pero hay que extraer el texto.

## 3. Purdue University
- **Catálogo:** https://catalog.purdue.edu (descripciones de 2014 en adelante; anteriores en https://www.purdue.edu/registrar/legacy/).
- **Descripciones:** sí.
- **HTML o JS:** por confirmar. La portada se lee bien, pero la página con la lista de cursos no devolvió texto. Revisar con F12 antes de decidir.
- **Créditos y ECTS:** credit hours; sin equivalencia a ECTS publicada.
- **Idioma:** inglés.
- **Nota:** tiene los mejores datos del grupo (más pares que Georgia Tech y el menor n:m, 29,7 %). Pero tiene varios campus y en el catálogo antiguo el mismo código aparece repetido por campus.

## 4. Universidad Torcuato Di Tella (UTDT)
- **Catálogo:** no hay catálogo de asignaturas público; la información para intercambio está en https://www.utdt.edu/listado_contenidos.php?id_item_menu=21666 y la oferta de cursos se pide a international@utdt.edu.
- **Descripciones:** no las encontré por asignatura (sí hay planes de estudio en folletos PDF).
- **HTML o JS:** HTML estático (web tradicional).
- **Créditos y ECTS:** es la única que publica una regla de conversión a ECTS, basada en horas totales de trabajo (por ejemplo, un curso de 68 horas de clase equivale a 7,5 ECTS). Fuente: https://www.utdt.edu/listado_contenidos.php?id_item_menu=22755
- **Idioma:** español salvo que se indique lo contrario; ofrecen más de 36 cursos en inglés por semestre.
- **Nota:** es la única de las seis con filas sin código destino (5,7 %), así que el emparejamiento tendría que apoyarse en el nombre de la asignatura.

## 5. Georgia Institute of Technology
- **Catálogo:** https://catalog.gatech.edu/coursesaz/ (una página por departamento, por ejemplo `/coursesaz/cs/`).
- **Descripciones:** sí, título, créditos y descripción de cada curso, incluidos los cursos con crédito excluyente ("no se da crédito por ambos").
- **HTML o JS:** HTML estático. La página se lee completa sin ejecutar JavaScript, así que se puede descargar con `requests` y `BeautifulSoup`.
- **Créditos y ECTS:** credit hours (la normativa define 1 crédito = 1 hora de clase en cursos de teoría); sin equivalencia a ECTS publicada.
- **Idioma:** inglés.
- **Nota:** hay ediciones archivadas en https://catalog.gatech.edu/archived-catalogs/, útil si los pares son de años anteriores. En los datos tiene todos los códigos destino rellenos y un n:m bajo (32,2 %, el segundo mejor).

## 6. University of Maryland
- **Catálogo:** https://academiccatalog.umd.edu/undergraduate/approved-courses/ (College Park, una página por prefijo, por ejemplo `/cmsc/`).
- **Descripciones:** sí, con créditos, prerrequisitos y avisos de "Credit Only Granted for".
- **HTML o JS:** HTML estático. Se lee completo sin ejecutar JavaScript.
- **Créditos y ECTS:** credits; sin equivalencia a ECTS publicada.
- **Idioma:** inglés.
- **Nota:** "University of Maryland" también puede ser Baltimore (catálogo aparte, en smartcatalogiq) o la Global Campus. Hay que comprobar en el dato que se refiere a College Park, por ejemplo mirando los prefijos de los códigos destino (`CMSC`, `BMGT`…).

## Recomendación

**Piloto: Georgia Tech.** Reúne las tres condiciones del criterio: 276 pares con todos los códigos destino rellenos y un n:m bajo (32,2 %), un catálogo oficial único en HTML estático con descripciones y créditos, y la documentación en inglés. No es la que más pares tiene, pero es la que menos riesgo técnico tiene.

Segunda opción: **Purdue**, si se confirma que su catálogo se puede leer sin JavaScript. Tiene más pares (361) y el n:m más bajo (29,7 %), pero el catálogo está sin confirmar y tiene varios campus. Si no es estático, la segunda opción pasa a ser **Maryland College Park** (272 pares, n:m 35,0 %, catálogo estático), siempre que el dato confirme ese campus.

Por qué no las demás:
- **UC** tiene muchos pares, pero mezcla campus sin identificar, el n:m más alto (64 %) y catálogos distintos por campus.
- **Baruch** tiene un n:m del 52 % y parece una SPA, así que habría que usar un navegador automatizado o sus PDFs.
- **UTDT** es interesante por su regla de ECTS y por estar en español, pero no tiene catálogo de asignaturas público y es la única con códigos destino vacíos (5,7 %).

## Pendiente de verificar
- Confirmar con F12 (pestaña Network/XHR) si Purdue, Baruch y Berkeley cargan los cursos con JavaScript. Es lo que decide la segunda opción.
- Confirmar que "University of Maryland" es College Park mirando los códigos destino.
- Ninguna de las seis publica equivalencia a ECTS en el catálogo salvo UTDT; si se necesita, habrá que definir una regla propia (conviene validarla con la oficina de relaciones internacionales).
- El n:m del notebook son relaciones múltiples posibles, no equivalencias conjuntas confirmadas.