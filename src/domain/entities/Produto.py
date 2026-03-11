# Artur Bonamigo

from pydantic import BaseModel

class Produto(BaseModel):
    id_produto: int = None
    nome: str
    descricao: str = None
    valorUnitario: float
    foto: bytes