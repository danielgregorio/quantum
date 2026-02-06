"""
AST Node for State Management (q:set)

This module contains the SetNode class, which represents the <q:set> tag
for state management in Quantum Language.

State Persistence Support:
    - persist="local" - localStorage (browser) or file (desktop)
    - persist="session" - sessionStorage (browser) or memory (desktop)
    - persist="sync" - synchronized across tabs/windows (browser) or network (desktop)
"""

from typing import Dict, Any, List, Optional

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

        # State Persistence
        self.persist: Optional[str] = None  # None, "local", "session", "sync"
        self.persist_key: Optional[str] = None  # Custom storage key (defaults to name)
        self.persist_encrypt: bool = False  # Encrypt persisted data
        self.persist_ttl: Optional[int] = None  # TTL in seconds for cached persistence

    def to_dict(self) -> Dict[str, Any]:
        result = {
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
        # Add persistence info if enabled
        if self.persist:
            result["persistence"] = {
                "scope": self.persist,
                "key": self.persist_key or self.name,
                "encrypt": self.persist_encrypt,
                "ttl": self.persist_ttl
            }
        return result

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

        # Validar persist scope
        if self.persist:
            valid_persist_scopes = ['local', 'session', 'sync']
            if self.persist not in valid_persist_scopes:
                errors.append(f"Invalid persist scope: {self.persist}. Must be one of {valid_persist_scopes}")

        return errors


class PersistNode(QuantumNode):
    """
    Represents a <q:persist> - Explicit persistence configuration.

    Allows fine-grained control over state persistence beyond the persist attribute on q:set.

    Examples:
      <q:persist scope="local" prefix="myapp_">
        <q:var name="theme" />
        <q:var name="locale" />
      </q:persist>

      <q:persist scope="sync" key="user_preferences" encrypt="true">
        <q:var name="darkMode" />
        <q:var name="fontSize" />
      </q:persist>

    Attributes:
      scope: "local" (localStorage), "session" (sessionStorage), "sync" (cross-tab/network)
      prefix: Optional prefix for all storage keys
      key: If set, all vars are stored under this single key as an object
      encrypt: Whether to encrypt persisted data
      ttl: Time-to-live in seconds (for cache invalidation)
      storage: Override storage backend ("localStorage", "indexedDB", "file", "db")
    """

    def __init__(
        self,
        scope: str = "local",
        prefix: Optional[str] = None,
        key: Optional[str] = None,
        encrypt: bool = False,
        ttl: Optional[int] = None,
        storage: Optional[str] = None
    ):
        self.scope = scope
        self.prefix = prefix
        self.key = key
        self.encrypt = encrypt
        self.ttl = ttl
        self.storage = storage
        self.variables: List[str] = []  # List of variable names to persist

    def add_variable(self, name: str):
        """Add a variable name to persist."""
        self.variables.append(name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "persist",
            "scope": self.scope,
            "prefix": self.prefix,
            "key": self.key,
            "encrypt": self.encrypt,
            "ttl": self.ttl,
            "storage": self.storage,
            "variables": self.variables
        }

    def validate(self) -> List[str]:
        errors = []

        # Validate scope
        valid_scopes = ['local', 'session', 'sync']
        if self.scope not in valid_scopes:
            errors.append(f"Invalid persist scope: {self.scope}. Must be one of {valid_scopes}")

        # Validate storage backend if specified
        if self.storage:
            valid_storage = ['localStorage', 'sessionStorage', 'indexedDB', 'file', 'db']
            if self.storage not in valid_storage:
                errors.append(f"Invalid storage backend: {self.storage}. Must be one of {valid_storage}")

        # Validate variables
        if not self.variables:
            errors.append("q:persist must contain at least one q:var element")

        return errors

    def __repr__(self):
        return f'<PersistNode scope={self.scope} vars={len(self.variables)}>'
