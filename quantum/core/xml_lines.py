"""XML into an ElementTree whose elements know their line (M2, DEV-2).

`xml.etree` does not keep source positions, so an error found after parsing —
a statement inside markup, an unknown attribute, a failing expression — could
name the tag but not where it is. This builds the same tree with expat (the
parser ElementTree itself runs on) and sets `element.sourceline` on each
element.
"""

from xml.etree import ElementTree as ET
from xml.parsers import expat


class _Element(ET.Element):
    """An Element that can carry `sourceline` (the C Element takes no new attributes)."""
    sourceline = None


def fromstring_with_lines(text: str) -> ET.Element:
    """Like ET.fromstring(text); every element gets `sourceline` (1-based)."""
    builder = ET.TreeBuilder(element_factory=_Element)
    parser = expat.ParserCreate(None, '}')
    parser.buffer_text = True
    parser.ordered_attributes = True

    def qualified(raw: str) -> str:
        # expat with a separator reports "uri}local"; ElementTree spells it "{uri}local".
        return '{' + raw if '}' in raw else raw

    def on_start(tag, attributes):
        pairs = dict(zip(attributes[0::2], attributes[1::2]))
        element = builder.start(qualified(tag), {qualified(k): v for k, v in pairs.items()})
        element.sourceline = parser.CurrentLineNumber

    parser.StartElementHandler = on_start
    parser.EndElementHandler = lambda tag: builder.end(qualified(tag))
    parser.CharacterDataHandler = builder.data
    try:
        parser.Parse(text, True)
    except expat.ExpatError as exc:
        error = ET.ParseError(str(exc))
        error.code = exc.code
        error.position = (exc.lineno, exc.offset)
        raise error from None
    return builder.close()


def line_of(item) -> int:
    """The source line of an element or an AST node, or None."""
    return getattr(item, 'sourceline', None) or getattr(item, 'source_line', None)


def tag_error(exc: BaseException, node) -> None:
    """DEV-2: the innermost node an error passes through names its file and line.

    Innermost across wrapping too: an error in a called component is re-raised
    as a new exception by the page; the line inside the component, already in
    the chain, wins over the line of the call."""
    if error_location(exc)[1] is not None:
        return
    line = getattr(node, 'source_line', None)
    if not line:
        return
    try:
        exc.quantum_line = line
        exc.quantum_file = getattr(node, 'source_file', None)
    except (AttributeError, TypeError):
        pass                                    # an exception type with __slots__


def error_location(exc: BaseException):
    """(file, line) of an error or of any error it wraps; (None, None) if unknown."""
    visto = set()
    while exc is not None and id(exc) not in visto:
        visto.add(id(exc))
        if getattr(exc, 'quantum_line', None) is not None:
            return getattr(exc, 'quantum_file', None), exc.quantum_line
        if getattr(exc, 'line', None) is not None and type(exc).__name__ == 'QuantumParseError':
            return getattr(exc, 'file', None), exc.line
        exc = exc.__cause__ or exc.__context__
    return None, None
