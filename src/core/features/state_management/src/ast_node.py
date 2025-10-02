"""
AST Node for State Management (q:set)

This module contains the SetNode class, which represents the <q:set> tag
for state management in Quantum Language.
"""

from typing import Dict, Any, List

# Import base class from parent AST nodes
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.ast_nodes import QuantumNode


class SetNode(QuantumNode):
    """Represents a <q:set> - State Management"""

    def __init__(self, name: str):
        # Obrigatórios
        self.name = name

        # Tipo e valor
        self.type = "string"
        self.value = None
        self.default = None

        # Validação
        self.required = False
        self.nullable = True
        self.validate_rule = None  # Renomeado de 'validate' para não conflitar com o método
        self.pattern = None
        self.mask = None
        self.range = None
        self.enum = None
        self.unique = None
        self.min = None
        self.max = None
        self.minlength = None
        self.maxlength = None

        # Comportamento
        self.scope = "local"
        self.operation = "assign"
        self.step = 1

        # Para operações em collections
        self.index = None
        self.key = None
        self.source = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "set",
            "name": self.name,
            "value_type": self.type,
            "value": self.value,
            "default": self.default,
            "scope": self.scope,
            "operation": self.operation,
            "required": self.required,
            "nullable": self.nullable,
            "validation": {
                "validate": self.validate_rule,
                "pattern": self.pattern,
                "mask": self.mask,
                "range": self.range,
                "enum": self.enum,
                "unique": self.unique,
                "min": self.min,
                "max": self.max,
                "minlength": self.minlength,
                "maxlength": self.maxlength
            }
        }

    def validate(self) -> List[str]:
        errors = []

        if not self.name:
            errors.append("Set variable name is required")

        # Validar tipo
        valid_types = ['string', 'number', 'decimal', 'boolean', 'date', 'datetime',
                      'array', 'object', 'json', 'binary', 'null']
        if self.type not in valid_types:
            errors.append(f"Invalid type: {self.type}. Must be one of {valid_types}")

        # Validar operação
        valid_operations = ['assign', 'increment', 'decrement', 'add', 'multiply',
                           'append', 'prepend', 'remove', 'removeAt', 'clear', 'sort',
                           'reverse', 'unique', 'merge', 'setProperty', 'deleteProperty',
                           'clone', 'uppercase', 'lowercase', 'trim', 'format']
        if self.operation not in valid_operations:
            errors.append(f"Invalid operation: {self.operation}")

        # Validar valor obrigatório para assign
        if self.operation == "assign" and not self.value and not self.default and self.required:
            errors.append("Set value or default is required when required=true")

        # Validar enum
        if self.enum and self.value:
            enum_values = [v.strip() for v in self.enum.split(',')]
            if self.value not in enum_values:
                errors.append(f"Value '{self.value}' not in enum: {enum_values}")

        # Validar minlength/maxlength
        if self.type == "string" and self.value:
            if self.minlength and len(str(self.value)) < int(self.minlength):
                errors.append(f"Value length {len(str(self.value))} is less than minlength {self.minlength}")
            if self.maxlength and len(str(self.value)) > int(self.maxlength):
                errors.append(f"Value length {len(str(self.value))} exceeds maxlength {self.maxlength}")

        return errors
