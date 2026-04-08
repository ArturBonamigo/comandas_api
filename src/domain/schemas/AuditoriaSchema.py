from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class AuditoriaCreate(BaseModel):
    """Schema para criar registro de auditoria"""
    funcionario_id: int
    acao: str = Field(..., max_length=50, description="Tipo de ação (LOGIN, LOGOUT, CREATE, UPDATE, DELETE, etc.)")
    recurso: str = Field(..., max_length=100, description="Recurso acessado (comanda, recebimento, produto, etc.)")
    recurso_id: Optional[int] = None
    dados_antigos: Optional[str] = None
    dados_novos: Optional[str] = None
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = None

class AuditoriaResponse(BaseModel):
    """Schema para resposta de auditoria com dados do funcionário"""
    id: int
    funcionario_id: int
    funcionario: Dict[str, Any] # Dados básicos do funcionário
    acao: str
    recurso: str
    recurso_id: Optional[int] = None
    dados_antigos: Optional[str] = None
    dados_novos: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    data_hora: datetime