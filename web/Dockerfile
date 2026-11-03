# Imagen de la web (Streamlit). Se construye con el contexto en web/:
#   docker build -t aisc-web web/
FROM python:3.11-slim

# Sin ficheros .pyc y con los logs al momento (Coolify los muestra en directo)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Primero solo las dependencias: si no cambian, Docker reutiliza esta capa
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Después el código de la web (lo que excluye .dockerignore no entra)
COPY . .

EXPOSE 8501

# Coolify usa esto para saber si la app está viva
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]