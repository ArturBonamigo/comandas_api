from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime

from domain.schemas.ComandaSchema import (
    ComandaCreate,
    ComandaUpdate,
    ComandaResponse,
    FuncionarioResponse,
    ClienteResponse,
    ComandaProdutosCreate,
    ComandaProdutosUpdate,
    ComandaProdutosResponse,
    ProdutoResponse
)
from domain.schemas.AuthSchema import FuncionarioAuth
from infra.orm.ComandaModel import ComandaDB, ComandaProdutoDB
from infra.orm.ProdutoModel import ProdutoDB
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.orm.ClienteModel import ClienteDB
from infra.database import get_async_db
from infra.dependencies import require_group, get_current_active_user
from infra.rate_limit import limiter
from services.AuditoriaService import AuditoriaService

router = APIRouter()


# busca comanda conforme id informado
@router.get("/comanda/{id}", response_model=ComandaResponse, tags=["Comanda"], summary="Buscar comanda por ID - protegida por JWT")
@limiter.limit("moderate")
async def get_comanda(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        # busca a comanda, funcionário e cliente com joins
        result = await db.execute(
            select(ComandaDB, FuncionarioDB, ClienteDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == ComandaDB.funcionario_id)
            .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
            .where(ComandaDB.id == id)
        )
        row = result.first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada"
            )

        # tupla com os resultados
        comanda, funcionario, cliente = row

        # Construir response manualmente
        comanda_response = ComandaResponse(
            id=comanda.id,
            comanda=comanda.comanda,
            data_hora=comanda.data_hora,
            status=comanda.status,
            cliente_id=comanda.cliente_id,
            funcionario_id=comanda.funcionario_id,
            funcionario=FuncionarioResponse(
                id=funcionario.id,
                nome=funcionario.nome,
                matricula=funcionario.matricula,
                cpf=funcionario.cpf,
                telefone=funcionario.telefone,
                grupo=funcionario.grupo
            ) if funcionario else None,
            cliente=ClienteResponse(
                id=cliente.id,
                nome=cliente.nome,
                cpf=cliente.cpf,
                telefone=cliente.telefone
            ) if cliente else None
        )

        return comanda_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar comanda: {str(e)}"
        )


# Lista todas as comandas com paginação e filtro opcional por status {0 - aberta, 1 - fechada, 2 - cancelada}
@router.get("/comanda/", response_model=List[ComandaResponse], tags=["Comanda"], summary="Listar todas as comandas - opção de filtro e paginação - protegida por JWT")
@limiter.limit("moderate")
async def get_comandas(
    request: Request,
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    id: Optional[int] = Query(None, description="Filtrar por ID"),
    comanda: Optional[int] = Query(None, description="Filtrar por número da comanda"),
    status: Optional[int] = Query(None, description="Filtrar por status: 0=aberta, 1=fechada, 2=cancelada"),
    funcionario_id: Optional[int] = Query(None, description="Filtrar por funcionário"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    data_inicio: Optional[datetime] = Query(None, description="Filtrar por data inicial"),
    data_fim: Optional[datetime] = Query(None, description="Filtrar por data final"),
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        # busca a comanda, funcionário e cliente com joins
        query = (
            select(ComandaDB, FuncionarioDB, ClienteDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == ComandaDB.funcionario_id)
            .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
        )

        # Aplicar filtros
        conditions = []

        if id is not None:
            conditions.append(ComandaDB.id == id)

        if comanda is not None:
            conditions.append(ComandaDB.comanda == comanda)

        if status is not None:
            conditions.append(ComandaDB.status == status)

        if funcionario_id is not None:
            conditions.append(ComandaDB.funcionario_id == funcionario_id)

        if cliente_id is not None:
            conditions.append(ComandaDB.cliente_id == cliente_id)

        if data_inicio is not None:
            try:
                data_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
                conditions.append(ComandaDB.data_hora >= data_inicio)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data início inválida. Use formato YYYY-MM-DD"
                )

        if data_fim is not None:
            try:
                data_fim = datetime.strptime(data_fim, "%Y-%m-%d")
                conditions.append(ComandaDB.data_hora <= data_fim)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data fim inválida. Use formato YYYY-MM-DD"
                )

        # Aplicar condições à query
        if conditions:
            query = query.where(*conditions)

        # executar query com paginação
        result = await db.execute(query.offset(skip).limit(limit))
        results = result.all()

        # Construir lista de responses manualmente
        comandas_response = []

        for comanda, funcionario, cliente in results:
            comanda_response = ComandaResponse(
                id=comanda.id,
                comanda=comanda.comanda,
                data_hora=comanda.data_hora,
                status=comanda.status,
                cliente_id=comanda.cliente_id,
                funcionario_id=comanda.funcionario_id,
                funcionario=FuncionarioResponse(
                    id=funcionario.id,
                    nome=funcionario.nome,
                    matricula=funcionario.matricula,
                    cpf=funcionario.cpf,
                    telefone=funcionario.telefone,
                    grupo=funcionario.grupo
                ) if funcionario else None,
                cliente=ClienteResponse(
                    id=cliente.id,
                    nome=cliente.nome,
                    cpf=cliente.cpf,
                    telefone=cliente.telefone
                ) if cliente else None
            )
            comandas_response.append(comanda_response)

        return comandas_response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar comandas: {str(e)}"
        )


