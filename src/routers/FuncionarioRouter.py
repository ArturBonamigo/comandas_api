# Artur Bonamigo

from fastapi import APIRouter, Depends, HTTPException, status, Request
from services.AuditoriaService import AuditoriaService
from infra.rate_limit import limiter, get_rate_limit
from slowapi.errors import RateLimitExceeded

from sqlalchemy.orm import Session
from typing import List

# Domain Schemas
from domain.schemas.FuncionarioSchema import(
    FuncionarioCreate,
    FuncionarioUpdate,
    FuncionarioResponse
)
from domain.schemas.AuthSchema import FuncionarioAuth

# Infra
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.database import get_db
from infra.security import get_password_hash
from infra.dependencies import get_current_active_user, require_group

router = APIRouter()

# Criar as rotas/endpoints: GET, POST, PUT, DELETE

@router.get("/funcionario/", response_model=List[FuncionarioResponse], tags=["Funcionário"], status_code=status.HTTP_200_OK, summary="Listar todos os funcionários - protegida por autenticação e grupo 1")
@limiter.limit(get_rate_limit("moderate"))
async def get_funcionario(
    request: Request,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Retorna todos os funcionários"""
    try:
        funcionarios = db.query(FuncionarioDB).all()
        return funcionarios
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar funcionários: {str(e)}"
        )

@router.get("/funcionario/{id}", response_model=FuncionarioResponse, tags=["Funcionário"], status_code=status.HTTP_200_OK, summary="Buscar funcionário por ID")
@limiter.limit(get_rate_limit("critical"))
async def get_funcionario(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    """Retorna um funcionário específico pelo ID"""
    try:
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.id == id).first()
        
        if not funcionario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado")
        return funcionario
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar funcionário: {str(e)}"
        )

@router.post("/funcionario/", response_model=FuncionarioResponse, status_code=status.HTTP_201_CREATED, tags=["Funcionário"], summary="Criar novo funcionário - protegida por JWT e grupo 1")
@limiter.limit(get_rate_limit("restrictive"))
async def post_funcionario(
    request: Request,
    funcionario_data: FuncionarioCreate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Cria um novo funcionário"""
    try:
        # Verifica se já existe funcionário com este CPF
        existing_funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.cpf == funcionario_data.cpf).first()
        
        if existing_funcionario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um funcionário com este CPF"
            )
        
        hashed_password = get_password_hash(funcionario_data.senha)
        
        # Cria o novo funcionário
        novo_funcionario = FuncionarioDB(
            id=None, # Será auto-incrementado
            nome=funcionario_data.nome,
            matricula=funcionario_data.matricula,
            cpf=funcionario_data.cpf,
            telefone=funcionario_data.telefone,
            grupo=funcionario_data.grupo,
            senha=hashed_password
        )

        db.add(novo_funcionario)
        db.commit()
        db.refresh(novo_funcionario)
        
        # Depois de tudo executado e antes do return, registra a ação na auditoria
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="FUNCIONARIO",
            recurso_id=novo_funcionario.id,
            dados_antigos=None,
            dados_novos=novo_funcionario, # Objeto SQLAlchemy com dados novos
            request=request # Request completo para capturar IP e user agent
            )

        return novo_funcionario
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao criar funcionário: {str(e)}"
        )

@router.put("/funcionario/{id}", response_model=FuncionarioResponse, tags=["Funcionário"], status_code=status.HTTP_200_OK, summary="Atualizar funcionário - protegida por JWT e grupo 1")
@limiter.limit(get_rate_limit("restrictive"))
async def put_funcionario(
    request: Request,
    id: int,
    funcionario_data: FuncionarioUpdate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Atualiza um funcionário existente"""
    try:
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.id == id).first()
        
        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado"
        )

        # Verifica se está tentando atualizar para um CPF que já existe
        if funcionario_data.cpf and funcionario_data.cpf != funcionario.cpf:
            existing_funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.cpf == funcionario_data.cpf).first()
                
            if existing_funcionario:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um funcionário com este CPF"
                )
            
        if funcionario_data.senha:
            funcionario_data.senha = get_password_hash(funcionario_data.senha)

        # se informado grupo, valida se é um grupo válido
        if funcionario_data.grupo:
            if funcionario_data.grupo not in [1, 2, 3]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Grupo inválido. Apenas grupos 1 (Admin), 2 (Atendimento Balcão) ou 3 (Atendimento Caixa) são permitidos."
                )
        
        # armazena uma copia do objeto com os dados atuais, para salvar na auditoria
        # não pode manter referencia com funcionário, para que o auditoria possa comparar
        # por isso a cópia do __dict__
        dados_antigos_obj = funcionario.__dict__.copy()
            
        # Atualiza apenas os campos fornecidos
        update_data = funcionario_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(funcionario, field, value)

        db.commit()
        db.refresh(funcionario) # Depois de tudo executado e antes do return, registra a ação na auditoria
        
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="FUNCIONARIO",
            recurso_id=funcionario.id,
            dados_antigos=dados_antigos_obj, # Objeto SQLAlchemy com dados antigos
            dados_novos=funcionario, # Objeto SQLAlchemy com dados novos
            request=request # Request completo para capturar IP e user agent
        )
        
        return funcionario

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao atualizar funcionário: {str(e)}"
        )

@router.delete("/funcionario/{id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Funcionário"], summary="Remover funcionário - protegida por JWT e grupo 1")
@limiter.limit(get_rate_limit("critical"))
async def delete_funcionario(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Remove um funcionário"""
    try:
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.id == id).first()
        
        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado"
            )
        
        db.delete(funcionario)
        db.commit()

        # Depois de tudo executado e antes do return, registra a ação na auditoria
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="FUNCIONARIO",
            recurso_id=funcionario.id,
            dados_antigos=funcionario,
            dados_novos=None,
            request=request
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao deletar funcionário: {str(e)}"
        )