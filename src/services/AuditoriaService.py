from sqlalchemy.orm import Session
from fastapi import Request
from typing import Optional, Dict, Any
from datetime import datetime
import json
from infra.orm.AuditoriaModel import AuditoriaDB

class AuditoriaService:
    """Serviço para registrar auditoria de acessos e ações"""
    
    @staticmethod
    def registrar_acao(db: Session, funcionario_id: int, acao: str, recurso: str, recurso_id: Optional[int] = None, dados_antigos: Optional[Dict[str, Any]] = None,
        dados_novos: Optional[Dict[str, Any]] = None, request: Optional[Request] = None
    ) -> bool:
        try:
            # Capturar informações da requisição
            ip_address = None
            user_agent = None
            
            if request:
                # IP do cliente
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    ip_address = forwarded_for.split(",")[0].strip()
                else:
                    ip_address = request.client.host
            
                # User Agent
                user_agent = request.headers.get("User-Agent")
            
            # dados_novos - Converter objeto SQLAlchemy para dicionário antes de serializar
            if dados_novos:
                if hasattr(dados_novos, '__dict__'):
                    # É um objeto SQLAlchemy, converter para dicionário
                    dados_novos_dict = {
                        column.name: getattr(dados_novos, column.name)
                        for column in dados_novos.__table__.columns
                    }
                    dados_novos_json = json.dumps(dados_novos_dict, default=str)
                else:
                    # Já é um dicionário ou JSON serializável
                    dados_novos_json = json.dumps(dados_novos, default=str)
            else:
                dados_novos_json = None
            
            # dados_antigos - Converter objeto SQLAlchemy para dicionário antes de serializar
            if dados_antigos:
                if hasattr(dados_antigos, '__dict__'):
                    # É um objeto SQLAlchemy, converter para dicionário
                    dados_antigos_dict = {
                        column.name: getattr(dados_antigos, column.name)
                        for column in dados_antigos.__table__.columns
                    }
                    dados_antigos_json = json.dumps(dados_antigos_dict, default=str)
                else:
                    # Já é um dicionário ou JSON serializável
                    dados_antigos_json = json.dumps(dados_antigos, default=str)
            else:
                dados_antigos_json = None
            
            # Criar registro de auditoria
            auditoria = AuditoriaDB(funcionario_id=funcionario_id, acao=acao, recurso=recurso, recurso_id=recurso_id, dados_antigos=dados_antigos_json, dados_novos=dados_novos_json, ip_address=ip_address, user_agent=user_agent, data_hora=datetime.now() )
            
            db.add(auditoria)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            return False