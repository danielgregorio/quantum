import { ReactiveRuntime } from './reactive-runtime.js';

// UI Component Tree
const componentTree = {
  "type": "Application",
  "props": {
    "width": "1400",
    "height": "900",
    "title": "E-Commerce Admin Dashboard"
  },
  "events": {},
  "children": [
    {
      "type": "HBox",
      "props": {
        "width": "100%",
        "height": "100%",
        "gap": "0"
      },
      "events": {},
      "children": [
        {
          "type": "VBox",
          "props": {
            "width": "250",
            "height": "100%",
            "backgroundColor": "#2c3e50",
            "padding": "0"
          },
          "events": {},
          "children": [
            {
              "type": "VBox",
              "props": {
                "width": "100%",
                "padding": "20",
                "backgroundColor": "#1a252f"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "\u26a1 ShopAdmin",
                    "fontSize": "24",
                    "fontWeight": "bold",
                    "color": "#ecf0f1"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "E-Commerce Dashboard",
                    "fontSize": "11",
                    "color": "#95a5a6"
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
                "gap": "5",
                "padding": "15"
              },
              "events": {},
              "children": [
                {
                  "type": "Button",
                  "props": {
                    "label": "\ud83d\udcca Dashboard",
                    "width": "100%",
                    "styleName": "{currentView == 'dashboard' ? 'nav-active' : 'nav-button'}"
                  },
                  "events": {
                    "click": "showDashboard()"
                  },
                  "children": []
                },
                {
                  "type": "Button",
                  "props": {
                    "label": "\ud83d\udce6 Products",
                    "width": "100%",
                    "styleName": "{currentView == 'products' ? 'nav-active' : 'nav-button'}"
                  },
                  "events": {
                    "click": "showProducts()"
                  },
                  "children": []
                },
                {
                  "type": "Button",
                  "props": {
                    "label": "\ud83d\udecd\ufe0f Orders",
                    "width": "100%",
                    "styleName": "{currentView == 'orders' ? 'nav-active' : 'nav-button'}"
                  },
                  "events": {
                    "click": "showOrders()"
                  },
                  "children": []
                },
                {
                  "type": "Button",
                  "props": {
                    "label": "\ud83d\udc65 Customers",
                    "width": "100%",
                    "styleName": "{currentView == 'customers' ? 'nav-active' : 'nav-button'}"
                  },
                  "events": {
                    "click": "showCustomers()"
                  },
                  "children": []
                },
                {
                  "type": "Spacer",
                  "props": {
                    "height": "20"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Button",
                  "props": {
                    "label": "\u2699\ufe0f Settings",
                    "width": "100%",
                    "styleName": "nav-button"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Button",
                  "props": {
                    "label": "\ud83d\udeaa Logout",
                    "width": "100%",
                    "styleName": "nav-button"
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
            "height": "100%",
            "padding": "0",
            "backgroundColor": "#ecf0f1"
          },
          "events": {},
          "children": [
            {
              "type": "VBox",
              "props": {
                "width": "100%",
                "height": "100%",
                "padding": "30",
                "gap": "20",
                "includeIn": "dashboard"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Dashboard",
                    "fontSize": "28",
                    "fontWeight": "bold",
                    "color": "#2c3e50"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "HBox",
                  "props": {
                    "width": "100%",
                    "gap": "20"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Panel",
                      "props": {
                        "width": "25%",
                        "title": "\ud83d\udcb0 Total Revenue",
                        "backgroundColor": "#3498db"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "padding": "20",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "${totalRevenue}",
                                "fontSize": "32",
                                "fontWeight": "bold",
                                "color": "#ffffff"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "+12.5% from last month",
                                "fontSize": "12",
                                "color": "#ecf0f1"
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
                        "width": "25%",
                        "title": "\ud83d\udccb Total Orders",
                        "backgroundColor": "#2ecc71"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "padding": "20",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "{totalOrders}",
                                "fontSize": "32",
                                "fontWeight": "bold",
                                "color": "#ffffff"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "+8.3% from last month",
                                "fontSize": "12",
                                "color": "#ecf0f1"
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
                        "width": "25%",
                        "title": "\ud83d\udc65 Customers",
                        "backgroundColor": "#9b59b6"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "padding": "20",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "{totalCustomers}",
                                "fontSize": "32",
                                "fontWeight": "bold",
                                "color": "#ffffff"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "+15.2% from last month",
                                "fontSize": "12",
                                "color": "#ecf0f1"
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
                        "width": "25%",
                        "title": "\ud83d\udce6 Products",
                        "backgroundColor": "#e74c3c"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "padding": "20",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "{totalProducts}",
                                "fontSize": "32",
                                "fontWeight": "bold",
                                "color": "#ffffff"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "10 low stock items",
                                "fontSize": "12",
                                "color": "#ecf0f1"
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
                  "type": "Panel",
                  "props": {
                    "width": "100%",
                    "title": "\ud83d\udccb Recent Orders"
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
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Order ID",
                                "width": "15%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Customer",
                                "width": "25%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Date",
                                "width": "20%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Total",
                                "width": "20%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Status",
                                "width": "20%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ORD-1001",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "John Smith",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2025-11-07",
                                "width": "20%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$1,329.98",
                                "width": "20%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Pending",
                                "width": "20%",
                                "color": "#f39c12"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ORD-1002",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Sarah Johnson",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2025-11-07",
                                "width": "20%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$79.99",
                                "width": "20%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Processing",
                                "width": "20%",
                                "color": "#3498db"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ORD-1003",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Mike Brown",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2025-11-06",
                                "width": "20%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$649.98",
                                "width": "20%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Shipped",
                                "width": "20%",
                                "color": "#9b59b6"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "View All Orders \u2192"
                          },
                          "events": {
                            "click": "showOrders()"
                          },
                          "children": []
                        }
                      ]
                    }
                  ]
                },
                {
                  "type": "Button",
                  "props": {
                    "label": "\ud83d\udd04 Refresh Dashboard"
                  },
                  "events": {
                    "click": "refreshDashboard()"
                  },
                  "children": []
                }
              ]
            },
            {
              "type": "VBox",
              "props": {
                "width": "100%",
                "height": "100%",
                "padding": "30",
                "gap": "20",
                "includeIn": "products"
              },
              "events": {},
              "children": [
                {
                  "type": "HBox",
                  "props": {
                    "width": "100%",
                    "verticalAlign": "middle",
                    "gap": "20"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Label",
                      "props": {
                        "text": "Products",
                        "fontSize": "28",
                        "fontWeight": "bold",
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
                      "type": "Button",
                      "props": {
                        "label": "\u2795 Add Product"
                      },
                      "events": {
                        "click": "addProduct()"
                      },
                      "children": []
                    }
                  ]
                },
                {
                  "type": "HBox",
                  "props": {
                    "width": "100%",
                    "gap": "10"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "TextInput",
                      "props": {
                        "text": "{productSearchQuery}",
                        "placeholder": "Search products...",
                        "width": "300"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "\ud83d\udd0d Search"
                      },
                      "events": {
                        "click": "searchProducts()"
                      },
                      "children": []
                    }
                  ]
                },
                {
                  "type": "Panel",
                  "props": {
                    "width": "100%",
                    "title": "Product List"
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
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ID",
                                "width": "8%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Product Name",
                                "width": "30%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Category",
                                "width": "15%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Price",
                                "width": "15%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Stock",
                                "width": "12%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Status",
                                "width": "20%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "1",
                                "width": "8%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Laptop Pro 15\"",
                                "width": "30%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Electronics",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$1,299.99",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "45",
                                "width": "12%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Active",
                                "width": "20%",
                                "color": "#2ecc71"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "2",
                                "width": "8%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Wireless Mouse",
                                "width": "30%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Electronics",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$29.99",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "156",
                                "width": "12%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Active",
                                "width": "20%",
                                "color": "#2ecc71"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "5",
                                "width": "8%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "4K Monitor 27\"",
                                "width": "30%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Electronics",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$449.99",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "12",
                                "width": "12%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Low Stock",
                                "width": "20%",
                                "color": "#f39c12"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "8",
                                "width": "8%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Office Chair",
                                "width": "30%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Furniture",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$299.99",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "8",
                                "width": "12%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Low Stock",
                                "width": "20%",
                                "color": "#f39c12"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "10",
                                "width": "8%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Noise Cancelling Headphones",
                                "width": "30%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Electronics",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$249.99",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "0",
                                "width": "12%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Out of Stock",
                                "width": "20%",
                                "color": "#e74c3c"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "Showing 5 of 234 products",
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
                  "type": "HBox",
                  "props": {
                    "gap": "10"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Button",
                      "props": {
                        "label": "\u270f\ufe0f Edit Selected"
                      },
                      "events": {
                        "click": "editProduct()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "\ud83d\uddd1\ufe0f Delete Selected"
                      },
                      "events": {
                        "click": "deleteProduct()"
                      },
                      "children": []
                    }
                  ]
                },
                {
                  "type": "Panel",
                  "props": {
                    "width": "600",
                    "title": "{selectedProduct ? 'Edit Product' : 'Add New Product'}",
                    "includeIn": "editing"
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
                          "type": "HBox",
                          "props": {
                            "gap": "10",
                            "width": "100%"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Name:",
                                "width": "120"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "TextInput",
                              "props": {
                                "text": "{formProductName}",
                                "width": "400"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
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
                              "type": "Label",
                              "props": {
                                "text": "Category:",
                                "width": "120"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "TextInput",
                              "props": {
                                "text": "{formProductCategory}",
                                "width": "400"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
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
                              "type": "Label",
                              "props": {
                                "text": "Price:",
                                "width": "120"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "NumericStepper",
                              "props": {
                                "value": "{formProductPrice}",
                                "minimum": "0",
                                "maximum": "10000",
                                "stepSize": "0.01",
                                "width": "200"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
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
                              "type": "Label",
                              "props": {
                                "text": "Stock:",
                                "width": "120"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "NumericStepper",
                              "props": {
                                "value": "{formProductStock}",
                                "minimum": "0",
                                "maximum": "1000",
                                "stepSize": "1",
                                "width": "200"
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
                              "type": "Button",
                              "props": {
                                "label": "\ud83d\udcbe Save"
                              },
                              "events": {
                                "click": "saveProduct()"
                              },
                              "children": []
                            },
                            {
                              "type": "Button",
                              "props": {
                                "label": "\u274c Cancel"
                              },
                              "events": {
                                "click": "cancelEdit()"
                              },
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
              "type": "VBox",
              "props": {
                "width": "100%",
                "height": "100%",
                "padding": "30",
                "gap": "20",
                "includeIn": "orders"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Orders",
                    "fontSize": "28",
                    "fontWeight": "bold",
                    "color": "#2c3e50"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "HBox",
                  "props": {
                    "width": "100%",
                    "gap": "10",
                    "verticalAlign": "middle"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Label",
                      "props": {
                        "text": "Filter by Status:"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "All"
                      },
                      "events": {
                        "click": "orderStatusFilter = 'All'; filterOrders()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Pending"
                      },
                      "events": {
                        "click": "orderStatusFilter = 'Pending'; filterOrders()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Processing"
                      },
                      "events": {
                        "click": "orderStatusFilter = 'Processing'; filterOrders()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Shipped"
                      },
                      "events": {
                        "click": "orderStatusFilter = 'Shipped'; filterOrders()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Delivered"
                      },
                      "events": {
                        "click": "orderStatusFilter = 'Delivered'; filterOrders()"
                      },
                      "children": []
                    }
                  ]
                },
                {
                  "type": "Panel",
                  "props": {
                    "width": "100%",
                    "title": "Order List"
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
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Order ID",
                                "width": "15%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Customer",
                                "width": "25%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Date",
                                "width": "15%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Items",
                                "width": "10%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Total",
                                "width": "15%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Status",
                                "width": "20%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ORD-1001",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "John Smith",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2025-11-07",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2",
                                "width": "10%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$1,329.98",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Pending",
                                "width": "20%",
                                "color": "#f39c12",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ORD-1002",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Sarah Johnson",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2025-11-07",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "1",
                                "width": "10%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$79.99",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Processing",
                                "width": "20%",
                                "color": "#3498db",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ORD-1003",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Mike Brown",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2025-11-06",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "3",
                                "width": "10%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$649.98",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Shipped",
                                "width": "20%",
                                "color": "#9b59b6",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ORD-1004",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Emily Davis",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2025-11-06",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "1",
                                "width": "10%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$249.99",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Delivered",
                                "width": "20%",
                                "color": "#2ecc71",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ORD-1005",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "David Wilson",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2025-11-05",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "5",
                                "width": "10%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$1,849.95",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Delivered",
                                "width": "20%",
                                "color": "#2ecc71",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ORD-1006",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Lisa Anderson",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2025-11-05",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "1",
                                "width": "10%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$299.99",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Cancelled",
                                "width": "20%",
                                "color": "#e74c3c",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "Showing 6 of 1,247 orders",
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
                  "type": "HBox",
                  "props": {
                    "gap": "10"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Button",
                      "props": {
                        "label": "\u2705 Update Status"
                      },
                      "events": {
                        "click": "updateOrderStatus()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "\u274c Cancel Order"
                      },
                      "events": {
                        "click": "cancelOrder()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "\ud83d\udcc4 View Details"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "\ud83d\udda8\ufe0f Print Invoice"
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
                "height": "100%",
                "padding": "30",
                "gap": "20",
                "includeIn": "customers"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Customers",
                    "fontSize": "28",
                    "fontWeight": "bold",
                    "color": "#2c3e50"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Panel",
                  "props": {
                    "width": "100%",
                    "title": "Customer List"
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
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "ID",
                                "width": "8%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Name",
                                "width": "25%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Email",
                                "width": "30%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Orders",
                                "width": "12%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Total Spent",
                                "width": "15%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Joined",
                                "width": "15%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "1",
                                "width": "8%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "John Smith",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "john.smith@email.com",
                                "width": "30%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "15",
                                "width": "12%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$4,523.85",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2024-03-15",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "2",
                                "width": "8%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Sarah Johnson",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "sarah.j@email.com",
                                "width": "30%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "8",
                                "width": "12%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$2,156.40",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2024-05-22",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "3",
                                "width": "8%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Mike Brown",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "mike.brown@email.com",
                                "width": "30%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "23",
                                "width": "12%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$8,934.50",
                                "width": "15%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2023-11-10",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "4",
                                "width": "8%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "Emily Davis",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "emily.d@email.com",
                                "width": "30%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "12",
                                "width": "12%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$3,421.75",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2024-01-08",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "width": "100%",
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "5",
                                "width": "8%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "David Wilson",
                                "width": "25%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "d.wilson@email.com",
                                "width": "30%"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "31",
                                "width": "12%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "$12,456.20",
                                "width": "15%",
                                "fontWeight": "bold"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "2023-08-20",
                                "width": "15%"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "Showing 5 of 892 customers",
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
                  "type": "HBox",
                  "props": {
                    "gap": "10"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "Button",
                      "props": {
                        "label": "\ud83d\udc64 View Profile"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "\ud83d\udce7 Send Email"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "\ud83d\udcca View Orders"
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
      "type": "states",
      "props": {},
      "events": {},
      "children": [
        {
          "type": "State",
          "props": {
            "name": "dashboard"
          },
          "events": {},
          "children": []
        },
        {
          "type": "State",
          "props": {
            "name": "products"
          },
          "events": {},
          "children": []
        },
        {
          "type": "State",
          "props": {
            "name": "orders"
          },
          "events": {},
          "children": []
        },
        {
          "type": "State",
          "props": {
            "name": "customers"
          },
          "events": {},
          "children": []
        },
        {
          "type": "State",
          "props": {
            "name": "editing",
            "basedOn": "products"
          },
          "events": {},
          "children": []
        }
      ]
    }
  ]
};

// Application Class (from ActionScript)
class App {
  constructor(runtime) {
    this.runtime = runtime;

    this.currentView = "dashboard";
    this._bindable_currentView = true;
    this.totalRevenue = 45280.50;
    this._bindable_totalRevenue = true;
    this.totalOrders = 1247;
    this._bindable_totalOrders = true;
    this.totalCustomers = 892;
    this._bindable_totalCustomers = true;
    this.totalProducts = 234;
    this._bindable_totalProducts = true;
    this.products = [
                {id: 1, name: "Laptop Pro 15\"", category: "Electronics", price: 1299.99, stock: 45, status: "Active"},
                {id: 2, name: "Wireless Mouse", category: "Electronics", price: 29.99, stock: 156, status: "Active"},
                {id: 3, name: "USB-C Hub", category: "Electronics", price: 49.99, stock: 89, status: "Active"},
                {id: 4, name: "Mechanical Keyboard", category: "Electronics", price: 159.99, stock: 23, status: "Active"},
                {id: 5, name: "4K Monitor 27\"", category: "Electronics", price: 449.99, stock: 12, status: "Low Stock"},
                {id: 6, name: "Webcam HD", category: "Electronics", price: 79.99, stock: 67, status: "Active"},
                {id: 7, name: "Desk Lamp LED", category: "Office", price: 34.99, stock: 145, status: "Active"},
                {id: 8, name: "Office Chair", category: "Furniture", price: 299.99, stock: 8, status: "Low Stock"},
                {id: 9, name: "Standing Desk", category: "Furniture", price: 599.99, stock: 15, status: "Active"},
                {id: 10, name: "Noise Cancelling Headphones", category: "Electronics", price: 249.99, stock: 0, status: "Out of Stock"}
            ];
    this._bindable_products = true;
    this.selectedProduct = null;
    this._bindable_selectedProduct = true;
    this.productSearchQuery = "";
    this._bindable_productSearchQuery = true;
    this.orders = [
                {id: "ORD-1001", customer: "John Smith", date: "2025-11-07", total: 1329.98, status: "Pending", items: 2},
                {id: "ORD-1002", customer: "Sarah Johnson", date: "2025-11-07", total: 79.99, status: "Processing", items: 1},
                {id: "ORD-1003", customer: "Mike Brown", date: "2025-11-06", total: 649.98, status: "Shipped", items: 3},
                {id: "ORD-1004", customer: "Emily Davis", date: "2025-11-06", total: 249.99, status: "Delivered", items: 1},
                {id: "ORD-1005", customer: "David Wilson", date: "2025-11-05", total: 1849.95, status: "Delivered", items: 5},
                {id: "ORD-1006", customer: "Lisa Anderson", date: "2025-11-05", total: 299.99, status: "Cancelled", items: 1},
                {id: "ORD-1007", customer: "Tom Martinez", date: "2025-11-04", total: 529.98, status: "Delivered", items: 2},
                {id: "ORD-1008", customer: "Anna Lee", date: "2025-11-04", total: 159.99, status: "Delivered", items: 1}
            ];
    this._bindable_orders = true;
    this.selectedOrder = null;
    this._bindable_selectedOrder = true;
    this.orderStatusFilter = "All";
    this._bindable_orderStatusFilter = true;
    this.customers = [
                {id: 1, name: "John Smith", email: "john.smith@email.com", orders: 15, totalSpent: 4523.85, joined: "2024-03-15"},
                {id: 2, name: "Sarah Johnson", email: "sarah.j@email.com", orders: 8, totalSpent: 2156.40, joined: "2024-05-22"},
                {id: 3, name: "Mike Brown", email: "mike.brown@email.com", orders: 23, totalSpent: 8934.50, joined: "2023-11-10"},
                {id: 4, name: "Emily Davis", email: "emily.d@email.com", orders: 12, totalSpent: 3421.75, joined: "2024-01-08"},
                {id: 5, name: "David Wilson", email: "d.wilson@email.com", orders: 31, totalSpent: 12456.20, joined: "2023-08-20"}
            ];
    this._bindable_customers = true;
    this.editingProduct = false;
    this._bindable_editingProduct = true;
    this.formProductName = "";
    this._bindable_formProductName = true;
    this.formProductPrice = 0;
    this._bindable_formProductPrice = true;
    this.formProductStock = 0;
    this._bindable_formProductStock = true;
    this.formProductCategory = "Electronics";
    this._bindable_formProductCategory = true;
  }

  showDashboard() {
    this.currentView = "dashboard";
  }

  showProducts() {
    this.currentView = "products";
  }

  showOrders() {
    this.currentView = "orders";
  }

  showCustomers() {
    this.currentView = "customers";
  }

  searchProducts() {
    console.log("Searching products: " + this.productSearchQuery);
  }

  addProduct() {
    this.editingProduct = true;
    this.formProductName = "";
    this.formProductPrice = 0;
    this.formProductStock = 0;
    this.formProductCategory = "Electronics";
  }

  editProduct() {
    if (this.selectedProduct != null) {
    this.editingProduct = true;
    this.formProductName = this.selectedProduct.name;
    this.formProductPrice = this.selectedProduct.price;
    this.formProductStock = this.selectedProduct.stock;
    this.formProductCategory = this.selectedProduct.category;
    }
  }

  saveProduct() {
    if (this.selectedProduct != null) {
    this.selectedProduct.name = this.formProductName;
    this.selectedProduct.price = this.formProductPrice;
    this.selectedProduct.stock = this.formProductStock;
    this.selectedProduct.category = this.formProductCategory;
    Alert.show("Product updated successfully!", "Success", Alert.OK, null, null, Alert.INFO);
    } else {
    var newId = this.products.length + 1;
    var newProduct = {
    id: this.newId,
    name: this.formProductName,
    category: this.formProductCategory,
    price: this.formProductPrice,
    stock: this.formProductStock,
    status: this.formProductStock > 20 ? "Active" : "Low Stock"
    };
    this.products.push(this.newProduct);
    Alert.show("Product added successfully!", "Success", Alert.OK, null, null, Alert.INFO);
    }
    this.editingProduct = false;
    this.selectedProduct = null;
  }

  cancelEdit() {
    this.editingProduct = false;
    this.selectedProduct = null;
  }

  deleteProduct() {
    if (this.selectedProduct != null) {
    Alert.show("Product deleted: " + this.selectedProduct.name, "Deleted", Alert.OK, null, null, Alert.WARNING);
    this.selectedProduct = null;
    }
  }

  filterOrders() {
    console.log("Filtering orders by status: " + this.orderStatusFilter);
  }

  updateOrderStatus() {
    if (this.selectedOrder != null) {
    var currentStatus = this.selectedOrder.status;
    var newStatus = "";
    if (this.currentStatus == "Pending") {
    this.newStatus = "Processing";
    } else if (this.currentStatus == "Processing") {
    this.newStatus = "Shipped";
    } else if (this.currentStatus == "Shipped") {
    this.newStatus = "Delivered";
    } else {
    this.newStatus = this.currentStatus;
    }
    this.selectedOrder.status = this.newStatus;
    Alert.show("Order status updated to: " + this.newStatus, "Updated", Alert.OK, null, null, Alert.INFO);
    }
  }

  cancelOrder() {
    if (this.selectedOrder != null) {
    this.selectedOrder.status = "Cancelled";
    Alert.show("Order cancelled: " + this.selectedOrder.id, "Cancelled", Alert.OK, null, null, Alert.WARNING);
    }
  }

  refreshDashboard() {
    Alert.show("Dashboard data refreshed!", "Refreshed", Alert.OK, null, null, Alert.INFO);
  }

  // Reactive getter/setter for currentView
  get currentView() {
    return this._currentView;
  }
  set currentView(value) {
    this._currentView = value;
    this.runtime.notifyChange('currentView', value);
  }

  // Reactive getter/setter for totalRevenue
  get totalRevenue() {
    return this._totalRevenue;
  }
  set totalRevenue(value) {
    this._totalRevenue = value;
    this.runtime.notifyChange('totalRevenue', value);
  }

  // Reactive getter/setter for totalOrders
  get totalOrders() {
    return this._totalOrders;
  }
  set totalOrders(value) {
    this._totalOrders = value;
    this.runtime.notifyChange('totalOrders', value);
  }

  // Reactive getter/setter for totalCustomers
  get totalCustomers() {
    return this._totalCustomers;
  }
  set totalCustomers(value) {
    this._totalCustomers = value;
    this.runtime.notifyChange('totalCustomers', value);
  }

  // Reactive getter/setter for totalProducts
  get totalProducts() {
    return this._totalProducts;
  }
  set totalProducts(value) {
    this._totalProducts = value;
    this.runtime.notifyChange('totalProducts', value);
  }

  // Reactive getter/setter for products
  get products() {
    return this._products;
  }
  set products(value) {
    this._products = value;
    this.runtime.notifyChange('products', value);
  }

  // Reactive getter/setter for selectedProduct
  get selectedProduct() {
    return this._selectedProduct;
  }
  set selectedProduct(value) {
    this._selectedProduct = value;
    this.runtime.notifyChange('selectedProduct', value);
  }

  // Reactive getter/setter for productSearchQuery
  get productSearchQuery() {
    return this._productSearchQuery;
  }
  set productSearchQuery(value) {
    this._productSearchQuery = value;
    this.runtime.notifyChange('productSearchQuery', value);
  }

  // Reactive getter/setter for orders
  get orders() {
    return this._orders;
  }
  set orders(value) {
    this._orders = value;
    this.runtime.notifyChange('orders', value);
  }

  // Reactive getter/setter for selectedOrder
  get selectedOrder() {
    return this._selectedOrder;
  }
  set selectedOrder(value) {
    this._selectedOrder = value;
    this.runtime.notifyChange('selectedOrder', value);
  }

  // Reactive getter/setter for orderStatusFilter
  get orderStatusFilter() {
    return this._orderStatusFilter;
  }
  set orderStatusFilter(value) {
    this._orderStatusFilter = value;
    this.runtime.notifyChange('orderStatusFilter', value);
  }

  // Reactive getter/setter for customers
  get customers() {
    return this._customers;
  }
  set customers(value) {
    this._customers = value;
    this.runtime.notifyChange('customers', value);
  }

  // Reactive getter/setter for editingProduct
  get editingProduct() {
    return this._editingProduct;
  }
  set editingProduct(value) {
    this._editingProduct = value;
    this.runtime.notifyChange('editingProduct', value);
  }

  // Reactive getter/setter for formProductName
  get formProductName() {
    return this._formProductName;
  }
  set formProductName(value) {
    this._formProductName = value;
    this.runtime.notifyChange('formProductName', value);
  }

  // Reactive getter/setter for formProductPrice
  get formProductPrice() {
    return this._formProductPrice;
  }
  set formProductPrice(value) {
    this._formProductPrice = value;
    this.runtime.notifyChange('formProductPrice', value);
  }

  // Reactive getter/setter for formProductStock
  get formProductStock() {
    return this._formProductStock;
  }
  set formProductStock(value) {
    this._formProductStock = value;
    this.runtime.notifyChange('formProductStock', value);
  }

  // Reactive getter/setter for formProductCategory
  get formProductCategory() {
    return this._formProductCategory;
  }
  set formProductCategory(value) {
    this._formProductCategory = value;
    this.runtime.notifyChange('formProductCategory', value);
  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.registerHealthCheck();  // Enable health monitoring
runtime.render(componentTree, document.getElementById('app'));