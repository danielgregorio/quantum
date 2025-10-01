"""
Debug script to analyze if-else parsing issues
"""

import sys
from pathlib import Path
import xml.etree.ElementTree as ET

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from core.parser import QuantumParser

def debug_xml_structure(file_path):
    """Debug XML structure of if-else files"""
    print(f"\n=== Debugging {file_path} ===")
    
    # Parse XML directly
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    print("XML Structure:")
    for elem in root.iter():
        print(f"  Tag: {elem.tag}, Attributes: {elem.attrib}, Text: {elem.text}")
    
    print("\nParsing with QuantumParser:")
    parser = QuantumParser()
    ast = parser.parse_file(file_path)
    
    print(f"Component: {ast.name}")
    print(f"Statements: {len(ast.statements)}")
    
    if ast.statements:
        if_stmt = ast.statements[0]
        print(f"If condition: {if_stmt.condition}")
        print(f"If body: {len(if_stmt.if_body)}")
        print(f"Else body: {len(if_stmt.else_body)}")
        print(f"Elseif blocks: {len(if_stmt.elseif_blocks)}")
        
        print("\nIf body contents:")
        for i, stmt in enumerate(if_stmt.if_body):
            print(f"  {i}: {type(stmt).__name__} - {getattr(stmt, 'value', 'N/A')}")
        
        print("\nElse body contents:")
        for i, stmt in enumerate(if_stmt.else_body):
            print(f"  {i}: {type(stmt).__name__} - {getattr(stmt, 'value', 'N/A')}")

if __name__ == "__main__":
    debug_xml_structure('examples/simple-if.q')
    debug_xml_structure('examples/test-if-else.q')
    debug_xml_structure('examples/test-elseif.q')