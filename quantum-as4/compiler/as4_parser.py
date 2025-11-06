"""
ActionScript 4 Parser - Parse AS4 code to AST

Supports a subset of AS4 syntax:
- Variable declarations
- Function declarations
- Basic expressions
- Event handlers

More features will be added incrementally.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class Variable:
    """
    Variable declaration
    Example: private var message:String = "Hello";
    """
    name: str
    type: Optional[str]
    value: Optional[str]
    is_bindable: bool = False


@dataclass
class Parameter:
    """Function parameter"""
    name: str
    type: Optional[str]
    default_value: Optional[str] = None


@dataclass
class Function:
    """
    Function declaration
    Example: private function handleClick():void { ... }
    """
    name: str
    params: List[Parameter]
    return_type: Optional[str]
    body: str
    is_async: bool = False


@dataclass
class AS4AST:
    """Complete ActionScript 4 AST"""
    variables: List[Variable]
    functions: List[Function]
    imports: List[str]
    metadata: Dict[str, List[str]]  # Decorators like [Bindable]


class AS4Parser:
    """
    Parse ActionScript 4 code

    Start with a simple regex-based parser.
    Can be upgraded to full lexer/parser later if needed.
    """

    def parse(self, code: str) -> AS4AST:
        """
        Parse ActionScript 4 code and return AST

        Args:
            code: AS4 source code

        Returns:
            AS4AST with parsed variables, functions, etc.
        """
        # Clean up code
        code = self._remove_comments(code)

        return AS4AST(
            variables=self._parse_variables(code),
            functions=self._parse_functions(code),
            imports=self._parse_imports(code),
            metadata=self._parse_metadata(code)
        )

    def _remove_comments(self, code: str) -> str:
        """Remove single-line and multi-line comments"""
        # Remove single-line comments: // comment
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)

        # Remove multi-line comments: /* comment */
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

        return code

    def _parse_imports(self, code: str) -> List[str]:
        """
        Parse import statements
        Example: import quantum.http.fetch;
        """
        imports = []
        pattern = r'import\s+([\w.]+);'

        for match in re.finditer(pattern, code):
            imports.append(match.group(1))

        return imports

    def _parse_metadata(self, code: str) -> Dict[str, List[str]]:
        """
        Parse metadata/decorators
        Example: [Bindable]
        """
        metadata = {}

        # Find all [Metadata] tags
        pattern = r'\[(\w+)(?:\((.*?)\))?\]'

        for match in re.finditer(pattern, code):
            meta_name = match.group(1)
            meta_args = match.group(2)

            if meta_name not in metadata:
                metadata[meta_name] = []

            if meta_args:
                metadata[meta_name].append(meta_args)

        return metadata

    def _parse_variables(self, code: str) -> List[Variable]:
        """
        Parse variable declarations

        Patterns supported:
        - var name:Type;
        - var name:Type = value;
        - private var name:Type = value;
        - [Bindable] private var name:Type = value;
        """
        variables = []

        # Pattern to match variable declarations
        # Captures: bindable flag, visibility, name, type, value
        pattern = r'(?:\[Bindable\])?\s*(?:private|public)?\s*var\s+(\w+)(?::(\w+(?:\.<\w+>)?)?)?\s*(?:=\s*(.+?))?;'

        for match in re.finditer(pattern, code):
            name = match.group(1)
            type_ = match.group(2)
            value = match.group(3)

            # Check if [Bindable] appears before this var
            var_start = match.start()
            preceding_code = code[max(0, var_start - 50):var_start]
            is_bindable = '[Bindable]' in preceding_code

            variables.append(Variable(
                name=name,
                type=type_,
                value=value.strip() if value else None,
                is_bindable=is_bindable
            ))

        return variables

    def _parse_functions(self, code: str) -> List[Function]:
        """
        Parse function declarations

        Patterns supported:
        - function name():void { }
        - function name(param:Type):ReturnType { }
        - private function name():void { }
        - async function name():Promise<Type> { }
        """
        functions = []

        # Pattern to match function declarations
        # Captures: async, visibility, name, params, return type, body
        pattern = r'(?:async\s+)?(?:private|public)?\s*function\s+(\w+)\s*\((.*?)\)\s*(?::(\w+(?:<\w+>)?)?)?\s*\{(.*?)\}'

        for match in re.finditer(pattern, code, re.DOTALL):
            name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3)
            body = match.group(4)

            # Check if async
            func_start = match.start()
            preceding_code = code[max(0, func_start - 20):func_start]
            is_async = 'async' in preceding_code

            # Parse parameters
            params = self._parse_parameters(params_str)

            functions.append(Function(
                name=name,
                params=params,
                return_type=return_type,
                body=body.strip(),
                is_async=is_async
            ))

        return functions

    def _parse_parameters(self, params_str: str) -> List[Parameter]:
        """
        Parse function parameters

        Examples:
        - name:Type
        - name:Type = defaultValue
        - name:Type, other:Type
        """
        params = []

        if not params_str.strip():
            return params

        # Split by comma (simple for now, doesn't handle complex defaults)
        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue

            # Parse: name:Type = default
            # or: name:Type
            # or: name
            match = re.match(r'(\w+)(?::(\w+(?:<\w+>)?))?(?:\s*=\s*(.+))?', param)

            if match:
                param_name = match.group(1)
                param_type = match.group(2)
                default_value = match.group(3)

                params.append(Parameter(
                    name=param_name,
                    type=param_type,
                    default_value=default_value.strip() if default_value else None
                ))

        return params


# Example usage
if __name__ == '__main__':
    # Test with sample AS4 code
    code = '''
        import quantum.http.fetch;

        [Bindable]
        private var message:String = "Hello World";

        [Bindable]
        private var count:int = 0;

        private function handleClick():void {
            count = count + 1;
            message = "Clicked " + count + " times";
        }

        private async function loadData():Promise<void> {
            const response = await fetch("/api/data");
            const data = await response.json();
        }
    '''

    parser = AS4Parser()
    ast = parser.parse(code)

    print(f"Imports: {ast.imports}")
    print(f"Variables: {len(ast.variables)}")
    for var in ast.variables:
        print(f"  - {var.name}: {var.type} = {var.value} (bindable: {var.is_bindable})")

    print(f"Functions: {len(ast.functions)}")
    for func in ast.functions:
        print(f"  - {func.name}({len(func.params)} params): {func.return_type} (async: {func.is_async})")
