import { ReactiveRuntime } from './reactive-runtime.js';

// UI Component Tree
const componentTree = {
  "type": "Application",
  "props": {
    "layout": "vertical"
  },
  "events": {},
  "children": [
    {
      "type": "Panel",
      "props": {
        "title": "Login Form",
        "width": "400",
        "height": "300"
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
              "props": {},
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Username:",
                    "width": "100"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "TextInput",
                  "props": {
                    "id": "txtUsername",
                    "width": "200"
                  },
                  "events": {},
                  "children": []
                }
              ]
            },
            {
              "type": "HBox",
              "props": {},
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "Password:",
                    "width": "100"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "TextInput",
                  "props": {
                    "id": "txtPassword",
                    "width": "200",
                    "displayAsPassword": "true"
                  },
                  "events": {},
                  "children": []
                }
              ]
            },
            {
              "type": "HBox",
              "props": {
                "horizontalAlign": "right"
              },
              "events": {},
              "children": [
                {
                  "type": "Button",
                  "props": {
                    "label": "Cancel"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Button",
                  "props": {
                    "label": "Login"
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

  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.render(componentTree, document.getElementById('app'));
