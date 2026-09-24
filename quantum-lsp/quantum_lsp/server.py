"""
Quantum Language Server - Main LSP server implementation

This module implements the core Language Server Protocol functionality
for the Quantum Framework using pygls.
"""

import argparse
import logging
import sys
from typing import Optional

from pygls.lsp.server import LanguageServer
from lsprotocol import types

from .capabilities import get_server_capabilities
from .handlers.completion import register_completion_handlers
from .handlers.hover import register_hover_handlers
from .handlers.definition import register_definition_handlers
from .handlers.references import register_references_handlers
from .handlers.diagnostics import register_diagnostics_handlers
from .handlers.formatting import register_formatting_handlers
from .handlers.symbols import register_symbols_handlers
from .analysis.workspace import WorkspaceAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("quantum-lsp")


class QuantumLanguageServer(LanguageServer):
    """
    Language Server for Quantum Framework (.q files).

    Provides IDE features like autocompletion, hover documentation,
    go-to-definition, find references, diagnostics, and formatting.
    """

    CMD_VALIDATE_DOCUMENT = "quantum.validateDocument"
    CMD_SHOW_AST = "quantum.showAst"

    def __init__(self, *args, **kwargs):
        super().__init__(
            name="quantum-lsp",
            version="1.0.0",
            *args,
            **kwargs
        )

        # Workspace analyzer for managing document state
        self.workspace_analyzer = WorkspaceAnalyzer(self)

        # Register all handlers
        self._register_handlers()

        logger.info("Quantum Language Server initialized")

    def _register_handlers(self):
        """Register all LSP handlers."""
        register_completion_handlers(self)
        register_hover_handlers(self)
        register_definition_handlers(self)
        register_references_handlers(self)
        register_diagnostics_handlers(self)
        register_formatting_handlers(self)
        register_symbols_handlers(self)

        # Register lifecycle handlers
        self._register_lifecycle_handlers()

        # Register custom commands
        self._register_commands()

    def _register_lifecycle_handlers(self):
        """Register document lifecycle handlers."""

        @self.feature(types.TEXT_DOCUMENT_DID_OPEN)
        def did_open(params: types.DidOpenTextDocumentParams):
            """Handle document open."""
            logger.debug(f"Document opened: {params.text_document.uri}")
            self.workspace_analyzer.open_document(
                params.text_document.uri,
                params.text_document.text,
                params.text_document.version
            )

        @self.feature(types.TEXT_DOCUMENT_DID_CHANGE)
        def did_change(params: types.DidChangeTextDocumentParams):
            """Handle document change."""
            logger.debug(f"Document changed: {params.text_document.uri}")
            # Get the full text (we use full sync)
            if params.content_changes:
                text = params.content_changes[-1].text
                self.workspace_analyzer.update_document(
                    params.text_document.uri,
                    text,
                    params.text_document.version
                )

        @self.feature(types.TEXT_DOCUMENT_DID_CLOSE)
        def did_close(params: types.DidCloseTextDocumentParams):
            """Handle document close."""
            logger.debug(f"Document closed: {params.text_document.uri}")
            self.workspace_analyzer.close_document(params.text_document.uri)

        @self.feature(types.TEXT_DOCUMENT_DID_SAVE)
        def did_save(params: types.DidSaveTextDocumentParams):
            """Handle document save."""
            logger.debug(f"Document saved: {params.text_document.uri}")
            # Re-validate on save
            if params.text:
                self.workspace_analyzer.update_document(
                    params.text_document.uri,
                    params.text,
                    None
                )

        @self.feature(types.INITIALIZED)
        def initialized(params: types.InitializedParams):
            """Handle initialized notification."""
            logger.info("Client initialized, server ready")

    def _register_commands(self):
        """Register custom commands."""

        @self.command(self.CMD_VALIDATE_DOCUMENT)
        def validate_document(params: list) -> dict:
            """Validate a document and return diagnostics."""
            if not params:
                return {"success": False, "error": "No URI provided"}

            uri = params[0]
            doc = self.workspace_analyzer.get_document(uri)
            if not doc:
                return {"success": False, "error": "Document not found"}

            diagnostics = self.workspace_analyzer.validate_document(uri)
            return {
                "success": True,
                "diagnostics_count": len(diagnostics),
                "diagnostics": [
                    {
                        "line": d.range.start.line,
                        "message": d.message,
                        "severity": d.severity.name if d.severity else "Error"
                    }
                    for d in diagnostics
                ]
            }

        @self.command(self.CMD_SHOW_AST)
        def show_ast(params: list) -> dict:
            """Parse document and return AST as JSON."""
            if not params:
                return {"success": False, "error": "No URI provided"}

            uri = params[0]
            doc = self.workspace_analyzer.get_document(uri)
            if not doc:
                return {"success": False, "error": "Document not found"}

            ast = doc.get_ast()
            if ast:
                return {
                    "success": True,
                    "ast": ast.to_dict() if hasattr(ast, 'to_dict') else str(ast)
                }
            return {"success": False, "error": "Failed to parse AST"}


def create_server() -> QuantumLanguageServer:
    """Create and configure the language server."""
    server = QuantumLanguageServer()
    return server


def main():
    """Main entry point for the language server."""
    parser = argparse.ArgumentParser(
        description="Quantum Language Server"
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Use stdio for communication"
    )
    parser.add_argument(
        "--tcp",
        action="store_true",
        help="Use TCP for communication"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="TCP host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=2087,
        help="TCP port (default: 2087)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="quantum-lsp 1.0.0"
    )

    args = parser.parse_args()

    # Set log level
    logging.getLogger("quantum-lsp").setLevel(getattr(logging, args.log_level))

    # Create server
    server = create_server()

    # Start server
    if args.tcp:
        logger.info(f"Starting Quantum LSP server on {args.host}:{args.port}")
        server.start_tcp(args.host, args.port)
    else:
        logger.info("Starting Quantum LSP server in stdio mode")
        server.start_io()


if __name__ == "__main__":
    main()
