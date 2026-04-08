from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from infra.database import Base

class AuditoriaDB(Base):
    """Modelo para registrar auditoria de acessos e ações"""
    __tablename__ = "tb_auditoria"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    funcionario_id = Column(Integer, ForeignKey("tb_funcionario.id", ondelete="RESTRICT"), nullable=False)
    acao = Column(String(50), nullable=False) # LOGIN, LOGOUT, CREATE, UPDATE, DELETE, CANCEL, etc.
    recurso = Column(String(100), nullable=False) # comanda, recebimento, produto, etc.
    recurso_id = Column(Integer, nullable=True) # ID do recurso específico
    dados_antigos = Column(Text, nullable=True) # JSON com dados antes da alteração
    dados_novos = Column(Text, nullable=True) # JSON com dados após a alteração
    ip_address = Column(String(45), nullable=True) # IP do cliente
    user_agent = Column(Text, nullable=True) # User agent do navegador
    data_hora = Column(DateTime, nullable=False)