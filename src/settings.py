# Artur Bonamigo

from dotenv import load_dotenv, find_dotenv
import os

# localiza o arquivo de .env
dotenv_file = find_dotenv()

# Carrega o arquivo .env
load_dotenv(dotenv_file)

# Configurações da API - com fallback para valores padrão
HOST = os.getenv("HOST", "0.0.0.0")
PORT = os.getenv("PORT", "8000")
RELOAD = os.getenv("RELOAD", True)

# Configurações banco de dados
DB_SGDB = os.getenv("DB_SGDB")
DB_NAME = os.getenv("DB_NAME")

# Caso seja diferente de sqlite
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# Ajusta STR_DATABASE conforme gerenciador escolhido
if DB_SGDB == 'sqlite':  # SQLite
    # habilita foreign keys - integridade referencial - pragma
    STR_DATABASE = f"sqlite:///{DB_NAME}.db?foreign_keys=1"

elif DB_SGDB == 'mysql':  # MySQL
    import pymysql
    STR_DATABASE = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"

elif DB_SGDB == 'mssql':  # SQL Server
    import pymssql
    STR_DATABASE = f"mssql+pymssql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8"

elif DB_SGDB == 'postgresql':  # PostgreSQL
    import psycopg2
    STR_DATABASE = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

else:  # SQLite padrão
    STR_DATABASE = f"sqlite:///apiDatabase.db?foreign_keys=1"

# Configurações de database assíncrono
# Converte string de conexão para async se necessário
if STR_DATABASE.startswith("sqlite:///"):
    ASYNC_STR_DATABASE = STR_DATABASE.replace("sqlite:///", "sqlite+aiosqlite:///")

elif STR_DATABASE.startswith("sqlite://"):
    ASYNC_STR_DATABASE = STR_DATABASE.replace("sqlite://", "sqlite+aiosqlite:///")

elif DB_SGDB == 'mysql':  # MySQL
    ASYNC_STR_DATABASE = STR_DATABASE.replace("mysql+pymysql://", "mysql+aiomysql://")

elif DB_SGDB == 'mssql':  # SQL Server
    # Nota: aiomssql não está disponível, mantém síncrono
    ASYNC_STR_DATABASE = STR_DATABASE

elif DB_SGDB == 'postgresql':  # PostgreSQL
    ASYNC_STR_DATABASE = STR_DATABASE.replace("postgresql://", "postgresql+asyncpg://")

else:
    # Para outros bancos, mantém a string original
    ASYNC_STR_DATABASE = STR_DATABASE

#Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY", "9b1c8e5f4a6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7g8h9i0jjf9hg32h3dq")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# Configurações de CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else "*"