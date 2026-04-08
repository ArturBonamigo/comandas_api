from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from datetime import datetime, timezone
import psutil

from infra.database import get_db
from infra.orm.FuncionarioModel import FuncionarioDB

router = APIRouter()


# Health check básico
@router.get(
    "/health",
    tags=["Health"],
    summary="Health check básico - Verificação básica de saúde da API - Usado por load balancers e orquestradores"
)
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "comandas-api",
        "version": "1.0.0"
    }


# Health check do banco de dados
@router.get(
    "/health/database",
    tags=["Health"],
    summary="Health check do banco de dados - Verifica conexão com banco de dados - Testa se consegue executar query simples"
)
async def database_health():
    db = None
    try:
        db = next(get_db())

        result = db.execute(text("SELECT 1 as test")).fetchone()

        if result and result[0] == 1:
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )

    finally:
        if db:
            db.close()


# Health check das tabelas
@router.get(
    "/health/database/tables",
    tags=["Health"],
    summary="Health check das tabelas - Verifica se tabelas críticas existem e têm dados"
)
async def database_tables_health():
    db = None
    try:
        db = next(get_db())

        checks = {}

        # Tabela funcionários
        try:
            count = db.query(FuncionarioDB).count()
            checks["funcionarios"] = {
                "status": "healthy",
                "count": count
            }
        except Exception as e:
            checks["funcionarios"] = {
                "status": "error",
                "error": str(e)
            }

        all_healthy = all(
            check["status"] == "healthy"
            for check in checks.values()
        )

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "tables": checks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database tables check failed: {str(e)}"
        )

    finally:
        if db:
            db.close()


# Health check do sistema
@router.get(
    "/health/system",
    tags=["Health"],
    summary="Health check do sistema - Verifica recursos do sistema (memória, disco, CPU)"
)
async def system_health():
    try:
        memory = psutil.virtual_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "status": "healthy" if memory.percent < 90 else "warning"
        }

        disk = psutil.disk_usage(".")
        disk_percent = (disk.used / disk.total) * 100
        disk_info = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk_percent,
            "status": "healthy" if disk_percent < 90 else "warning"
        }

        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_info = {
            "percent": cpu_percent,
            "count": psutil.cpu_count(),
            "status": "healthy" if cpu_percent < 80 else "warning"
        }

        all_healthy = all([
            memory_info["status"] == "healthy",
            disk_info["status"] == "healthy",
            cpu_info["status"] == "healthy"
        ])

        return {
            "status": "healthy" if all_healthy else "warning",
            "memory": memory_info,
            "disk": disk_info,
            "cpu": cpu_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"System health check failed: {str(e)}"
        )


# Health check completo
@router.get(
    "/health/full",
    tags=["Health"],
    summary="Health check completo - Verificação completa de todos os componentes"
)
async def full_health_check():
    try:
        checks = {}

        # API
        checks["api"] = {"status": "healthy", "message": "API responding"}

        # Database
        try:
            db = next(get_db())
            db.execute(text("SELECT 1"))
            checks["database"] = {
                "status": "healthy",
                "message": "Database connected"
            }
            db.close()
        except Exception as e:
            checks["database"] = {
                "status": "unhealthy",
                "message": str(e)
            }

        # System
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(".")
            cpu = psutil.cpu_percent(interval=1)

            system_healthy = (
                memory.percent < 90 and
                (disk.used / disk.total) * 100 < 90 and
                cpu < 80
            )

            checks["system"] = {
                "status": "healthy" if system_healthy else "warning",
                "memory_percent": memory.percent,
                "disk_percent": (disk.used / disk.total) * 100,
                "cpu_percent": cpu
            }

        except Exception as e:
            checks["system"] = {
                "status": "error",
                "message": str(e)
            }

        # Status geral
        overall_status = "healthy"
        for check in checks.values():
            if check["status"] == "unhealthy":
                overall_status = "unhealthy"
                break
            elif check["status"] == "warning" and overall_status == "healthy":
                overall_status = "warning"
            elif check["status"] == "error":
                overall_status = "unhealthy"
                break

        return {
            "status": overall_status,
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "comandas-api",
            "version": "1.0.0"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Full health check failed: {str(e)}"
        )


# Readiness probe
@router.get(
    "/ready",
    tags=["Health"],
    summary="Readiness probe - Verifica se API está pronta para receber tráfego"
)
async def readiness_check():
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready - database unavailable: {str(e)}"
        )

    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Liveness probe
@router.get(
    "/live",
    tags=["Health"],
    summary="Liveness probe - Verifica se API está viva (não travada)"
)
async def liveness_check():
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": "running"
    }