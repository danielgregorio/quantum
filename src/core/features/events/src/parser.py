"""
Parser for Event System (q:on, q:dispatch)
"""

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from .ast_node import OnEventNode, DispatchEventNode


def parse_on_event(element: ET.Element) -> OnEventNode:
    """
    Parse <q:on> tag - Event handler

    Examples:
      <q:on event="userLogin" function="handleLogin" />
      <q:on event="click" once="true" prevent_default="true" />
    """
    event_name = element.get('event')
    if not event_name:
        raise ValueError("Event handler requires 'event' attribute")

    function_name = element.get('function')

    # Parse boolean attributes
    once = element.get('once', 'false').lower() == 'true'
    capture = element.get('capture', 'false').lower() == 'true'
    prevent_default = element.get('preventDefault', element.get('prevent_default', 'false')).lower() == 'true'
    stop_propagation = element.get('stopPropagation', element.get('stop_propagation', 'false')).lower() == 'true'

    # Parse timing attributes
    debounce_str = element.get('debounce')
    debounce = int(debounce_str) if debounce_str else None

    throttle_str = element.get('throttle')
    throttle = int(throttle_str) if throttle_str else None

    return OnEventNode(
        event_name=event_name,
        function_name=function_name,
        once=once,
        capture=capture,
        debounce=debounce,
        throttle=throttle,
        prevent_default=prevent_default,
        stop_propagation=stop_propagation
    )


def parse_dispatch_event(element: ET.Element) -> DispatchEventNode:
    """
    Parse <q:dispatch> tag - Emit event

    Examples:
      <q:dispatch event="userLogin" data="{user}" />
      <q:dispatch event="dataChange" bubbles="false" />
    """
    event_name = element.get('event')
    if not event_name:
        raise ValueError("Event dispatch requires 'event' attribute")

    data = element.get('data')

    # Parse boolean attributes
    bubbles = element.get('bubbles', 'true').lower() == 'true'
    cancelable = element.get('cancelable', 'true').lower() == 'true'
    composed = element.get('composed', 'false').lower() == 'true'

    # Parse custom data from child elements
    event_data = {}
    for child in element:
        if child.tag.endswith('data'):
            key = child.get('key')
            value = child.get('value')
            if key and value:
                event_data[key] = value

    return DispatchEventNode(
        event_name=event_name,
        data=data,
        bubbles=bubbles,
        cancelable=cancelable,
        composed=composed,
        event_data=event_data
    )
