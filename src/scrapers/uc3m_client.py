"""Cliente HTTP para la API pública de la UC3M (aplicaciones.uc3m.es/cpa).

Expone los endpoints JSON (años, planes, asignaturas de un plan) y la descarga de
las fichas de asignatura (HTML estático en ISO-8859-1), con pausa entre
peticiones, reintentos con backoff y caché en disco de las fichas.

Las fichas se tratan siempre como ``bytes``: nunca se decodifican aquí.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://aplicaciones.uc3m.es/cpa"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "uc3m"
PAUSA_SEGUNDOS = 1.5
USER_AGENT = "aisc-convalidaciones/0.1 (+https://github.com/AISC-Madrid/aisc-convalidaciones)"
TIMEOUT_SEGUNDOS = 30

IDIOMAS = {"ES": 1, "EN": 2}


class ErrorAPIUC3M(RuntimeError):
    """La API de la UC3M respondió con un error o un formato inesperado."""


@dataclass(frozen=True)
class Plan:
    codigo: int
    nombre: str
    estudio: int
    es_grado: bool
    activo: bool


@dataclass(frozen=True)
class AsignaturaPlan:
    codigo: int
    nombre: str
    nombre_en: str | None
    plan: int
    estudio: int


def url_ficha(est: int, plan: int, asig: int, anio: int, idioma: str) -> str:
    """Construye la URL de la ficha de una asignatura (idioma "ES" o "EN")."""
    try:
        codigo_idioma = IDIOMAS[idioma]
    except KeyError:
        raise ValueError(f"Idioma no soportado: {idioma!r} (usa 'ES' o 'EN')") from None
    params = {"est": est, "plan": plan, "asig": asig, "anio": anio, "idioma": codigo_idioma}
    return f"{BASE_URL}/generaFicha?{urlencode(params)}"


def _es_reintentable(status: int) -> bool:
    return status == 429 or status >= 500


class ClienteUC3M:
    """Cliente educado (pausas, reintentos, caché) para la API de la UC3M."""

    def __init__(
        self,
        cache_dir: Path = CACHE_DIR,
        pausa: float = PAUSA_SEGUNDOS,
        session: requests.Session | None = None,
        reintentos: int = 3,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.pausa = pausa
        self.reintentos = max(1, reintentos)
        self.peticiones = 0
        if session is None:
            session = requests.Session()
            session.headers.update({"User-Agent": USER_AGENT})
        self.session = session

    # ------------------------------------------------------------------ HTTP

    def _peticion(self, metodo: str, url: str, **kwargs: Any) -> requests.Response:
        """Hace una petición con pausa previa y reintentos con backoff creciente."""
        kwargs.setdefault("timeout", TIMEOUT_SEGUNDOS)
        ultimo_error: Exception | None = None
        for intento in range(1, self.reintentos + 1):
            time.sleep(self.pausa)
            self.peticiones += 1
            try:
                if metodo == "POST":
                    respuesta = self.session.post(url, **kwargs)
                else:
                    respuesta = self.session.get(url, **kwargs)
            except requests.RequestException as error:
                ultimo_error = error
                logger.warning("Error de red en %s (intento %d): %s", url, intento, error)
            else:
                status = respuesta.status_code
                if not _es_reintentable(status):
                    respuesta.raise_for_status()
                    return respuesta
                ultimo_error = requests.HTTPError(f"HTTP {status} en {url}", response=respuesta)
                if status == 429:
                    self.pausa = max(self.pausa * 2, 1.0)
                    logger.warning("HTTP 429 en %s: subo la pausa a %.1f s", url, self.pausa)
                else:
                    logger.warning("HTTP %d en %s (intento %d)", status, url, intento)
            if intento < self.reintentos:
                time.sleep(self.pausa * intento)
        raise ErrorAPIUC3M(
            f"Fallo tras {self.reintentos} intentos en {url}: {ultimo_error}"
        ) from ultimo_error

    def _post_json(self, endpoint: str, data: dict[str, Any] | None = None) -> Any:
        url = f"{BASE_URL}/{endpoint}"
        respuesta = self._peticion("POST", url, data=data or {})
        try:
            cuerpo = json.loads(respuesta.content)
        except ValueError as error:
            raise ErrorAPIUC3M(f"Respuesta no JSON en {url}") from error
        if not isinstance(cuerpo, dict) or cuerpo.get("ok") != "S":
            raise ErrorAPIUC3M(f"La API respondió con error en {url}: {str(cuerpo)[:200]}")
        return cuerpo.get("datos")

    # ------------------------------------------------------------ Endpoints

    def listar_anos(self) -> list[int]:
        """Años académicos disponibles (p. ej. [2026, 2025, ...])."""
        return [int(ano) for ano in self._post_json("findAnos.ajax") or []]

    def listar_planes(self, solo_grados_activos: bool = True) -> list[Plan]:
        """Planes de estudio; por defecto solo los grados activos."""
        planes = []
        for bruto in self._post_json("findPlanes.ajax") or []:
            tipo = (bruto.get("tipoEstudio") or {}).get("denominacion")
            estudio = (bruto.get("estudio") or {}).get("codigo")
            plan = Plan(
                codigo=int(bruto["codigo"]),
                nombre=(bruto.get("nombre") or "").strip(),
                estudio=int(estudio) if estudio is not None else 0,
                es_grado=tipo == "Grado",
                activo=bruto.get("activado") == "A" and not bruto.get("baja", False),
            )
            if solo_grados_activos and not (plan.es_grado and plan.activo):
                continue
            planes.append(plan)
        logger.info(
            "Planes obtenidos: %d (solo_grados_activos=%s)", len(planes), solo_grados_activos
        )
        return planes

    def listar_asignaturas(self, plan: int, ano: int) -> list[AsignaturaPlan]:
        """Asignaturas de un plan en un año académico."""
        datos = self._post_json("findAsignaturas.ajax", {"codPlan": plan, "ano": ano}) or []
        asignaturas = []
        for bruto in datos:
            estudio = ((bruto.get("plan") or {}).get("estudio") or {}).get("codigo")
            nombre_en = (bruto.get("denominacionEng") or "").strip() or None
            asignaturas.append(
                AsignaturaPlan(
                    codigo=int(bruto["codigo"]),
                    nombre=(bruto.get("denominacion") or "").strip(),
                    nombre_en=nombre_en,
                    plan=plan,
                    estudio=int(estudio) if estudio is not None else 0,
                )
            )
        logger.info("Plan %s, año %s: %d asignaturas", plan, ano, len(asignaturas))
        return asignaturas

    # --------------------------------------------------------------- Fichas

    def url_ficha(self, est: int, plan: int, asig: int, anio: int, idioma: str) -> str:
        return url_ficha(est, plan, asig, anio, idioma)

    def ruta_cache(self, asig: int, anio: int, idioma: str) -> Path:
        return self.cache_dir / str(anio) / f"{asig}_{idioma}.html"

    def descargar_ficha(self, est: int, plan: int, asig: int, anio: int, idioma: str) -> bytes:
        """Devuelve los bytes de la ficha, desde caché si existe o descargándola."""
        url = url_ficha(est, plan, asig, anio, idioma)
        ruta = self.ruta_cache(asig, anio, idioma)
        if ruta.is_file() and ruta.stat().st_size > 0:
            logger.debug("Ficha en caché: %s", ruta)
            return ruta.read_bytes()

        contenido = self._peticion("GET", url).content
        ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = ruta.with_name(ruta.name + ".tmp")
        temporal.write_bytes(contenido)
        temporal.replace(ruta)
        logger.info(
            "Ficha descargada: asig=%s anio=%s idioma=%s (%d bytes)",
            asig,
            anio,
            idioma,
            len(contenido),
        )
        return contenido
