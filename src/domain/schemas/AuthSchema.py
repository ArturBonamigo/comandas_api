from pydantic import BaseModel, ConfigDict
from typing import Optional

class LoginRequest(BaseModel):
    cpf: str
    senha: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    cpf: Optional[str] = None
    id_funcionario: Optional[str] = None

class FuncionarioAuth(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    matricula: str
    cpf: str
    grupo: int
    
class ClienteAuth(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    cpf: str
    telefone: str

class ProdutoAuth(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    preco: float