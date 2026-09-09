"""
GTK Component Renderers - Desktop equivalent of web components

Maps MXML components to GTK widgets for native desktop applications.
Maintains API compatibility with web version.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
import re
from typing import Dict, Any


def render_application(runtime, node: Dict):
    """Render Application as VBox container"""
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

    # Apply background color if specified
    if 'props' in node and 'backgroundColor' in node['props']:
        bg_color = node['props']['backgroundColor']
        # Parse color and apply via CSS
        css = f"""
        * {{
            background-color: {bg_color};
        }}
        """
        apply_css(vbox, css)

    # Render children
    for child in node.get('children', []):
        widget = runtime.render_component(child)
        if widget:
            vbox.pack_start(widget, True, True, 0)

    runtime.apply_common_props(vbox, node.get('props', {}))
    return vbox


def render_vbox(runtime, node: Dict):
    """Render VBox as GTK vertical box"""
    props = node.get('props', {})

    # Get spacing (gap)
    spacing = int(props.get('gap', 0))
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)

    # Apply padding
    if 'padding' in props:
        padding = int(props['padding'])
        vbox.set_margin_top(padding)
        vbox.set_margin_bottom(padding)
        vbox.set_margin_start(padding)
        vbox.set_margin_end(padding)

    # Render children
    for child in node.get('children', []):
        widget = runtime.render_component(child)
        if widget:
            expand = child.get('type') in ['Panel', 'DataGrid', 'List', 'TextArea']
            vbox.pack_start(widget, expand, expand, 0)

    runtime.apply_common_props(vbox, props)
    return vbox


def render_hbox(runtime, node: Dict):
    """Render HBox as GTK horizontal box"""
    props = node.get('props', {})

    spacing = int(props.get('gap', 0))
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)

    # Apply padding
    if 'padding' in props:
        padding = int(props['padding'])
        hbox.set_margin_top(padding)
        hbox.set_margin_bottom(padding)
        hbox.set_margin_start(padding)
        hbox.set_margin_end(padding)

    # Vertical alignment
    if 'verticalAlign' in props:
        align = props['verticalAlign']
        if align == 'middle':
            hbox.set_valign(Gtk.Align.CENTER)
        elif align == 'top':
            hbox.set_valign(Gtk.Align.START)
        elif align == 'bottom':
            hbox.set_valign(Gtk.Align.END)

    # Render children
    for child in node.get('children', []):
        widget = runtime.render_component(child)
        if widget:
            expand = child.get('type') == 'Spacer' or 'flex' in child.get('props', {})
            hbox.pack_start(widget, expand, expand, 0)

    runtime.apply_common_props(hbox, props)
    return hbox


def render_label(runtime, node: Dict):
    """Render Label as GTK label"""
    props = node.get('props', {})
    label = Gtk.Label()

    # Set text with reactive binding
    if 'text' in props:
        runtime.create_reactive_binding(label, props['text'], 'label')

    # Font size
    if 'fontSize' in props:
        font_size = props['fontSize']
        markup = f'<span font_size="{font_size * 1024}">{label.get_label()}</span>'
        label.set_markup(markup)

    # Font weight
    if 'fontWeight' in props and props['fontWeight'] == 'bold':
        label.set_markup(f'<b>{label.get_label()}</b>')

    # Color
    if 'color' in props:
        color = props['color']
        label.set_markup(f'<span foreground="{color}">{label.get_label()}</span>')

    # Alignment
    if 'textAlign' in props:
        align = props['textAlign']
        if align == 'center':
            label.set_xalign(0.5)
        elif align == 'right':
            label.set_xalign(1.0)
        else:
            label.set_xalign(0.0)

    runtime.apply_common_props(label, props)
    return label


def render_button(runtime, node: Dict):
    """Render Button as GTK button"""
    props = node.get('props', {})
    events = node.get('events', {})

    label_text = props.get('label', 'Button')
    button = Gtk.Button(label=label_text)

    # Enabled/disabled
    if 'enabled' in props and props['enabled'] == 'false':
        button.set_sensitive(False)

    # Click handler
    if 'click' in events:
        handler_code = events['click']
        button.connect('clicked', lambda btn: runtime.execute_handler(handler_code, btn))

    runtime.apply_common_props(button, props)
    return button


def render_text_input(runtime, node: Dict):
    """Render TextInput as GTK entry"""
    props = node.get('props', {})
    events = node.get('events', {})

    entry = Gtk.Entry()

    # Initial value with reactive binding
    if 'text' in props:
        match = re.match(r'\{([^}]+)\}', props['text'])
        if match:
            var_name = match.group(1).strip()
            # Set initial value
            initial_value = runtime.evaluate_binding(props['text'])
            entry.set_text(str(initial_value))
            # Setup two-way binding
            runtime.setup_two_way_binding(entry, var_name)
        else:
            entry.set_text(props['text'])

    # Placeholder
    if 'placeholder' in props:
        entry.set_placeholder_text(props['placeholder'])

    # Max length
    if 'maxChars' in props:
        entry.set_max_length(int(props['maxChars']))

    # Password mode
    if 'displayAsPassword' in props and props['displayAsPassword'] == 'true':
        entry.set_visibility(False)

    # Event handlers
    if 'change' in events:
        entry.connect('changed', lambda e: runtime.execute_handler(events['change'], e))

    runtime.apply_common_props(entry, props)
    return entry


def render_panel(runtime, node: Dict):
    """Render Panel as GTK frame"""
    props = node.get('props', {})

    frame = Gtk.Frame()

    # Set title
    if 'title' in props:
        frame.set_label(props['title'])

    # Create inner container
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    vbox.set_margin_top(10)
    vbox.set_margin_bottom(10)
    vbox.set_margin_start(10)
    vbox.set_margin_end(10)

    # Render children
    for child in node.get('children', []):
        widget = runtime.render_component(child)
        if widget:
            vbox.pack_start(widget, False, False, 0)

    frame.add(vbox)
    runtime.apply_common_props(frame, props)
    return frame


def render_spacer(runtime, node: Dict):
    """Render Spacer as expanding box"""
    props = node.get('props', {})
    spacer = Gtk.Box()

    if 'width' in props:
        spacer.set_size_request(int(props['width']), -1)
    elif 'height' in props:
        spacer.set_size_request(-1, int(props['height']))
    else:
        spacer.set_hexpand(True)
        spacer.set_vexpand(True)

    return spacer


def render_checkbox(runtime, node: Dict):
    """Render CheckBox as GTK checkbox"""
    props = node.get('props', {})
    events = node.get('events', {})

    label_text = props.get('label', '')
    checkbox = Gtk.CheckButton(label=label_text)

    # Initial selected state
    if 'selected' in props:
        initial_value = runtime.evaluate_binding(props['selected'])
        checkbox.set_active(initial_value == True or initial_value == 'true')

    # Two-way binding
    if 'selected' in props and '{' in props['selected']:
        match = re.match(r'\{([^}]+)\}', props['selected'])
        if match:
            var_name = match.group(1).strip()

            # Update app property when checkbox changes
            def on_toggled(widget):
                setattr(runtime.app, var_name, widget.get_active())

            checkbox.connect('toggled', on_toggled)

            # Update checkbox when app property changes
            def update_fn(new_value):
                checkbox.set_active(new_value == True or new_value == 'true')

            runtime.track_dependency(var_name, update_fn)

    # Change event
    if 'change' in events:
        checkbox.connect('toggled', lambda cb: runtime.execute_handler(events['change'], cb.get_active()))

    # Enabled/disabled
    if 'enabled' in props and props['enabled'] == 'false':
        checkbox.set_sensitive(False)

    runtime.apply_common_props(checkbox, props)
    return checkbox


def render_text_area(runtime, node: Dict):
    """Render TextArea as GTK TextView with ScrolledWindow"""
    props = node.get('props', {})

    # Create TextView
    textview = Gtk.TextView()
    textview.set_wrap_mode(Gtk.WrapMode.WORD)

    # Create ScrolledWindow
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scrolled.add(textview)

    # Set size
    width = int(props.get('width', 300))
    height = int(props.get('height', 150))
    scrolled.set_size_request(width, height)

    # Initial text
    if 'text' in props:
        match = re.match(r'\{([^}]+)\}', props['text'])
        if match:
            var_name = match.group(1).strip()
            initial_value = runtime.evaluate_binding(props['text'])
            textview.get_buffer().set_text(str(initial_value))
            runtime.setup_two_way_binding(textview, var_name)
        else:
            textview.get_buffer().set_text(props['text'])

    runtime.apply_common_props(scrolled, props)
    return scrolled


def render_numeric_stepper(runtime, node: Dict):
    """Render NumericStepper as GTK SpinButton"""
    props = node.get('props', {})

    minimum = float(props.get('minimum', 0))
    maximum = float(props.get('maximum', 100))
    step = float(props.get('stepSize', 1))
    value = float(props.get('value', minimum))

    adjustment = Gtk.Adjustment(value=value, lower=minimum, upper=maximum,
                                 step_increment=step, page_increment=step * 10)

    spinner = Gtk.SpinButton()
    spinner.set_adjustment(adjustment)

    # Two-way binding
    if 'value' in props and '{' in props['value']:
        match = re.match(r'\{([^}]+)\}', props['value'])
        if match:
            var_name = match.group(1).strip()

            def on_value_changed(widget):
                setattr(runtime.app, var_name, widget.get_value())

            spinner.connect('value-changed', on_value_changed)

            def update_fn(new_value):
                spinner.set_value(float(new_value))

            runtime.track_dependency(var_name, update_fn)

    runtime.apply_common_props(spinner, props)
    return spinner


def render_slider(runtime, node: Dict):
    """Render Slider as GTK Scale"""
    props = node.get('props', {})

    minimum = float(props.get('minimum', 0))
    maximum = float(props.get('maximum', 100))
    value = float(props.get('value', minimum))

    # Determine orientation
    is_vertical = node.get('type') == 'VSlider'
    orientation = Gtk.Orientation.VERTICAL if is_vertical else Gtk.Orientation.HORIZONTAL

    adjustment = Gtk.Adjustment(value=value, lower=minimum, upper=maximum,
                                 step_increment=1, page_increment=10)

    scale = Gtk.Scale(orientation=orientation, adjustment=adjustment)
    scale.set_draw_value(True)

    if not is_vertical:
        scale.set_size_request(200, -1)
    else:
        scale.set_size_request(-1, 200)

    # Two-way binding
    if 'value' in props and '{' in props['value']:
        match = re.match(r'\{([^}]+)\}', props['value'])
        if match:
            var_name = match.group(1).strip()

            def on_value_changed(widget):
                setattr(runtime.app, var_name, widget.get_value())

            scale.connect('value-changed', on_value_changed)

            def update_fn(new_value):
                scale.set_value(float(new_value))

            runtime.track_dependency(var_name, update_fn)

    runtime.apply_common_props(scale, props)
    return scale


def render_progress_bar(runtime, node: Dict):
    """Render ProgressBar as GTK ProgressBar"""
    props = node.get('props', {})

    progress = Gtk.ProgressBar()

    # Set initial value
    if 'value' in props:
        initial_value = runtime.evaluate_binding(props['value'])
        maximum = float(props.get('maximum', 100))
        progress.set_fraction(float(initial_value) / maximum)

    # Reactive binding
    if 'value' in props and '{' in props['value']:
        match = re.match(r'\{([^}]+)\}', props['value'])
        if match:
            var_name = match.group(1).strip()
            maximum = float(props.get('maximum', 100))

            def update_fn(new_value):
                progress.set_fraction(float(new_value) / maximum)
                progress.set_text(f"{new_value}%")

            runtime.track_dependency(var_name, update_fn)

    # Label
    if 'label' in props:
        label_text = runtime.evaluate_binding(props['label'])
        progress.set_text(label_text)
        progress.set_show_text(True)

    runtime.apply_common_props(progress, props)
    return progress


def render_combobox(runtime, node: Dict):
    """Render ComboBox as GTK ComboBoxText"""
    props = node.get('props', {})

    combo = Gtk.ComboBoxText()

    # Get data provider
    data = []
    if 'dataProvider' in props:
        data = runtime.evaluate_binding(props['dataProvider'])
        if not isinstance(data, list):
            data = []

    label_field = props.get('labelField', 'label')

    # Add prompt
    if 'prompt' in props:
        combo.append_text(props['prompt'])
        combo.set_active(0)

    # Add data items
    for item in data:
        if isinstance(item, dict):
            combo.append_text(item.get(label_field, str(item)))
        else:
            combo.append_text(str(item))

    # Two-way binding for selectedIndex
    if 'selectedIndex' in props and '{' in props['selectedIndex']:
        match = re.match(r'\{([^}]+)\}', props['selectedIndex'])
        if match:
            var_name = match.group(1).strip()
            has_prompt = 'prompt' in props

            def on_changed(widget):
                index = widget.get_active()
                if has_prompt:
                    index -= 1
                setattr(runtime.app, var_name, index)

            combo.connect('changed', on_changed)

            def update_fn(new_value):
                index = int(new_value)
                if has_prompt:
                    index += 1
                combo.set_active(index)

            runtime.track_dependency(var_name, update_fn)

    runtime.apply_common_props(combo, props)
    return combo


def apply_css(widget, css_str: str):
    """Apply CSS styling to widget"""
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(css_str.encode())

    context = widget.get_style_context()
    context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
