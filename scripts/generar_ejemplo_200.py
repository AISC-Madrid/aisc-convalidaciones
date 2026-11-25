"""Genera public/data/ejemplo_200.json: 200 resultados INVENTADOS para probar la web.

Sirve para ver la pantalla de resultados con el volumen del dato real antes de tenerlo: 
paginación, filtros, nombres muy largos en la tabla y en el PDF y varios
grupos n:m. Se sustituye por el JSON real del export más adelante (misma combinación en
index.json, otro archivo).

Uso, desde la raíz del repo:
    python scripts/generar_ejemplo_200.py

La semilla es fija: si no cambias el código, el JSON sale idéntico.
"""

import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.models.match import Resultados, ects_dispares  # noqa: E402

SALIDA = RAIZ / "public" / "data" / "ejemplo_200.json"
SEMILLA = 41  # número de la issue
TOTAL_FILAS = 200
UMBRAL = 0.71
URL_DESTINO = "https://catalog.gatech.edu/courses-undergrad/"

# (nombre UC3M, nombre destino, prefijo del código destino)
TEMAS = [
    ("Biología Celular", "Cell and Molecular Biology", "BIOL"),
    ("Bioquímica", "Biochemistry", "CHEM"),
    ("Fisiología Humana", "Human Physiology", "APPH"),
    ("Anatomía", "Human Anatomy", "APPH"),
    ("Biomecánica", "Biomechanics", "BMED"),
    ("Biomateriales", "Biomaterials", "BMED"),
    ("Instrumentación Biomédica", "Biomedical Instrumentation", "BMED"),
    ("Señales Biomédicas", "Biomedical Signal Processing", "BMED"),
    ("Imagen Médica", "Medical Imaging Systems", "BMED"),
    ("Ingeniería de Tejidos", "Tissue Engineering", "BMED"),
    ("Cálculo", "Calculus", "MATH"),
    ("Álgebra Lineal", "Linear Algebra", "MATH"),
    ("Ecuaciones Diferenciales", "Differential Equations", "MATH"),
    ("Estadística", "Statistics and Applications", "ISYE"),
    ("Física", "Physics", "PHYS"),
    ("Programación", "Introduction to Computing", "CS"),
    ("Electrónica", "Circuit Analysis", "ECE"),
    ("Termodinámica", "Thermodynamics", "ME"),
    ("Mecánica de Fluidos", "Fluid Mechanics", "ME"),
    ("Química", "General Chemistry", "CHEM"),
    ("Sistemas de Control", "Control Systems", "ECE"),
    ("Aprendizaje Automático", "Machine Learning", "CS"),
    ("Neuroingeniería", "Neuroengineering", "BMED"),
    ("Farmacología", "Pharmacology", "BIOL"),
    ("Gestión Sanitaria", "Healthcare Management", "MGT"),
]
# Coletillas para alargar nombres: la tabla y el PDF tienen que aguantarlos.
COLETILLAS_UC3M = [
    "",
    " I",
    " II",
    " Avanzada",
    " y sus Aplicaciones Clínicas",
    ": Fundamentos, Modelado Computacional y Aplicaciones en Entornos Hospitalarios",
]
COLETILLAS_DESTINO = [
    "",
    " I",
    " II",
    " Laboratory",
    " for Engineers",
    ": Principles, Computational Modeling and Clinical Applications in Hospital Settings",
]
ECTS_UC3M = [6, 6, 6, 6, 3, 4.5, 9]
ECTS_DESTINO = [6.0, 6.0, 6.0, 4.5, 4.5, 3.0, 7.5, 9.0]
# Forma de cada grupo n:m: (asignaturas UC3M, asignaturas destino).
FORMAS_GRUPO = [(1, 2), (2, 1), (2, 2), (1, 3), (3, 1)]
NUM_GRUPOS = 10


