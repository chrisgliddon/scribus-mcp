FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        scribus scribus-data fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/*

ENV QT_QPA_PLATFORM=offscreen
ENV SCRIBUS_EXECUTABLE=/usr/bin/scribus

RUN useradd --create-home --shell /bin/bash mcpuser
WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

USER mcpuser
RUN mkdir -p /home/mcpuser/.scribus-mcp/workspace

CMD ["scribus-mcp"]
