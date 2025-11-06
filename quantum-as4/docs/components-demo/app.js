import { ReactiveRuntime } from './reactive-runtime.js';

// UI Component Tree
const componentTree = {
  "type": "Application",
  "props": {
    "title": "Component Library Demo"
  },
  "events": {},
  "children": [
    {
      "type": "VBox",
      "props": {
        "padding": "30",
        "gap": "30",
        "width": "100%"
      },
      "events": {},
      "children": [
        {
          "type": "Label",
          "props": {
            "text": "ActionScript 4 Component Library Demo",
            "fontSize": "24",
            "fontWeight": "bold"
          },
          "events": {},
          "children": []
        },
        {
          "type": "Panel",
          "props": {
            "title": "CheckBox Component",
            "width": "600"
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
                  "type": "Label",
                  "props": {
                    "text": "Interactive checkbox with two-way binding:",
                    "fontWeight": "bold"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "CheckBox",
                  "props": {
                    "label": "I agree to the terms and conditions",
                    "selected": "{agreedToTerms}"
                  },
                  "events": {
                    "change": "handleCheckboxChange"
                  },
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Agreed: {agreedToTerms}"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "CheckBox",
                  "props": {
                    "label": "Disabled checkbox",
                    "selected": "false",
                    "enabled": "false"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "CheckBox",
                  "props": {
                    "label": "Label on left",
                    "labelPlacement": "left",
                    "selected": "true"
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
            "title": "ComboBox Component",
            "width": "600"
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
                  "type": "Label",
                  "props": {
                    "text": "Dropdown with data provider and binding:",
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
                      "type": "Label",
                      "props": {
                        "text": "Select Country:"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "ComboBox",
                      "props": {
                        "dataProvider": "{countries}",
                        "selectedIndex": "{selectedCountry}",
                        "prompt": "Choose a country..."
                      },
                      "events": {
                        "change": "handleComboChange"
                      },
                      "children": []
                    }
                  ]
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Selected Index: {selectedCountry}"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Selected Country: {countries[selectedCountry]}"
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
            "title": "DatePicker Component",
            "width": "600"
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
                  "type": "Label",
                  "props": {
                    "text": "Date selection with binding:",
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
                      "type": "Label",
                      "props": {
                        "text": "Select Date:"
                      },
                      "events": {},
                      "children": []
                    },
                    {
                      "type": "DatePicker",
                      "props": {
                        "selectedDate": "{selectedDate}"
                      },
                      "events": {
                        "change": "handleDateChange"
                      },
                      "children": []
                    }
                  ]
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Selected: {selectedDate}"
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
            "title": "Tree Component",
            "width": "600"
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
                  "type": "Label",
                  "props": {
                    "text": "Hierarchical data display:",
                    "fontWeight": "bold"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Tree",
                  "props": {
                    "width": "100%",
                    "height": "200"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Advanced tree implementation available in components/Tree.js",
                    "fontSize": "12",
                    "color": "#999"
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
            "title": "TabNavigator Component",
            "width": "600"
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
                  "type": "Label",
                  "props": {
                    "text": "Tabbed interface:",
                    "fontWeight": "bold"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "TabNavigator",
                  "props": {
                    "width": "100%",
                    "height": "200",
                    "selectedIndex": "{currentTab}"
                  },
                  "events": {
                    "change": "handleTabChange"
                  },
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "Full tabbed navigation available in components/TabNavigator.js",
                    "fontSize": "12",
                    "color": "#999"
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

    this.agreedToTerms = false;
    this.selectedCountry = 0;
    this.countries = ["USA", "Canada", "Mexico", "Brazil", "UK", "France"];
    this.selectedDate = new Date();
    this.currentTab = 0;
  }

  handleCheckboxChange(checked) {
    this.console.log("Checkbox changed to: " + this.checked);
  }

  handleComboChange(item, index) {
    this.console.log("Selected country: " + this.item + " at index " + this.index);
  }

  handleDateChange(date) {
    this.console.log("Selected date: " + this.date.this.toDateString());
  }

  handleTabChange(index) {
    this.console.log("Tab changed to: " + this.index);
  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.render(componentTree, document.getElementById('app'));
