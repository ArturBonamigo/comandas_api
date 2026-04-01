from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta

from domain.schemas.AuthSchema import LoginRequest, TokenResponse, RefreshTokenRequest, FuncionarioAuth, ClienteAuth, ProdutoAuth

from infra.orm.FuncionarioModel import FuncionarioDB
from infra.orm.ClienteModel import ClienteDB
from infra.orm.ProdutoModel import ProdutoDB
from infra.database import get_db
from infra.security import verify_password, create_access_token, create_refresh_token, verify_refresh_token
from infra.dependencies import get_current_active_user

from settings import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

router = APIRouter()

@router.post("/auth/login", response_model=TokenResponse, tags=["Autenticação"], summary="Login de funcionário - pública - retorna access e refresh token")
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    
    Realiza login do funcionário e retorna access token e refresh token
    - **cpf**: CPF do funcionário - **senha**: Senha do funcionário
    
    Retorna: - access_token: Token de curta duração (15 minutos) - refresh_token: Token de longa duração (7 dias)
    """
    try:
        # Busca funcionário pelo CPF
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.cpf == login_data.cpf).first()
        
        if not funcionario:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="CPF ou senha inválidos", headers={"WWW-Authenticate": "Bearer"}, )
    
        # Verifica se a senha está correta
        if not verify_password(login_data.senha, funcionario.senha):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="CPF ou senha inválidos", headers={"WWW-Authenticate": "Bearer"}, )
    
        # Cria o access token JWT (curta duração)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": funcionario.cpf, # subject = CPF
                "id": funcionario.id, # ID do funcionário
                "grupo": funcionario.grupo
            },
            expires_delta=access_token_expires
        )
    
        # Cria o refresh token JWT (longa duração)
        refresh_token = create_refresh_token(
            data={
                "sub": funcionario.cpf, # subject = CPF
                "id": funcionario.id, # ID do funcionário
                "grupo": funcionario.grupo
            }
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60, # em segundos
            refresh_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 # em segundos
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException( status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao realizar login: {str(e)}" )
    
@router.post("/auth/refresh", response_model=TokenResponse, tags=["Autenticação"], summary="Refresh token - pública - renova access token")
async def refresh_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Renova o access token usando um refresh token válido
    
    - **refresh_token**: Refresh token válido retornado no login
    
    Retorna novo access token e refresh token
    """
    try:
        # Verifica e decodifica o refresh token
        payload = verify_refresh_token(refresh_data.refresh_token)

        # Busca funcionário para garantir que ainda existe
        cpf = payload.get("sub")
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.cpf == cpf).first()
        
        if not funcionario:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Funcionário não encontrado", headers={"WWW-Authenticate": "Bearer"}, )

        # Cria novo access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": funcionario.cpf,
                "id": funcionario.id,
                "grupo": funcionario.grupo
            },
            expires_delta=access_token_expires
        )

        # Cria novo refresh token
        new_refresh_token = create_refresh_token(
            data={
                "sub": funcionario.cpf,
                "id": funcionario.id,
                "grupo": funcionario.grupo
            }
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Erro ao renovar token: {str(e)}", headers={"WWW-Authenticate": "Bearer"}, )
    
@router.get("/auth/me", response_model=FuncionarioAuth, tags=["Autenticação"], summary="Dados do usuário atual - protegida por autenticação")
async def get_current_user_info(current_user: FuncionarioAuth = Depends(get_current_active_user)):
    """
    Retorna informações do usuário autenticado atual
    Requer header: Authorization: Bearer <access_token>
    """
    return current_user

@router.post("/auth/logout", tags=["Autenticação"], summary="Logout - pública")
async def logout():
    """
    Endpoint para logout (client-side)
    Na prática, o logout é implementado no cliente removendo os tokens
    Este endpoint existe apenas para completude da API
    """
    return {"message": "Logout realizado com sucesso"}