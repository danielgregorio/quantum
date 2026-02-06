"""
Completion handler for textDocument/completion.

Provides autocompletion for:
- Tag names (q:set, q:loop, ui:button, etc.)
- Attribute names based on current tag
- Attribute values (enums, booleans)
- Variable references in {databinding}
- Function names
"""

import logging
from typing import List, Optional

from lsprotocol import types

from ..schema import QUANTUM_TAGS, get_tag_info, get_attributes_for_tag
from ..schema.types import AttributeType

logger = logging.getLogger("quantum-lsp")


def register_completion_handlers(server):
    """Register completion handlers with the server."""

    @server.feature(types.TEXT_DOCUMENT_COMPLETION)
    def completion(params: types.CompletionParams) -> Optional[types.CompletionList]:
        """Handle completion request."""
        uri = params.text_document.uri
        position = params.position

        doc = server.workspace_analyzer.get_document(uri)
        if not doc:
            return None

        # Determine context
        context = doc.get_context_at_position(position.line, position.character)
        logger.debug(f"Completion context: {context}")

        items = []

        if context["context"] == "tag_name":
            items = _get_tag_completions(context["prefix"])

        elif context["context"] == "attribute_name":
            items = _get_attribute_completions(context["tag"], context["prefix"])

        elif context["context"] == "attribute_value":
            items = _get_value_completions(context["tag"], context["attribute"], context["prefix"])

        elif context["context"] == "databinding":
            items = _get_databinding_completions(doc, context["prefix"])

        elif context["context"] == "content":
            # Offer tag completions when typing <
            items = _get_tag_completions("")

        return types.CompletionList(is_incomplete=False, items=items)

    @server.feature(types.COMPLETION_ITEM_RESOLVE)
    def completion_resolve(item: types.CompletionItem) -> types.CompletionItem:
        """Resolve additional completion item details."""
        # Add documentation if available
        if item.data and isinstance(item.data, dict):
            if "tag" in item.data:
                tag_info = get_tag_info(item.data["tag"])
                if tag_info:
                    item.documentation = types.MarkupContent(
                        kind=types.MarkupKind.Markdown,
                        value=tag_info.get_documentation()
                    )

            if "attribute" in item.data and "tag" in item.data:
                attrs = get_attributes_for_tag(item.data["tag"])
                attr_info = attrs.get(item.data["attribute"])
                if attr_info:
                    item.documentation = types.MarkupContent(
                        kind=types.MarkupKind.Markdown,
                        value=attr_info.get_documentation()
                    )

        return item


def _get_tag_completions(prefix: str) -> List[types.CompletionItem]:
    """Get tag name completions."""
    items = []

    for tag_name, tag_info in QUANTUM_TAGS.items():
        # Filter by prefix
        if prefix and not tag_name.lower().startswith(prefix.lower()):
            continue

        # Create snippet with required attributes
        snippet = tag_name
        required_attrs = tag_info.get_required_attributes()
        placeholders = []
        for i, attr in enumerate(required_attrs, 1):
            placeholders.append(f'{attr}="${{{i}:}}"')

        if placeholders:
            snippet += " " + " ".join(placeholders)

        if tag_info.self_closing:
            snippet += " />"
        else:
            snippet += f">${{0:}}</{tag_name}>"

        items.append(types.CompletionItem(
            label=tag_name,
            kind=types.CompletionItemKind.Class,
            detail=tag_info.description[:50] + "..." if len(tag_info.description) > 50 else tag_info.description,
            insert_text=snippet,
            insert_text_format=types.InsertTextFormat.Snippet,
            data={"tag": tag_name}
        ))

    return items


def _get_attribute_completions(tag: str, prefix: str) -> List[types.CompletionItem]:
    """Get attribute name completions for a tag."""
    items = []

    if not tag:
        return items

    # Get tag info
    tag_info = get_tag_info(tag)
    if not tag_info:
        return items

    attrs = tag_info.attributes

    for attr_name, attr_info in attrs.items():
        # Filter by prefix
        if prefix and not attr_name.lower().startswith(prefix.lower()):
            continue

        # Create snippet based on attribute type
        if attr_info.type == AttributeType.BOOLEAN:
            snippet = f'{attr_name}="${{1|true,false|}}"'
        elif attr_info.type == AttributeType.ENUM and attr_info.enum_values:
            values = ",".join(attr_info.enum_values)
            snippet = f'{attr_name}="${{1|{values}|}}"'
        else:
            snippet = f'{attr_name}="${{1:}}"'

        # Mark required attributes
        label = attr_name
        if attr_info.required:
            label = f"{attr_name}*"

        items.append(types.CompletionItem(
            label=label,
            kind=types.CompletionItemKind.Property,
            detail=f"({attr_info.type.value})" + (" required" if attr_info.required else ""),
            documentation=attr_info.description,
            insert_text=snippet,
            insert_text_format=types.InsertTextFormat.Snippet,
            sort_text="0" + attr_name if attr_info.required else "1" + attr_name,
            data={"tag": tag, "attribute": attr_name}
        ))

    return items


def _get_value_completions(tag: str, attribute: str, prefix: str) -> List[types.CompletionItem]:
    """Get attribute value completions."""
    items = []

    if not tag or not attribute:
        return items

    tag_info = get_tag_info(tag)
    if not tag_info:
        return items

    attr_info = tag_info.attributes.get(attribute)
    if not attr_info:
        return items

    # Boolean values
    if attr_info.type == AttributeType.BOOLEAN:
        for value in ["true", "false"]:
            if not prefix or value.startswith(prefix.lower()):
                items.append(types.CompletionItem(
                    label=value,
                    kind=types.CompletionItemKind.Value,
                    insert_text=value
                ))

    # Enum values
    elif attr_info.type == AttributeType.ENUM and attr_info.enum_values:
        for value in attr_info.enum_values:
            if not prefix or value.lower().startswith(prefix.lower()):
                items.append(types.CompletionItem(
                    label=value,
                    kind=types.CompletionItemKind.EnumMember,
                    insert_text=value
                ))

    return items


def _get_databinding_completions(doc, prefix: str) -> List[types.CompletionItem]:
    """Get completions for {databinding} expressions."""
    items = []

    # Get all variables from the document
    for symbol in doc.symbols.get_variables():
        if not prefix or symbol.name.lower().startswith(prefix.lower()):
            items.append(types.CompletionItem(
                label=symbol.name,
                kind=types.CompletionItemKind.Variable,
                detail=f"({symbol.type_hint})" if symbol.type_hint else None,
                documentation=symbol.description,
                insert_text=symbol.name
            ))

    # Get all parameters
    for symbol in doc.symbols.get_symbols_by_kind(doc.symbols._by_kind):
        pass  # Already included in variables conceptually

    # Get all queries
    for symbol in doc.symbols.get_queries():
        if not prefix or symbol.name.lower().startswith(prefix.lower()):
            items.append(types.CompletionItem(
                label=symbol.name,
                kind=types.CompletionItemKind.Struct,
                detail="(query)",
                documentation=symbol.description,
                insert_text=symbol.name
            ))

    # Get all functions
    for symbol in doc.symbols.get_functions():
        if not prefix or symbol.name.lower().startswith(prefix.lower()):
            items.append(types.CompletionItem(
                label=symbol.name + "()",
                kind=types.CompletionItemKind.Function,
                detail=f"(): {symbol.type_hint}" if symbol.type_hint else "()",
                documentation=symbol.description,
                insert_text=symbol.name + "()"
            ))

    return items
