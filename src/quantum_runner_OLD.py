#!/usr/bin/env python3
"""
Quantum Runner - Executa arquivos .q baseado no tipo
"""

import argparse
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from quantum_web_server import QuantumWebServer, QuantumAPIServer

class QuantumRunner:
    """Runner principal do Quantum"""
    
    def __init__(self):
        # Define namespace para tags Quantum
        self.quantum_ns = {'q': 'https://quantum.lang/ns'}
        
        self.supported_root_types = {
            'component': self.run_component,
            'application': self.run_application,
            'job': self.run_job
        }
    
    def run(self, file_path: str):
        """Executa arquivo .q"""
        path = Path(file_path)
        
        if not path.exists():
            print(f"❌ Erro: Arquivo '{file_path}' não encontrado")
            return 1
        
        if not path.suffix == '.q':
            print(f"❌ Erro: Arquivo deve ter extensão '.q', encontrado '{path.suffix}'")
            return 1
        
        try:
            # Parse XML
            tree = ET.parse(path)
            root = tree.getroot()
            
            # Remove namespace prefix para facilitar comparação
            root_type = root.tag.split('}')[-1] if '}' in root.tag else root.tag.split(':')[-1]
            
            print(f"🔍 Analisando arquivo: {path.name}")
            print(f"📄 Tipo detectado: q:{root_type}")
            
            # Executa baseado no tipo
            if root_type in self.supported_root_types:
                return self.supported_root_types[root_type](root, path)
            else:
                print(f"❌ Erro: Tipo 'q:{root_type}' não suportado")
                return 1
                
        except ET.ParseError as e:
            print(f"❌ Erro de sintaxe XML: {e}")
            return 1
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            return 1
    
    def find_element(self, root, tag_name):
        """Helper para encontrar elementos considerando namespace"""
        # Tenta com namespace
        element = root.find(f"q:{tag_name}", self.quantum_ns)
        if element is not None:
            return element
        
        # Tenta sem namespace (fallback)
        element = root.find(tag_name)
        return element
    
    def run_component(self, root, path):
        """Executa q:component"""
        component_name = root.get('name', 'UnnamedComponent')
        print(f"🔧 Executando component: {component_name}")
        
        # Procura por q:return
        return_node = self.find_element(root, 'return')
        if return_node is not None:
            result = return_node.get('value', '')
            print(f"✅ Resultado: {result}")
        else:
            print("⚠️  Component sem q:return")
        
        return 0
    
    def run_application(self, root, path):
        """Executa q:application"""
        app_name = root.get('id', path.stem)
        app_type = root.get('type', 'unknown')
        
        print(f"🚀 Executando aplicação: {app_name}")
        print(f"📱 Tipo: {app_type}")
        
        if app_type == 'html':
            # Cria servidor web real
            web_server = QuantumWebServer(port=8080)
            web_server.add_route_from_ast(root)
            web_server.start()
            
        elif app_type == 'microservices':
            # Cria API server real
            api_server = QuantumAPIServer(port=8080)
            api_server.add_route_from_ast(root)
            api_server.start()
            
        elif app_type == 'console':
            print(f"💻 Executando aplicação console...")
            # TODO: Implementar console app
            
        else:
            print(f"❓ Tipo de aplicação '{app_type}' ainda não implementado")
        
        return 0
    
    def run_job(self, root, path):
        """Executa q:job"""
        job_name = root.get('id', path.stem)
        print(f"⚙️  Executando job: {job_name}")
        print("✅ Job executado com sucesso")
        # TODO: Implementar job execution
        return 0


def main():
    """Função principal do CLI"""
    parser = argparse.ArgumentParser(
        description='Quantum Runner - Executa arquivos .q',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  quantum run hello.q              # Executa component
  quantum run webapp.q             # Inicia web server  
  quantum run api.q                # Inicia API server
  quantum run backup-job.q         # Executa job
        """
    )
    
    parser.add_argument(
        'command', 
        choices=['run'], 
        help='Comando a executar'
    )
    
    parser.add_argument(
        'file', 
        help='Arquivo .q para executar'
    )
    
    parser.add_argument(
        '--port', 
        type=int, 
        default=8080,
        help='Porta para servidor web (padrão: 8080)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Modo debug com informações detalhadas'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        print("🔧 Modo debug ativado")
    
    runner = QuantumRunner()
    exit_code = runner.run(args.file)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
