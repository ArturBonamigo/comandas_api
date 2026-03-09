from fastapi import APIRouter
from domain.entities.Funcionario import Funcionario

router = APIRouter()

# Criar as rotas/endpoints: GET, POST, PUT, DELETE

@router.get("/funcionario/", tags=["Funcionário"], status_code=200)
def get_funcionario():
    return {"msg": "funcionario get todos executado"}

@router.get("/funcionario/{id}", tags=["Funcionário"], status_code=200)
def get_funcionario(id: int):
    return {"msg": "funcionario get um executado"}

@router.post("/funcionario/", tags=["Funcionário"], status_code=200)
def post_funcionario(corpo: Funcionario):
    return {"msg": "funcionario post executado", "nome": corpo.nome, "cpf": corpo.cpf, "telefone": corpo.telefone}

@router.put("/funcionario/{id}", tags=["Funcionário"], status_code=200)
def put_funcionario(id: int, corpo: Funcionario):
    return {"msg": "funcionario put executado", "id": id, "nome": corpo.nome, "cpf": corpo.cpf, "telefone": corpo.telefone}

@router.delete("/funcionario/{id}", tags=["Funcionário"], status_code=200)
def delete_funcionario(id: int):
    return {"msg": "funcionario delete executado", "id":id}