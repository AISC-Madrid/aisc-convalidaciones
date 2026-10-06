import base64
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
LOGO = HERE / "assets" / "aisc_logo.png"
CONVALIDACIONES = HERE / "convalidaciones"
GUIA = HERE / "guia_ia_gratis"
TARGETS = {
    "report": (
        CONVALIDACIONES / "report_final_template.html",
        CONVALIDACIONES / "pdf" / "Proyecto AISC - Buscador de convalidaciones (roadmap actualizado).pdf",
    ),
    "slides": (
        CONVALIDACIONES / "slides_template.html",
        CONVALIDACIONES / "pdf" / "Proyecto AISC - Buscador de convalidaciones (presentación).pdf",
    ),
    "guia": (
        GUIA / "guia_ia_gratis_estudiantes.html",
        GUIA / "pdf" / "AISC - Guía de IA gratis para estudiantes.pdf",
    ),
}
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]


def build(template, output, browser):
    html = template.read_text(encoding="utf-8").replace(
        "__LOGO_B64__", base64.b64encode(LOGO.read_bytes()).decode()
    )
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run(
            [
                browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--user-data-dir={tmp}", f"--print-to-pdf={output}", page.as_uri(),
            ],
            check=True, timeout=120,
        )
    print(f"PDF generado: {output}")


def main():
    browser = next(b for b in BROWSERS if Path(b).exists())
    for name in sys.argv[1:] or TARGETS:
        build(*TARGETS[name], browser)


if __name__ == "__main__":
    main()
