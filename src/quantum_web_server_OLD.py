#!/usr/bin/env python3
"""
Quantum Web Server - Servidor web integrado para aplicações Quantum
"""

from flask import Flask, jsonify, request
from pathlib import Path
import threading
import time

class QuantumWebServer:
    """Servidor web para aplicações Quantum"""
    
    def __init__(self, port=8080):
        self.port = port
        self.app = Flask(__name__)
        self.routes = {}
        self.setup_routes()
    
    def setup_routes(self):
        """Configura rotas padrão"""
        @self.app.route('/', methods=['GET'])
        def index():
            return """
            <html>
            <head><title>Quantum Web Server</title></head>
            <body>
                <h1>🚀 Quantum Web Server</h1>
                <p>Servidor rodando com sucesso!</p>
                <hr>
                <h3>Rotas disponíveis:</h3>
                <ul>
            """ + "\n".join([f"<li><a href='{route}'>{route}</a></li>" for route in self.routes.keys()]) + """
                </ul>
            </body>
            </html>
            """
    
    def add_route_from_ast(self, ast_root):
        """Adiciona rotas baseado no AST do arquivo .q"""
        # Procura por q:route elements
        for route_element in ast_root.findall(".//q:route", {'q': 'https://quantum.lang/ns'}):
            path = route_element.get('path', '/')
            method = route_element.get('method', 'GET').upper()
            
            # Procura q:return dentro da rota
            return_element = route_element.find("q:return", {'q': 'https://quantum.lang/ns'})
            return_value = return_element.get('value', 'No content') if return_element is not None else 'No content'
            
            self.add_route(path, method, return_value)
    
    def add_route(self, path, method, content):
        """Adiciona uma rota ao servidor"""
        self.routes[path] = {'method': method, 'content': content}
        
        def route_handler():
            # Se parece com JSON, retorna como JSON
            if content.strip().startswith('{') or content.strip().startswith('['):
                try:
                    import json
                    return jsonify(json.loads(content))
                except:
                    pass
            
            # Se parece com HTML, retorna como HTML
            if '<' in content and '>' in content:
                return content
            
            # Texto simples
            return f"<html><body><h1>Quantum Response</h1><p>{content}</p></body></html>"
        
        # Adiciona rota ao Flask dinamicamente
        route_handler.__name__ = f"route_{path.replace('/', '_').replace('-', '_')}"
        self.app.add_url_rule(path, route_handler.__name__, route_handler, methods=[method])
    
    def start(self):
        """Inicia o servidor web"""
        print(f"🌐 Quantum Web Server iniciando na porta {self.port}")
        print(f"🔗 Acesse: http://localhost:{self.port}")
        print("🛑 Para parar: Ctrl+C")
        
        try:
            self.app.run(host='0.0.0.0', port=self.port, debug=False)
        except KeyboardInterrupt:
            print("\n👋 Servidor parado pelo usuário")
        except Exception as e:
            print(f"❌ Erro no servidor: {e}")


class QuantumAPIServer:
    """Servidor API para microservices Quantum"""
    
    def __init__(self, port=8080):
        self.port = port
        self.app = Flask(__name__)
        self.routes = {}
        self.setup_default_routes()
    
    def setup_default_routes(self):
        """Configura rotas padrão da API"""
        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({
                "status": "healthy",
                "server": "Quantum API",
                "routes": list(self.routes.keys())
            })
    
    def add_route_from_ast(self, ast_root):
        """Adiciona rotas baseado no AST do arquivo .q"""
        for route_element in ast_root.findall(".//q:route", {'q': 'https://quantum.lang/ns'}):
            path = route_element.get('path', '/')
            method = route_element.get('method', 'GET').upper()
            
            return_element = route_element.find("q:return", {'q': 'https://quantum.lang/ns'})
            return_value = return_element.get('value', '{}') if return_element is not None else '{}'
            
            self.add_api_route(path, method, return_value)
    
    def add_api_route(self, path, method, content):
        """Adiciona uma rota API"""
        self.routes[path] = {'method': method, 'content': content}
        
        def api_handler():
            try:
                import json
                return jsonify(json.loads(content))
            except:
                return jsonify({"result": content, "type": "text"})
        
        api_handler.__name__ = f"api_{path.replace('/', '_').replace('-', '_')}"
        self.app.add_url_rule(path, api_handler.__name__, api_handler, methods=[method])
    
    def start(self):
        """Inicia o servidor API"""
        print(f"🛠️  Quantum API Server iniciando na porta {self.port}")
        print(f"🔗 API: http://localhost:{self.port}")
        print(f"🩺 Health: http://localhost:{self.port}/health")
        print("🛑 Para parar: Ctrl+C")
        
        try:
            self.app.run(host='0.0.0.0', port=self.port, debug=False)
        except KeyboardInterrupt:
            print("\n👋 API servidor parado pelo usuário")
        except Exception as e:
            print(f"❌ Erro no servidor: {e}")
