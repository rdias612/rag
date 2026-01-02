"""
Módulo de rotas da API.

Esse módulo exporta um Blueprint único que agrega todos os sub-blueprints
por domínio, mantendo compatibilidade retroativa com o código existente.
"""
from flask import Blueprint
from apscheduler.schedulers.background import BackgroundScheduler

from src.core.conversation import conversation_manager
from src.core.logger import api_logger

# Criar blueprint principal (mantém compatibilidade com routes.py original)
api = Blueprint("api", __name__)

# Importar sub-blueprints
from src.api.routes.health import health_bp
from src.api.routes.query import query_bp
from src.api.routes.sessions import sessions_bp
from src.api.routes.documents import documents_bp
from src.api.routes.prompts import prompts_bp
from src.api.routes.metrics import metrics_bp
from src.api.routes.admin import admin_bp
from src.api.routes.quality_metrics import quality_bp
from src.api.routes.logs import init_logs_routes

# Registrar sub-blueprints no blueprint principal
api.register_blueprint(health_bp)  # /health, /stats, /collections
api.register_blueprint(query_bp)   # /query, /query/stream, /search, /chat
api.register_blueprint(sessions_bp, url_prefix="/chat")  # /chat/sessions, /chat/new
api.register_blueprint(documents_bp)  # /ingest/*, /documents/*
api.register_blueprint(prompts_bp, url_prefix="/prompts")  # /prompts/*
api.register_blueprint(metrics_bp)  # /cache/*, /classify, /evaluate, /hyde/*, /metrics
api.register_blueprint(quality_bp, url_prefix="/metrics/quality")  # /stats, /recent, /trends, /top-worst, /evaluate
api.register_blueprint(admin_bp)  # /embeddings/*, /admin/*

# Registrar rota de logs (recebe logs do frontend)
init_logs_routes(api)

# =============================================================================
# Agendador de Tarefas em Background (APScheduler)
# =============================================================================
scheduler = BackgroundScheduler()


def _run_session_cleanup():
    """Wrapper para a tarefa de limpeza periódica de sessões."""
    try:
        count = conversation_manager.cleanup_expired_sessions()
        if count > 0:
            api_logger.debug(f"Background cleanup: {count} sessions removed")
    except Exception as e:
        api_logger.error(f"Error in background session cleanup: {e}")


# Adicionar job para rodar a cada 10 minutos
scheduler.add_job(_run_session_cleanup, 'interval', minutes=10, id='session_cleanup')
scheduler.start()
