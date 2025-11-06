import { ReactiveRuntime } from './reactive-runtime.js';

// UI Component Tree
const componentTree = {
  "type": "Application",
  "props": {
    "width": "900",
    "height": "900",
    "title": "FASE 3 Demo - Effects and Formatters"
  },
  "events": {},
  "children": [
    {
      "type": "Fade",
      "props": {
        "id": "fadeIn",
        "alphaFrom": "0",
        "alphaTo": "1",
        "duration": "1000"
      },
      "events": {},
      "children": []
    },
    {
      "type": "Fade",
      "props": {
        "id": "fadeOut",
        "alphaFrom": "1",
        "alphaTo": "0",
        "duration": "1000"
      },
      "events": {},
      "children": []
    },
    {
      "type": "Move",
      "props": {
        "id": "moveRight",
        "xBy": "200",
        "yBy": "0",
        "duration": "1000"
      },
      "events": {},
      "children": []
    },
    {
      "type": "Resize",
      "props": {
        "id": "resizeEffect",
        "widthBy": "100",
        "heightBy": "50",
        "duration": "1000"
      },
      "events": {},
      "children": []
    },
    {
      "type": "Glow",
      "props": {
        "id": "glowEffect",
        "color": "#3498db",
        "alphaFrom": "0",
        "alphaTo": "1",
        "blurXTo": "20",
        "duration": "1000"
      },
      "events": {},
      "children": []
    },
    {
      "type": "DateFormatter",
      "props": {
        "id": "dateFormatter1",
        "formatString": "MM/DD/YYYY"
      },
      "events": {},
      "children": []
    },
    {
      "type": "DateFormatter",
      "props": {
        "id": "dateFormatter2",
        "formatString": "EEEE, MMMM D, YYYY"
      },
      "events": {},
      "children": []
    },
    {
      "type": "DateFormatter",
      "props": {
        "id": "dateFormatter3",
        "formatString": "HH:mm:ss"
      },
      "events": {},
      "children": []
    },
    {
      "type": "DateFormatter",
      "props": {
        "id": "dateFormatter4",
        "formatString": "MMM DD, YYYY HH:mm A"
      },
      "events": {},
      "children": []
    },
    {
      "type": "NumberFormatter",
      "props": {
        "id": "numberFormatter",
        "precision": "2",
        "useThousandsSeparator": "true",
        "decimalSeparator": ".",
        "thousandsSeparator": ","
      },
      "events": {},
      "children": []
    },
    {
      "type": "CurrencyFormatter",
      "props": {
        "id": "currencyFormatter",
        "precision": "2",
        "currencySymbol": "$",
        "alignSymbol": "left",
        "useThousandsSeparator": "true"
      },
      "events": {},
      "children": []
    },
    {
      "type": "CurrencyFormatter",
      "props": {
        "id": "euroFormatter",
        "precision": "2",
        "currencySymbol": "\u20ac",
        "alignSymbol": "right",
        "useThousandsSeparator": "true",
        "decimalSeparator": ",",
        "thousandsSeparator": "."
      },
      "events": {},
      "children": []
    },
    {
      "type": "PhoneFormatter",
      "props": {
        "id": "phoneFormatter",
        "formatString": "(###) ###-####"
      },
      "events": {},
      "children": []
    },
    {
      "type": "ZipCodeFormatter",
      "props": {
        "id": "zipFormatter"
      },
      "events": {},
      "children": []
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
            "title": "FASE 3 Components Demo"
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
                    "text": "Effects and Formatters System",
                    "fontSize": "14",
                    "fontWeight": "bold"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Demonstrates: Visual Effects (Fade, Move, Resize, Glow) and Data Formatters (Date, Number, Currency, Phone)",
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
          "type": "HBox",
          "props": {
            "width": "100%",
            "gap": "20"
          },
          "events": {},
          "children": [
            {
              "type": "VBox",
              "props": {
                "width": "50%",
                "gap": "15"
              },
              "events": {},
              "children": [
                {
                  "type": "Panel",
                  "props": {
                    "width": "100%",
                    "title": "Fade Effect"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "12",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Animate opacity (alpha) transitions:",
                            "fontSize": "12"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Panel",
                          "props": {
                            "id": "fadeBox",
                            "width": "200",
                            "height": "100",
                            "backgroundColor": "#3498db",
                            "title": "Fade Target"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "VBox",
                              "props": {
                                "padding": "10",
                                "horizontalAlign": "center",
                                "verticalAlign": "middle",
                                "width": "100%",
                                "height": "100%"
                              },
                              "events": {},
                              "children": [
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "Watch me fade!",
                                    "color": "#ffffff",
                                    "fontWeight": "bold"
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
                                "label": "Fade In"
                              },
                              "events": {
                                "click": "playFadeIn()"
                              },
                              "children": []
                            },
                            {
                              "type": "Button",
                              "props": {
                                "label": "Fade Out"
                              },
                              "events": {
                                "click": "playFadeOut()"
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
                    "title": "Move Effect"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "12",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Animate position changes:",
                            "fontSize": "12"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Panel",
                          "props": {
                            "id": "moveBox",
                            "width": "150",
                            "height": "80",
                            "backgroundColor": "#2ecc71",
                            "title": "Move Target"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "VBox",
                              "props": {
                                "padding": "10",
                                "horizontalAlign": "center",
                                "verticalAlign": "middle",
                                "width": "100%",
                                "height": "100%"
                              },
                              "events": {},
                              "children": [
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "I can move!",
                                    "color": "#ffffff",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                }
                              ]
                            }
                          ]
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "Move Right"
                          },
                          "events": {
                            "click": "playMove()"
                          },
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
                    "title": "Resize Effect"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "12",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Animate size changes:",
                            "fontSize": "12"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Panel",
                          "props": {
                            "id": "resizeBox",
                            "width": "150",
                            "height": "80",
                            "backgroundColor": "#e74c3c",
                            "title": "Resize Target"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "VBox",
                              "props": {
                                "padding": "10",
                                "horizontalAlign": "center",
                                "verticalAlign": "middle",
                                "width": "100%",
                                "height": "100%"
                              },
                              "events": {},
                              "children": [
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "Watch me grow!",
                                    "color": "#ffffff",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                }
                              ]
                            }
                          ]
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "Resize"
                          },
                          "events": {
                            "click": "playResize()"
                          },
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
                    "title": "Glow Effect"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "12",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Add drop shadow glow:",
                            "fontSize": "12"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Panel",
                          "props": {
                            "id": "glowBox",
                            "width": "150",
                            "height": "80",
                            "backgroundColor": "#9b59b6",
                            "title": "Glow Target"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "VBox",
                              "props": {
                                "padding": "10",
                                "horizontalAlign": "center",
                                "verticalAlign": "middle",
                                "width": "100%",
                                "height": "100%"
                              },
                              "events": {},
                              "children": [
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "I can glow!",
                                    "color": "#ffffff",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                }
                              ]
                            }
                          ]
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "Glow"
                          },
                          "events": {
                            "click": "playGlow()"
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
              "type": "VBox",
              "props": {
                "width": "50%",
                "gap": "15"
              },
              "events": {},
              "children": [
                {
                  "type": "Panel",
                  "props": {
                    "width": "100%",
                    "title": "Date Formatter"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "12",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Format dates with various patterns:",
                            "fontSize": "12"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "VBox",
                          "props": {
                            "gap": "8",
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
                                    "text": "MM/DD/YYYY:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{dateFormatter1.format(currentDate)}"
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
                                    "text": "Full Date:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{dateFormatter2.format(currentDate)}"
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
                                    "text": "Time:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{dateFormatter3.format(currentDate)}"
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
                                    "text": "Date and Time:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{dateFormatter4.format(currentDate)}"
                                  },
                                  "events": {},
                                  "children": []
                                }
                              ]
                            }
                          ]
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "Update Date"
                          },
                          "events": {
                            "click": "updateDate()"
                          },
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
                    "title": "Number Formatter"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "12",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Format numbers with precision and separators:",
                            "fontSize": "12"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "VBox",
                          "props": {
                            "gap": "8",
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
                                    "text": "Price:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{numberFormatter.format(price)}"
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
                                    "text": "Population:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{numberFormatter.format(population)}"
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
                                    "text": "Pi:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{numberFormatter.format(3.14159265359)}"
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
                    "title": "Currency Formatter"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "12",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Format currency values with symbols:",
                            "fontSize": "12"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "VBox",
                          "props": {
                            "gap": "8",
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
                                    "text": "USD:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{currencyFormatter.format(price)}"
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
                                    "text": "EUR:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{euroFormatter.format(price)}"
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
                                    "text": "Salary:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{currencyFormatter.format(75000)}"
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
                                    "text": "Negative:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{currencyFormatter.format(-99.99)}"
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
                    "title": "Phone and Zip Code Formatters"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "12",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Format phone numbers and zip codes:",
                            "fontSize": "12"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "VBox",
                          "props": {
                            "gap": "8",
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
                                    "text": "Phone:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{phoneFormatter.format(phoneNumber)}"
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
                                    "text": "Zip Code:",
                                    "width": "150",
                                    "fontWeight": "bold"
                                  },
                                  "events": {},
                                  "children": []
                                },
                                {
                                  "type": "Label",
                                  "props": {
                                    "text": "{zipFormatter.format(zipCode)}"
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
        },
        {
          "type": "Panel",
          "props": {
            "width": "100%",
            "title": "Effect and Formatter Features"
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
                    "text": "Effects:",
                    "fontWeight": "bold"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 Fade: Animate opacity transitions (alphaFrom, alphaTo, duration)",
                    "fontSize": "11"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 Move: Animate position (xBy, yBy, xFrom, yFrom, xTo, yTo, duration)",
                    "fontSize": "11"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 Resize: Animate size (widthBy, heightBy, widthFrom, heightFrom, widthTo, heightTo)",
                    "fontSize": "11"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 Glow: Add drop shadow effects (color, alphaFrom, alphaTo, blurXFrom, blurXTo)",
                    "fontSize": "11"
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
                    "text": "Formatters:",
                    "fontWeight": "bold"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 DateFormatter: Format dates (MM/DD/YYYY, EEEE MMMM D, HH:mm:ss, etc.)",
                    "fontSize": "11"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 NumberFormatter: Format numbers (precision, thousands separator, decimal separator)",
                    "fontSize": "11"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 CurrencyFormatter: Format currency (symbol, position, precision)",
                    "fontSize": "11"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 PhoneFormatter: Format phone numbers with patterns",
                    "fontSize": "11"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 ZipCodeFormatter: Format ZIP codes (5-digit or 9-digit)",
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
};

// Application Class (from ActionScript)
class App {
  constructor(runtime) {
    this.runtime = runtime;

    this.currentDate = new Date();
    this.price = 1234.56;
    this.population = 7900000000;
    this.phoneNumber = "5551234567";
    this.zipCode = "123456789";
    this.showEffectBox = true;
  }

  playFadeIn() {
    this.fadeIn.play(this.fadeBox);
    console.log("Fade In effect started");
  }

  playFadeOut() {
    this.fadeOut.play(this.fadeBox);
    console.log("Fade Out effect started");
  }

  playMove() {
    this.moveRight.play(this.moveBox);
    console.log("Move effect started");
  }

  playResize() {
    this.resizeEffect.play(this.resizeBox);
    console.log("Resize effect started");
  }

  playGlow() {
    this.glowEffect.play(this.glowBox);
    console.log("Glow effect started");
  }

  updateDate() {
    this.currentDate = new Date();
    console.log("Date updated: " + this.currentDate);
  }

  handleEffectEnd() {
    console.log("Effect completed!");
  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.render(componentTree, document.getElementById('app'));
