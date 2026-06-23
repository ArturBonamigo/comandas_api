from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.schemas.AuthSchema import FuncionarioAuth
from domain.schemas.ClienteSchema import ClienteResponse
from domain.schemas.FuncionarioSchema import FuncionarioResponse
from domain.schemas.ProdutoSchema import ProdutoResponse
from domain.schemas.RecebimentoSchema import (
    RecebimentoComandaDetalhe,
    RecebimentoComandaResponse,
    RecebimentoComprovante,
    RecebimentoCreate,
    RecebimentoDashboardItem,
    RecebimentoDetalhe,
    RecebimentoProdutoDetalhe,
    RecebimentoResponse,
)
from infra.database import get_async_db
from infra.dependencies import require_group
from infra.orm.ClienteModel import ClienteDB
from infra.orm.ComandaModel import ComandaDB, ComandaProdutoDB
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.orm.ProdutoModel import ProdutoDB
from infra.orm.RecebimentoModel import RecebimentoComandaDB, RecebimentoDB
from infra.rate_limit import limiter
from services.AuditoriaService import AuditoriaService

router = APIRouter()


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _cliente_response(cliente):
    if not cliente:
        return None
    return ClienteResponse(
        id=cliente.id,
        nome=cliente.nome,
        cpf=cliente.cpf,
        telefone=cliente.telefone,
    )


def _funcionario_response(funcionario):
    if not funcionario:
        return None
    return FuncionarioResponse(
        id=funcionario.id,
        nome=funcionario.nome,
        matricula=funcionario.matricula,
        cpf=funcionario.cpf,
        telefone=funcionario.telefone,
        grupo=funcionario.grupo,
    )


def _produto_response(produto):
    if not produto:
        return None
    return ProdutoResponse(
        id=produto.id,
        nome=produto.nome,
        descricao=produto.descricao,
        foto=produto.foto,
        valor_unitario=produto.valor_unitario,
    )


def _parse_ids(ids: str) -> List[int]:
    try:
        parsed_ids = [int(item.strip()) for item in ids.split(",") if item.strip()]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="IDs de comandas invalidos",
        )

    parsed_ids = list(dict.fromkeys(parsed_ids))

    if not parsed_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe ao menos uma comanda",
        )

    return parsed_ids


async def _montar_detalhe_comandas(
    comanda_ids: List[int],
    db: AsyncSession,
    exigir_abertas: bool = False,
) -> RecebimentoDetalhe:
    comandas_result = await db.execute(
        select(ComandaDB, ClienteDB)
        .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
        .where(ComandaDB.id.in_(comanda_ids))
    )
    comandas_rows = comandas_result.all()
    comandas_por_id = {comanda.id: (comanda, cliente) for comanda, cliente in comandas_rows}

    ids_nao_encontrados = [id for id in comanda_ids if id not in comandas_por_id]
    if ids_nao_encontrados:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comanda(s) nao encontrada(s): {ids_nao_encontrados}",
        )

    produtos_result = await db.execute(
        select(ComandaProdutoDB, ProdutoDB)
        .outerjoin(ProdutoDB, ProdutoDB.id == ComandaProdutoDB.produto_id)
        .where(ComandaProdutoDB.comanda_id.in_(comanda_ids))
        .order_by(ComandaProdutoDB.comanda_id, ComandaProdutoDB.id)
    )

    produtos_por_comanda = defaultdict(list)
    totais_por_comanda = defaultdict(lambda: Decimal("0"))

    for comanda_produto, produto in produtos_result.all():
        valor_total = _to_decimal(comanda_produto.valor_unitario) * Decimal(comanda_produto.quantidade)
        totais_por_comanda[comanda_produto.comanda_id] += valor_total
        produtos_por_comanda[comanda_produto.comanda_id].append(
            RecebimentoProdutoDetalhe(
                id=comanda_produto.id,
                produto_id=comanda_produto.produto_id,
                produto=_produto_response(produto),
                quantidade=comanda_produto.quantidade,
                valor_unitario=float(comanda_produto.valor_unitario),
                valor_total=float(valor_total),
            )
        )

    detalhes = []
    valor_bruto = Decimal("0")

    for comanda_id in comanda_ids:
        comanda, cliente = comandas_por_id[comanda_id]

        if exigir_abertas and comanda.status != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Comanda {comanda.comanda} nao esta aberta",
            )

        total_comanda = totais_por_comanda[comanda.id]
        valor_bruto += total_comanda

        detalhes.append(
            RecebimentoComandaDetalhe(
                id=comanda.id,
                comanda=comanda.comanda,
                data_hora=comanda.data_hora,
                status=comanda.status,
                cliente_id=comanda.cliente_id,
                cliente=_cliente_response(cliente),
                produtos=produtos_por_comanda[comanda.id],
                total=float(total_comanda),
            )
        )

    return RecebimentoDetalhe(
        comandas=detalhes,
        valor_bruto=float(valor_bruto),
    )


async def _montar_recebimento_response(recebimento_id: int, db: AsyncSession) -> RecebimentoResponse:
    recebimento_result = await db.execute(
        select(RecebimentoDB, FuncionarioDB)
        .outerjoin(FuncionarioDB, FuncionarioDB.id == RecebimentoDB.funcionario_id)
        .where(RecebimentoDB.id == recebimento_id)
    )
    row = recebimento_result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recebimento nao encontrado",
        )

    recebimento, funcionario = row

    comandas_result = await db.execute(
        select(RecebimentoComandaDB)
        .where(RecebimentoComandaDB.recebimento_id == recebimento.id)
        .order_by(RecebimentoComandaDB.id)
    )
    comandas = [
        RecebimentoComandaResponse(
            id=item.id,
            recebimento_id=item.recebimento_id,
            comanda_id=item.comanda_id,
            valor_comanda=float(item.valor_comanda),
        )
        for item in comandas_result.scalars().all()
    ]

    return RecebimentoResponse(
        id=recebimento.id,
        funcionario_id=recebimento.funcionario_id,
        funcionario=_funcionario_response(funcionario),
        data_hora=recebimento.data_hora,
        valor_bruto=float(recebimento.valor_bruto),
        desconto=float(recebimento.desconto),
        acrescimo=float(recebimento.acrescimo),
        valor_final=float(recebimento.valor_final),
        comandas=comandas,
    )


