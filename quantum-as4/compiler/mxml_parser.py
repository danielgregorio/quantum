"""
MXML Parser - Parse MXML files to AST

Parses Flex/Spark MXML syntax and extracts:
- ActionScript code from <fx:Script>
- CSS styles from <fx:Style>
- UI component tree
"""

from lxml import etree
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Component:
    """Represents a UI component in the MXML tree"""
    type: str                    # "VBox", "Button", "Label", etc.
    props: Dict[str, str]        # {"padding": "20", "gap": "15", "text": "Hello"}
    children: List['Component']  # Child components
    events: Dict[str, str]       # {"click": "handleClick()"}


@dataclass
class Application:
    """Represents the complete parsed MXML application"""
    script: str          # ActionScript code from <fx:Script>
    style: str           # CSS code from <fx:Style>
    ui: Component        # Root UI component tree


class MXMLParser:
    """
    Parse MXML files using lxml

    Supports Flex namespaces:
    - fx: http://ns.adobe.com/mxml/2009
    - s: library://ns.adobe.com/flex/spark
    - mx: library://ns.adobe.com/flex/mx
    """

    NAMESPACES = {
        'fx': 'http://ns.adobe.com/mxml/2009',
        's': 'library://ns.adobe.com/flex/spark',
        'mx': 'library://ns.adobe.com/flex/mx',
        'q': 'http://quantum-lang.org/qml/2025'
    }

    # Additional namespace variations (Flex 3 uses different URIs)
    LEGACY_NAMESPACES = {
        'mx': 'http://www.adobe.com/2006/mxml'
    }

    # Events that should be extracted from props
    EVENT_ATTRIBUTES = [
        'click', 'change', 'input', 'focus', 'blur',
        'mouseOver', 'mouseOut', 'keyDown', 'keyUp',
        'creationComplete', 'initialize'
    ]

    def parse(self, mxml_file: str) -> Application:
        """
        Parse MXML file and return Application AST

        Args:
            mxml_file: Path to .mxml file

        Returns:
            Application object with script, style, and UI tree
        """
        # Parse XML
        tree = etree.parse(mxml_file)
        root = tree.getroot()

        # Extract sections
        script = self._extract_script(root)
        style = self._extract_style(root)
        ui = self._parse_component(root)

        return Application(
            script=script,
            style=style,
            ui=ui
        )

    def parse_string(self, mxml_string: str) -> Application:
        """Parse MXML from string instead of file"""
        root = etree.fromstring(mxml_string.encode('utf-8'))

        script = self._extract_script(root)
        style = self._extract_style(root)
        ui = self._parse_component(root)

        return Application(
            script=script,
            style=style,
            ui=ui
        )

    def _extract_script(self, root) -> str:
        """
        Extract ActionScript code from <fx:Script> or <mx:Script> block

        The script is usually wrapped in CDATA:
        <fx:Script>
            <![CDATA[
                private var message:String = "Hello";
            ]]>
        </fx:Script>
        """
        # Try fx:Script first (Flex 4)
        script_elem = root.find('.//fx:Script', self.NAMESPACES)
        if script_elem is None:
            # Try mx:Script with Flex 4 namespace
            script_elem = root.find('.//mx:Script', self.NAMESPACES)
        if script_elem is None:
            # Try mx:Script with Flex 3 namespace (legacy)
            script_elem = root.find('.//mx:Script', self.LEGACY_NAMESPACES)

        if script_elem is not None:
            # Get text content (CDATA is treated as text)
            return script_elem.text or ''
        return ''

    def _extract_style(self, root) -> str:
        """
        Extract CSS from <fx:Style> or <mx:Style> block

        Can be inline or reference external file:
        <fx:Style>
            .button { color: red; }
        </fx:Style>

        <fx:Style source="styles.css"/>
        """
        # Try fx:Style first (Flex 4)
        style_elem = root.find('.//fx:Style', self.NAMESPACES)
        if style_elem is None:
            # Try mx:Style with Flex 4 namespace
            style_elem = root.find('.//mx:Style', self.NAMESPACES)
        if style_elem is None:
            # Try mx:Style with Flex 3 namespace (legacy)
            style_elem = root.find('.//mx:Style', self.LEGACY_NAMESPACES)

        if style_elem is not None:
            # Check for source attribute (external CSS)
            if 'source' in style_elem.attrib:
                # TODO: Load external CSS file
                return f"/* External: {style_elem.attrib['source']} */"
            # Inline CSS
            return style_elem.text or ''
        return ''

    def _parse_component(self, elem) -> Component:
        """
        Recursively parse a component element and its children

        Example:
        <s:VBox padding="20" gap="15">
            <s:Label text="Hello"/>
            <s:Button label="Click" click="handleClick()"/>
        </s:VBox>
        """
        # Get component type (remove namespace prefix)
        # "{http://ns.adobe.com/flex/spark}VBox" → "VBox"
        tag = elem.tag
        if '}' in tag:
            tag = tag.split('}')[-1]

        # Separate props and events
        props = {}
        events = {}

        for key, value in elem.attrib.items():
            # Remove namespace from attribute names
            if '}' in key:
                key = key.split('}')[-1]

            # Check if it's an event handler
            if key in self.EVENT_ATTRIBUTES:
                events[key] = value
            else:
                props[key] = value

        # Parse children recursively
        children = []
        for child in elem:
            # Skip non-element nodes (comments, processing instructions, etc.)
            if not isinstance(child.tag, str):
                continue

            child_tag = child.tag
            if '}' in child_tag:
                child_tag = child_tag.split('}')[-1]

            # Skip Script and Style elements (already extracted)
            if child_tag not in ['Script', 'Style']:
                children.append(self._parse_component(child))

        return Component(
            type=tag,
            props=props,
            children=children,
            events=events
        )


# Example usage
if __name__ == '__main__':
    # Test with a simple MXML string
    mxml = '''<?xml version="1.0"?>
    <Application xmlns:fx="http://ns.adobe.com/mxml/2009"
                 xmlns:s="library://ns.adobe.com/flex/spark">
        <fx:Script>
            <![CDATA[
                private var message:String = "Hello World";
            ]]>
        </fx:Script>

        <s:VBox padding="20">
            <s:Label text="{message}"/>
        </s:VBox>
    </Application>
    '''

    parser = MXMLParser()
    app = parser.parse_string(mxml)

    print(f"Script: {app.script.strip()}")
    print(f"UI Type: {app.ui.type}")
    print(f"Children: {len(app.ui.children)}")
