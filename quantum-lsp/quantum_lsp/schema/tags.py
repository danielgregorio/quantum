"""
Quantum Tag Definitions

Complete schema for all Quantum framework tags organized by namespace.
"""

from typing import Dict, List, Optional
from .types import TagInfo, AttributeInfo, AttributeType
from .core_tags import CORE_AI_TAGS


def _attr(
    name: str,
    type: AttributeType = AttributeType.STRING,
    required: bool = False,
    default: Optional[str] = None,
    description: str = "",
    enum_values: List[str] = None
) -> AttributeInfo:
    """Helper to create AttributeInfo."""
    return AttributeInfo(
        name=name,
        type=type,
        required=required,
        default=default,
        description=description,
        enum_values=enum_values or []
    )


# =============================================================================
# QUANTUM CORE TAGS (q: namespace)
# =============================================================================


Q_APPLICATION = TagInfo(
    name="application",
    namespace="q",
    description="Defines a Quantum application. Applications can be game, terminal, or UI type.",
    attributes={
        "id": _attr("id", required=True, description="Unique application identifier"),
        "type": _attr("type", type=AttributeType.ENUM, required=True,
                     enum_values=["game", "terminal", "ui"],
                     description="Application type (html, api and microservices were removed in 0.11, testing in 0.22)"),
        "engine": _attr("engine", description="Engine variant (e.g., '2d' for game type)"),
        "theme": _attr("theme", description="Theme preset for UI applications"),
    },
    children=["q:component"],
    examples=[
        '<q:application id="myGame" type="game" engine="2d">\n</q:application>',
    ],
    see_also=["q:component"]
)


Q_LOG = TagInfo(
    name="log",
    namespace="q",
    description="Logs a message for debugging or monitoring.",
    attributes={
        "message": _attr("message", type=AttributeType.EXPRESSION,
                        description="Log message (supports databinding)"),
        "level": _attr("level", type=AttributeType.ENUM, default="info",
                      enum_values=["debug", "info", "warn", "error"],
                      description="Log level"),
        "var": _attr("var", description="Variable to dump"),
    },
    self_closing=True,
    examples=[
        '<q:log message="Processing user {userId}" level="debug" />',
        '<q:log var="userData" level="info" />',
    ],
    see_also=["q:dump"]
)

Q_DUMP = TagInfo(
    name="dump",
    namespace="q",
    description="Dumps a variable's contents for debugging.",
    attributes={
        "var": _attr("var", required=True, description="Variable to dump"),
        "label": _attr("label", description="Label for the dump output"),
        "format": _attr("format", type=AttributeType.ENUM, default="auto",
                       enum_values=["auto", "json", "table", "tree"],
                       description="Output format"),
    },
    self_closing=True,
    examples=[
        '<q:dump var="users" />',
        '<q:dump var="config" label="Configuration" format="json" />',
    ],
    see_also=["q:log"]
)


Q_ONEVENT = TagInfo(
    name="onEvent",
    namespace="q",
    description="Subscribes to and handles events.",
    attributes={
        "event": _attr("event", required=True, description="Event pattern (supports wildcards)"),
        "queue": _attr("queue", description="Queue name for message broker"),
        "maxRetries": _attr("maxRetries", type=AttributeType.INTEGER, default="0",
                           description="Maximum retry attempts"),
        "retryDelay": _attr("retryDelay", description="Delay between retries (e.g., '30s')"),
        "deadLetter": _attr("deadLetter", description="Dead letter queue name"),
        "filter": _attr("filter", type=AttributeType.EXPRESSION, description="Filter expression"),
        "concurrent": _attr("concurrent", type=AttributeType.INTEGER, default="1",
                           description="Concurrent handler count"),
        "timeout": _attr("timeout", description="Handler timeout"),
    },
    children=["q:set", "q:if", "q:query", "q:invoke"],
    examples=[
        '<q:onEvent event="user.created">\n  <q:log message="User created: {event.data.userId}" />\n</q:onEvent>',
    ],
    see_also=["q:dispatchEvent"]
)

Q_DISPATCHEVENT = TagInfo(
    name="dispatchEvent",
    namespace="q",
    description="Publishes an event to the event bus.",
    attributes={
        "event": _attr("event", required=True, description="Event name"),
        "data": _attr("data", type=AttributeType.EXPRESSION, description="Event payload"),
        "queue": _attr("queue", description="Target queue"),
        "exchange": _attr("exchange", description="Exchange name"),
        "routingKey": _attr("routingKey", description="Routing key"),
        "priority": _attr("priority", type=AttributeType.ENUM, default="normal",
                         enum_values=["low", "normal", "high"],
                         description="Event priority"),
        "delay": _attr("delay", description="Delay before delivery (e.g., '5s')"),
        "ttl": _attr("ttl", description="Time-to-live (e.g., '60s')"),
    },
    self_closing=True,
    examples=[
        '<q:dispatchEvent event="user.created" data="{userData}" />',
    ],
    see_also=["q:onEvent"]
)


