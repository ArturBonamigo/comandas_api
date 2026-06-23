from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime

from domain.schemas.ClienteSchema import ClienteResponse
from domain.schemas.FuncionarioSchema import FuncionarioResponse
from domain.schemas.ProdutoSchema import ProdutoResponse


class RecebimentoCreate(BaseModel):
    comanda_ids: List[int] = Field(..., min_length=1)
    desconto: float = Field(default=0, ge=0)
    acrescimo: float = Field(default=0, ge=0)


class RecebimentoComandaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recebimento_id: int
    comanda_id: int
    valor_comanda: float


class RecebimentoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    funcionario_id: int
    funcionario: Optional[FuncionarioResponse] = None
    data_hora: datetime
    valor_bruto: float
    desconto: float
    acrescimo: float
    valor_final: float
    comandas: List[RecebimentoComandaResponse] = []


class RecebimentoDashboardItem(BaseModel):
    id: int
    comanda: str
    data_hora: datetime
    status: int
    cliente_id: Optional[int] = None
    cliente: Optional[ClienteResponse] = None
    total: float
    quantidade_itens: int


class RecebimentoProdutoDetalhe(BaseModel):
    id: int
    produto_id: int
    produto: Optional[ProdutoResponse] = None
    quantidade: int
    valor_unitario: float
    valor_total: float


class RecebimentoComandaDetalhe(BaseModel):
    id: int
    comanda: str
    data_hora: datetime
    status: int
    cliente_id: Optional[int] = None
    cliente: Optional[ClienteResponse] = None
    produtos: List[RecebimentoProdutoDetalhe] = []
    total: float


class RecebimentoDetalhe(BaseModel):
    comandas: List[RecebimentoComandaDetalhe]
    valor_bruto: float


class RecebimentoComprovante(BaseModel):
    recebimento: RecebimentoResponse
    detalhes: RecebimentoDetalhe