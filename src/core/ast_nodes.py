"""
Quantum AST Nodes - Classes that represent elements of the Quantum language
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

class QuantumNode(ABC):
    """Base class for all Quantum AST nodes"""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to dictionary (debug/serialization)"""
        pass
    
    @abstractmethod
    def validate(self) -> List[str]:
        """Validate the node and return list of errors"""
        pass


@dataclass
class QuantumParam:
    """Represents a <q:param>"""
    name: str
    type: str = "string"
    required: bool = False
    default: Optional[str] = None
    validation: Optional[str] = None
    description: Optional[str] = None
    
    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Param name is required")
        return errors


@dataclass
class QuantumReturn:
    """Represents a <q:return>"""
    name: Optional[str] = None
    type: str = "string" 
    value: Optional[str] = None
    description: Optional[str] = None
    
    def validate(self) -> List[str]:
        errors = []
        if not self.value:
            errors.append("Return value is required")
        return errors


@dataclass
class QuantumRoute:
    """Represents a <q:route>"""
    path: str
    method: str = "GET"
    returns: List[QuantumReturn] = None
    
    def __post_init__(self):
        if self.returns is None:
            self.returns = []
    
    def validate(self) -> List[str]:
        errors = []
        if not self.path:
            errors.append("Route path is required")
        if self.method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
            errors.append(f"Invalid HTTP method: {self.method}")
        return errors


class IfNode(QuantumNode):
    """Represents a <q:if> with elseif and else"""
    
    def __init__(self, condition: str):
        self.condition = condition
        self.if_body: List[QuantumNode] = []
        
        # Support for elseif blocks
        self.elseif_blocks: List[Dict[str, Any]] = []  # [{"condition": str, "body": List[QuantumNode]}]
        
        # Support for else block
        self.else_body: List[QuantumNode] = []
    
    def add_if_statement(self, statement: QuantumNode):
        """Add statement to if body"""
        self.if_body.append(statement)
    
    def add_elseif_block(self, condition: str, body: List[QuantumNode] = None):
        """Add elseif block"""
        self.elseif_blocks.append({
            "condition": condition,
            "body": body or []
        })
    
    def add_else_statement(self, statement: QuantumNode):
        """Add statement to else body"""
        self.else_body.append(statement)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "if",
            "condition": self.condition,
            "if_body_count": len(self.if_body),
            "elseif_count": len(self.elseif_blocks),
            "has_else": len(self.else_body) > 0
        }
    
    def validate(self) -> List[str]:
        errors = []
        if not self.condition:
            errors.append("If condition is required")
        
        # Validate all bodies
        for statement in self.if_body:
            errors.extend(statement.validate())
        
        for elseif_block in self.elseif_blocks:
            if not elseif_block["condition"]:
                errors.append("Elseif condition is required")
            for statement in elseif_block["body"]:
                errors.extend(statement.validate())
        
        for statement in self.else_body:
            errors.extend(statement.validate())
        
        return errors


class ComponentNode(QuantumNode):
    """Represents a <q:component>"""
    
    def __init__(self, name: str, component_type: str = "module"):
        self.name = name
        self.component_type = component_type
        self.params: List[QuantumParam] = []
        self.returns: List[QuantumReturn] = []
        self.functions: List['FunctionNode'] = []
        self.script_blocks: List[str] = []
        self.statements: List[QuantumNode] = []  # For control flow statements
    
    def add_param(self, param: QuantumParam):
        self.params.append(param)
    
    def add_return(self, return_node: QuantumReturn):
        self.returns.append(return_node)
    
    def add_function(self, function: 'FunctionNode'):
        self.functions.append(function)
    
    def add_script(self, script: str):
        self.script_blocks.append(script)
    
    def add_statement(self, statement: QuantumNode):
        """Add control flow statement (if, loop, set, etc)"""
        self.statements.append(statement)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "component",
            "name": self.name,
            "component_type": self.component_type,
            "params": [p.__dict__ for p in self.params],
            "returns": [r.__dict__ for r in self.returns],
            "functions": [f.to_dict() for f in self.functions],
            "script_blocks": len(self.script_blocks),
            "statements": len(self.statements)
        }
    
    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Component name is required")
        
        for param in self.params:
            errors.extend(param.validate())
        
        for ret in self.returns:
            errors.extend(ret.validate())
        
        for statement in self.statements:
            errors.extend(statement.validate())
        
        return errors


class ApplicationNode(QuantumNode):
    """Represents a <q:application>"""
    
    def __init__(self, app_id: str, app_type: str):
        self.app_id = app_id
        self.app_type = app_type
        self.routes: List[QuantumRoute] = []
        self.components: List[ComponentNode] = []
    
    def add_route(self, route: QuantumRoute):
        self.routes.append(route)
    
    def add_component(self, component: ComponentNode):
        self.components.append(component)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "application",
            "app_id": self.app_id,
            "app_type": self.app_type,
            "routes": [r.__dict__ for r in self.routes],
            "components": [c.to_dict() for c in self.components]
        }
    
    def validate(self) -> List[str]:
        errors = []
        if not self.app_id:
            errors.append("Application ID is required")
        if not self.app_type:
            errors.append("Application type is required")
        
        for route in self.routes:
            errors.extend(route.validate())
        
        for component in self.components:
            errors.extend(component.validate())
        
        return errors


class JobNode(QuantumNode):
    """Represents a <q:job>"""
    
    def __init__(self, job_id: str, schedule: Optional[str] = None):
        self.job_id = job_id
        self.schedule = schedule
        self.tasks: List[Dict[str, Any]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "job",
            "job_id": self.job_id,
            "schedule": self.schedule,
            "tasks": self.tasks
        }
    
    def validate(self) -> List[str]:
        errors = []
        if not self.job_id:
            errors.append("Job ID is required")
        return errors


class FunctionNode(QuantumNode):
    """Represents a <q:function>"""
    
    def __init__(self, name: str, params: str = ""):
        self.name = name
        self.params = params
        self.body: List[QuantumNode] = []
    
    def add_statement(self, statement: QuantumNode):
        self.body.append(statement)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "function", 
            "name": self.name,
            "params": self.params,
            "body_statements": len(self.body)
        }
    
    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Function name is required")
        
        for statement in self.body:
            errors.extend(statement.validate())
        
        return errors
