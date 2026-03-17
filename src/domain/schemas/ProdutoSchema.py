# Artur Bonamigo

from pydantic import BaseModel, ConfigDict
from typing import Optional

class ProdutoCreate(BaseModel):
    nome: str
    descricao: str
    foto: bytes = None
    valor_unitario: float

class ProdutoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    foto: Optional[bytes] = None
    valor_unitario: Optional[float] = None

class ProdutoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    descricao: str
    foto: bytes
    valor_unitario: float