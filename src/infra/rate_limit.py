# Artur Bonamigo

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Criar limiter com base no IP do cliente
limiter = Limiter(key_func=get_remote_address)

# Handler personalizado para exceção de rate limit
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Handler personalizado para quando o rate limit é excedido. - Retorna uma resposta JSON formatada em vez de erro HTML.
    """
    # Calcular retry_after baseado no limite
    if "minute" in exc.detail:
        retry_after = 60  # 1 minuto
    elif "hour" in exc.detail:
        retry_after = 3600  # 1 hora
    elif "second" in exc.detail:
        retry_after = 1  # 1 segundo
    elif "day" in exc.detail:
        retry_after = 86400  # 1 dia
    else:
        retry_after = 60  # Padrão para 1 minuto

    response = Response(content=f'{{"error": "Rate limit exceeded", "message": "Too many requests. Limit: {exc.detail}", "retry_after": {retry_after}, "timestamp": "{datetime.now(timezone.utc).isoformat()}"}}', status_code=429,
media_type="application/json")
    
    # Adiciona headers informativos
    response.headers["X-RateLimit-Limit"] = str(exc.detail)
    response.headers["X-RateLimit-Remaining"] = "0"
    response.headers["X-RateLimit-Reset"] = str(int(datetime.now(timezone.utc).timestamp()) + retry_after)
    response.headers["Retry-After"] = str(retry_after)

    return response

# Configuração de limites por perfil (carregados do .env)
RATE_LIMITS = {
    "critical": os.getenv("RATE_LIMIT_CRITICAL", "5/minute"), # Muito restritivo - Login, refresh, logout, exclusões, operações sensíveis
    "restrictive": os.getenv("RATE_LIMIT_RESTRICTIVE", "20/minute"), # Restritivo - Criações, atualizações, exclusões de dados
    "moderate": os.getenv("RATE_LIMIT_MODERATE", "100/minute"), # Moderado - Listagens, buscas por ID, auditoria
    "low": os.getenv("RATE_LIMIT_LOW", "200/minute"), # Baixo - Health checks, endpoints de sistema, documentos
    "light": os.getenv("RATE_LIMIT_LIGHT", "300/minute"), # Leve - Endpoints públicos, documentação
    "default": os.getenv("RATE_LIMIT_DEFAULT", "50/minute") # Padrão para endpoints não especificados
}

# Retorna o rate limit para um tipo de endpoint
def get_rate_limit(endpoint_type: str) -> str:
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["default"])