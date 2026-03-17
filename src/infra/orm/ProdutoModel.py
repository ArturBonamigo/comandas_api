# Artur Bonamigo

from infra import database
from sqlalchemy import BLOB, Column, VARCHAR, CHAR, Integer, Float

# ORM

class ProdutoDB(database.Base):
    __tablename__ = 'tb_produto'

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nome = Column(VARCHAR(100), nullable=False)
    descricao = Column(VARCHAR(200), nullable=False)
    foto = Column(BLOB, nullable=True)
    valor_unitario = Column(Float, nullable=False)

def __init__(self, id, nome, descricao, foto, valor_unitario):
    self.id = id
    self.nome = nome
    self.descricao = descricao
    self.foto = foto
    self.valor_unitario = valor_unitario