# =============================================================================
# UI ENGINE TAGS (ui: namespace)
# =============================================================================

# Layout attributes shared by most UI containers
_LAYOUT_ATTRS = {
    "gap": _attr("gap", type=AttributeType.CSS_SIZE, description="Gap between children"),
    "padding": _attr("padding", type=AttributeType.CSS_SIZE, description="Inner padding"),
    "margin": _attr("margin", type=AttributeType.CSS_SIZE, description="Outer margin"),
    "align": _attr("align", type=AttributeType.ENUM,
                  enum_values=["start", "center", "end", "stretch", "left", "right", "justify", "top", "bottom", "middle", "baseline"],
                  description="Cross-axis alignment"),
    "justify": _attr("justify", type=AttributeType.ENUM,
                    enum_values=["start", "center", "end", "between", "around"],
                    description="Main-axis alignment"),
    "width": _attr("width", type=AttributeType.CSS_SIZE, description="Width"),
    "height": _attr("height", type=AttributeType.CSS_SIZE, description="Height"),
    "background": _attr("background", type=AttributeType.CSS_COLOR, description="Background color"),
    "color": _attr("color", type=AttributeType.CSS_COLOR, description="Text color"),
    "border": _attr("border", description="Border style"),
    "id": _attr("id", description="Element ID"),
    "class": _attr("class", description="CSS class(es)"),
    "visible": _attr("visible", type=AttributeType.EXPRESSION, description="Visibility binding"),
}

