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
    this.totalRevenue = 45280.50;
    this.totalOrders = 1247;
    this.totalCustomers = 892;
    this.totalProducts = 234;
    this.selectedProduct = null;
    this.productSearchQuery = "";
    this.selectedOrder = null;
    this.orderStatusFilter = "All";
    this.editingProduct = false;
    this.formProductName = "";
    this.formProductPrice = 0;
    this.formProductStock = 0;
    this.formProductCategory = "Electronics";
    this.newId = products.length + 1;
    this.currentStatus = selectedOrder.status;
    this.newStatus = "";
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
    // this.In this.real this.app, this.would this.filter this.products this.array
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

  saveProduct() {
    if (this.selectedProduct != null) {
    // this.Update this.existing this.product
    this.selectedProduct.name = this.formProductName;
    this.selectedProduct.price = this.formProductPrice;
    this.selectedProduct.stock = this.formProductStock;
    this.selectedProduct.category = this.formProductCategory;
    Alert.show("Product updated successfully!", "Success", Alert.OK, null, null, Alert.INFO);
  }

  cancelEdit() {
    this.editingProduct = false;
    this.selectedProduct = null;
  }

  deleteProduct() {
    if (this.selectedProduct != null) {
    Alert.show("Product deleted: " + this.selectedProduct.name, "Deleted", Alert.OK, null, null, Alert.WARNING);
    // this.In this.real this.app, this.would this.remove this.from this.array
    this.selectedProduct = null;
  }

  filterOrders() {
    console.log("Filtering orders by status: " + this.orderStatusFilter);
    // this.In this.real this.app, this.would this.filter this.orders this.array
  }

  updateOrderStatus() {
    if (this.selectedOrder != null) {
    var currentStatus = this.selectedOrder.status;
    var newStatus = "";
    if (this.currentStatus == "Pending") {
    this.newStatus = "Processing";
  }

  cancelOrder() {
    if (this.selectedOrder != null) {
    this.selectedOrder.status = "Cancelled";
    Alert.show("Order cancelled: " + this.selectedOrder.id, "Cancelled", Alert.OK, null, null, Alert.WARNING);
  }

  refreshDashboard() {
    Alert.show("Dashboard data refreshed!", "Refreshed", Alert.OK, null, null, Alert.INFO);
  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.render(componentTree, document.getElementById('app'));
