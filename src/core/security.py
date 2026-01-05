"""
Módulo de segurança para proteção em trânsito e headers de segurança.

Implementa:
- Forçamento de HTTPS
- Headers de segurança (HSTS, CSP, XSS Protection, etc.)
- Proteção contra ataques comuns
"""
import ssl

from flask import Flask, request, redirect
from functools import wraps
from src.config import (
    ENABLE_HTTPS,
    SSL_PROTOCOL,
    SSL_CIPHERS,
    SSL_CERT_PATH,
    SSL_KEY_PATH
)


print("rag.security")


class SecurityMiddleware:
    """
    Middleware de segurança para proteção em trânsito.
    """
    
    def __init__(self, app: Flask):
        self.app = app
        self.setup_security_headers()
        self.setup_https_enforcement()
    
    def setup_security_headers(self):
        """
        Configura headers de segurança HTTP.
        """
        @self.app.after_request
        def add_security_headers(response):
            """
            Adiciona headers de segurança a todas as respostas.
            
            Headers incluídos:
            - Strict-Transport-Security (HSTS): Força HTTPS
            - X-Content-Type-Options: Previne MIME type sniffing
            - X-Frame-Options: Previne clickjacking
            - X-XSS-Protection: Ativa proteção XSS do navegador
            - Content-Security-Policy: Controla fontes de conteúdo
            - Referrer-Policy: Controla informações de referer
            - Permissions-Policy: Controla APIs do navegador
            """
            
            # Strict-Transport-Security (HSTS)
            # Força o uso de HTTPS por 1 ano (31536000 segundos)
            # includeSubDomains: Aplica a todos os subdomínios
            # preload: Permite inclusão na HSTS preload list
            if ENABLE_HTTPS:
                response.headers['Strict-Transport-Security'] = \
                    'max-age=31536000; includeSubDomains; preload'
            
            # X-Content-Type-Options
            # Previne que o navegador faça MIME type sniffing
            # Protege contra ataques de type confusion
            response.headers['X-Content-Type-Options'] = 'nosniff'
            
            # X-Frame-Options
            # Previne que o site seja renderizado em um frame/iframe
            # Protege contra ataques de clickjacking
            response.headers['X-Frame-Options'] = 'DENY'
            
            # X-XSS-Protection
            # Ativa o filtro XSS do navegador (legacy, mas útil para browsers antigos)
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Content-Security-Policy (CSP)
            # Controla quais recursos o navegador pode carregar
            # default-src 'self': Só permite recursos do mesmo domínio
            # script-src 'self' 'unsafe-inline': Scripts do mesmo domínio ou inline
            # style-src 'self' 'unsafe-inline': Estilos do mesmo domínio ou inline
            # img-src 'self' data: https: : Imagens do mesmo domínio, data URIs ou HTTPS
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
            response.headers['Content-Security-Policy'] = csp
            
            # Referrer-Policy
            # Controla quanta informação do referer é enviada
            # strict-origin-when-cross-origin: Envia full URL para same-origin, 
            # apenas origin para cross-origin
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Permissions-Policy (antigo Feature-Policy)
            # Controla quais APIs/features o navegador pode usar
            # geolocation=(), camera=(), microphone=(): Desativa geolocalização, câmera e microfone
            permissions_policy = (
                "geolocation=(), "
                "camera=(), "
                "microphone=(), "
                "payment=(), "
                "usb=()"
            )
            response.headers['Permissions-Policy'] = permissions_policy
            
            # Cache-Control para respostas sensíveis
            # no-store, no-cache: Não armazena em cache
            # must-revalidate: Deve revalidar com o servidor
            if request.path.startswith('/api/') and request.method in ['POST', 'PUT', 'DELETE']:
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            
            return response
    
    def setup_https_enforcement(self):
        """
        Força o uso de HTTPS em produção.
        """
        if ENABLE_HTTPS:
            @self.app.before_request
            def enforce_https():
                """
                Redireciona todas as requisições HTTP para HTTPS.
                """
                if not request.is_secure:
                    # Redirecionar para HTTPS mantendo o path e query string
                    url = request.url.replace('http://', 'https://', 1)
                    print("Redirecting HTTP to HTTPS: %s", url)
                    return redirect(url, code=301)
                
                # Verificar protocolo SSL (se disponível)
                if hasattr(request, 'ssl') and request.ssl:
                    ssl_version = request.ssl.get('ssl_version', '')
                    if ssl_version and SSL_PROTOCOL not in ssl_version:
                        print(
                            "SSL protocol mismatch. Expected: %s, Got: %s",
                            SSL_PROTOCOL, ssl_version
                        )


