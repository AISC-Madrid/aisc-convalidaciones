# Web en el mismo servidor que MySQL. Las variables van en Coolify, no en la imagen.
FROM python:3.11-slim-bookworm

ARG GH_VERSION=2.63.2
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSL "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${TARGETARCH}.tar.gz" \
        | tar -xz -C /tmp \
    && mv /tmp/gh_${GH_VERSION}_linux_${TARGETARCH}/bin/gh /usr/local/bin/gh \
    && rm -rf /tmp/gh_${GH_VERSION}_linux_${TARGETARCH} /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8501
CMD ["sh", "-c", "python -m src.sync.volcar_mysql && exec streamlit run src/ui/app.py --server.address=0.0.0.0 --server.port=8501"]