# nova comanda
@router.post("/comanda/", response_model=ComandaResponse, status_code=status.HTTP_201_CREATED, tags=["Comanda"], summary="Criar nova comanda - protegida por JWT")
@limiter.limit("restrictive")
async def create_comanda(
    comanda_data: ComandaCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        # Verificar se o funcionário existe
        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.id == comanda_data.funcionario_id)
        )
        funcionario = result.scalar_one_or_none()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Funcionário não encontrado"
            )

        # Verificar se o cliente existe (se informado)
        if comanda_data.cliente_id:
            result = await db.execute(
                select(ClienteDB).where(ClienteDB.id == comanda_data.cliente_id)
            )
            cliente = result.scalar_one_or_none()

            if not cliente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cliente não encontrado"
                )

        # validar se o status é válido, na criação só pode ser 0 (aberta)
        if comanda_data.status not in [0]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status inválido - na abertura a comanda deve estar com status 0 (aberta)"
            )

        # antes de abrir a comanda validar se ela já não esta aberta, status == 0
        result = await db.execute(
            select(ComandaDB)
            .where(ComandaDB.comanda == comanda_data.comanda)
            .where(ComandaDB.status == 0)
        )
        comanda_existente = result.scalar_one_or_none()

        if comanda_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comanda já existe e está aberta"
            )

        # Criar nova comanda
        new_comanda = ComandaDB(
            comanda=comanda_data.comanda,
            data_hora=datetime.now(),
            status=comanda_data.status,
            cliente_id=comanda_data.cliente_id,
            funcionario_id=comanda_data.funcionario_id
        )

        db.add(new_comanda)
        await db.commit()
        await db.refresh(new_comanda)

        # Registrar auditoria de criação
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="COMANDA",
            recurso_id=new_comanda.id,
            dados_novos=new_comanda,
            request=request
        )

        return new_comanda

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar comanda: {str(e)}"
        )


# atualizar comanda
@router.put("/comanda/{id}", response_model=ComandaResponse, tags=["Comanda"], summary="Atualizar comanda - protegida por JWT e grupo 1")
@limiter.limit("restrictive")
async def update_comanda(
    id: int,
    comanda_data: ComandaUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        result = await db.execute(select(ComandaDB).where(ComandaDB.id == id))
        comanda = result.scalar_one_or_none()

        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada"
            )

        # armazena uma copia do objeto com os dados atuais, para salvar na auditoria
        dados_antigos_obj = comanda.__dict__.copy()

        # Atualizar campos se fornecidos
        if comanda_data.comanda is not None:
            comanda.comanda = comanda_data.comanda

        if comanda_data.status is not None:
            comanda.status = comanda_data.status

        if comanda_data.cliente_id is not None:
            if comanda_data.cliente_id != 0:
                result = await db.execute(
                    select(ClienteDB).where(ClienteDB.id == comanda_data.cliente_id)
                )
                cliente = result.scalar_one_or_none()

                if not cliente:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cliente não encontrado"
                    )

                comanda.cliente_id = comanda_data.cliente_id
            else:
                comanda.cliente_id = None

        if comanda_data.funcionario_id is not None:
            result = await db.execute(
                select(FuncionarioDB).where(FuncionarioDB.id == comanda_data.funcionario_id)
            )
            funcionario = result.scalar_one_or_none()

            if not funcionario:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Funcionário não encontrado"
                )

            comanda.funcionario_id = comanda_data.funcionario_id

        await db.commit()
        await db.refresh(comanda)

        # Registrar auditoria de atualização
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="COMANDA",
            recurso_id=comanda.id,
            dados_antigos=dados_antigos_obj,
            dados_novos=comanda,
            request=request
        )

        return comanda

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar comanda: {str(e)}"
        )


