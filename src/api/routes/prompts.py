"""
Blueprint de gerenciamento de prompts.

Endpoints:
- GET /prompts - Lista prompts
- GET /prompts/<id> - Detalhes do prompt
- POST /prompts - Cria prompt
- PUT /prompts/<id> - Atualiza prompt
- DELETE /prompts/<id> - Deleta prompt
- GET /prompts/<id>/can-delete - Verifica se pode deletar
- GET /prompts/categories - Lista categorias
"""
import time
from flask import Blueprint, request, jsonify

from src.data.database import (
    list_prompts,
    get_prompt_by_id,
    create_prompt,
    update_prompt_full,
    delete_prompt_safe,
    can_delete_prompt,
    CRITICAL_CATEGORIES
)
from src.core.logger import api_logger, log_api_request, log_api_response, log_api_input

prompts_bp = Blueprint("prompts", __name__)


@prompts_bp.route("", methods=["GET"])
def get_all_prompts():
    """Lista todos os prompts disponíveis."""
    start_time = time.time()
    log_api_request("/api/prompts", "GET")
    
    try:
        prompts = list_prompts()
        log_api_response("/api/prompts", 200, time.time() - start_time)
        
        return jsonify({
            "prompts": prompts,
            "count": len(prompts)
        })
    except Exception as e:
        api_logger.error(f"Error in /prompts: {e}")
        log_api_response("/api/prompts", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@prompts_bp.route("/<int:prompt_id>", methods=["GET"])
def get_prompt_detail(prompt_id: int):
    """Retorna detalhes completos de um prompt específico."""
    start_time = time.time()
    log_api_request(f"/api/prompts/{prompt_id}", "GET")
    
    try:
        prompt = get_prompt_by_id(prompt_id)
        
        if not prompt:
            log_api_response(f"/api/prompts/{prompt_id}", 404, time.time() - start_time)
            return jsonify({"error": "Prompt não encontrado"}), 404
        
        log_api_response(f"/api/prompts/{prompt_id}", 200, time.time() - start_time)
        return jsonify(prompt)
        
    except Exception as e:
        api_logger.error(f"Error in /prompts/{prompt_id}: {e}")
        log_api_response(f"/api/prompts/{prompt_id}", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@prompts_bp.route("", methods=["POST"])
def create_new_prompt():
    """Cria um novo prompt."""
    start_time = time.time()
    data = request.get_json() or {}
    log_api_input("/api/prompts", "POST", {**data, "template": "..."})
    
    required_fields = ["name", "template", "category"]
    missing_fields = [f for f in required_fields if f not in data]
    
    if missing_fields:
        log_api_response("/api/prompts", 400, time.time() - start_time)
        return jsonify({
            "error": "Campos obrigatórios faltando",
            "missing_fields": missing_fields
        }), 400
    
    try:
        success, prompt_id, error_msg = create_prompt(
            name=data["name"],
            template=data["template"],
            category=data["category"],
            description=data.get("description"),
            priority=data.get("priority", 100),
            tags=data.get("tags", []),
            use_case=data.get("use_case"),
            created_by="user"
        )
        
        if not success:
            log_api_response("/api/prompts", 400, time.time() - start_time)
            return jsonify({"error": error_msg}), 400
        
        log_api_response("/api/prompts", 201, time.time() - start_time)
        return jsonify({
            "success": True,
            "prompt_id": prompt_id,
            "message": "Prompt criado com sucesso"
        }), 201
        
    except Exception as e:
        api_logger.error(f"Error creating prompt: {e}")
        log_api_response("/api/prompts", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@prompts_bp.route("/<int:prompt_id>", methods=["PUT"])
def update_prompt_endpoint(prompt_id: int):
    """Atualiza um prompt existente."""
    start_time = time.time()
    data = request.get_json() or {}
    log_api_input(f"/api/prompts/{prompt_id}", "PUT", data)
    
    try:
        success, error_msg = update_prompt_full(
            prompt_id=prompt_id,
            template=data.get("template"),
            description=data.get("description"),
            priority=data.get("priority"),
            tags=data.get("tags"),
            use_case=data.get("use_case"),
            is_active=data.get("is_active")
        )
        
        if not success:
            log_api_response(f"/api/prompts/{prompt_id}", 400, time.time() - start_time)
            return jsonify({"error": error_msg}), 400
        
        log_api_response(f"/api/prompts/{prompt_id}", 200, time.time() - start_time)
        return jsonify({
            "success": True,
            "message": "Prompt atualizado com sucesso"
        })
        
    except Exception as e:
        api_logger.error(f"Error updating prompt {prompt_id}: {e}")
        log_api_response(f"/api/prompts/{prompt_id}", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@prompts_bp.route("/<int:prompt_id>/can-delete", methods=["GET"])
def check_can_delete_prompt(prompt_id: int):
    """Verifica se um prompt pode ser deletado."""
    start_time = time.time()
    log_api_request(f"/api/prompts/{prompt_id}/can-delete", "GET")
    
    try:
        can_delete, reason = can_delete_prompt(prompt_id)
        
        log_api_response(f"/api/prompts/{prompt_id}/can-delete", 200, time.time() - start_time)
        
        return jsonify({
            "can_delete": can_delete,
            "reason": reason
        })
    except Exception as e:
        api_logger.error(f"Error checking delete permission for prompt {prompt_id}: {e}")
        log_api_response(f"/api/prompts/{prompt_id}/can-delete", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@prompts_bp.route("/<int:prompt_id>", methods=["DELETE"])
def delete_prompt_endpoint(prompt_id: int):
    """Deleta um prompt (com validação)."""
    start_time = time.time()
    log_api_request(f"/api/prompts/{prompt_id}", "DELETE")
    
    try:
        success, error_msg = delete_prompt_safe(prompt_id)
        
        if not success:
            log_api_response(f"/api/prompts/{prompt_id}", 400, time.time() - start_time)
            return jsonify({"error": error_msg}), 400
        
        log_api_response(f"/api/prompts/{prompt_id}", 200, time.time() - start_time)
        return jsonify({
            "success": True,
            "message": "Prompt deletado com sucesso"
        })
        
    except Exception as e:
        api_logger.error(f"Error deleting prompt {prompt_id}: {e}")
        log_api_response(f"/api/prompts/{prompt_id}", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@prompts_bp.route("/categories", methods=["GET"])
def get_prompt_categories():
    """Retorna as categorias disponíveis e suas descrições."""
    start_time = time.time()
    log_api_request("/api/prompts/categories", "GET")
    
    categories = {
        **CRITICAL_CATEGORIES,
        "instruction": "Instruções específicas por tipo de pergunta"
    }
    
    log_api_response("/api/prompts/categories", 200, time.time() - start_time)
    
    return jsonify({"categories": categories})
