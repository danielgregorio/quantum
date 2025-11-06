import { ReactiveRuntime } from './reactive-runtime.js';

// UI Component Tree
const componentTree = {
  "type": "Application",
  "props": {
    "width": "900",
    "height": "800",
    "title": "FASE 2 Demo - Advanced Inputs and Validation"
  },
  "events": {},
  "children": [
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
            "name": "formView"
          },
          "events": {},
          "children": []
        },
        {
          "type": "State",
          "props": {
            "name": "settingsView"
          },
          "events": {},
          "children": []
        }
      ]
    },
    {
      "type": "StringValidator",
      "props": {
        "id": "usernameValidator",
        "source": "{usernameInput}",
        "property": "text",
        "minLength": "3",
        "maxLength": "20",
        "required": "true",
        "tooShortError": "Username must be at least 3 characters",
        "tooLongError": "Username cannot exceed 20 characters",
        "requiredFieldError": "Username is required",
        "trigger": "blur",
        "invalid": "validateUsername(event)",
        "valid": "validateUsername(event)"
      },
      "events": {},
      "children": []
    },
    {
      "type": "EmailValidator",
      "props": {
        "id": "emailValidator",
        "source": "{emailInput}",
        "property": "text",
        "required": "true",
        "requiredFieldError": "Email is required",
        "invalidCharError": "Please enter a valid email address",
        "trigger": "blur",
        "invalid": "validateEmail(event)",
        "valid": "validateEmail(event)"
      },
      "events": {},
      "children": []
    },
    {
      "type": "NumberValidator",
      "props": {
        "id": "ageValidator",
        "source": "{ageInput}",
        "property": "value",
        "minValue": "18",
        "maxValue": "120",
        "domain": "int",
        "required": "true",
        "lowerThanMinError": "You must be at least 18 years old",
        "exceedsMaxError": "Please enter a valid age",
        "integerError": "Age must be a whole number",
        "trigger": "blur",
        "invalid": "validateAge(event)",
        "valid": "validateAge(event)"
      },
      "events": {},
      "children": []
    },
    {
      "type": "NumberValidator",
      "props": {
        "id": "priceValidator",
        "source": "{priceInput}",
        "property": "value",
        "minValue": "0",
        "allowNegative": "false",
        "required": "false",
        "negativeError": "Price cannot be negative",
        "trigger": "blur"
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
            "title": "FASE 2 Components Demo"
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
                    "text": "Advanced Input Controls and Validation System",
                    "fontSize": "14",
                    "fontWeight": "bold"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Demonstrates: NumericStepper, Sliders, TextArea, States, and Validators",
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
                        "label": "Main Demo"
                      },
                      "events": {
                        "click": "switchToDefault()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Form with Validation"
                      },
                      "events": {
                        "click": "switchToForm()"
                      },
                      "children": []
                    },
                    {
                      "type": "Button",
                      "props": {
                        "label": "Settings Panel"
                      },
                      "events": {
                        "click": "switchToSettings()"
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
                "title": "NumericStepper Component"
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
                        "text": "Quantity selector with increment/decrement buttons:",
                        "fontSize": "12"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "HBox",
                      "props": {
                        "gap": "15",
                        "verticalAlign": "middle"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Quantity:",
                            "width": "100"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "NumericStepper",
                          "props": {
                            "id": "quantityInput",
                            "value": "{quantity}",
                            "minimum": "1",
                            "maximum": "100",
                            "stepSize": "1",
                            "width": "120"
                          },
                          "events": {
                            "change": "handleQuantityChange(event)"
                          },
                          "children": []
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "{quantity} items selected",
                            "fontSize": "11",
                            "color": "#666666"
                          },
                          "events": {},
                          "children": []
                        }
                      ]
                    },
                    {
                      "type": "HBox",
                      "props": {
                        "gap": "15",
                        "verticalAlign": "middle"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Price ($):",
                            "width": "100"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "NumericStepper",
                          "props": {
                            "id": "priceInput",
                            "value": "{price}",
                            "minimum": "0",
                            "maximum": "9999",
                            "stepSize": "0.50",
                            "width": "120"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "$${price.toFixed(2)}",
                            "fontSize": "11",
                            "color": "#2ecc71",
                            "fontWeight": "bold"
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
                "title": "Slider Components (HSlider and VSlider)"
              },
              "events": {},
              "children": [
                {
                  "type": "HBox",
                  "props": {
                    "padding": "15",
                    "gap": "30",
                    "width": "100%"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "gap": "15",
                        "width": "60%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Horizontal Sliders:",
                            "fontSize": "12",
                            "fontWeight": "bold"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "HBox",
                          "props": {
                            "gap": "10",
                            "verticalAlign": "middle"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Volume:",
                                "width": "80"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "HSlider",
                              "props": {
                                "id": "volumeSlider",
                                "value": "{volume}",
                                "minimum": "0",
                                "maximum": "100",
                                "snapInterval": "1",
                                "liveDragging": "true",
                                "width": "250"
                              },
                              "events": {
                                "change": "handleVolumeChange(event)"
                              },
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "{Math.round(volume)}%",
                                "width": "50",
                                "fontSize": "11"
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
                            "verticalAlign": "middle"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Brightness:",
                                "width": "80"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "HSlider",
                              "props": {
                                "id": "brightnessSlider",
                                "value": "{brightness}",
                                "minimum": "0",
                                "maximum": "100",
                                "snapInterval": "5",
                                "liveDragging": "true",
                                "width": "250"
                              },
                              "events": {
                                "change": "handleBrightnessChange(event)"
                              },
                              "children": []
                            },
                            {
                              "type": "Label",
                              "props": {
                                "text": "{Math.round(brightness)}%",
                                "width": "50",
                                "fontSize": "11"
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
                            "verticalAlign": "middle"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Preview:",
                                "width": "80"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "Panel",
                              "props": {
                                "width": "250",
                                "height": "50",
                                "backgroundColor": "#{Math.floor(brightness * 2.55).toString(16).padStart(2, '0') + Math.floor(brightness * 2.55).toString(16).padStart(2, '0') + Math.floor(brightness * 2.55).toString(16).padStart(2, '0')}"
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
                        "gap": "10",
                        "horizontalAlign": "center"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Vertical Slider:",
                            "fontSize": "12",
                            "fontWeight": "bold"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "VSlider",
                          "props": {
                            "id": "verticalSlider",
                            "value": "50",
                            "minimum": "0",
                            "maximum": "100",
                            "snapInterval": "10",
                            "liveDragging": "true",
                            "height": "180"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "Value: 50",
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
            },
            {
              "type": "Panel",
              "props": {
                "width": "100%",
                "title": "TextArea Component"
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
                        "text": "Multi-line text input with character limit:",
                        "fontSize": "12"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "TextArea",
                      "props": {
                        "id": "commentsArea",
                        "text": "{comments}",
                        "width": "100%",
                        "height": "120",
                        "maxChars": "500",
                        "wordWrap": "true"
                      },
                      "events": {
                        "change": "handleCommentsChange(event)"
                      },
                      "children": []
                    },
                    {
                      "type": "Label",
                      "props": {
                        "text": "Tips: Try typing more than 500 characters to see the limit in action.",
                        "fontSize": "10",
                        "color": "#999999"
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
            "title": "User Registration Form",
            "includeIn": "formView"
          },
          "events": {},
          "children": [
            {
              "type": "Form",
              "props": {
                "width": "100%",
                "padding": "20"
              },
              "events": {},
              "children": [
                {
                  "type": "FormHeading",
                  "props": {
                    "label": "Personal Information"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "FormItem",
                  "props": {
                    "label": "Username",
                    "required": "true"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "TextInput",
                      "props": {
                        "id": "usernameInput",
                        "text": "{username}",
                        "width": "100%"
                      },
                      "events": {},
                      "children": []
                    }
                  ]
                },
                {
                  "type": "FormItem",
                  "props": {
                    "label": "Email",
                    "required": "true"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "TextInput",
                      "props": {
                        "id": "emailInput",
                        "text": "{email}",
                        "width": "100%"
                      },
                      "events": {},
                      "children": []
                    }
                  ]
                },
                {
                  "type": "FormItem",
                  "props": {
                    "label": "Age",
                    "required": "true"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "NumericStepper",
                      "props": {
                        "id": "ageInput",
                        "value": "{age}",
                        "minimum": "18",
                        "maximum": "120",
                        "stepSize": "1",
                        "width": "120"
                      },
                      "events": {},
                      "children": []
                    }
                  ]
                },
                {
                  "type": "FormHeading",
                  "props": {
                    "label": "Additional Details"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "FormItem",
                  "props": {
                    "label": "Comments",
                    "direction": "vertical"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "TextArea",
                      "props": {
                        "text": "{comments}",
                        "width": "100%",
                        "height": "100",
                        "maxChars": "500",
                        "wordWrap": "true"
                      },
                      "events": {},
                      "children": []
                    }
                  ]
                },
                {
                  "type": "FormItem",
                  "props": {},
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
                          "type": "Button",
                          "props": {
                            "label": "Submit Form"
                          },
                          "events": {
                            "click": "submitForm()"
                          },
                          "children": []
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "Reset"
                          },
                          "events": {
                            "click": "resetForm()"
                          },
                          "children": []
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "Back"
                          },
                          "events": {
                            "click": "switchToDefault()"
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
            "gap": "15",
            "includeIn": "settingsView"
          },
          "events": {},
          "children": [
            {
              "type": "Panel",
              "props": {
                "width": "100%",
                "title": "Audio Settings"
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
                        "verticalAlign": "middle",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Master Volume:",
                            "width": "120"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "HSlider",
                          "props": {
                            "value": "{volume}",
                            "minimum": "0",
                            "maximum": "100",
                            "snapInterval": "1",
                            "liveDragging": "true",
                            "width": "300"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "{Math.round(volume)}%",
                            "width": "50"
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
                        "verticalAlign": "middle",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Effect Volume:",
                            "width": "120"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "HSlider",
                          "props": {
                            "value": "75",
                            "minimum": "0",
                            "maximum": "100",
                            "snapInterval": "1",
                            "liveDragging": "true",
                            "width": "300"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "75%",
                            "width": "50"
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
                "title": "Display Settings"
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
                        "verticalAlign": "middle",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Brightness:",
                            "width": "120"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "HSlider",
                          "props": {
                            "value": "{brightness}",
                            "minimum": "0",
                            "maximum": "100",
                            "snapInterval": "5",
                            "liveDragging": "true",
                            "width": "300"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "{Math.round(brightness)}%",
                            "width": "50"
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
                        "verticalAlign": "middle",
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Label",
                          "props": {
                            "text": "Contrast:",
                            "width": "120"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "HSlider",
                          "props": {
                            "value": "50",
                            "minimum": "0",
                            "maximum": "100",
                            "snapInterval": "5",
                            "liveDragging": "true",
                            "width": "300"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "50%",
                            "width": "50"
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
              "type": "HBox",
              "props": {
                "gap": "10"
              },
              "events": {},
              "children": [
                {
                  "type": "Button",
                  "props": {
                    "label": "Apply Settings"
                  },
                  "events": {
                    "click": "trace('Settings applied')"
                  },
                  "children": []
                },
                {
                  "type": "Button",
                  "props": {
                    "label": "Back to Main"
                  },
                  "events": {
                    "click": "switchToDefault()"
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
            "title": "Debug Info"
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
                    "text": "Quantity: {quantity} | Volume: {Math.round(volume)}% | Brightness: {Math.round(brightness)}%",
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

    this.quantity = 5;
    this.volume = 50;
    this.brightness = 75;
    this.comments = "";
    this.username = "";
    this.email = "";
    this.age = 25;
    this.price = 0;
    this.currentView = "default";
    this.isSubmitting = false;
  }

  handleQuantityChange(event) {
    console.log("Quantity changed to: " + this.quantity);
  }

  handleVolumeChange(event) {
    console.log("Volume: " + this.volume + "%");
  }

  handleBrightnessChange(event) {
    console.log("Brightness: " + this.brightness + "%");
  }

  handleCommentsChange(event) {
    console.log("Comments length: " + this.comments.length);
  }

  switchToForm() {
    this.currentState = "formView";
    console.log("Switched to form view");
  }

  switchToSettings() {
    this.currentState = "settingsView";
    console.log("Switched to settings view");
  }

  switchToDefault() {
    this.currentState = "default";
    console.log("Switched to default view");
  }

  validateUsername(event) {
    if (this.event.valid) {
    console.log("Username is valid!");
  }

  validateEmail(event) {
    if (this.event.valid) {
    console.log("Email is valid!");
  }

  validateAge(event) {
    if (this.event.valid) {
    console.log("Age is valid!");
  }

  submitForm() {
    console.log("=== Form Submission ===");
    console.log("Username: " + this.username);
    console.log("Email: " + this.email);
    console.log("Age: " + this.age);
    console.log("Comments: " + this.comments);
    // this.Validate this.all this.fields
    const usernameValid = this.usernameValidator.validate();
    const emailValid = this.emailValidator.validate();
    const ageValid = this.ageValidator.validate();
    if (this.usernameValid.valid && this.emailValid.valid && this.ageValid.valid) {
    Alert.show(
    "Form submitted successfully!\n\nUsername: " + this.username + "\nEmail: " + this.email + "\nAge: " + this.age,
    "Success",
    Alert.OK,
    null,
    null,
    Alert.INFO
    );
  }

  resetForm() {
    this.username = "";
    this.email = "";
    this.age = 18;
    this.comments = "";
    console.log("Form reset");
  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.render(componentTree, document.getElementById('app'));
