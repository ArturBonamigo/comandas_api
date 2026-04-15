from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

from domain.schemas.FuncionarioSchema import FuncionarioResponse
from domain.schemas.ClienteSchema import ClienteResponse
from domain.schemas.ProdutoSchema import ProdutoResponse


class ComandaCreate(BaseModel):
    comanda: str
    status: int
    cliente_id: Optional[int] = None
    funcionario_id: int


class ComandaUpdate(BaseModel):
    comanda: Optional[str] = None
    status: Optional[int] = None
    cliente_id: Optional[int] = None
    funcionario_id: Optional[int] = None


class ComandaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    comanda: str
    data_hora: datetime
    status: int
    funcionario_id: int
    funcionario: Optional[FuncionarioResponse] = None
    cliente_id: Optional[int] = None
    cliente: Optional[ClienteResponse] = None


# Comanda Produtos
class ComandaProdutosCreate(BaseModel):
    produto_id: int
    funcionario_id: int
    quantidade: int
    valor_unitario: float


class ComandaProdutosUpdate(BaseModel):
    quantidade: Optional[int] = None
    valor_unitario: Optional[float] = None


class ComandaProdutosResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    comanda_id: int
    funcionario_id: int
    funcionario: Optional[FuncionarioResponse] = None
    produto_id: int
    produto: Optional[ProdutoResponse] = None
    quantidade: int
    valor_unitario: float