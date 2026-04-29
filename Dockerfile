# Multi-stage build

# Builder stage
FROM python:3.14-alpine AS builder

# Metadados da imagem
LABEL maintainer="Luciano Coelho <luciano.coelho@gmail.com>" 
LABEL description="API FastAPI com Hypercorn e QUIC - Alpine Multi-stage"
LABEL version="1.0.0"

# Instala dependências de build no Alpine
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

# Instala dependências do projeto Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.14-alpine

# Configurações de ambiente
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/local/bin:$PATH" PYTHONPATH="/app/local/lib/python3.14/site-packages"

# Instala dependências de runtime Alpine
RUN apk add --no-cache curl && rm -rf /var/cache/apk/*

# Cria usuário e diretórios
RUN addgroup -g 1001 appuser && adduser -D -u 1001 -G appuser appuser && \
    mkdir -p /app/logs && chown appuser:appuser /app

# Diretório de trabalho
WORKDIR /app

# Copia dependências do builder de forma segura (isolada)
COPY --from=builder /usr/local/lib/python3.14/site-packages /app/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /app/local/bin

# Copia código da aplicação
COPY --chown=appuser:appuser ./src /app

# cria diretório para certificados - será montado via volume
RUN mkdir -p /cert && chown appuser:appuser /cert

USER appuser

# Health check - verifica se a API está respondendo a cada 30s
# Atualiza status do container (healthy/unhealthy) - Afeta Docker Compose (espera healthy antes de continuar)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f https://localhost:4443/health --insecure || exit 1

# expõe a porta 4443 para tcp (https) e udp (quic/h3) - expose apenas documenta, não publica a porta.
EXPOSE 4443/tcp
EXPOSE 4443/udp

# iniciar o servidor hypercorn
# removido: --reload, não faz sentido em produção
# removido: --insecure-bind 0.0.0.0:8080, não queremos http://

# ENTRYPOINT para configuração do Hypercorn
ENTRYPOINT ["hypercorn", "--certfile=/cert/cert.pem", "--keyfile=/cert/ecc-key.pem"]

# CMD para execução - pode ser sobrescrito no runtime
CMD ["--bind", "0.0.0.0:4443", "--quic-bind", "0.0.0.0:4443", "main:app"]