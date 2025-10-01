#!/usr/bin/env python3
"""
Quantum CLI - Entry point refatorado para arquitetura modular
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório src ao path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Importa runner refatorado
from cli.runner import main

if __name__ == '__main__':
    main()
