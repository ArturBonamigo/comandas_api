# Artur Bonamigo

from fastapi import FastAPI
from settings import HOST, PORT, RELOAD
import uvicorn

# import das classes com as rotas/endpoints
from routers import AuthRouter
from routers import FuncionarioRouter
from routers import ClienteRouter
from routers import ProdutoRouter

# lifespan - ciclo de vida da aplicação
from infra import database
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # executa no startup
    print("API has started")
    # cria, caso não existam, as tabelas de todos os modelos que encontrar na aplicação (importados)
    await database.cria_tabelas()
    yield
    # executa no shutdown
    print("API is shutting down")

# cria a aplicação FastAPI com o contexto de vida
app = FastAPI(lifespan=lifespan)

# rota padrão
@app.get("/", tags=["Root"], status_code=200)
async def root():
    return {"detail":"API Pastelaria", "Swagger UI": "http://127.0.0.1:8000/docs", "ReDoc":
"http://127.0.0.1:8000/redoc" }

# incluir as rotas/endpoints no FastAPI
app.include_router(AuthRouter.router)
app.include_router(FuncionarioRouter.router)
app.include_router(ClienteRouter.router)
app.include_router(ProdutoRouter.router)

if __name__ == "__main__":
    uvicorn.run('main:app', host=HOST, port=int(PORT), reload=RELOAD)