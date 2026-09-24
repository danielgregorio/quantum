"""
LSP Capabilities Configuration

Defines the server capabilities advertised to clients.
"""

from lsprotocol import types


def get_server_capabilities() -> types.ServerCapabilities:
    """
    Get the server capabilities to advertise to clients.

    Returns:
        ServerCapabilities with all supported features.
    """
    return types.ServerCapabilities(
        # Document sync - full sync for simplicity
        text_document_sync=types.TextDocumentSyncOptions(
            open_close=True,
            change=types.TextDocumentSyncKind.Full,
            save=types.SaveOptions(include_text=True),
        ),

        # Completion
        completion_provider=types.CompletionOptions(
            trigger_characters=["<", " ", ":", "{", '"', "'", "=", "/"],
            resolve_provider=True,
        ),

        # Hover
        hover_provider=types.HoverOptions(
            work_done_progress=False,
        ),

        # Go to definition
        definition_provider=types.DefinitionOptions(
            work_done_progress=False,
        ),

        # Find references
        references_provider=types.ReferenceOptions(
            work_done_progress=False,
        ),

        # Document symbols (outline)
        document_symbol_provider=types.DocumentSymbolOptions(
            work_done_progress=False,
        ),

        # Formatting
        document_formatting_provider=types.DocumentFormattingOptions(
            work_done_progress=False,
        ),

        # Range formatting
        document_range_formatting_provider=types.DocumentRangeFormattingOptions(
            work_done_progress=False,
        ),

        # Workspace capabilities
        workspace=types.ServerCapabilitiesWorkspaceType(
            workspace_folders=types.WorkspaceFoldersServerCapabilities(
                supported=True,
                change_notifications=True,
            ),
        ),

        # Execute command
        execute_command_provider=types.ExecuteCommandOptions(
            commands=[
                "quantum.validateDocument",
                "quantum.showAst",
            ]
        ),
    )
