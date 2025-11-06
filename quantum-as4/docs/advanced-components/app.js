import { ReactiveRuntime } from './reactive-runtime.js';

// UI Component Tree
const componentTree = {
  "type": "Application",
  "props": {
    "title": "Advanced Components Demo"
  },
  "events": {},
  "children": [
    {
      "type": "VBox",
      "props": {
        "width": "100%",
        "height": "100%",
        "padding": "0"
      },
      "events": {},
      "children": [
        {
          "type": "MenuBar",
          "props": {
            "dataProvider": "{menuData}",
            "itemClick": "handleMenuClick(event)"
          },
          "events": {},
          "children": []
        },
        {
          "type": "TabNavigator",
          "props": {
            "width": "100%",
            "height": "100%"
          },
          "events": {},
          "children": [
            {
              "type": "VBox",
              "props": {
                "label": "Drag and Drop",
                "padding": "20",
                "gap": "20"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Drag and Drop Task List",
                    "styleName": "title"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Drag tasks to reorder them",
                    "styleName": "subtitle"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "HBox",
                  "props": {
                    "gap": "30",
                    "width": "100%"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "width": "400"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Panel",
                          "props": {
                            "title": "Task List (Drag to Reorder)",
                            "width": "100%"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "List",
                              "props": {
                                "dataProvider": "{taskList}",
                                "selectable": "true",
                                "dragEnabled": "true",
                                "dropEnabled": "true",
                                "height": "300",
                                "itemsReordered": "handleTasksReordered(event)",
                                "selectionChange": "handleTaskSelection(event)"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        }
                      ]
                    },
                    {
                      "type": "VBox",
                      "props": {
                        "width": "300"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Panel",
                          "props": {
                            "title": "Selection Info",
                            "width": "100%"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "VBox",
                              "props": {
                                "padding": "15",
                                "gap": "10"
                              },
                              "events": {},
                              "children": [
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{selectedTask}"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "\ud83d\udca1 Tip: Drag items to reorder",
                                    "styleName": "subtitle"
                                  },
                                  "events": {},
                                  "children": []
                                }
                              ]
                            }
                          ]
                        }
                      ]
                    }
                  ]
                }
              ]
            },
            {
              "type": "VBox",
              "props": {
                "label": "Advanced DataGrid",
                "padding": "20",
                "gap": "20"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Employee Management",
                    "styleName": "title"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Features: Column Resizing, Inline Editing, Sorting, Filtering",
                    "styleName": "subtitle"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Panel",
                  "props": {
                    "title": "Employees",
                    "width": "100%"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "AdvancedDataGrid",
                      "props": {
                        "dataProvider": "{employees}",
                        "columns": "{employeeColumns}",
                        "sortable": "true",
                        "filterable": "true",
                        "selectable": "true",
                        "editable": "true",
                        "resizableColumns": "true",
                        "pageSize": "10",
                        "cellEdit": "handleCellEdit(event)",
                        "width": "100%",
                        "height": "400"
                      },
                      "events": {},
                      "children": []
                    }
                  ]
                },
                {
                  "type": "HBox",
                  "props": {
                    "gap": "10"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Label",
                      "props": {
                        "text": "\ud83d\udca1 Double-click cells to edit"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Label",
                      "props": {
                        "text": "\u2022"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Label",
                      "props": {
                        "text": "Drag column edges to resize"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Label",
                      "props": {
                        "text": "\u2022"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Label",
                      "props": {
                        "text": "Click headers to sort"
                      },
                      "events": {},
                      "children": []
                    }
                  ]
                }
              ]
            },
            {
              "type": "VBox",
              "props": {
                "label": "TileList",
                "padding": "20",
                "gap": "20"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Image Gallery",
                    "styleName": "title"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Grid layout with selectable tiles",
                    "styleName": "subtitle"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Panel",
                  "props": {
                    "title": "Photo Gallery",
                    "width": "100%"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "TileList",
                      "props": {
                        "dataProvider": "{galleryItems}",
                        "columnCount": "3",
                        "columnWidth": "220",
                        "rowHeight": "220",
                        "selectable": "true",
                        "labelField": "label",
                        "imageField": "image",
                        "selectionChange": "handleImageSelection(event)",
                        "width": "100%",
                        "height": "500"
                      },
                      "events": {},
                      "children": []
                    }
                  ]
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "{selectedImage}"
                  },
                  "events": {},
                  "children": []
                }
              ]
            },
            {
              "type": "VBox",
              "props": {
                "label": "Accordion",
                "padding": "20",
                "gap": "20"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Collapsible Panels",
                    "styleName": "title"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Click headers to expand/collapse sections",
                    "styleName": "subtitle"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Accordion",
                  "props": {
                    "width": "600"
                  },
                  "events": {
                    "change": "handleAccordionChange(event)"
                  },
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "label": "Getting Started"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "padding": "15",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Welcome to the Advanced Components Demo!",
                                "styleName": "subtitle"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "This demo showcases the latest features:"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Drag and drop support"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Advanced DataGrid with editing"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 TileList for grid layouts"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Accordion for collapsible content"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 MenuBar for application menus"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        }
                      ]
                    },
                    {
                      "type": "VBox",
                      "props": {
                        "label": "Features"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "padding": "15",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Drag & Drop:",
                                "styleName": "subtitle"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Reorder list items by dragging"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Visual feedback with drop indicators"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Automatic data updates"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Spacer",
                              "props": {
                                "height": "10"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Advanced DataGrid:",
                                "styleName": "subtitle"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Column resizing by dragging edges"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Inline editing with double-click"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Sorting, filtering, and pagination"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        }
                      ]
                    },
                    {
                      "type": "VBox",
                      "props": {
                        "label": "Documentation"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "padding": "15",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Component API:",
                                "styleName": "subtitle"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "See examples/README.md for full API documentation"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Spacer",
                              "props": {
                                "height": "10"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Component List:",
                                "styleName": "subtitle"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2713 List with drag reordering"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2713 AdvancedDataGrid"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2713 TileList"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2713 Accordion"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2713 Menu / MenuBar"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2713 DragManager utility"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        }
                      ]
                    },
                    {
                      "type": "VBox",
                      "props": {
                        "label": "About"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "padding": "15",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ActionScript 4 / MXML Compiler",
                                "styleName": "subtitle"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "A modern implementation of Adobe Flex for the web"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Spacer",
                              "props": {
                                "height": "10"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Built with:"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Reactive data binding"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Modern JavaScript (ES6+)"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 Flex-compatible MXML syntax"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "\u2022 HTML5/CSS3 rendering"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
};

// Application Class (from ActionScript)
class App {
  constructor(runtime) {
    this.runtime = runtime;

    this.selectedTask = "";
    this.selectedImage = "";
  }

  handleTasksReordered(newOrder, sourceIndex, targetIndex) {
    console.log("Tasks reordered from index " + this.sourceIndex + " to " + this.targetIndex);
  }

  handleTaskSelection(items, index) {
    if (this.items.length > 0) {
    this.selectedTask = "Selected: " + this.items[0];
  }

  handleCellEdit(event) {
    console.log("Cell edited: " + this.event.field + " changed from " + this.event.oldValue + " to " + this.event.newValue);
  }

  handleMenuClick(item) {
    console.log("Menu clicked: " + this.item.label);
  }

  handleAccordionChange(index, expanded) {
    console.log("Panel " + this.index + (this.expanded ? " expanded" : " collapsed"));
  }

  handleImageSelection(items, index) {
    if (this.items.length > 0) {
    this.selectedImage = "Selected: " + this.items[0].label;
  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.render(componentTree, document.getElementById('app'));
