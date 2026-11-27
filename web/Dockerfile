# Imagen de la web (Streamlit). Se construye DESDE LA RAÍZ del repo:
#   docker build -f web/Dockerfile -t aisc-web .
FROM python:3.11-slim

# Sin ficheros .pyc y con los logs al momento (Coolify los muestra en directo)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Misma carpeta de trabajo que antes (web/), así Streamlit se comporta igual
WORKDIR /app/web

# Primero solo las dependencias: si no cambian, Docker reutiliza esta capa
COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Solo el código de la web: los resultados y el catálogo se leen de la MySQL
# (lo que excluye web/Dockerfile.dockerignore no entra)
COPY web/ .

EXPOSE 8501

# Coolify usa esto para saber si la app está viva
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]