def require_https(f):
    """
    Decorator para exigir HTTPS em endpoints específicos.
    
    Uso:
        @app.route('/api/sensitive')
        @require_https
        def sensitive_endpoint():
            return "This endpoint requires HTTPS"
    
    Args:
        f: Função a ser decorada
        
    Returns:
        Função decorada
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure:
            print(
                "HTTPS required but insecure request to %s", request.path
            )
            return {
                "error": "HTTPS is required for this endpoint",
                "message": "Please use HTTPS to access this resource"
            }, 403
        return f(*args, **kwargs)
    return decorated_function


def get_ssl_context():
    """
    Configura e retorna o contexto SSL para HTTPS.
    
    Returns:
        Objeto SSLContext configurado ou None se HTTPS não estiver habilitado
    """
    if not ENABLE_HTTPS:
        return None
    
    try:
        if not SSL_CERT_PATH or not SSL_KEY_PATH:
            print(
                "HTTPS enabled but SSL_CERT_PATH or SSL_KEY_PATH not set"
            )
            return None
        
        # Criar contexto SSL
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        
        # Configurar protocolo
        if SSL_PROTOCOL == "TLSv1.3":
            context.minimum_version = ssl.TLSVersion.TLSv1_3
            context.maximum_version = ssl.TLSVersion.TLSv1_3
        elif SSL_PROTOCOL == "TLSv1.2":
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_3
        else:
            print("Unknown SSL protocol: %s, using default", SSL_PROTOCOL)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # Configurar cifras
        context.set_ciphers(SSL_CIPHERS)
        
        # Carregar certificado e chave
        context.load_cert_chain(certfile=SSL_CERT_PATH, keyfile=SSL_KEY_PATH)
        
        # Opções de segurança adicionais
        context.options |= (
            ssl.OP_NO_SSLv2 |
            ssl.OP_NO_SSLv3 |
            ssl.OP_NO_COMPRESSION |
            ssl.OP_NO_TICKET |
            ssl.OP_SINGLE_DH_USE |
            ssl.OP_SINGLE_ECDH_USE
        )
        
        # Verificar certificado
        context.verify_mode = ssl.CERT_NONE  # O servidor não verifica clientes por padrão
        
        print(
            "SSL context configured with protocol: %s, ciphers: %s",
            SSL_PROTOCOL, SSL_CIPHERS
        )
        
        return context
        
    except ImportError:
        print("SSL module not available")
        return None
    except Exception as e:
        print("Failed to create SSL context: %s", str(e))
        return None


def init_security(app: Flask):
    """
    Inicializa o middleware de segurança na aplicação Flask.
    
    Args:
        app: Instância da aplicação Flask
    """
    if not app:
        raise ValueError("Flask app instance is required")
    
    # Inicializar middleware de segurança
    security_middleware = SecurityMiddleware(app)
    
    print("Security middleware initialized")
    
    if ENABLE_HTTPS:
        print("HTTPS enforcement enabled")
        ssl_context = get_ssl_context()
        if ssl_context:
            print("SSL context created successfully")
        else:
            print("SSL context creation failed, HTTPS may not work")
    else:
        print("HTTPS enforcement disabled (ENABLE_HTTPS=false)")
    
    return security_middleware
