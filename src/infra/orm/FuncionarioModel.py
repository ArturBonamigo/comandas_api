# Artur Bonamigo

from infra import database
from sqlalchemy import Column, VARCHAR, CHAR, Integer

# ORM

class FuncionarioDB(database.Base):
    __tablename__ = 'tb_funcionario'
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nome = Column(VARCHAR(100), nullable=False)
    matricula = Column(CHAR(10), nullable=False)
    cpf = Column(CHAR(11), unique=True, nullable=False, index=True)
    telefone = Column(CHAR(11), nullable=False)
    grupo = Column(Integer, nullable=False)
    senha = Column(VARCHAR(200), nullable=False)

def __init__(self, id, nome, matricula, cpf, telefone, grupo, senha):
    self.id = id
    self.nome = nome
    self.matricula = matricula
    self.cpf = cpf
    self.telefone = telefone
    self.grupo = grupo
    self.senha = senha