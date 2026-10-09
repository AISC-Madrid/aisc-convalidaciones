"""Parser de las fichas de asignatura de la UC3M (``/cpa/generaFicha``).

Convierte el HTML estático de una ficha (en español o inglés) en un diccionario con los
campos que usa el proyecto. No hace peticiones de red: sólo analiza el HTML recibido.
"""

from __future__ import annotations

import html as html_lib
import re
import unicodedata

from bs4 import BeautifulSoup, NavigableString, Tag

CODIFICACION_POR_DEFECTO = "iso-8859-1"

# Etiquetas de cabecera (normalizadas, sin ":"), en español e inglés.
ETIQUETAS: dict[str, tuple[str, ...]] = {
    "fecha_actualizacion": ("ultima actualizacion", "checking date"),
    "coordinador": ("coordinador/a", "coordinador", "coordinating teacher"),
    "departamento": ("departamento asignado a la asignatura", "department assigned to the subject"),
    "tipo": ("tipo", "type"),
    "creditos": ("creditos", "ects credits", "credits"),
    "curso": ("curso", "course"),
    "cuatrimestre": ("cuatrimestre", "semester"),
    "rama": ("rama de conocimiento", "branch of knowledge"),
}

# Prefijos de los títulos de sección (normalizados), en español e inglés.
SECCIONES: dict[str, tuple[str, ...]] = {
    "requisitos": ("requisitos", "requirements"),
    "objetivos": ("objetivos", "objectives"),
    "resultados": ("resultados del proceso", "learning outcomes"),
    "programa": ("descripcion de contenidos", "description of contents"),
    "bibliografia_basica": ("bibliografia basica", "basic bibliography"),
}

# Palabras (normalizadas) que delatan el idioma de la ficha.
_MARCAS_ES = (
    "ultima actualizacion",
    "coordinador/a",
    "departamento asignado a la asignatura",
    "tipo",
    "creditos",
    "cuatrimestre",
    "objetivos",
    "descripcion de contenidos",
    "sistema de evaluacion",
    "bibliografia basica",
    "curso academico",
)
_MARCAS_EN = (
    "checking date",
    "coordinating teacher",
    "department assigned to the subject",
    "type",
    "ects credits",
    "semester",
    "objectives",
    "description of contents",
    "assessment system",
    "basic bibliography",
)

_TIPOS: dict[str, str] = {
    "formacion basica": "FB",
    "basic core": "FB",
    "obligatoria": "OB",
    "compulsory": "OB",
    "optativa": "OP",
    "electives": "OP",
    "elective": "OP",
    "cursos de humanidades": "HUM",
    "courses of humanities": "HUM",
}

_RE_CHARSET = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9_\-:.]+)""", re.I)
_RE_CODIGO = re.compile(r"^\(\s*(\d+)\s*\)$")
_RE_PLAN = re.compile(r"\(\s*Plan:\s*(\d+)\s*-\s*Estudio:\s*(\d+)\s*\)", re.I)
_RE_CURSO_ACADEMICO = re.compile(r"(\d{4})\s*/\s*(\d{4})")
_RE_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")
_RE_ENTERO = re.compile(r"\d+")
_RE_ENTIDAD = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|[A-Za-z]+\d*);")


def normalizar_titulo(texto: str) -> str:
    """Pasa a minúsculas, quita acentos, ":" final y espacios sobrantes."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    limpio = re.sub(r"\s+", " ", sin_acentos).strip().lower()
    return limpio.rstrip(":").strip()


def _decodificar(contenido: bytes) -> str:
    """Decodifica con el charset declarado; si falla, UTF-8 y por último ISO-8859-1."""
    candidatas: list[str] = []
    declarado = _RE_CHARSET.search(contenido[:8192])
    if declarado:
        candidatas.append(declarado.group(1).decode("ascii", "ignore"))
    candidatas += ["utf-8", CODIFICACION_POR_DEFECTO]
    for codificacion in candidatas:
        try:
            return contenido.decode(codificacion)
        except (UnicodeDecodeError, LookupError):
            continue
    return contenido.decode(CODIFICACION_POR_DEFECTO, errors="replace")


def _limpiar_texto(texto: str | None) -> str | None:
    """Colapsa espacios dentro de cada línea, conserva saltos de párrafo y recorta."""
    if texto is None:
        return None
    if _RE_ENTIDAD.search(texto):
        texto = html_lib.unescape(texto)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    lineas = [re.sub(r"[^\S\n]+", " ", linea).strip() for linea in texto.split("\n")]
    resultado: list[str] = []
    for linea in lineas:
        if linea or (resultado and resultado[-1]):
            resultado.append(linea)
    limpio = "\n".join(resultado).strip()
    return limpio or None


def _valor_etiqueta(strong: Tag) -> str:
    """Texto que sigue a ``<strong>Etiqueta:</strong>`` hasta la siguiente etiqueta."""
    partes: list[str] = []
    for hermano in strong.next_siblings:
        if isinstance(hermano, Tag) and hermano.name == "strong":
            break
        if isinstance(hermano, NavigableString):
            partes.append(str(hermano))
        elif isinstance(hermano, Tag):
            partes.append(hermano.get_text(" "))
    return re.sub(r"\s+", " ", "".join(partes)).strip()


def _cabecera(soup: BeautifulSoup) -> tuple[dict[str, str], list[str]]:
    """Devuelve los valores de cabecera por campo y las etiquetas normalizadas vistas."""
    valores: dict[str, str] = {}
    vistas: list[str] = []
    for strong in soup.find_all("strong"):
        etiqueta = normalizar_titulo(strong.get_text(" "))
        if not etiqueta:
            continue
        vistas.append(etiqueta)
        for campo, alias in ETIQUETAS.items():
            if etiqueta in alias and campo not in valores:
                valores[campo] = _valor_etiqueta(strong)
                break
    return valores, vistas