@router.get(
    "/recebimento/dashboard",
    response_model=List[RecebimentoDashboardItem],
    tags=["Recebimento"],
    summary="Dashboard do caixa com comandas abertas - protegida por JWT e grupos 1 e 3",
)
@limiter.limit("moderate")
async def get_recebimento_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):
    try:
        total_expr = func.coalesce(
            func.sum(ComandaProdutoDB.quantidade * ComandaProdutoDB.valor_unitario),
            0,
        )
        quantidade_expr = func.coalesce(func.sum(ComandaProdutoDB.quantidade), 0)

        result = await db.execute(
            select(ComandaDB, ClienteDB, total_expr, quantidade_expr)
            .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
            .outerjoin(ComandaProdutoDB, ComandaProdutoDB.comanda_id == ComandaDB.id)
            .where(ComandaDB.status == 0)
            .group_by(
                ComandaDB.id,
                ComandaDB.comanda,
                ComandaDB.data_hora,
                ComandaDB.status,
                ComandaDB.cliente_id,
                ComandaDB.funcionario_id,
                ClienteDB.id,
                ClienteDB.nome,
                ClienteDB.cpf,
                ClienteDB.telefone,
            )
            .order_by(ComandaDB.data_hora)
        )

        dashboard = []
        for comanda, cliente, total, quantidade_itens in result.all():
            dashboard.append(
                RecebimentoDashboardItem(
                    id=comanda.id,
                    comanda=comanda.comanda,
                    data_hora=comanda.data_hora,
                    status=comanda.status,
                    cliente_id=comanda.cliente_id,
                    cliente=_cliente_response(cliente),
                    total=float(total or 0),
                    quantidade_itens=int(quantidade_itens or 0),
                )
            )

        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao carregar dashboard do caixa: {str(e)}",
        )


@router.get(
    "/recebimento/comandas/detalhe/{ids}",
    response_model=RecebimentoDetalhe,
    tags=["Recebimento"],
    summary="Detalhar comandas selecionadas para recebimento - protegida por JWT e grupos 1 e 3",
)
@limiter.limit("moderate")
async def get_detalhe_comandas_recebimento(
    ids: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):
    comanda_ids = _parse_ids(ids)
    return await _montar_detalhe_comandas(comanda_ids, db, exigir_abertas=True)


@router.post(
    "/recebimento/completo",
    response_model=RecebimentoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Recebimento"],
    summary="Processar recebimento e fechar comandas - protegida por JWT e grupos 1 e 3",
)
@limiter.limit("restrictive")
async def receber_comandas(
    recebimento_data: RecebimentoCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):
    try:
        comanda_ids = list(dict.fromkeys(recebimento_data.comanda_ids))
        detalhes = await _montar_detalhe_comandas(comanda_ids, db, exigir_abertas=True)

        valor_bruto = _to_decimal(detalhes.valor_bruto)
        desconto = _to_decimal(recebimento_data.desconto)
        acrescimo = _to_decimal(recebimento_data.acrescimo)
        valor_final = valor_bruto - desconto + acrescimo

        if valor_bruto <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao e possivel receber comandas sem consumo",
            )

        if desconto > valor_bruto + acrescimo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Desconto maior que o valor total",
            )

        if valor_final < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valor final nao pode ser negativo",
            )

        recebimento = RecebimentoDB(
            funcionario_id=current_user.id,
            data_hora=datetime.now(),
            valor_bruto=valor_bruto,
            desconto=desconto,
            acrescimo=acrescimo,
            valor_final=valor_final,
        )

        db.add(recebimento)
        await db.flush()

        for comanda_detalhe in detalhes.comandas:
            db.add(
                RecebimentoComandaDB(
                    recebimento_id=recebimento.id,
                    comanda_id=comanda_detalhe.id,
                    valor_comanda=_to_decimal(comanda_detalhe.total),
                )
            )

            comanda = await db.get(ComandaDB, comanda_detalhe.id)
            comanda.status = 1

        await db.commit()
        await db.refresh(recebimento)

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="RECEBIMENTO",
            recurso_id=recebimento.id,
            dados_novos={
                "comanda_ids": comanda_ids,
                "valor_bruto": float(valor_bruto),
                "desconto": float(desconto),
                "acrescimo": float(acrescimo),
                "valor_final": float(valor_final),
            },
            request=request,
        )

        return await _montar_recebimento_response(recebimento.id, db)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar recebimento: {str(e)}",
        )


@router.get(
    "/recebimento/comprovante/{id}",
    response_model=RecebimentoComprovante,
    tags=["Recebimento"],
    summary="Gerar comprovante de recebimento - protegida por JWT e grupos 1 e 3",
)
@limiter.limit("moderate")
async def get_comprovante_recebimento(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):
    recebimento = await _montar_recebimento_response(id, db)
    comanda_ids = [item.comanda_id for item in recebimento.comandas]
    detalhes = await _montar_detalhe_comandas(comanda_ids, db, exigir_abertas=False)

    return RecebimentoComprovante(
        recebimento=recebimento,
        detalhes=detalhes,
    )
