FROM python:3.10-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# Environnement du proxy
# ============================================================

RUN pip install --no-cache-dir \
    "mcp==1.27.2" \
    "mcp-proxy==0.12.0"

# ============================================================
# Environnement isolé pour Chroma MCP
# Chroma MCP impose MCP 1.6.0
# ============================================================

RUN python -m venv /opt/chroma-mcp/.venv

COPY mcp/pyproject.toml mcp/uv.lock mcp/README.md mcp/LICENSE /opt/chroma-mcp/
COPY mcp/src /opt/chroma-mcp/src

RUN /opt/chroma-mcp/.venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/chroma-mcp/.venv/bin/pip install --no-cache-dir /opt/chroma-mcp ollama

# Wrapper vers le venv dédié de Chroma MCP
RUN printf '#!/bin/sh\nexec /opt/chroma-mcp/.venv/bin/chroma-mcp "$@"\n' \
    > /usr/local/bin/chroma-mcp \
    && chmod +x /usr/local/bin/chroma-mcp

EXPOSE 8080

ENTRYPOINT ["mcp-proxy", "--host", "0.0.0.0", "--port", "8080", "--pass-environment", "--", "chroma-mcp"]