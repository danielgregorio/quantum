"""
CLI Component Renderers - Terminal/Console version of components

Maps MXML components to text-based terminal output.
Maintains API compatibility with web and desktop versions.
"""

from typing import Dict, Any
import re


def render_application(runtime, node: Dict):
    """Render Application as container"""
    # Just render children
    for child in node.get('children', []):
        runtime.render_component(child)


def render_vbox(runtime, node: Dict):
    """Render VBox as vertical sections"""
    props = node.get('props', {})

    # Add spacing before if padding specified
    if 'padding' in props:
        runtime.rendered_output.append("")

    # Render children vertically
    for child in node.get('children', []):
        runtime.render_component(child)

        # Add gap between children
        gap = int(props.get('gap', 0))
        if gap > 0:
            for _ in range(gap // 10):  # Convert px to line breaks
                runtime.rendered_output.append("")

    # Add spacing after if padding specified
    if 'padding' in props:
        runtime.rendered_output.append("")


def render_hbox(runtime, node: Dict):
    """Render HBox as horizontal layout (side by side text)"""
    props = node.get('props', {})

    # Collect child outputs
    child_outputs = []
    for child in node.get('children', []):
        # Capture output for this child
        temp_output = runtime.rendered_output.copy()
        runtime.rendered_output = []

        runtime.render_component(child)

        child_output = runtime.rendered_output
        runtime.rendered_output = temp_output

        child_outputs.append(child_output)

    # Combine horizontally (simple approach: join with spacing)
    gap = props.get('gap', '10')
    gap_str = " " * (int(gap) // 5)  # Convert px to spaces

    # For simplicity, join on same line
    combined = gap_str.join([
        " ".join(lines) for lines in child_outputs
    ])
    runtime.rendered_output.append(combined)


def render_label(runtime, node: Dict):
    """Render Label as text"""
    props = node.get('props', {})

    # Get text with binding support
    text = props.get('text', '')
    text = runtime.evaluate_binding(text)

    # Apply styling
    font_size = int(props.get('fontSize', 14))
    font_weight = props.get('fontWeight', 'normal')
    color = props.get('color', '')

    # Format text based on size
    if font_size >= 24:
        # Large title
        text = f"\n{'=' * len(str(text))}\n{text}\n{'=' * len(str(text))}\n"
    elif font_size >= 18:
        # Subtitle
        text = f"\n{text}\n{'-' * len(str(text))}"
    elif font_weight == 'bold':
        # Bold (uppercase)
        text = str(text).upper()

    runtime.rendered_output.append(str(text))


def render_button(runtime, node: Dict):
    """Render Button as menu option"""
    props = node.get('props', {})
    events = node.get('events', {})

    label = props.get('label', 'Button')

    # Add to menu items for interactive selection
    if 'click' in events:
        handler_code = events['click']

        def handler():
            runtime.execute_handler(handler_code)

        runtime.menu_items.append((label, handler))


def render_text_input(runtime, node: Dict):
    """Render TextInput as interactive prompt"""
    props = node.get('props', {})
    events = node.get('events', {})

    label = props.get('placeholder', 'Enter text')
    text_prop = props.get('text', '')

    # Check if it's bound to a variable
    match = re.match(r'\{([^}]+)\}', text_prop)
    if match:
        var_name = match.group(1).strip()
        current_value = getattr(runtime.app, var_name, '')

        # Add as interactive menu option
        def handler():
            new_value = input(f"{label}: ")
            setattr(runtime.app, var_name, new_value)
            print(f"Updated {var_name} = {new_value}")

        runtime.menu_items.append((f"Edit: {label}", handler))

        # Show current value
        runtime.rendered_output.append(f"{label}: {current_value}")
    else:
        runtime.rendered_output.append(f"{label}: ")


def render_panel(runtime, node: Dict):
    """Render Panel as bordered section"""
    props = node.get('props', {})

    title = props.get('title', '')

    # Top border
    if title:
        runtime.rendered_output.append("")
        runtime.rendered_output.append(f"╔══ {title} " + "═" * (50 - len(title)))
    else:
        runtime.rendered_output.append("╔" + "═" * 58 + "╗")

    # Render children with indent
    temp_output = runtime.rendered_output.copy()
    runtime.rendered_output = []

    for child in node.get('children', []):
        runtime.render_component(child)

    # Add indent to child output
    for line in runtime.rendered_output:
        temp_output.append(f"║  {line}")

    runtime.rendered_output = temp_output

    # Bottom border
    runtime.rendered_output.append("╚" + "═" * 58 + "╝")
    runtime.rendered_output.append("")


def render_spacer(runtime, node: Dict):
    """Render Spacer as blank lines"""
    props = node.get('props', {})

    height = int(props.get('height', 10))
    lines = max(1, height // 20)  # Convert px to lines

    for _ in range(lines):
        runtime.rendered_output.append("")


def render_checkbox(runtime, node: Dict):
    """Render CheckBox as toggle option"""
    props = node.get('props', {})
    events = node.get('events', {})

    label = props.get('label', 'Checkbox')
    selected_prop = props.get('selected', 'false')

    # Check if bound to variable
    match = re.match(r'\{([^}]+)\}', selected_prop)
    if match:
        var_name = match.group(1).strip()
        current_value = getattr(runtime.app, var_name, False)

        # Add as interactive menu option
        def handler():
            new_value = not current_value
            setattr(runtime.app, var_name, new_value)
            print(f"Toggled {var_name} = {new_value}")

        runtime.menu_items.append((f"Toggle: {label}", handler))

        # Show current state
        check = "☑" if current_value else "☐"
        runtime.rendered_output.append(f"{check} {label}")
    else:
        check = "☑" if selected_prop == 'true' else "☐"
        runtime.rendered_output.append(f"{check} {label}")


def render_progress_bar(runtime, node: Dict):
    """Render ProgressBar as text-based progress"""
    props = node.get('props', {})

    value_expr = props.get('value', '0')
    value = runtime.evaluate_binding(value_expr)
    maximum = float(props.get('maximum', 100))

    # Calculate progress
    progress = int((float(value) / maximum) * 40)  # 40 chars wide

    # Render progress bar
    bar = "█" * progress + "░" * (40 - progress)
    runtime.rendered_output.append(f"[{bar}] {value}%")


def render_numeric_stepper(runtime, node: Dict):
    """Render NumericStepper as interactive number input"""
    props = node.get('props', {})

    value_prop = props.get('value', '0')
    minimum = float(props.get('minimum', 0))
    maximum = float(props.get('maximum', 100))
    step = float(props.get('stepSize', 1))

    # Check if bound to variable
    match = re.match(r'\{([^}]+)\}', value_prop)
    if match:
        var_name = match.group(1).strip()
        current_value = float(getattr(runtime.app, var_name, 0))

        # Add increment/decrement options
        def increment():
            new_value = min(maximum, current_value + step)
            setattr(runtime.app, var_name, new_value)

        def decrement():
            new_value = max(minimum, current_value - step)
            setattr(runtime.app, var_name, new_value)

        runtime.menu_items.append((f"Increment {var_name}", increment))
        runtime.menu_items.append((f"Decrement {var_name}", decrement))

        # Show current value
        runtime.rendered_output.append(f"{var_name}: {current_value}")
    else:
        runtime.rendered_output.append(f"Value: {value_prop}")


def render_slider(runtime, node: Dict):
    """Render Slider as visual scale"""
    props = node.get('props', {})

    value_expr = props.get('value', '0')
    value = float(runtime.evaluate_binding(value_expr))
    minimum = float(props.get('minimum', 0))
    maximum = float(props.get('maximum', 100))

    # Calculate position
    range_size = maximum - minimum
    position = int(((value - minimum) / range_size) * 30) if range_size > 0 else 0

    # Render slider
    slider = "─" * position + "●" + "─" * (30 - position)
    runtime.rendered_output.append(f"[{slider}] {value}")