def _texto_seccion(cuerpo: Tag) -> str | None:
    """Extrae el texto de un ``div.panel-body`` (``div.tarea``, ``textarea`` o listas)."""
    bloques: list[str] = []
    for elemento in cuerpo.find_all(["div", "textarea", "ul", "ol", "p"]):
        if elemento.name == "div" and "tarea" not in (elemento.get("class") or []):
            continue
        if elemento.find_parent(["ul", "ol", "textarea"]) is not None:
            continue
        if elemento.name == "div" and elemento.find_parent("div", class_="tarea"):
            continue
        if elemento.name in ("ul", "ol"):
            texto = "\n".join(li.get_text(" ") for li in elemento.find_all("li"))
        else:
            texto = elemento.get_text()
        limpio = _limpiar_texto(texto)
        if limpio:
            bloques.append(limpio)
    return "\n\n".join(bloques) if bloques else None


def _secciones(soup: BeautifulSoup) -> tuple[dict[str, str | None], list[str]]:
    """Devuelve el texto de las secciones conocidas y los títulos normalizados vistos."""
    textos: dict[str, str | None] = {}
    titulos: list[str] = []
    for panel in soup.select("div.panel.apartado"):
        cabecera = panel.select_one("div.panel-heading")
        if cabecera is None:
            continue
        titulo = normalizar_titulo(cabecera.get_text(" "))
        titulos.append(titulo)
        cuerpo = panel.select_one("div.panel-body") or panel
        for campo, prefijos in SECCIONES.items():
            if campo not in textos and titulo.startswith(prefijos):
                textos[campo] = _texto_seccion(cuerpo)
                break
    return textos, titulos


def _detectar_idioma(textos: list[str]) -> str:
    """Devuelve "EN" si predominan las etiquetas/títulos en inglés; si no, "ES"."""
    puntos_es = sum(1 for t in textos if any(t.startswith(m) for m in _MARCAS_ES))
    puntos_en = sum(1 for t in textos if any(t.startswith(m) for m in _MARCAS_EN))
    return "EN" if puntos_en > puntos_es else "ES"


def _a_float(texto: str | None) -> float | None:
    if not texto:
        return None
    encontrado = _RE_NUMERO.search(texto)
    return float(encontrado.group(0).replace(",", ".")) if encontrado else None


def _a_int(texto: str | None) -> int | None:
    if not texto:
        return None
    encontrado = _RE_ENTERO.search(texto)
    return int(encontrado.group(0)) if encontrado else None


def _normalizar_tipo(texto: str | None) -> str | None:
    if not texto:
        return None
    return _TIPOS.get(normalizar_titulo(texto), texto)


def _o_none(texto: str | None) -> str | None:
    return texto if texto else None


def parse_ficha(html: bytes | str) -> dict:
    """Analiza una ficha de asignatura de la UC3M y devuelve sus campos.

    Lanza ``ValueError`` sólo si el HTML no contiene código de asignatura (no es una ficha).
    Las partes opcionales ausentes se devuelven como ``None``.
    """
    texto_html = _decodificar(html) if isinstance(html, bytes) else html
    soup = BeautifulSoup(texto_html, "html.parser")

    codigo: str | None = None
    nombre: str | None = None
    for div in soup.select("div.asignatura"):
        contenido = re.sub(r"\s+", " ", div.get_text(" ")).strip()
        coincidencia = _RE_CODIGO.match(contenido)
        if coincidencia and codigo is None:
            codigo = coincidencia.group(1)
        elif contenido and nombre is None:
            nombre = contenido
    if codigo is None:
        raise ValueError("El HTML no parece una ficha de asignatura de la UC3M: falta el código")

    texto_plano = soup.get_text(" ")
    plan_estudio = _RE_PLAN.search(texto_plano)

    curso_academico: str | None = None
    anio = soup.select_one("div.anio")
    if anio is not None:
        coincidencia = _RE_CURSO_ACADEMICO.search(anio.get_text(" "))
        if coincidencia:
            curso_academico = f"{coincidencia.group(1)}/{coincidencia.group(2)}"

    cabecera, etiquetas = _cabecera(soup)
    secciones, titulos = _secciones(soup)

    return {
        "codigo": codigo,
        "nombre": nombre or "",
        "plan": plan_estudio.group(1) if plan_estudio else None,
        "estudio": plan_estudio.group(2) if plan_estudio else None,
        "curso_academico": curso_academico,
        "tipo": _normalizar_tipo(cabecera.get("tipo")),
        "creditos": _a_float(cabecera.get("creditos")),
        "curso": _a_int(cabecera.get("curso")),
        "cuatrimestre": _a_int(cabecera.get("cuatrimestre")),
        "coordinador": _o_none(cabecera.get("coordinador")),
        "departamento": _o_none(cabecera.get("departamento")),
        "rama": _o_none(cabecera.get("rama")),
        "requisitos": secciones.get("requisitos"),
        "objetivos": secciones.get("objetivos"),
        "resultados": secciones.get("resultados"),
        "programa": secciones.get("programa"),
        "bibliografia_basica": secciones.get("bibliografia_basica"),
        "idioma": _detectar_idioma(etiquetas + titulos),
        "fecha_actualizacion": _o_none(cabecera.get("fecha_actualizacion")),
    }
