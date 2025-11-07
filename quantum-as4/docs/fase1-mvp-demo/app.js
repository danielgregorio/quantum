import { ReactiveRuntime } from './reactive-runtime.js';

// UI Component Tree
const componentTree = {
  "type": "Application",
  "props": {
    "title": "FASE 1 MVP Demo"
  },
  "events": {},
  "children": [
    {
      "type": "HTTPService",
      "props": {
        "id": "userAPI",
        "url": "https://jsonplaceholder.typicode.com/users",
        "method": "GET",
        "resultFormat": "json",
        "showBusyCursor": "true",
        "result": "handleAPIResult(event)",
        "fault": "handleAPIError(event)"
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
            "title": "FASE 1 MVP Demo - Complete Form System",
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
                    "text": "Testing: Form, FormItem, HTTPService, ProgressBar, Image, Alert",
                    "styleName": "subtitle"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "{statusMessage}"
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
            "gap": "20",
            "width": "100%"
          },
          "events": {},
          "children": [
            {
              "type": "Panel",
              "props": {
                "title": "User Registration",
                "width": "500"
              },
              "events": {},
              "children": [
                {
                  "type": "VBox",
                  "props": {
                    "padding": "20",
                    "gap": "15"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "HBox",
                      "props": {
                        "gap": "15",
                        "horizontalAlign": "center"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "Image",
                          "props": {
                            "source": "{profileImage}",
                            "width": "150",
                            "height": "150",
                            "scaleMode": "zoom",
                            "complete": "trace('Image loaded')",
                            "ioError": "trace('Image failed')"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "VBox",
                          "props": {
                            "gap": "10"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Button",
                              "props": {
                                "label": "Test Image Error"
                              },
                              "events": {
                                "click": "testImageError()"
                              },
                              "children": []
                            },
                            {
                              "type": "Button",
                              "props": {
                                "label": "Reset Image"
                              },
                              "events": {
                                "click": "resetImage()"
                              },
                              "children": []
                            }
                          ]
                        }
                      ]
                    },
                    {
                      "type": "Form",
                      "props": {
                        "width": "100%"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "FormHeading",
                          "props": {
                            "label": "Account Information"
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
                            "label": "Password",
                            "required": "true"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "TextInput",
                              "props": {
                                "text": "{password}",
                                "width": "100%",
                                "displayAsPassword": "true"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "FormItem",
                          "props": {
                            "label": "Country"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "ComboBox",
                              "props": {
                                "dataProvider": "{countries}",
                                "selectedIndex": "-1",
                                "prompt": "Select a country..."
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "FormHeading",
                          "props": {
                            "label": "Terms and Conditions"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "FormItem",
                          "props": {
                            "label": ""
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "CheckBox",
                              "props": {
                                "label": "I accept the terms and conditions",
                                "selected": "{acceptTerms}"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "FormItem",
                          "props": {
                            "label": "Upload Progress",
                            "visible": "{isSubmitting}"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "ProgressBar",
                              "props": {
                                "value": "{uploadProgress}",
                                "maximum": "100",
                                "mode": "determinate",
                                "width": "100%",
                                "height": "24",
                                "labelPlacement": "center"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "FormItem",
                          "props": {
                            "label": ""
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
                                  "type": "Button",
                                  "props": {
                                    "label": "Submit Registration",
                                    "enabled": "{!isSubmitting}"
                                  },
                                  "events": {
                                    "click": "submitForm()"
                                  },
                                  "children": []
                                },
                                {
                                  "type": "Button",
                                  "props": {
                                    "label": "Reset",
                                    "enabled": "{!isSubmitting}"
                                  },
                                  "events": {
                                    "click": "handleSuccess(event)"
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
                }
              ]
            },
            {
              "type": "VBox",
              "props": {
                "gap": "15",
                "width": "350"
              },
              "events": {},
              "children": [
                {
                  "type": "Panel",
                  "props": {
                    "title": "Alert Component Demos",
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
                            "text": "Test different alert types:",
                            "styleName": "subtitle"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "Info Alert",
                            "width": "100%"
                          },
                          "events": {
                            "click": "showInfoAlert()"
                          },
                          "children": []
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "Warning Alert",
                            "width": "100%"
                          },
                          "events": {
                            "click": "showWarningAlert()"
                          },
                          "children": []
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "Error Alert",
                            "width": "100%"
                          },
                          "events": {
                            "click": "showErrorAlert()"
                          },
                          "children": []
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "Yes/No Alert",
                            "width": "100%"
                          },
                          "events": {
                            "click": "showYesNoAlert()"
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
                    "title": "HTTPService Demo",
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
                            "text": "Test REST API integration:",
                            "styleName": "subtitle"
                          },
                          "events": {},
                          "children": []
                        },
                        {
                          "type": "Button",
                          "props": {
                            "label": "Load Users from API",
                            "width": "100%"
                          },
                          "events": {
                            "click": "loadUsers()"
                          },
                          "children": []
                        },
                        {
                          "type": "Label",
                          "props": {
                            "text": "{apiData.length} users loaded",
                            "visible": "{apiData.length > 0}"
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
                    "title": "ProgressBar Demos",
                    "width": "100%"
                  },
                  "events": {},
                  "children": [
                    {
                      "type": "VBox",
                      "props": {
                        "padding": "15",
                        "gap": "15"
                      },
                      "events": {},
                      "children": [
                        {
                          "type": "VBox",
                          "props": {
                            "gap": "5"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Determinate (0%):"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "ProgressBar",
                              "props": {
                                "value": "0",
                                "mode": "determinate",
                                "width": "100%"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "VBox",
                          "props": {
                            "gap": "5"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Determinate (50%):"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "ProgressBar",
                              "props": {
                                "value": "50",
                                "mode": "determinate",
                                "width": "100%"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "VBox",
                          "props": {
                            "gap": "5"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Determinate (100%):"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "ProgressBar",
                              "props": {
                                "value": "100",
                                "mode": "determinate",
                                "width": "100%"
                              },
                              "events": {},
                              "children": []
                            }
                          ]
                        },
                        {
                          "type": "VBox",
                          "props": {
                            "gap": "5"
                          },
                          "events": {},
                          "children": [
                            {
                              "type": "Label",
                              "props": {
                                "text": "Indeterminate (loading):"
                              },
                              "events": {},
                              "children": []
                            },
                            {
                              "type": "ProgressBar",
                              "props": {
                                "mode": "indeterminate",
                                "width": "100%"
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

    this.username = "";
    this.email = "";
    this.password = "";
    this.country = "";
    this.countries = ["USA", "Brazil", "Canada", "Mexico", "UK"];
    this.acceptTerms = false;
    this.uploadProgress = 0;
    this.isSubmitting = false;
    this.apiData = [];
    this.profileImage = "https://via.placeholder.com/150/3498db/ffffff?text=User";
    this.statusMessage = "Ready to submit";
    this.interval = setInterval(function():void {
                uploadProgress += 10;
  }

  submitForm() {
    // Validation
    if (!this.username || this.username.length < 3) {
    Alert.show("Username must be at least 3 characters", "Validation Error", Alert.OK, null, null, Alert.WARNING);
    return;
    }
    if (!this.email || this.email.indexOf("@") === -1) {
    Alert.show("Please enter a valid email address", "Validation Error", Alert.OK, null, null, Alert.WARNING);
    return;
    }
    if (!this.password || this.password.length < 6) {
    Alert.show("Password must be at least 6 characters", "Validation Error", Alert.OK, null, null, Alert.WARNING);
    return;
    }
    if (!this.acceptTerms) {
    Alert.show("You must accept the terms and conditions", "Terms Required", Alert.OK, null, null, Alert.ERROR);
    return;
    }
    // Confirm submission
    Alert.show(
    "Are you sure you want to create this account?\n\nUsername: " + this.username + "\nEmail: " + this.email,
    "Confirm Registration",
    Alert.YES | Alert.NO,
    null,
    this.handleConfirm,
    Alert.QUESTION
    );
  }

  handleConfirm(event) {
    if (this.event.detail === Alert.YES) {
    // Simulate form submission with progress
    this.isSubmitting = true;
    this.statusMessage = "Submitting...";
    this.uploadProgress = 0;
    this.simulateUpload();
    }
  }

  simulateUpload() {
    // Simulate progress
    var interval = this.setInterval(function():void {
    this.uploadProgress += 10;
    if (this.uploadProgress >= 100) {
    this.clearInterval(this.interval);
    this.isSubmitting = false;
    this.statusMessage = "Registration successful!";
    Alert.show(
    "Your account has been created successfully!\n\nWelcome, " + this.username + "!",
    "Success",
    Alert.OK,
    null,
    this.handleSuccess,
    Alert.INFO
    );
    }
    }, 200);
  }

  handleSuccess(event) {
    // Reset form
    this.username = "";
    this.email = "";
    this.password = "";
    this.country = "";
    this.acceptTerms = false;
    this.uploadProgress = 0;
    this.statusMessage = "Ready to submit";
  }

  loadUsers() {
    this.statusMessage = "Loading users from API...";
    this.userAPI.send();
  }

  handleAPIResult(event) {
    this.apiData = this.event.result;
    this.statusMessage = "Loaded " + this.apiData.length + " users from API";
    Alert.show(
    "Successfully loaded " + this.apiData.length + " users from JSONPlaceholder API!",
    "API Success",
    Alert.OK,
    null,
    null,
    Alert.INFO
    );
  }

  handleAPIError(event) {
    this.statusMessage = "API Error: " + this.event.message;
    Alert.show(
    "Failed to load data from API:\n\n" + this.event.fault.faultString,
    "API Error",
    Alert.OK,
    null,
    null,
    Alert.ERROR
    );
  }

  testImageError() {
    this.profileImage = "https://invalid-url-that-does-not-exist.com/image.jpg";
  }

  resetImage() {
    this.profileImage = "https://via.placeholder.com/150/3498db/ffffff?text=User";
  }

  showInfoAlert() {
    Alert.show(
    "This is an informational message demonstrating the Alert component.",
    "Information",
    Alert.OK,
    null,
    null,
    Alert.INFO
    );
  }

  showWarningAlert() {
    Alert.show(
    "This is a warning message! Be careful.",
    "Warning",
    Alert.OK,
    null,
    null,
    Alert.WARNING
    );
  }

  showErrorAlert() {
    Alert.show(
    "This is an error message! Something went wrong.",
    "Error",
    Alert.OK,
    null,
    null,
    Alert.ERROR
    );
  }

  showYesNoAlert() {
    Alert.show(
    "Do you want to proceed with this action?",
    "Confirm Action",
    Alert.YES | Alert.NO,
    null,
    function(e):void {
    Alert.show(
    "You clicked: " + (this.e.detail === Alert.YES ? "YES" : "NO"),
    "Result",
    Alert.OK
    );
    },
    Alert.QUESTION
    );
  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.render(componentTree, document.getElementById('app'));
