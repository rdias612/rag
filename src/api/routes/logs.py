"""
Rota para receber logs do frontend.
"""
import json
import logging
from flask import request, jsonify

webserver_logger = logging.getLogger("rag.webserver")


def init_logs_routes(bp):
    """Inicializa as rotas de logs."""
    
    @bp.route("/logs", methods=["POST"])
    def receive_logs():
        """
        Recebe logs do frontend e escreve em webserver.log.
        
        Body esperado:
        {
            "logs": [
                {
                    "timestamp": "2026-01-02T16:00:00.000Z",
                    "level": "INFO",
                    "component": "App",
                    "message": "User clicked button",
                    "data": {...}
                }
            ]
        }
        """
        try:
            data = request.get_json()
            
            if not data or "logs" not in data:
                return jsonify({"error": "Missing 'logs' field"}), 400
            
            logs = data["logs"]
            
            if not isinstance(logs, list):
                return jsonify({"error": "'logs' must be an array"}), 400
            
            # Escrever cada log no webserver.log
            for log_entry in logs:
                timestamp = log_entry.get("timestamp", "")
                level = log_entry.get("level", "INFO")
                component = log_entry.get("component", "unknown")
                message = log_entry.get("message", "")
                log_data = log_entry.get("data")
                
                # Construir mensagem de log
                if log_data:
                    data_str = json.dumps(log_data, ensure_ascii=False, default=str)
                    log_message = f"{message} {data_str}"
                else:
                    log_message = message
                
                # Mapear níveis do frontend para logging levels
                level_map = {
                    "DEBUG": webserver_logger.debug,
                    "INFO": webserver_logger.info,
                    "WARNING": webserver_logger.warning,
                    "ERROR": webserver_logger.error
                }
                
                log_func = level_map.get(level, webserver_logger.info)
                log_func("%s %s %s %s", timestamp, level, component, log_message)
            
            return jsonify({"status": "ok", "logs_received": len(logs)}), 200
            
        except Exception as e:
            webserver_logger.exception("Error processing logs: %s", e)
            return jsonify({"error": str(e)}), 500