# exclui comanda
@router.delete("/comanda/{id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Comanda"], summary="Remover comanda - protegida por JWT e grupo 1")
@limiter.limit("critical")
async def delete_comanda(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        # Buscar a comanda
        result = await db.execute(select(ComandaDB).where(ComandaDB.id == id))
        comanda = result.scalar_one_or_none()

        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada"
            )

        # Verificar se existem produtos vinculados
        result = await db.execute(
            select(func.count(ComandaProdutoDB.id))
            .where(ComandaProdutoDB.comanda_id == id)
        )
        produtos_count = result.scalar()

        if produtos_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível excluir comanda com {produtos_count} produtos vinculados. Remova os produtos primeiro."
            )

        await db.delete(comanda)
        await db.commit()

        # Registrar auditoria de exclusão
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="COMANDA",
            recurso_id=id,
            dados_antigos=comanda,
            request=request
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover comanda: {str(e)}"
        )


# cancelar comanda
@router.put("/comanda/{id}/cancelar", response_model=ComandaResponse, tags=["Comanda"], summary="Cancelar comanda - protegida por JWT e grupo 1")
@limiter.limit("critical")
async def cancelar_comanda(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        # Buscar comanda
        result = await db.execute(select(ComandaDB).where(ComandaDB.id == id))
        comanda = result.scalar_one_or_none()

        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada"
            )

        # Verificar se já está cancelada
        if comanda.status == 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comanda já está cancelada"
            )

        # Verificar se já está fechada (paga)
        if comanda.status == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comanda já está fechada e não pode ser cancelada"
            )

        # Salvar dados antigos para auditoria
        dados_antigos = {
            "id": comanda.id,
            "comanda": comanda.comanda,
            "status": comanda.status,
            "data_hora": comanda.data_hora.isoformat() if comanda.data_hora else None
        }

        # Cancelar a comanda
        comanda.status = 2
        await db.commit()
        await db.refresh(comanda)

        # Registrar auditoria de cancelamento
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CANCEL",
            recurso="comanda",
            recurso_id=comanda.id,
            dados_antigos=dados_antigos,
            request=request
        )

        # Buscar dados relacionados para response
        query = (
            select(ComandaDB, FuncionarioDB, ClienteDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == ComandaDB.funcionario_id)
            .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
            .where(ComandaDB.id == id)
        )
        result = await db.execute(query)
        comanda_data = result.first()
        comanda, funcionario, cliente = comanda_data

        # Construir response
        comanda_response = ComandaResponse(
            id=comanda.id,
            comanda=comanda.comanda,
            data_hora=comanda.data_hora,
            status=comanda.status,
            cliente_id=comanda.cliente_id,
            funcionario_id=comanda.funcionario_id,
            funcionario=FuncionarioResponse(
                id=funcionario.id,
                nome=funcionario.nome,
                matricula=funcionario.matricula,
                cpf=funcionario.cpf,
                telefone=funcionario.telefone,
                grupo=funcionario.grupo
            ) if funcionario else None,
            cliente=ClienteResponse(
                id=cliente.id,
                nome=cliente.nome,
                cpf=cliente.cpf,
                telefone=cliente.telefone
            ) if cliente else None
        )

        return comanda_response

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao cancelar comanda: {str(e)}"
        )


# comanda produtos
# cadastra produto na comanda
@router.post("/comanda/{comanda_id}/produto", response_model=ComandaProdutosResponse, status_code=status.HTTP_201_CREATED, tags=["Comanda"], summary="Adicionar produto à comanda - protegida por JWT")
@limiter.limit("restrictive")
async def add_produto_to_comanda(
    comanda_id: int,
    produto_data: ComandaProdutosCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        # Verificar se a comanda existe
        result = await db.execute(select(ComandaDB).where(ComandaDB.id == comanda_id))
        comanda = result.scalar_one_or_none()

        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada"
            )

        # Verificar se a comanda está aberta
        if comanda.status != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível adicionar produtos a uma comanda fechada ou cancelada"
            )

        # Verificar se o produto existe
        result = await db.execute(select(ProdutoDB).where(ProdutoDB.id == produto_data.produto_id))
        produto = result.scalar_one_or_none()

        if not produto:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Produto não encontrado"
            )

        # Verificar se o funcionário existe
        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.id == produto_data.funcionario_id)
        )
        funcionario = result.scalar_one_or_none()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Funcionário não encontrado"
            )

        # Criar relação comanda-produto
        new_comanda_produto = ComandaProdutoDB(
            comanda_id=comanda_id,
            produto_id=produto_data.produto_id,
            funcionario_id=produto_data.funcionario_id,
            quantidade=produto_data.quantidade,
            valor_unitario=produto_data.valor_unitario
        )

        db.add(new_comanda_produto)
        await db.commit()
        await db.refresh(new_comanda_produto)

        # Registrar auditoria de adição de produto
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="COMANDA_PRODUTO",
            recurso_id=new_comanda_produto.id,
            dados_novos=new_comanda_produto,
            request=request
        )

        return new_comanda_produto

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao adicionar produto à comanda: {str(e)}"
        )


