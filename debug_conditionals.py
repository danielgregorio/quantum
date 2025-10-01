"""
Debug test for conditional parsing
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / 'src'))

from core.parser import QuantumParser

def test_conditional_parsing():
    parser = QuantumParser()
    
    # Test simple if
    ast = parser.parse_file('examples/simple-if.q')
    
    print(f"Component: {ast.name}")
    print(f"Statements: {len(ast.statements)}")
    
    if ast.statements:
        if_stmt = ast.statements[0]
        print(f"If condition: {if_stmt.condition}")
        print(f"If body: {len(if_stmt.if_body)}")
        print(f"Else body: {len(if_stmt.else_body)}")
        print(f"Elseif blocks: {len(if_stmt.elseif_blocks)}")
        
        if if_stmt.if_body:
            return_stmt = if_stmt.if_body[0]
            print(f"Return value: {return_stmt.value}")

if __name__ == "__main__":
    test_conditional_parsing()