UI_WINDOW = TagInfo(
    name="window",
    namespace="ui",
    description="Top-level window container for UI applications.",
    attributes={
        "title": _attr("title", description="Window title"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:window title="My App">\n  <ui:vbox>\n    <ui:text>Hello World</ui:text>\n  </ui:vbox>\n</ui:window>'],
    see_also=["ui:vbox", "ui:hbox", "ui:panel"]
)

UI_VBOX = TagInfo(
    name="vbox",
    namespace="ui",
    description="Vertical flex container. Children are stacked vertically.",
    attributes=_LAYOUT_ATTRS,
    examples=['<ui:vbox gap="10">\n  <ui:text>Item 1</ui:text>\n  <ui:text>Item 2</ui:text>\n</ui:vbox>'],
    see_also=["ui:hbox", "ui:grid"]
)

UI_HBOX = TagInfo(
    name="hbox",
    namespace="ui",
    description="Horizontal flex container. Children are arranged horizontally.",
    attributes=_LAYOUT_ATTRS,
    examples=['<ui:hbox gap="10" justify="between">\n  <ui:button>Left</ui:button>\n  <ui:button>Right</ui:button>\n</ui:hbox>'],
    see_also=["ui:vbox", "ui:grid"]
)

UI_PANEL = TagInfo(
    name="panel",
    namespace="ui",
    description="Bordered container with optional title.",
    attributes={
        "title": _attr("title", description="Panel title"),
        "collapsible": _attr("collapsible", type=AttributeType.BOOLEAN, default="false",
                            description="Allow collapsing"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:panel title="Settings" collapsible="true">\n  <ui:input bind="name" />\n</ui:panel>'],
    see_also=["ui:card", "ui:accordion"]
)

UI_GRID = TagInfo(
    name="grid",
    namespace="ui",
    description="CSS grid container.",
    attributes={
        "columns": _attr("columns", description="Column definition (e.g., '3' or '1fr 2fr 1fr')"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:grid columns="3" gap="10">\n  <ui:panel>1</ui:panel>\n  <ui:panel>2</ui:panel>\n  <ui:panel>3</ui:panel>\n</ui:grid>'],
    see_also=["ui:vbox", "ui:hbox"]
)

UI_BUTTON = TagInfo(
    name="button",
    namespace="ui",
    description="Clickable button widget.",
    attributes={
        "onClick": _attr("onClick", type=AttributeType.EXPRESSION, description="Click handler"),
        "variant": _attr("variant", type=AttributeType.ENUM,
                        enum_values=["primary", "secondary", "danger", "success"],
                        description="Button style variant"),
        "disabled": _attr("disabled", type=AttributeType.BOOLEAN, default="false",
                         description="Disable the button"),
        **_LAYOUT_ATTRS,
    },
    examples=[
        '<ui:button onClick="handleSave" variant="primary">Save</ui:button>',
        '<ui:button disabled="{!isValid}">Submit</ui:button>',
    ],
    see_also=["ui:link"]
)

UI_INPUT = TagInfo(
    name="input",
    namespace="ui",
    description="Text input widget with validation support.",
    attributes={
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Two-way binding variable"),
        "placeholder": _attr("placeholder", description="Placeholder text"),
        "type": _attr("type", type=AttributeType.ENUM, default="text",
                     enum_values=["text", "password", "email", "number", "tel", "url", "search", "date", "time", "datetime-local"],
                     description="Input type"),
        "onChange": _attr("onChange", type=AttributeType.EXPRESSION, description="Change handler"),
        "onSubmit": _attr("onSubmit", type=AttributeType.EXPRESSION, description="Submit handler"),
        "required": _attr("required", type=AttributeType.BOOLEAN, default="false",
                         description="Field is required"),
        "min": _attr("min", description="Minimum value"),
        "max": _attr("max", description="Maximum value"),
        "minlength": _attr("minlength", type=AttributeType.INTEGER, description="Minimum length"),
        "maxlength": _attr("maxlength", type=AttributeType.INTEGER, description="Maximum length"),
        "pattern": _attr("pattern", type=AttributeType.REGEX, description="Validation pattern"),
        "errorMessage": _attr("errorMessage", description="Custom error message"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=[
        '<ui:input bind="email" type="email" placeholder="Enter email" required="true" />',
        '<ui:input bind="age" type="number" min="0" max="120" />',
    ],
    see_also=["ui:form", "ui:select", "ui:checkbox"]
)

UI_TEXT = TagInfo(
    name="text",
    namespace="ui",
    description="Text display widget.",
    attributes={
        "size": _attr("size", type=AttributeType.ENUM,
                     enum_values=["xs", "sm", "md", "lg", "xl", "2xl"],
                     description="Text size"),
        "weight": _attr("weight", type=AttributeType.ENUM,
                       enum_values=["normal", "bold", "light"],
                       description="Font weight"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:text size="xl" weight="bold">Title</ui:text>'],
    see_also=["ui:markdown", "ui:header"]
)

UI_SELECT = TagInfo(
    name="select",
    namespace="ui",
    description="Dropdown select widget.",
    attributes={
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Binding variable"),
        "options": _attr("options", description="Comma-separated options or binding"),
        "source": _attr("source", type=AttributeType.EXPRESSION, description="Data source for options"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:option"],
    examples=[
        '<ui:select bind="country" options="US,CA,UK,AU" />',
        '<ui:select bind="user" source="{users}">\n  <ui:option value="{item.id}" label="{item.name}" />\n</ui:select>',
    ],
    see_also=["ui:input", "ui:radio"]
)

UI_OPTION = TagInfo(
    name="option",
    namespace="ui",
    description="Option for select, menu, or dropdown.",
    attributes={
        "value": _attr("value", description="Option value"),
        "label": _attr("label", description="Display label"),
        "onClick": _attr("onClick", type=AttributeType.EXPRESSION, description="Click handler"),
    },
    parent_tags=["ui:select", "ui:menu", "ui:dropdown"],
    examples=['<ui:option value="1" label="Option 1" />'],
    see_also=["ui:select", "ui:dropdown"]
)

UI_CHECKBOX = TagInfo(
    name="checkbox",
    namespace="ui",
    description="Checkbox widget.",
    attributes={
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Binding variable"),
        "label": _attr("label", description="Checkbox label"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:checkbox bind="agreed" label="I agree to terms" />'],
    see_also=["ui:switch", "ui:radio"]
)

UI_SWITCH = TagInfo(
    name="switch",
    namespace="ui",
    description="Toggle switch widget.",
    attributes={
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Binding variable"),
        "label": _attr("label", description="Switch label"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:switch bind="darkMode" label="Dark Mode" />'],
    see_also=["ui:checkbox"]
)

UI_RADIO = TagInfo(
    name="radio",
    namespace="ui",
    description="Radio button group.",
    attributes={
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Binding variable"),
        "options": _attr("options", description="Comma-separated options"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:radio bind="size" options="S,M,L,XL" />'],
    see_also=["ui:checkbox", "ui:select"]
)

UI_TABLE = TagInfo(
    name="table",
    namespace="ui",
    description="Data table widget.",
    attributes={
        "source": _attr("source", type=AttributeType.EXPRESSION, required=True,
                       description="Data source binding"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:column"],
    examples=['<ui:table source="{users}">\n  <ui:column key="name" label="Name" />\n  <ui:column key="email" label="Email" />\n</ui:table>'],
    see_also=["ui:list", "ui:column"]
)

UI_COLUMN = TagInfo(
    name="column",
    namespace="ui",
    description="Table column definition.",
    attributes={
        "key": _attr("key", required=True, description="Data field key"),
        "label": _attr("label", description="Column header label"),
        "width": _attr("width", type=AttributeType.CSS_SIZE, description="Column width"),
        "align": _attr("align", type=AttributeType.ENUM,
                      enum_values=["left", "center", "right"],
                      description="Text alignment"),
    },
    parent_tags=["ui:table"],
    self_closing=True,
    examples=['<ui:column key="name" label="Name" width="200" />'],
    see_also=["ui:table"]
)

UI_LIST = TagInfo(
    name="list",
    namespace="ui",
    description="Repeating list widget.",
    attributes={
        "source": _attr("source", type=AttributeType.EXPRESSION, description="Data source binding"),
        "as": _attr("as", description="Loop variable name"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:item"],
    examples=['<ui:list source="{items}" as="item">\n  <ui:item>\n    <ui:text>{item.name}</ui:text>\n  </ui:item>\n</ui:list>'],
    see_also=["ui:table", "ui:item"]
)

UI_ITEM = TagInfo(
    name="item",
    namespace="ui",
    description="List item container.",
    attributes=_LAYOUT_ATTRS,
    parent_tags=["ui:list"],
    examples=['<ui:item>\n  <ui:text>{item.name}</ui:text>\n</ui:item>'],
    see_also=["ui:list"]
)

UI_FORM = TagInfo(
    name="form",
    namespace="ui",
    description="Form container with validation support.",
    attributes={
        "onSubmit": _attr("onSubmit", type=AttributeType.EXPRESSION, description="Submit handler"),
        "validationMode": _attr("validationMode", type=AttributeType.ENUM, default="both",
                               enum_values=["client", "server", "both"],
                               description="Validation mode"),
        "errorDisplay": _attr("errorDisplay", type=AttributeType.ENUM, default="inline",
                             enum_values=["inline", "summary", "both"],
                             description="Error display mode"),
        "novalidate": _attr("novalidate", type=AttributeType.BOOLEAN, default="false",
                           description="Disable HTML5 validation"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:formitem", "ui:input", "ui:select", "ui:button", "ui:validator"],
    examples=['<ui:form onSubmit="handleSubmit">\n  <ui:formitem label="Email">\n    <ui:input bind="email" type="email" required="true" />\n  </ui:formitem>\n  <ui:button type="submit">Submit</ui:button>\n</ui:form>'],
    see_also=["ui:formitem", "ui:input", "ui:validator"]
)

UI_FORMITEM = TagInfo(
    name="formitem",
    namespace="ui",
    description="Form item wrapper with label.",
    attributes={
        "label": _attr("label", description="Field label"),
        **_LAYOUT_ATTRS,
    },
    parent_tags=["ui:form"],
    examples=['<ui:formitem label="Name">\n  <ui:input bind="name" />\n</ui:formitem>'],
    see_also=["ui:form", "ui:input"]
)

UI_IMAGE = TagInfo(
    name="image",
    namespace="ui",
    description="Image display widget.",
    attributes={
        "src": _attr("src", type=AttributeType.URL, required=True, description="Image source URL"),
        "alt": _attr("alt", description="Alternative text"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:image src="/images/logo.png" alt="Logo" width="200" />'],
    see_also=["ui:avatar"]
)

UI_LINK = TagInfo(
    name="link",
    namespace="ui",
    description="Hyperlink widget.",
    attributes={
        "to": _attr("to", type=AttributeType.URL, required=True, description="Target URL"),
        "external": _attr("external", type=AttributeType.BOOLEAN, default="false",
                         description="Open in new tab"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:link to="/about">About Us</ui:link>'],
    see_also=["ui:button"]
)

UI_MODAL = TagInfo(
    name="modal",
    namespace="ui",
    description="Modal/dialog container.",
    attributes={
        "title": _attr("title", description="Modal title"),
        "id": _attr("id", description="Modal ID for targeting"),
        "open": _attr("open", type=AttributeType.BOOLEAN, default="false",
                     description="Initial open state"),
        "closable": _attr("closable", type=AttributeType.BOOLEAN, default="true",
                         description="Show close button"),
        "size": _attr("size", type=AttributeType.ENUM,
                     enum_values=["sm", "md", "lg", "xl", "full"],
                     description="Modal size"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:modal title="Confirm" id="confirmModal">\n  <ui:text>Are you sure?</ui:text>\n  <ui:hbox>\n    <ui:button onClick="closeModal">Cancel</ui:button>\n    <ui:button onClick="confirm" variant="danger">Delete</ui:button>\n  </ui:hbox>\n</ui:modal>'],
    see_also=["ui:panel", "ui:alert"]
)

UI_CARD = TagInfo(
    name="card",
    namespace="ui",
    description="Card container with header, body, and footer sections.",
    attributes={
        "title": _attr("title", description="Card title"),
        "subtitle": _attr("subtitle", description="Card subtitle"),
        "image": _attr("image", type=AttributeType.URL, description="Header image"),
        "variant": _attr("variant", type=AttributeType.ENUM,
                        enum_values=["default", "elevated", "outlined"],
                        description="Card style"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:card-header", "ui:card-body", "ui:card-footer"],
    examples=['<ui:card title="Product" image="/product.jpg">\n  <ui:card-body>\n    <ui:text>Description</ui:text>\n  </ui:card-body>\n  <ui:card-footer>\n    <ui:button>Buy</ui:button>\n  </ui:card-footer>\n</ui:card>'],
    see_also=["ui:panel"]
)

UI_ALERT = TagInfo(
    name="alert",
    namespace="ui",
    description="Alert/notification box.",
    attributes={
        "title": _attr("title", description="Alert title"),
        "variant": _attr("variant", type=AttributeType.ENUM, default="info",
                        enum_values=["info", "success", "warning", "danger"],
                        description="Alert style"),
        "dismissible": _attr("dismissible", type=AttributeType.BOOLEAN, default="false",
                            description="Allow dismissing"),
        "icon": _attr("icon", description="Icon name"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:alert variant="success" dismissible="true">\n  Operation completed successfully!\n</ui:alert>'],
    see_also=["ui:modal"]
)

UI_PROGRESS = TagInfo(
    name="progress",
    namespace="ui",
    description="Progress bar widget.",
    attributes={
        "value": _attr("value", type=AttributeType.EXPRESSION, description="Current value binding"),
        "max": _attr("max", default="100", description="Maximum value"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:progress value="{progress}" max="100" />'],
    see_also=["ui:loading", "ui:skeleton"]
)

UI_LOADING = TagInfo(
    name="loading",
    namespace="ui",
    description="Loading indicator widget.",
    attributes={
        "text": _attr("text", description="Loading text"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:loading text="Loading data..." />'],
    see_also=["ui:progress", "ui:skeleton"]
)

UI_BADGE = TagInfo(
    name="badge",
    namespace="ui",
    description="Small status badge.",
    attributes={
        "variant": _attr("variant", type=AttributeType.ENUM,
                        enum_values=["primary", "secondary", "danger", "success", "warning"],
                        description="Badge style"),
        "color": _attr("color", type=AttributeType.CSS_COLOR, description="Custom color"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:badge variant="success">Active</ui:badge>'],
    see_also=["ui:text"]
)

UI_TOOLTIP = TagInfo(
    name="tooltip",
    namespace="ui",
    description="Tooltip on hover.",
    attributes={
        "content": _attr("content", required=True, description="Tooltip text"),
        "position": _attr("position", type=AttributeType.ENUM, default="top",
                         enum_values=["top", "bottom", "left", "right"],
                         description="Tooltip position"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:tooltip content="Click to save" position="bottom">\n  <ui:button>Save</ui:button>\n</ui:tooltip>'],
    see_also=["ui:dropdown"]
)

UI_DROPDOWN = TagInfo(
    name="dropdown",
    namespace="ui",
    description="Dropdown menu.",
    attributes={
        "label": _attr("label", description="Trigger button label"),
        "trigger": _attr("trigger", type=AttributeType.ENUM, default="click",
                        enum_values=["click", "hover"],
                        description="Trigger mode"),
        "align": _attr("align", type=AttributeType.ENUM, default="left",
                      enum_values=["left", "right"],
                      description="Menu alignment"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:option"],
    examples=['<ui:dropdown label="Actions">\n  <ui:option label="Edit" onClick="handleEdit" />\n  <ui:option label="Delete" onClick="handleDelete" />\n</ui:dropdown>'],
    see_also=["ui:menu", "ui:select"]
)

UI_TABPANEL = TagInfo(
    name="tabpanel",
    namespace="ui",
    description="Tabbed content container.",
    attributes=_LAYOUT_ATTRS,
    children=["ui:tab"],
    examples=['<ui:tabpanel>\n  <ui:tab title="Tab 1">\n    <ui:text>Content 1</ui:text>\n  </ui:tab>\n  <ui:tab title="Tab 2">\n    <ui:text>Content 2</ui:text>\n  </ui:tab>\n</ui:tabpanel>'],
    see_also=["ui:tab", "ui:accordion"]
)

UI_TAB = TagInfo(
    name="tab",
    namespace="ui",
    description="Individual tab inside a tabpanel.",
    attributes={
        "title": _attr("title", required=True, description="Tab title"),
        **_LAYOUT_ATTRS,
    },
    parent_tags=["ui:tabpanel"],
    examples=['<ui:tab title="Settings">\n  <ui:text>Settings content</ui:text>\n</ui:tab>'],
    see_also=["ui:tabpanel"]
)

UI_ACCORDION = TagInfo(
    name="accordion",
    namespace="ui",
    description="Collapsible sections container.",
    attributes=_LAYOUT_ATTRS,
    children=["ui:section"],
    examples=['<ui:accordion>\n  <ui:section title="Section 1" expanded="true">\n    Content 1\n  </ui:section>\n  <ui:section title="Section 2">\n    Content 2\n  </ui:section>\n</ui:accordion>'],
    see_also=["ui:section", "ui:tabpanel"]
)

UI_SECTION = TagInfo(
    name="section",
    namespace="ui",
    description="Collapsible section inside an accordion.",
    attributes={
        "title": _attr("title", required=True, description="Section title"),
        "expanded": _attr("expanded", type=AttributeType.BOOLEAN, default="false",
                         description="Initial expanded state"),
        **_LAYOUT_ATTRS,
    },
    parent_tags=["ui:accordion"],
    examples=['<ui:section title="Details" expanded="true">\n  Section content\n</ui:section>'],
    see_also=["ui:accordion", "ui:panel"]
)

UI_SPACER = TagInfo(
    name="spacer",
    namespace="ui",
    description="Flexible space filler.",
    attributes={
        "size": _attr("size", type=AttributeType.CSS_SIZE, description="Fixed size"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:hbox>\n  <ui:text>Left</ui:text>\n  <ui:spacer />\n  <ui:text>Right</ui:text>\n</ui:hbox>'],
    see_also=["ui:rule"]
)

UI_RULE = TagInfo(
    name="rule",
    namespace="ui",
    description="Horizontal rule/separator.",
    self_closing=True,
    examples=['<ui:rule />'],
    see_also=["ui:spacer"]
)

UI_MARKDOWN = TagInfo(
    name="markdown",
    namespace="ui",
    description="Markdown rendered content.",
    attributes=_LAYOUT_ATTRS,
    examples=['<ui:markdown>\n# Heading\n\nThis is **bold** text.\n</ui:markdown>'],
    see_also=["ui:text"]
)

UI_HEADER = TagInfo(
    name="header",
    namespace="ui",
    description="Page/window header.",
    attributes={
        "title": _attr("title", description="Header title"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:header title="Dashboard" />'],
    see_also=["ui:footer"]
)

UI_FOOTER = TagInfo(
    name="footer",
    namespace="ui",
    description="Page/window footer.",
    attributes=_LAYOUT_ATTRS,
    examples=['<ui:footer>\n  <ui:text>Copyright 2024</ui:text>\n</ui:footer>'],
    see_also=["ui:header"]
)

UI_AVATAR = TagInfo(
    name="avatar",
    namespace="ui",
    description="User avatar with image or initials.",
    attributes={
        "src": _attr("src", type=AttributeType.URL, description="Image URL"),
        "name": _attr("name", description="Name for initials fallback"),
        "size": _attr("size", type=AttributeType.ENUM,
                     enum_values=["xs", "sm", "md", "lg", "xl"],
                     description="Avatar size"),
        "shape": _attr("shape", type=AttributeType.ENUM, default="circle",
                      enum_values=["circle", "square"],
                      description="Avatar shape"),
        "status": _attr("status", type=AttributeType.ENUM,
                       enum_values=["online", "offline", "away", "busy"],
                       description="Status indicator"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:avatar src="/user.jpg" name="John Doe" size="lg" status="online" />'],
    see_also=["ui:image"]
)

UI_CHART = TagInfo(
    name="chart",
    namespace="ui",
    description="Simple charts (bar, line, pie).",
    attributes={
        "type": _attr("type", type=AttributeType.ENUM, default="bar",
                     enum_values=["bar", "line", "pie", "doughnut"],
                     description="Chart type"),
        "source": _attr("source", type=AttributeType.EXPRESSION, description="Data source"),
        "labels": _attr("labels", description="Comma-separated labels"),
        "values": _attr("values", description="Comma-separated values"),
        "title": _attr("title", description="Chart title"),
        "colors": _attr("colors", description="Comma-separated colors"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:chart type="bar" labels="Jan,Feb,Mar" values="10,20,30" title="Sales" />'],
    see_also=["ui:table"]
)

UI_BREADCRUMB = TagInfo(
    name="breadcrumb",
    namespace="ui",
    description="Navigation breadcrumbs.",
    attributes={
        "separator": _attr("separator", default="/", description="Separator character"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:breadcrumb-item"],
    examples=['<ui:breadcrumb>\n  <ui:breadcrumb-item label="Home" to="/" />\n  <ui:breadcrumb-item label="Products" to="/products" />\n  <ui:breadcrumb-item label="Details" />\n</ui:breadcrumb>'],
    see_also=["ui:link"]
)

UI_PAGINATION = TagInfo(
    name="pagination",
    namespace="ui",
    description="Pagination controls.",
    attributes={
        "total": _attr("total", type=AttributeType.EXPRESSION, description="Total items"),
        "pageSize": _attr("pageSize", default="10", description="Items per page"),
        "current": _attr("current", default="1", description="Current page"),
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Binding for current page"),
        "onChange": _attr("onChange", type=AttributeType.EXPRESSION, description="Page change handler"),
        "showTotal": _attr("showTotal", type=AttributeType.BOOLEAN, default="false",
                          description="Show total count"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:pagination total="{totalItems}" pageSize="20" bind="currentPage" />'],
    see_also=["ui:table"]
)

UI_SKELETON = TagInfo(
    name="skeleton",
    namespace="ui",
    description="Loading skeleton placeholder.",
    attributes={
        "variant": _attr("variant", type=AttributeType.ENUM, default="text",
                        enum_values=["text", "circle", "rect", "card"],
                        description="Skeleton shape"),
        "lines": _attr("lines", type=AttributeType.INTEGER, default="1",
                      description="Number of lines for text variant"),
        "animated": _attr("animated", type=AttributeType.BOOLEAN, default="true",
                         description="Animate the skeleton"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:skeleton variant="text" lines="3" />'],
    see_also=["ui:loading"]
)

UI_ANIMATE = TagInfo(
    name="animate",
    namespace="ui",
    description="Animation wrapper container.",
    attributes={
        "type": _attr("type", type=AttributeType.ENUM,
                     enum_values=["fade", "slide", "scale", "rotate", "slide-left", "slide-right",
                                 "slide-up", "slide-down", "fade-in", "fade-out", "bounce", "pulse", "shake", "rotate-in", "rotate-out", "zoom-in", "zoom-out", "flip", "slide-left", "slide-right", "scale-in", "scale-out"],
                     description="Animation type"),
        "duration": _attr("duration", description="Duration in ms"),
        "delay": _attr("delay", description="Delay before animation"),
        "easing": _attr("easing", type=AttributeType.ENUM,
                       enum_values=["ease", "ease-in", "ease-out", "ease-in-out", "linear", "spring", "bounce"],
                       description="Easing function"),
        "repeat": _attr("repeat", description="Repeat count (or 'infinite')"),
        "trigger": _attr("trigger", type=AttributeType.ENUM, default="on-load",
                        enum_values=["on-load", "on-hover", "on-click", "on-visible", "none"],
                        description="Animation trigger"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:animate type="fade-in" duration="300" trigger="on-load">\n  <ui:panel>Animated content</ui:panel>\n</ui:animate>'],
    see_also=["ui:panel"]
)


# =============================================================================
# TAG REGISTRY
# =============================================================================

QUANTUM_TAGS: Dict[str, TagInfo] = {
    # Core and AI tags (q:): quantum_lsp/schema/core_tags.py
    **CORE_AI_TAGS,

    # Laboratory / Experimental q: tags
    "q:application": Q_APPLICATION,
    "q:log": Q_LOG,
    "q:dump": Q_DUMP,
    "q:onEvent": Q_ONEVENT,
    "q:dispatchEvent": Q_DISPATCHEVENT,

    # UI engine tags (ui:)
    "ui:window": UI_WINDOW,
    "ui:vbox": UI_VBOX,
    "ui:hbox": UI_HBOX,
    "ui:panel": UI_PANEL,
    "ui:grid": UI_GRID,
    "ui:button": UI_BUTTON,
    "ui:input": UI_INPUT,
    "ui:text": UI_TEXT,
    "ui:select": UI_SELECT,
    "ui:option": UI_OPTION,
    "ui:checkbox": UI_CHECKBOX,
    "ui:switch": UI_SWITCH,
    "ui:radio": UI_RADIO,
    "ui:table": UI_TABLE,
    "ui:column": UI_COLUMN,
    "ui:list": UI_LIST,
    "ui:item": UI_ITEM,
    "ui:form": UI_FORM,
    "ui:formitem": UI_FORMITEM,
    "ui:image": UI_IMAGE,
    "ui:link": UI_LINK,
    "ui:modal": UI_MODAL,
    "ui:card": UI_CARD,
    "ui:alert": UI_ALERT,
    "ui:progress": UI_PROGRESS,
    "ui:loading": UI_LOADING,
    "ui:badge": UI_BADGE,
    "ui:tooltip": UI_TOOLTIP,
    "ui:dropdown": UI_DROPDOWN,
    "ui:tabpanel": UI_TABPANEL,
    "ui:tab": UI_TAB,
    "ui:accordion": UI_ACCORDION,
    "ui:section": UI_SECTION,
    "ui:spacer": UI_SPACER,
    "ui:rule": UI_RULE,
    "ui:markdown": UI_MARKDOWN,
    "ui:header": UI_HEADER,
    "ui:footer": UI_FOOTER,
    "ui:avatar": UI_AVATAR,
    "ui:chart": UI_CHART,
    "ui:breadcrumb": UI_BREADCRUMB,
    "ui:pagination": UI_PAGINATION,
    "ui:skeleton": UI_SKELETON,
    "ui:animate": UI_ANIMATE,
}


# Type names accepted by the RUNTIME (component._PARAM_INT_TYPES and
# _PARAM_FLOAT_TYPES) that this schema did not list. `type="number"` is used 36
# times in the examples themselves and the server reported it as invalid: 240 of
# the 623 false diagnostics came from there. A hand-kept schema drifts; the list
# below exists to record WHERE it has to be derived from.

# NESTED tags: resolved by the PARENT's parser (q:tool inside q:agent,
# q:column inside q:data, ui:card-body inside ui:card), so they never
# appear in the top-level tag registry. Without this list the server
# reported them as unknown in correct files.
#
# Collected from the repository's own .q files. To regenerate:
#   grep -rho "<\(q\|ui\):[a-zA-Z][a-zA-Z0-9_-]*" examples components | sort -u
NESTED_TAGS = frozenset({
    "q:arg", "q:behavior", "q:column", "q:compute",
    "q:dead-letter", "q:execute", "q:fetch", "q:field",
    "q:filter", "q:instruction", "q:limit", "q:message-ack",
    "q:message-nack", "q:on-close", "q:on-connect", "q:on-error",
    "q:on-message", "q:onError", "q:onMessage", "q:prefab",
    "q:shared", "q:sort", "q:throw", "q:tool",
    "q:transform", "q:ttl", "q:var", "ui:breadcrumb-item",
    "ui:calendar", "ui:card-body", "ui:card-footer", "ui:card-header",
    "ui:carousel", "ui:color", "ui:date-picker", "ui:form-item",
    "ui:slide", "ui:step", "ui:stepper", "ui:theme",
    "ui:toast-container", "ui:validator",
})


def _framework_tags() -> set:
    """The tags the framework's parser actually registers.

    QUANTUM_TAGS is a list kept BY HAND, and it drifted: 76 entries here
    against 95 in the registry. The server reported "Unknown tag <q:python>",
    "<q:queue>", "<ui:card-body>" in files the framework parses cleanly —
    623 false diagnostics in 124 files. Mass false positives are what makes
    someone turn off the language server.

    Asking the registry is the only way for the two not to drift again. If
    the framework cannot be imported, it returns empty and the old path applies.
    """
    try:
        from quantum.core.parser import QuantumParser
        registry = QuantumParser().parser_registry
        names = set(getattr(registry, '_parsers', {}) or {})
        return {n for n in names if n}
    except Exception:
        return set()


_FRAMEWORK_TAGS = None


def is_known_tag(tag_name: str) -> bool:
    """If the schema OR the framework knows the tag, it is not unknown."""
    global _FRAMEWORK_TAGS
    if tag_name in QUANTUM_TAGS or tag_name in NESTED_TAGS:
        return True
    if _FRAMEWORK_TAGS is None:
        _FRAMEWORK_TAGS = _framework_tags()
    return tag_name.split(':')[-1] in _FRAMEWORK_TAGS


def get_tag_info(tag_name: str) -> Optional[TagInfo]:
    """Get tag information by full tag name (e.g., 'q:set')."""
    return QUANTUM_TAGS.get(tag_name)


def get_all_tags() -> List[str]:
    """Get all registered tag names."""
    return list(QUANTUM_TAGS.keys())


def get_tags_by_namespace(namespace: str) -> List[TagInfo]:
    """Get all tags for a given namespace (e.g., 'q', 'ui')."""
    return [tag for name, tag in QUANTUM_TAGS.items() if tag.namespace == namespace]
