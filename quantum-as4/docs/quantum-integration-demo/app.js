import { ReactiveRuntime } from './reactive-runtime.js';

// UI Component Tree
const componentTree = {
  "type": "Application",
  "props": {
    "width": "1000",
    "height": "900",
    "title": "Quantum Integration Demo"
  },
  "events": {},
  "children": [
    {
      "type": "QuantumService",
      "props": {
        "id": "productsService",
        "url": "{quantumServerUrl + '/products'}",
        "method": "GET",
        "result": "handleProductsResult(event)",
        "fault": "handleProductsFault(event)",
        "extractData": "true"
      },
      "events": {},
      "children": []
    },
    {
      "type": "QuantumService",
      "props": {
        "id": "helloService",
        "url": "{quantumServerUrl + '/hello'}",
        "method": "GET",
        "result": "handleHelloResult(event)",
        "fault": "handleHelloFault(event)"
      },
      "events": {},
      "children": []
    },
    {
      "type": "QuantumComponent",
      "props": {
        "id": "quantumComponent",
        "url": "{quantumServerUrl + '/hello'}",
        "width": "800",
        "height": "300",
        "autoResize": "true",
        "load": "handleComponentLoad(event)",
        "error": "handleComponentError(event)",
        "message": "handleComponentMessage(event)",
        "includeIn": "embedView"
      },
      "events": {},
      "children": []
    },
    {
      "type": "QuantumBridge",
      "props": {
        "id": "quantumBridge",
        "targetOrigin": "{quantumServerUrl}"
      },
      "events": {},
      "children": []
    },
    {
      "type": "states",
      "props": {},
      "events": {},
      "children": [
        {
          "type": "State",
          "props": {
            "name": "default"
          },
          "events": {},
          "children": []
        },
        {
          "type": "State",
          "props": {
            "name": "serviceView"
          },
          "events": {},
          "children": []
        },
        {
          "type": "State",
          "props": {
            "name": "embedView"
          },
          "events": {},
          "children": []
        },
        {
          "type": "State",
          "props": {
            "name": "bridgeView"
          },
          "events": {},
          "children": []
        }
      ]
    },
    {
      "type": "VBox",
      "props": {
        "width": "100%",
        "height": "100%",
        "padding": "20",
        "gap": "20"
      },
      "events": {},
      "children": [
        {
          "type": "Panel",
          "props": {
            "width": "100%",
            "title": "Quantum Integration Demo"
          },
          "events": {},
          "children": [
            {
              "type": "VBox",
              "props": {
                "padding": "15",
                "gap": "10",
                "width": "100%"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Integration between MXML and Quantum Language",
                    "fontSize": "14",
                    "fontWeight": "bold"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Demonstrates: QuantumService (HTTP), QuantumComponent (iframe), QuantumBridge (PostMessage)",
                    "fontSize": "11"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "HBox",
                  "props": {
                    "gap": "10",
                    "width": "100%"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Button",
                      "props": {
                        "label": "HTTP Service"
                      },
                      "events": {
                        "click": "currentState = 'serviceView'"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Embed Component"
                      },
                      "events": {
                        "click": "currentState = 'embedView'"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Bridge Communication"
                      },
                      "events": {
                        "click": "currentState = 'bridgeView'"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Overview"
                      },
                      "events": {
                        "click": "currentState = 'default'"
                      },
                      "children": []
                    }
                  ]
                }
              ]
            }
          ]
        },
        {
          "type": "Panel",
          "props": {
            "width": "100%",
            "title": "Status"
          },
          "events": {},
          "children": [
            {
              "type": "HBox",
              "props": {
                "padding": "10",
                "gap": "10",
                "width": "100%",
                "verticalAlign": "middle"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "\ud83d\udce1",
                    "fontSize": "16"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "{statusMessage}",
                    "fontSize": "12",
                    "color": "#2c3e50"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Spacer",
                  "props": {},
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Server: {quantumServerUrl}",
                    "fontSize": "11",
                    "color": "#7f8c8d"
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
            "width": "100%",
            "gap": "15",
            "includeIn": "default"
          },
          "events": {},
          "children": [
            {
              "type": "Panel",
              "props": {
                "width": "100%",
                "title": "\ud83d\udd0c QuantumService - HTTP Client"
              },
              "events": {},
              "children": [
                {
                  "type": "VBox",
                  "props": {
                    "padding": "20",
                    "gap": "12",
                    "width": "100%"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Label",
                      "props": {
                        "text": "Call Quantum endpoints and retrieve data",
                        "fontSize": "12"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Label",
                      "props": {
                        "text": "Features: GET/POST/PUT/DELETE, auto-retry, data extraction from HTML, timeout handling",
                        "fontSize": "11",
                        "color": "#666666"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "HBox",
                      "props": {
                        "gap": "10"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Button",
                          "props": {
                            "label": "Try QuantumService"
                          },
                          "events": {
                            "click": "currentState = 'serviceView'"
                          },
                          "children": []
                        }
                      ]
                    },
                    {
                      "type": "Label",
                      "props": {
                        "text": "Example usage:",
                        "fontSize": "11",
                        "fontWeight": "bold"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Panel",
                      "props": {
                        "width": "100%",
                        "backgroundColor": "#f8f9fa"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "padding": "10",
                            "gap": "5"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "<mx:QuantumService id=\"service\"",
                                "fontSize": "10",
                                "fontFamily": "monospace"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "    url=\"http://localhost:8080/products\"",
                                "fontSize": "10",
                                "fontFamily": "monospace"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "    method=\"GET\"",
                                "fontSize": "10",
                                "fontFamily": "monospace"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "    result=\"handleResult(event)\"",
                                "fontSize": "10",
                                "fontFamily": "monospace"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "    fault=\"handleFault(event)\" />",
                                "fontSize": "10",
                                "fontFamily": "monospace"
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
            },
            {
              "type": "Panel",
              "props": {
                "width": "100%",
                "title": "\ud83d\udcfa QuantumComponent - iframe Embedding"
              },
              "events": {},
              "children": [
                {
                  "type": "VBox",
                  "props": {
                    "padding": "20",
                    "gap": "12",
                    "width": "100%"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Label",
                      "props": {
                        "text": "Embed Quantum .q components inside MXML UI",
                        "fontSize": "12"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Label",
                      "props": {
                        "text": "Features: iframe sandbox, auto-resize, loading states, PostMessage communication",
                        "fontSize": "11",
                        "color": "#666666"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "HBox",
                      "props": {
                        "gap": "10"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Button",
                          "props": {
                            "label": "Try QuantumComponent"
                          },
                          "events": {
                            "click": "currentState = 'embedView'"
                          },
                          "children": []
                        }
                      ]
                    },
                    {
                      "type": "Label",
                      "props": {
                        "text": "Example usage:",
                        "fontSize": "11",
                        "fontWeight": "bold"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Panel",
                      "props": {
                        "width": "100%",
                        "backgroundColor": "#f8f9fa"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "padding": "10",
                            "gap": "5"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "<mx:QuantumComponent",
                                "fontSize": "10",
                                "fontFamily": "monospace"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "    url=\"http://localhost:8080/hello\"",
                                "fontSize": "10",
                                "fontFamily": "monospace"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "    width=\"600\" height=\"400\"",
                                "fontSize": "10",
                                "fontFamily": "monospace"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "    autoResize=\"true\" />",
                                "fontSize": "10",
                                "fontFamily": "monospace"
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
            },
            {
              "type": "Panel",
              "props": {
                "width": "100%",
                "title": "\ud83c\udf09 QuantumBridge - Bidirectional Communication"
              },
              "events": {},
              "children": [
                {
                  "type": "VBox",
                  "props": {
                    "padding": "20",
                    "gap": "12",
                    "width": "100%"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Label",
                      "props": {
                        "text": "PostMessage-based bridge for real-time communication",
                        "fontSize": "12"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Label",
                      "props": {
                        "text": "Features: event handlers, RPC-style method calls, message routing, timeout handling",
                        "fontSize": "11",
                        "color": "#666666"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "HBox",
                      "props": {
                        "gap": "10"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Button",
                          "props": {
                            "label": "Try QuantumBridge"
                          },
                          "events": {
                            "click": "currentState = 'bridgeView'"
                          },
                          "children": []
                        }
                      ]
                    },
                    {
                      "type": "Label",
                      "props": {
                        "text": "Example usage:",
                        "fontSize": "11",
                        "fontWeight": "bold"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Panel",
                      "props": {
                        "width": "100%",
                        "backgroundColor": "#f8f9fa"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "padding": "10",
                            "gap": "5"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "bridge.on(\"quantum:data\", handler);",
                                "fontSize": "10",
                                "fontFamily": "monospace"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "bridge.send(\"mxml:event\", {data});",
                                "fontSize": "10",
                                "fontFamily": "monospace"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "bridge.call(\"method\", {params}).then(...);",
                                "fontSize": "10",
                                "fontFamily": "monospace"
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
          "type": "Panel",
          "props": {
            "width": "100%",
            "title": "QuantumService Demo",
            "includeIn": "serviceView"
          },
          "events": {},
          "children": [
            {
              "type": "VBox",
              "props": {
                "padding": "20",
                "gap": "15",
                "width": "100%"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "HTTP Client for Quantum Endpoints",
                    "fontSize": "14",
                    "fontWeight": "bold"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "HBox",
                  "props": {
                    "gap": "10"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Button",
                      "props": {
                        "label": "Load /products",
                        "enabled": "{!isLoading}"
                      },
                      "events": {
                        "click": "loadProducts()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Load /hello",
                        "enabled": "{!isLoading}"
                      },
                      "events": {
                        "click": "loadHelloComponent()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Refresh Status"
                      },
                      "events": {
                        "click": "refreshStatus()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Back"
                      },
                      "events": {
                        "click": "currentState = 'default'"
                      },
                      "children": []
                    }
                  ]
                },
                {
                  "type": "Panel",
                  "props": {
                    "width": "100%",
                    "title": "Response Data"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "10",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
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
                                "text": "Status:",
                                "fontWeight": "bold",
                                "width": "80"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "{isLoading ? '\u23f3 Loading...' : '\u2705 Ready'}"
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
                                "text": "Data:",
                                "fontWeight": "bold",
                                "width": "80"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "{productsData ? JSON.stringify(productsData).substring(0, 100) + '...' : 'No data loaded'}"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        }
                      ]
                    }
                  ]
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Note: Make sure Quantum server is running at {quantumServerUrl}",
                    "fontSize": "11",
                    "color": "#e74c3c"
                  },
                  "events": {},
                  "children": []
                }
              ]
            }
          ]
        },
        {
          "type": "Panel",
          "props": {
            "width": "100%",
            "title": "QuantumComponent Demo",
            "includeIn": "embedView"
          },
          "events": {},
          "children": [
            {
              "type": "VBox",
              "props": {
                "padding": "20",
                "gap": "15",
                "width": "100%"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Embedded Quantum Component",
                    "fontSize": "14",
                    "fontWeight": "bold"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "HBox",
                  "props": {
                    "gap": "10"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Button",
                      "props": {
                        "label": "Send Message"
                      },
                      "events": {
                        "click": "sendMessageToComponent()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Back"
                      },
                      "events": {
                        "click": "currentState = 'default'"
                      },
                      "children": []
                    }
                  ]
                },
                {
                  "type": "Panel",
                  "props": {
                    "width": "100%",
                    "title": "Embedded Component Preview"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "10",
                        "gap": "10",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "The Quantum component from /hello endpoint will appear below:",
                            "fontSize": "11"
                          },
                          "events": {},
                          "children": []
                        }
                      ]
                    }
                  ]
                },
                {
                  "type": "Panel",
                  "props": {
                    "width": "100%",
                    "title": "Messages"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "10",
                        "gap": "5",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Last Message: {lastMessage}",
                            "fontSize": "11"
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
        },
        {
          "type": "Panel",
          "props": {
            "width": "100%",
            "title": "QuantumBridge Demo",
            "includeIn": "bridgeView"
          },
          "events": {},
          "children": [
            {
              "type": "VBox",
              "props": {
                "padding": "20",
                "gap": "15",
                "width": "100%"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Bidirectional PostMessage Communication",
                    "fontSize": "14",
                    "fontWeight": "bold"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "HBox",
                  "props": {
                    "gap": "10"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Button",
                      "props": {
                        "label": "Initialize Bridge"
                      },
                      "events": {
                        "click": "setupBridge()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Send Message"
                      },
                      "events": {
                        "click": "sendViaBridge()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Call RPC Method"
                      },
                      "events": {
                        "click": "callQuantumMethod()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Back"
                      },
                      "events": {
                        "click": "currentState = 'default'"
                      },
                      "children": []
                    }
                  ]
                },
                {
                  "type": "Panel",
                  "props": {
                    "width": "100%",
                    "title": "Bridge Status"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "10",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Target Origin: {quantumServerUrl}",
                            "fontSize": "11"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "Last Message: {lastMessage}",
                            "fontSize": "11"
                          },
                          "events": {},
                          "children": []
                        }
                      ]
                    }
                  ]
                },
                {
                  "type": "Panel",
                  "props": {
                    "width": "100%",
                    "title": "Available Methods"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "8",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "\u2022 bridge.on(type, handler) - Register message handler",
                            "fontSize": "11",
                            "fontFamily": "monospace"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "\u2022 bridge.send(type, data) - Send message to Quantum",
                            "fontSize": "11",
                            "fontFamily": "monospace"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "\u2022 bridge.call(method, params) - RPC-style method call",
                            "fontSize": "11",
                            "fontFamily": "monospace"
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
        },
        {
          "type": "Panel",
          "props": {
            "width": "100%",
            "title": "Info"
          },
          "events": {},
          "children": [
            {
              "type": "VBox",
              "props": {
                "padding": "10",
                "gap": "5",
                "width": "100%"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Current State: {currentState}",
                    "fontSize": "11"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "This demo requires a running Quantum server at {quantumServerUrl}",
                    "fontSize": "10",
                    "color": "#666666"
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
};

// Application Class (from ActionScript)
class App {
  constructor(runtime) {
    this.runtime = runtime;

    this.quantumServerUrl = "http://localhost:8080";
    this.productsData = null;
    this.statusMessage = "Ready";
    this.isLoading = false;
    this.lastMessage = "";
    this.messageLog = [];
  }

  handleProductsResult(event) {
    console.log("Products loaded successfully!");
    this.productsData = this.event.result;
    this.statusMessage = "Products loaded successfully!";
    this.isLoading = false;
    // this.Log this.the this.response
    console.log("Status Code: " + this.event.statusCode);
    console.log("URL: " + this.event.url);
    if (this.event.result.data) {
    console.log("Data: " + JSON.stringify(this.event.result.data));
  }

  handleProductsFault(event) {
    console.log("Error loading products: " + this.event.error);
    this.statusMessage = "Error: " + this.event.error;
    this.isLoading = false;
    Alert.show(
    "Failed to load data from Quantum server.\n\nMake sure the Quantum server is running at " + this.quantumServerUrl,
    "Connection Error",
    Alert.OK,
    null,
    null,
    Alert.ERROR
    );
  }

  loadProducts() {
    if (this.isLoading) return;
    this.isLoading = true;
    this.statusMessage = "Loading products from Quantum server...";
    this.productsService.send();
    console.log("Requesting products from: " + this.quantumServerUrl + "/products");
  }

  loadHelloComponent() {
    this.statusMessage = "Loading Hello component...";
    this.helloService.send();
  }

  handleHelloResult(event) {
    console.log("Hello component loaded!");
    this.statusMessage = "Hello component data loaded";
    if (this.event.result.title) {
    console.log("Title: " + this.event.result.title);
  }

  handleHelloFault(event) {
    console.log("Error loading hello: " + this.event.error);
    this.statusMessage = "Error loading hello component";
  }

  handleComponentLoad(event) {
    console.log("Quantum component embedded successfully!");
    this.statusMessage = "Quantum component embedded";
  }

  handleComponentError(event) {
    console.log("Error embedding component: " + this.event.error);
    this.statusMessage = "Error embedding component";
  }

  handleComponentMessage(event) {
    console.log("Message from Quantum component: " + JSON.stringify(this.event.data));
    this.lastMessage = JSON.stringify(this.event.data);
    this.messageLog.push({
    this.timestamp: new Date().toLocaleTimeString(),
    this.data: this.event.data,
    this.origin: this.event.origin
  }

  sendMessageToComponent() {
    if (this.quantumComponent) {
    this.quantumComponent.postMessage({
    this.type: 'this.greeting',
    this.message: 'this.Hello this.from this.MXML!',
    this.timestamp: Date.now()
  }

  setupBridge() {
    if (this.quantumBridge) {
    // this.Register this.handler for this.messages this.from this.Quantum
    this.quantumBridge.on('this.quantum:this.data', function(this.data) {
    console.log("Bridge received data: " + JSON.stringify(this.data));
    this.lastMessage = "Bridge: " + JSON.stringify(this.data);
  }

  sendViaBridge() {
    if (this.quantumBridge) {
    this.quantumBridge.send('this.mxml:this.message', {
    this.from: 'this.MXML this.Application',
    this.message: 'this.Testing this.bridge this.communication',
    this.timestamp: Date.now()
  }

  callQuantumMethod() {
    if (this.quantumBridge) {
    this.statusMessage = "Calling Quantum method...";
    this.quantumBridge.call('this.getServerInfo', {
  }

  refreshStatus() {
    const now = new Date().toLocaleTimeString();
    this.statusMessage = "Status refreshed at " + this.now;
  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.render(componentTree, document.getElementById('app'));