class Generador:
    def __init__(self, semilla=SEMILLA):
        self.rng = random.Random(semilla)
        self.siguiente_uc3m = 18100
        self.siguiente_destino = {}

    def _tema(self):
        return self.rng.choice(TEMAS)

    def asignatura_uc3m(self, tema, larga=False):
        self.siguiente_uc3m += 1
        coletilla = COLETILLAS_UC3M[-1] if larga else self.rng.choice(COLETILLAS_UC3M)
        return {
            "codigo": str(self.siguiente_uc3m),
            "nombre": tema[0] + coletilla,
            "ects": self.rng.choice(ECTS_UC3M),
            "tipo": self.rng.choice(["FB", "OB", "OB", "OP"]),
        }

    def asignatura_destino(self, tema, larga=False):
        prefijo = tema[2]
        numero = self.siguiente_destino.get(prefijo, 1000) + self.rng.randint(1, 40)
        self.siguiente_destino[prefijo] = numero
        coletilla = COLETILLAS_DESTINO[-1] if larga else self.rng.choice(COLETILLAS_DESTINO)
        return {
            "codigo": f"{prefijo} {numero}",
            "nombre": tema[1] + coletilla,
            "ects": self.rng.choice(ECTS_DESTINO),
            "url": URL_DESTINO,
        }

    def score(self, etiqueta):
        # Los precedentes se muestran siempre, aunque estén por debajo del umbral.
        if etiqueta == "PRECEDENTE_APROBADO":
            return round(self.rng.uniform(0.45, 0.97), 2)
        return round(self.rng.uniform(UMBRAL, 0.95), 2)

    def grupos(self):
        """Filas de los grupos n:m (siempre precedentes: salen del histórico)."""
        filas = []
        for numero in range(1, NUM_GRUPOS + 1):
            n, m = FORMAS_GRUPO[(numero - 1) % len(FORMAS_GRUPO)]
            tema = self._tema()
            larga = numero <= 2  # los dos primeros grupos, con nombres larguísimos
            # Solo la primera de cada lado lleva el nombre larguísimo, para que se distingan.
            origenes = [self.asignatura_uc3m(tema, larga and i == 0) for i in range(n)]
            destinos = [self.asignatura_destino(tema, larga and i == 0) for i in range(m)]
            pares = [(origenes[i % n], destinos[i % m]) for i in range(max(n, m))]
            total_origen = sum(o["ects"] for o in origenes)
            total_destino = sum(d["ects"] for d in destinos)
            aviso = ects_dispares(total_origen, total_destino)
            filas += [
                {
                    "origen": origen,
                    "destino": destino,
                    "score": self.score("PRECEDENTE_APROBADO"),
                    "etiqueta": "PRECEDENTE_APROBADO",
                    "aviso_ects": aviso,
                    "grupo": numero,
                }
                for origen, destino in pares
            ]
        return filas

    def individuales(self, cuantas):
        """Filas 1:1. Algunas asignaturas UC3M tienen varias candidatas, como en el top-10."""
        filas = []
        origenes = []
        for i in range(cuantas):
            if origenes and self.rng.random() < 0.3:
                origen, tema = self.rng.choice(origenes)
            else:
                tema = self._tema()
                origen = self.asignatura_uc3m(tema, larga=i < 3)
                origenes.append((origen, tema))
            destino = self.asignatura_destino(tema, larga=i < 3)
            if self.rng.random() < 0.75:  # lo normal es que los créditos cuadren
                destino["ects"] = float(origen["ects"])
            etiqueta = "PRECEDENTE_APROBADO" if self.rng.random() < 0.35 else "SUGERENCIA_IA"
            filas.append(
                {
                    "origen": origen,
                    "destino": destino,
                    "score": self.score(etiqueta),
                    "etiqueta": etiqueta,
                    "aviso_ects": ects_dispares(origen["ects"], destino["ects"]),
                    "grupo": None,
                }
            )
        return filas


def generar(semilla=SEMILLA):
    gen = Generador(semilla)
    grupos = gen.grupos()
    filas = grupos + gen.individuales(TOTAL_FILAS - len(grupos))
    gen.rng.shuffle(filas)  # el orden lo pone la web, no el JSON
    datos = {
        "grado": "Grado en Ingeniería Biomédica",
        "universidad": "Georgia Institute of Technology",
        "generado": "2026-11-25",
        "modelo": "multilingual-e5-small",
        "umbral": UMBRAL,
        "resultados": filas,
    }
    Resultados.model_validate(datos)  # mismo contrato que el export real
    return datos


def main():
    datos = generar()
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    grupos = {f["grupo"] for f in datos["resultados"] if f["grupo"] is not None}
    print(f"{SALIDA.relative_to(RAIZ)}: {len(datos['resultados'])} filas, {len(grupos)} grupos n:m")


if __name__ == "__main__":
    main()