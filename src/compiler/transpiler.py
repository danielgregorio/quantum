"""
Quantum Transpiler
==================

Main orchestrator for transpiling Quantum code to Python/JavaScript.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.parser import QuantumParser
from core.ast_nodes import QuantumNode


@dataclass
class CompilationResult:
    """Result of a compilation."""
    success: bool
    code: str
    source_file: Optional[str] = None
    target: str = 'python'
    errors: List[str] = None
    warnings: List[str] = None
    sourcemap: Optional[str] = None
    stats: Dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.stats is None:
            self.stats = {}


class Transpiler:
    """
    Main transpiler class.

    Orchestrates parsing and code generation for Quantum files.

    Usage:
        transpiler = Transpiler(target='python')
        result = transpiler.compile_file('app.q')
        print(result.code)

        # Or from string
        result = transpiler.compile_string('<q:component>...</q:component>')
    """

    def __init__(
        self,
        target: str = 'python',
        optimize: bool = False,
        sourcemap: bool = False,
        strict: bool = False
    ):
        """
        Initialize the transpiler.

        Args:
            target: Target language ('python' or 'javascript')
            optimize: Enable optimizations
            sourcemap: Generate source maps
            strict: Strict mode (treat warnings as errors)
        """
        self.target = target.lower()
        self.optimize = optimize
        self.sourcemap = sourcemap
        self.strict = strict
        self.parser = QuantumParser()
        self._generator = None

    def _get_generator(self):
        """Get the code generator for current target."""
        if self._generator is None:
            if self.target == 'python':
                from compiler.python.generator import PythonGenerator
                self._generator = PythonGenerator()
            elif self.target == 'javascript':
                from compiler.javascript.generator import JavaScriptGenerator
                self._generator = JavaScriptGenerator()
            else:
                raise ValueError(f"Unknown target: {self.target}")
        return self._generator

    def compile_file(self, filepath: str) -> CompilationResult:
        """
        Compile a Quantum file.

        Args:
            filepath: Path to the .q file

        Returns:
            CompilationResult with generated code
        """
        import time
        start_time = time.perf_counter()

        path = Path(filepath)
        if not path.exists():
            return CompilationResult(
                success=False,
                code='',
                source_file=str(path),
                target=self.target,
                errors=[f"File not found: {filepath}"]
            )

        try:
            source = path.read_text(encoding='utf-8')
            result = self.compile_string(source, source_file=str(path))
            result.stats['compile_time_ms'] = (time.perf_counter() - start_time) * 1000
            return result

        except Exception as e:
            return CompilationResult(
                success=False,
                code='',
                source_file=str(path),
                target=self.target,
                errors=[f"Error reading file: {e}"]
            )

    def compile_string(self, source: str, source_file: str = '<string>') -> CompilationResult:
        """
        Compile Quantum source code from string.

        Args:
            source: Quantum source code
            source_file: Optional source file name for error messages

        Returns:
            CompilationResult with generated code
        """
        import time
        start_time = time.perf_counter()

        errors = []
        warnings = []

        # Parse
        try:
            ast = self.parser.parse(source)
        except Exception as e:
            return CompilationResult(
                success=False,
                code='',
                source_file=source_file,
                target=self.target,
                errors=[f"Parse error: {e}"]
            )

        if ast is None:
            return CompilationResult(
                success=False,
                code='',
                source_file=source_file,
                target=self.target,
                errors=["Parse returned None"]
            )

        # Optimize (if enabled)
        if self.optimize:
            try:
                ast = self._optimize(ast)
            except Exception as e:
                warnings.append(f"Optimization warning: {e}")

        # Generate code
        try:
            generator = self._get_generator()
            code = generator.generate(ast)
        except Exception as e:
            return CompilationResult(
                success=False,
                code='',
                source_file=source_file,
                target=self.target,
                errors=[f"Code generation error: {e}"]
            )

        # Post-generation optimization (if enabled)
        if self.optimize:
            try:
                from compiler.optimizer import CodeOptimizer
                optimizer = CodeOptimizer(target=self.target, level=2)
                code = optimizer.optimize(code)
                opt_stats = optimizer.get_stats()
                warnings.append(f"Optimized: {sum(opt_stats.values())} transformations")
            except Exception as e:
                warnings.append(f"Post-optimization warning: {e}")

        # Generate source map (if enabled)
        sourcemap = None
        if self.sourcemap:
            try:
                sourcemap = self._generate_sourcemap(ast, code, source_file)
            except Exception as e:
                warnings.append(f"Source map warning: {e}")

        # Build stats
        stats = {
            'parse_time_ms': 0,  # TODO: measure separately
            'generate_time_ms': (time.perf_counter() - start_time) * 1000,
            'source_lines': source.count('\n') + 1,
            'output_lines': code.count('\n') + 1,
        }

        # Check strict mode
        if self.strict and warnings:
            errors.extend(warnings)
            warnings = []
            return CompilationResult(
                success=False,
                code=code,
                source_file=source_file,
                target=self.target,
                errors=errors,
                warnings=[],
                stats=stats
            )

        return CompilationResult(
            success=True,
            code=code,
            source_file=source_file,
            target=self.target,
            errors=errors,
            warnings=warnings,
            sourcemap=sourcemap,
            stats=stats
        )

    def _optimize(self, ast: QuantumNode) -> QuantumNode:
        """Apply optimizations to AST."""
        # TODO: Implement optimizations
        # - Constant folding
        # - Dead code elimination
        # - Expression simplification
        return ast

    def _generate_sourcemap(self, ast: QuantumNode, code: str, source_file: str) -> str:
        """Generate source map."""
        # TODO: Implement source map generation
        # For now, return empty
        return ''

    def compile_directory(
        self,
        source_dir: str,
        output_dir: str,
        recursive: bool = True
    ) -> Dict[str, CompilationResult]:
        """
        Compile all Quantum files in a directory.

        Args:
            source_dir: Source directory containing .q files
            output_dir: Output directory for generated files
            recursive: Process subdirectories

        Returns:
            Dictionary mapping source files to compilation results
        """
        source_path = Path(source_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = {}
        pattern = '**/*.q' if recursive else '*.q'

        for q_file in source_path.glob(pattern):
            rel_path = q_file.relative_to(source_path)

            # Determine output file
            ext = '.py' if self.target == 'python' else '.js'
            out_file = output_path / rel_path.with_suffix(ext)
            out_file.parent.mkdir(parents=True, exist_ok=True)

            # Compile
            result = self.compile_file(str(q_file))
            results[str(q_file)] = result

            # Write output
            if result.success:
                out_file.write_text(result.code, encoding='utf-8')

                # Write source map
                if result.sourcemap:
                    map_file = out_file.with_suffix(ext + '.map')
                    map_file.write_text(result.sourcemap, encoding='utf-8')

        return results


def compile_file(filepath: str, target: str = 'python', **kwargs) -> CompilationResult:
    """
    Convenience function to compile a single file.

    Args:
        filepath: Path to .q file
        target: Target language
        **kwargs: Additional transpiler options

    Returns:
        CompilationResult
    """
    transpiler = Transpiler(target=target, **kwargs)
    return transpiler.compile_file(filepath)


def compile_string(source: str, target: str = 'python', **kwargs) -> CompilationResult:
    """
    Convenience function to compile source string.

    Args:
        source: Quantum source code
        target: Target language
        **kwargs: Additional transpiler options

    Returns:
        CompilationResult
    """
    transpiler = Transpiler(target=target, **kwargs)
    return transpiler.compile_string(source)