# listar produtos de uma comanda
@router.get("/comanda/{id}/produtos", response_model=List[ComandaProdutosResponse], tags=["Comanda"], summary="Listar produtos de uma comanda - protegida por JWT")
@limiter.limit("moderate")
async def get_comanda_produtos(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        # Verificar se a comanda existe
        result = await db.execute(select(ComandaDB).where(ComandaDB.id == id))
        comanda = result.scalar_one_or_none()

        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada"
            )

        # Buscar produtos da comanda com joins para produto e funcionário
        produtos_query = (
            select(ComandaProdutoDB, ProdutoDB, FuncionarioDB)
            .outerjoin(ProdutoDB, ComandaProdutoDB.produto_id == ProdutoDB.id)
            .outerjoin(FuncionarioDB, ComandaProdutoDB.funcionario_id == FuncionarioDB.id)
            .where(ComandaProdutoDB.comanda_id == id)
        )

        produtos_result = await db.execute(produtos_query)
        produtos = produtos_result.all()

        # Construir response manualmente
        produtos_response = []

        for comanda_produto, produto, funcionario in produtos:
            produto_response = None
            if produto:
                produto_response = ProdutoResponse(
                    id=produto.id,
                    nome=produto.nome,
                    descricao=produto.descricao,
                    foto=produto.foto,
                    valor_unitario=produto.valor_unitario
                )

            funcionario_response = None
            if funcionario:
                funcionario_response = FuncionarioResponse(
                    id=funcionario.id,
                    nome=funcionario.nome,
                    matricula=funcionario.matricula,
                    cpf=funcionario.cpf,
                    telefone=funcionario.telefone,
                    grupo=funcionario.grupo
                )

            comanda_produto_response = ComandaProdutosResponse(
                id=comanda_produto.id,
                comanda_id=comanda_produto.comanda_id,
                funcionario_id=comanda_produto.funcionario_id,
                funcionario=funcionario_response,
                produto_id=comanda_produto.produto_id,
                produto=produto_response,
                quantidade=comanda_produto.quantidade,
                valor_unitario=comanda_produto.valor_unitario
            )
            produtos_response.append(comanda_produto_response)

        return produtos_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar produtos da comanda: {str(e)}"
        )


# atualizar produto de uma comanda
@router.put("/comanda/produto/{id}", response_model=ComandaProdutosResponse, tags=["Comanda"], summary="Atualizar produto na comanda - quantidade e/ou valor - protegida por JWT e grupo 1")
@limiter.limit("restrictive")
async def update_comanda_produto(
    id: int,
    produto_data: ComandaProdutosUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        # Buscar o produto da comanda
        result = await db.execute(select(ComandaProdutoDB).where(ComandaProdutoDB.id == id))
        comanda_produto = result.scalar_one_or_none()

        if not comanda_produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto da comanda não encontrado"
            )

        # armazena uma copia do objeto com os dados atuais
        dados_antigos_obj = comanda_produto.__dict__.copy()
        print("dados_antigos_obj:", dados_antigos_obj)

        # Atualizar campos se fornecidos
        if produto_data.quantidade is not None:
            if produto_data.quantidade <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quantidade deve ser maior que zero"
                )
            comanda_produto.quantidade = produto_data.quantidade

        if produto_data.valor_unitario is not None:
            if produto_data.valor_unitario <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Valor unitário deve ser maior que zero"
                )
            comanda_produto.valor_unitario = produto_data.valor_unitario

        await db.commit()
        await db.refresh(comanda_produto)

        # Registrar auditoria de atualização
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="COMANDA_PRODUTO",
            recurso_id=comanda_produto.id,
            dados_antigos=dados_antigos_obj,
            dados_novos=comanda_produto,
            request=request
        )

        return comanda_produto

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar produto da comanda: {str(e)}"
        )


# deletar produto da comanda
@router.delete("/comanda/produto/{id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Comanda"], summary="Remover produto da comanda - protegida por JWT e grupo 1")
@limiter.limit("critical")
async def remove_produto_from_comanda(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        # verificar se o produto da comanda existe
        result = await db.execute(select(ComandaProdutoDB).where(ComandaProdutoDB.id == id))
        comanda_produto = result.scalar_one_or_none()

        if not comanda_produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto da comanda não encontrado"
            )

        await db.delete(comanda_produto)
        await db.commit()

        # Registrar auditoria de exclusão
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="COMANDA_PRODUTO",
            recurso_id=id,
            dados_antigos=comanda_produto,
            request=request
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover produto da comanda: {str(e)}"
        )