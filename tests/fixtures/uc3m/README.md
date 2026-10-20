# Fixtures de fichas UC3M

**Las fichas HTML no se suben al repo** (contienen los temarios completos de la UC3M) y están en
`.gitignore`. Para tenerlas en local y que corran todos los tests:

```bash
python -m src.sync.datos descargar --paquete fixtures   # del repo privado de datos
python tests/fixtures/uc3m/descargar.py                 # o directamente de la UC3M
```

Sin ellas, solo se saltan (`skipped`) los tests de `test_uc3m_parser.py` que leen fichas reales.
Lo demás corre siempre, también en la CI:

- `sinteticas/`: 5 fichas **inventadas** (códigos 10001-10003, planes 900 y 901) con la misma
  estructura HTML que las reales: completa en ES y EN, sin objetivos, de Humanidades sin curso ni
  cuatrimestre y de un curso anterior con una sección vacía. Las usan
  `test_uc3m_parser_sintetico.py` y la carga de principio a fin (`test_uc3m_carga.py`). Sí se suben.
- `respuestas/sin_ficha.html`: la página real que devuelve `generaFicha` (HTTP 200) cuando no hay
  ficha para ese plan, año e idioma ("Error al generar la ficha"), sin `jsessionid` ni Google Tag
  Manager. No tiene temario. Sí se sube.
- Los JSON de esta carpeta (solo códigos y nombres), para los tests del cliente.

Fichas HTML de `generaFicha` guardadas tal cual se descargaron (bytes sin re-codificar).
Aunque se esperaba ISO-8859-1, el servidor las sirve en UTF-8 (`Content-Type: text/html;charset=utf-8`
y dos `<meta ... charset=UTF-8>`); parte de los acentos vienen como entidades HTML (`&Aacute;`).
Descargadas en octubre de 2026 con User-Agent `aisc-convalidaciones/0.1` y 1,5 s entre peticiones.

Base: `https://aplicaciones.uc3m.es/cpa/generaFicha` (`idioma=1` ES, `idioma=2` EN).

| Fichero | Asignatura | URL |
|---|---|---|
| `15363_2026_ES.html` | Álgebra Lineal (FB) | `?est=371&plan=456&asig=15363&anio=2026&idioma=1` |
| `15363_2026_EN.html` | Linear Algebra (FB) | `?est=371&plan=456&asig=15363&anio=2026&idioma=2` |
| `15363_2024_ES.html` | Álgebra Lineal, curso 2024/2025 | `?est=371&plan=456&asig=15363&anio=2024&idioma=1` |
| `13881_2026_ES.html` | Ficheros y bases de datos (OB, Grado Ing. Informática) | `?est=218&plan=489&asig=13881&anio=2026&idioma=1` |
| `13881_2026_EN.html` | Files and data bases | `?est=218&plan=489&asig=13881&anio=2026&idioma=2` |
| `17631_2026_ES.html` | Fundamentos de producción de software para negocios digitales (OB) | `?est=351&plan=486&asig=17631&anio=2026&idioma=1` |
| `17631_2026_EN.html` | Fundamentals of Software Production for Digital Business | `?est=351&plan=486&asig=17631&anio=2026&idioma=2` |
| `11692_2026_ES.html` | ¿Qué significa todo esto? Una introducción a la filosofía (Cursos de Humanidades) | `?est=371&plan=456&asig=11692&anio=2026&idioma=1` |
| `11692_2026_EN.html` | What does it all mean? An introduction to philosophy | `?est=371&plan=456&asig=11692&anio=2026&idioma=2` |
| `13565_2026_ES.html` | Constitución y sistema de fuentes (FB, Grado en Derecho) | `?est=206&plan=557&asig=13565&anio=2026&idioma=1` |
| `13565_2026_EN.html` | Constitucion and sources of law system | `?est=206&plan=557&asig=13565&anio=2026&idioma=2` |

Notas:

- 13881 y 17631 no pertenecen al plan 456: con `est=371&plan=456` el servidor devuelve una
  página vacía de ~2,8 KB sin ficha. Sus planes se localizaron con `findAsignaturas.ajax`.
- 13881 y 17631 no tienen sección "Objetivos"; 17631 tampoco "Resultados".
- 11692 sí tiene "Objetivos", declara 3.0 ECTS y deja vacío el cuatrimestre.
- En `15363_2024_ES.html` la sección "Resultados…" existe pero su `<textarea>` está vacío.
